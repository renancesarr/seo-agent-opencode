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


def prepare_run(project, store):
    record = {
        'run_id': str(uuid4()),
        'project_id': project['id'],
        'created_at': datetime.now(UTC).isoformat(),
        'project': project,
        'status': 'prepared',
        'result': None,
    }
    store.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(store)) as database, database:
        database.execute(
            'CREATE TABLE IF NOT EXISTS runs '
            '(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, record TEXT NOT NULL)'
        )
        database.execute(
            'INSERT INTO runs (id, project_id, record) VALUES (?, ?, ?)',
            (record['run_id'], project['id'], json.dumps(record, ensure_ascii=False)),
        )
    return record


def history(project_id, store):
    validate_identifier(project_id)
    if not store.exists():
        return {'project_id': project_id, 'runs': []}
    with closing(sqlite3.connect(store)) as database:
        rows = database.execute(
            'SELECT record FROM runs WHERE project_id = ? ORDER BY rowid', (project_id,)
        ).fetchall()
    return {'project_id': project_id, 'runs': [json.loads(row[0]) for row in rows]}


def main():
    parser = argparse.ArgumentParser(description='Projetos, busca web e inspeção SEO.')
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate', help='Validar configuração do projeto.')
    validate.add_argument('--project', type=Path, required=True)
    prepare = commands.add_parser('prepare', help='Registrar uma execução preparada, sem pesquisar.')
    prepare.add_argument('--project', type=Path, required=True)
    prepare.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
    listing = commands.add_parser('history', help='Consultar execuções de um projeto.')
    listing.add_argument('--project-id', required=True)
    listing.add_argument('--store', type=Path, default=Path('data/seo-agent.sqlite3'))
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
    args = parser.parse_args()
    try:
        if args.command == 'search':
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
