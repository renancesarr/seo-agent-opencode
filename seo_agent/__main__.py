"""Interface de projetos, busca e inspeção do agente SEO."""

import argparse
from contextlib import closing
from datetime import datetime, UTC
import json
from pathlib import Path
import re
import sqlite3
import sys
from uuid import uuid4


TEXT_FIELDS = ('id', 'business_context', 'audience', 'language', 'geography', 'content_goal')
LIST_FIELDS = ('keywords', 'domains', 'competitors', 'sources')


def validate_identifier(identifier):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', identifier):
        raise ValueError("Campo 'id': use letras minúsculas sem acentos, números e hífens entre palavras.")


def validate_project(project):
    if not isinstance(project, dict):
        raise ValueError('A configuração deve ser um objeto JSON.')
    unknown = project.keys() - set(TEXT_FIELDS + LIST_FIELDS)
    if unknown:
        raise ValueError(f'Campos desconhecidos: {", ".join(sorted(unknown))}. Confira a configuração.')
    for field in TEXT_FIELDS:
        if not isinstance(project.get(field), str) or not project[field].strip():
            raise ValueError(f"Campo '{field}': informe um texto não vazio.")
    validate_identifier(project['id'])
    for field in LIST_FIELDS:
        if field != 'keywords' and field not in project:
            continue
        values = project.get(field)
        if not isinstance(values, list) or (field == 'keywords' and not values):
            raise ValueError(f"Campo '{field}': informe uma lista de textos; keywords exige ao menos um item.")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"Campo '{field}': cada item deve ser um texto não vazio.")
    return project


def prepare_run(project, store, *, status='prepared', result=None):
    record = {
        'run_id': str(uuid4()),
        'project_id': project['id'],
        'created_at': datetime.now(UTC).isoformat(),
        'project': project,
        'status': status,
        'result': result,
    }
    if result and result.get('outline'):
        result['outline'].setdefault('created_run_id', record['run_id'])
    if result is not None:
        from seo_agent.monitoring import add_notices

        def before_insert(database):
            previous = [json.loads(row[0]) for row in database.execute(
                'SELECT record FROM runs WHERE project_id=? ORDER BY rowid', (project['id'],))]
            add_notices(record, previous)
    else:
        before_insert = None
    from seo_agent.store import save_run
    save_run(record, store, before_insert=before_insert)
    return record


def history(project_id, store):
    validate_identifier(project_id)
    if not store.exists():
        return {'project_id': project_id, 'runs': []}
    with closing(sqlite3.connect(store)) as database:
        if not database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runs'").fetchone():
            return {'project_id': project_id, 'runs': []}
        rows = database.execute(
            'SELECT record FROM runs WHERE project_id = ? ORDER BY rowid', (project_id,)
        ).fetchall()
    return {'project_id': project_id, 'runs': [json.loads(row[0]) for row in rows]}


def execute_project(args, project, providers, fetch, wait, generate):
    from seo_agent.workflow import collect_project
    from seo_agent.outlines import create_outline, get_outline
    from seo_agent.monitoring import compare_evidence
    from seo_agent.scheduler import project_lock
    with project_lock(args.store, project['id']):
        status, collected = collect_project(project, providers, fetch=fetch, max_pages=args.max_pages,
                                            max_queries=args.max_queries, interval_seconds=args.interval_seconds, wait=wait)
        if args.proposal_file:
            def generate(project, evidence):
                return json.loads(args.proposal_file.read_text(encoding='utf-8'))
        runs = history(project['id'], args.store)['runs']
        latest = next(((run.get('result') or {}).get('outline') for run in reversed(runs)
                       if (run.get('result') or {}).get('outline')), None)
        request = None
        if latest:
            reviewed = get_outline(project['id'], latest['version_id'], args.store, runs)
            if reviewed['outline']['review_status'] == 'request-changes':
                request = reviewed['reviews'][-1]
        if compare_evidence(project, collected, runs, request):
            create_outline(project, collected, generate)
        if collected['errors'] and collected['sources']:
            status = 'partial'
        return prepare_run(project, args.store, status=status, result=collected)


