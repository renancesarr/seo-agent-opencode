"""Interface de projetos, busca e inspeção do agente SEO."""

import argparse
from contextlib import closing
from datetime import datetime, UTC
import json
from pathlib import Path
import re
import sqlite3
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
    inspect = commands.add_parser('inspect', help='Ler conteúdo e sinais SEO de uma URL pública.')
    inspect.add_argument('--url', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'search':
            from seo_agent.web import search_web
            result = search_web(args.query, endpoint=args.endpoint, language=args.language, limit=args.limit)
        elif args.command == 'inspect':
            from seo_agent.web import inspect_page
            result = inspect_page(args.url)
        elif args.command == 'history':
            result = history(args.project_id, args.store)
        else:
            project = validate_project(json.loads(args.project.read_text(encoding='utf-8')))
            result = {'project': project} if args.command == 'validate' else prepare_run(project, args.store)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