def main(argv=None, *, providers=None, fetch=None, wait=None, generate=None, model_runner=None, environment=None,
         clock=None, worker=None):
    parser = argparse.ArgumentParser(description='Projetos, busca web e inspeção SEO.')
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate', help='Validar configuração do projeto.')
    validate.add_argument('--project', type=Path, required=True)
    prepare = commands.add_parser('prepare', help='Registrar uma execução preparada, sem pesquisar.')
    prepare.add_argument('--project', type=Path, required=True)
    prepare.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
    run = commands.add_parser('run', help='Executar descoberta/leitura de um projeto e preservar evidências.')
    run.add_argument('--project', type=Path, required=True)
    run.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
    run.add_argument('--env-file', type=Path, default=Path('.env'))
    run.add_argument('--no-searxng', action='store_true')
    run.add_argument('--endpoint', default='http://127.0.0.1:8080')
    run.add_argument('--max-pages', type=int, default=10)
    run.add_argument('--max-queries', type=int, default=10)
    run.add_argument('--interval-seconds', type=int, default=300)
    generation = run.add_mutually_exclusive_group()
    generation.add_argument('--proposal-file', type=Path, help='Proposta JSON controlada; não executa modelo.')
    generation.add_argument('--model', help='Gerar pelo OpenCode usando provedor/modelo.')
    for name in ('outline', 'review'):
        command = commands.add_parser(name, help='Consultar/revisar uma versão exata do outline.')
        command.add_argument('--project-id', required=True)
        command.add_argument('--version-id', required=True)
        command.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
        if name == 'review':
            command.add_argument('--decision', choices=['approve', 'request-changes'], required=True)
            command.add_argument('--reason', default='')
    listing = commands.add_parser('history', help='Consultar execuções de um projeto.')
    listing.add_argument('--project-id', required=True)
    listing.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
    notices = commands.add_parser('notices', help='Consultar avisos locais sem repetir fatos inalterados.')
    notices.add_argument('--project-id', required=True)
    notices.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
    extraction = commands.add_parser('extract', help='Extrair de forma determinística as URLs já coletadas.')
    extraction.add_argument('--project-id', required=True)
    extraction.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
    browser_experiment = commands.add_parser('browser-experiment', help='Comparar Quick Actions remotas em fixtures explícitas.')
    browser_experiment.add_argument('--fixtures', type=Path, required=True)
    browser_experiment.add_argument('--output', type=Path, required=True)
    browser_experiment.add_argument('--env-file', type=Path, default=Path('.env'))
    for name in ('schedule-tick', 'monitor'):
        scheduled = commands.add_parser(name, help='Executar horário devido; monitor repete até Ctrl-C.')
        scheduled.add_argument('--config', type=Path, required=True)
    search = commands.add_parser('search', help='Buscar páginas pela API JSON do SearXNG.')
    search.add_argument('--query', required=True)
    search.add_argument('--endpoint', default='http://127.0.0.1:8080')
    search.add_argument('--language', default='pt-BR')
    search.add_argument('--limit', type=int, default=5)
    batch = commands.add_parser('search-batch', help='Pesquisar consultas em sequência e coletar páginas HTTP 200.')
    batch.add_argument('--queries-file', type=Path, required=True,
                       help='Arquivo JSON contendo uma lista de consultas.')
    batch.add_argument('--output', type=Path, required=True)
    batch.add_argument('--endpoint', default='http://127.0.0.1:8080')
    batch.add_argument('--language', default='pt-BR')
    batch.add_argument('--interval-seconds', type=int, default=300)
    batch.add_argument('--env-file', type=Path, default=Path('.env'), help='Credenciais locais; ambiente exportado tem prioridade.')
    batch.add_argument('--no-searxng', action='store_true', help='Usar somente APIs configuradas.')
    inspect = commands.add_parser('inspect', help='Ler conteúdo e sinais SEO de uma URL pública.')
    inspect.add_argument('--url', required=True)
    crawl = commands.add_parser('crawl', help='Buscar, percorrer páginas públicas e comparar viewports.')
    crawl.add_argument('--query', required=True)
    crawl.add_argument('--endpoint', default='http://127.0.0.1:8080')
    crawl.add_argument('--language', default='pt-BR')
    crawl.add_argument('--limit', type=int, default=5)
    crawl.add_argument('--max-pages', type=int, default=6)
    crawl.add_argument('--evidence-dir', type=Path, default=Path('data/browser-evidence'))
    args = parser.parse_args(argv)
    try:
        if args.command in {'schedule-tick', 'monitor'}:
            from seo_agent.scheduler import schedule_tick
            from time import sleep
            if args.command == 'monitor':
                try:
                    while True:
                        schedule_tick(args.config, clock=clock, worker=worker)
                        (wait or sleep)(60)
                except KeyboardInterrupt:
                    result = {'status': 'stopped'}
            else:
                result = schedule_tick(args.config, clock=clock, worker=worker)
        elif args.command == 'browser-experiment':
            from seo_agent.browser_experiment import experiment
            from seo_agent.search_providers import load_environment
            result = experiment(json.loads(args.fixtures.read_text(encoding='utf-8')), args.output,
                                environment if environment is not None else load_environment(args.env_file), fetch=fetch)
        elif args.command == 'run':
            from seo_agent.search_providers import configured_providers, SearchProvider
            from seo_agent.web import search_web
            project = validate_project(json.loads(args.project.read_text(encoding='utf-8')))
            if args.model:
                from seo_agent.opencode import OpenCodeGenerator
                generate = OpenCodeGenerator(args.model, runner=model_runner)
            if providers is None:
                providers = configured_providers(environment, env_file=args.env_file, fetch=fetch)
                if not args.no_searxng:
                    def searxng(query):
                        discovery = search_web(query, endpoint=args.endpoint, language=project['language'],
                                               limit=20, fetch=fetch)
                        return {'results': [{'url': item['url'], 'title': item['title'],
                                 'buscador': item['engines'] or ['searxng']} for item in discovery['results']],
                                'partial_failure': bool(discovery['unresponsive_engines'])}
                    providers.insert(0, SearchProvider('searxng', searxng))
            if not providers and not project.get('sources') and not project.get('competitors'):
                raise ValueError('Nenhum provedor ou fonte indicada disponível para o projeto.')
            result = execute_project(args, project, providers, fetch, wait, generate)
        elif args.command in {'outline', 'review'}:
            from seo_agent.outlines import get_outline, review_outline
            runs = history(args.project_id, args.store)['runs']
            if args.command == 'outline':
                result = get_outline(args.project_id, args.version_id, args.store, runs)
            else:
                result = review_outline(args.project_id, args.version_id, args.decision, args.reason, args.store, runs)
        elif args.command == 'notices':
            result = {'project_id': args.project_id, 'notices': [notice
                      for run in history(args.project_id, args.store)['runs']
                      for notice in (run.get('result') or {}).get('notices', [])]}
        elif args.command == 'extract':
            from seo_agent.extract import extract_project
            result = extract_project(args.project_id, history(args.project_id, args.store)['runs'], args.store)
        elif args.command == 'search':
            from seo_agent.web import search_web
            result = search_web(args.query, endpoint=args.endpoint, language=args.language, limit=args.limit)
        elif args.command == 'search-batch':
            from seo_agent.search_batch import run_queries
            from seo_agent.search_providers import configured_providers, SearchProvider
            from seo_agent.web import search_web
            queries = json.loads(args.queries_file.read_text(encoding='utf-8'))
            if (not isinstance(queries, list) or not queries
                    or any(not isinstance(query, str) or not query.strip() for query in queries)):
                raise ValueError('O arquivo de consultas deve conter uma lista não vazia de textos.')
            def searxng(query):
                result = search_web(query, endpoint=args.endpoint, language=args.language, limit=20)
                return [{'title': item['title'], 'url': item['url'],
                         'buscador': item['engines'] or ['searxng']}
                        for item in result['results']]
            providers = configured_providers(env_file=args.env_file)
            if not args.no_searxng:
                providers.insert(0, SearchProvider('searxng', searxng))
            if not providers:
                raise ValueError('Nenhum provedor configurado: preencha as credenciais ou habilite SearXNG.')
            errors = []
            def report_error(error):
                errors.append(error)
                print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
            result = run_queries(queries, providers, interval_seconds=args.interval_seconds, on_error=report_error)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            error_file = args.output.with_name(args.output.name + '.errors.json')
            error_file.write_text(json.dumps(errors, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if errors and not result:
                raise ValueError('O lote não obteve páginas HTTP 200 e houve falhas de busca; confira o arquivo .errors.json.')
        elif args.command == 'inspect':
            from seo_agent.web import inspect_page
            result = inspect_page(args.url)
        elif args.command == 'crawl':
            from seo_agent.web import crawl_web
            result = crawl_web(args.query, endpoint=args.endpoint, language=args.language,
                               limit=args.limit, max_pages=args.max_pages,
                               evidence_dir=args.evidence_dir)
        elif args.command == 'history':
            result = history(args.project_id, args.store)
        else:
            project = validate_project(json.loads(args.project.read_text(encoding='utf-8')))
            result = {'project': project} if args.command == 'validate' else prepare_run(project, args.store)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
