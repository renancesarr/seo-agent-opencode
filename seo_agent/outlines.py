"""Contrato editorial e decisões persistentes sobre versões exatas."""

from contextlib import closing
from datetime import datetime, UTC
import json
import sqlite3
from uuid import uuid4


def validate_proposal(proposal, sources):
    if isinstance(proposal, str):
        proposal = json.loads(proposal)
    if not isinstance(proposal, dict):
        raise ValueError('Proposta deve ser um objeto JSON.')
    def text(item, field):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError(f'Proposta exige {field} não vazio.')
    for field in ('title', 'audience', 'search_intent'):
        text(proposal, field)
    allowed = {source['url'] for source in sources}
    if not allowed:
        raise ValueError('Nenhuma fonte disponível para fundamentar a proposta.')
    for field in ('sections', 'opportunities', 'pending'):
        if not isinstance(proposal.get(field), list):
            raise ValueError(f'Proposta exige lista {field}.')
    if not proposal['sections']:
        raise ValueError('Proposta exige ao menos uma seção.')
    for item in proposal['sections'] + proposal['opportunities']:
        if not isinstance(item, dict):
            raise ValueError('Seções e oportunidades devem ser objetos.')
        refs = item.get('references')
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in allowed for ref in refs):
            raise ValueError('Referência não corresponde às fontes lidas nesta execução.')
    for item in proposal['sections']:
        text(item, 'heading')
        text(item, 'content')
        if not item['references']:
            raise ValueError('Seção exige fonte lida.')
    for item in proposal['opportunities']:
        text(item, 'description')
        text(item, 'justification')
        if item.get('kind') not in {'observation', 'hypothesis'}:
            raise ValueError('Oportunidade deve identificar observation ou hypothesis.')
        if item['kind'] == 'observation' and not item['references']:
            raise ValueError('Observação exige fonte lida.')
    if any(not isinstance(item, str) or not item.strip() for item in proposal['pending']):
        raise ValueError('Pendências devem ser textos não vazios.')
    return json.loads(json.dumps(proposal, ensure_ascii=False, allow_nan=False))


def create_outline(project, result, generate):
    if not result['sources'] or generate is None:
        return
    try:
        proposal = validate_proposal(generate(project, result), result['sources'])
    except (OSError, ValueError, TypeError):
        if result.get('generator', {}).get('status') == 'started':
            result['generator']['status'] = 'invalid_proposal'
        result['errors'].append({'stage': 'generation', 'error': 'Proposta inválida ou gerador indisponível; conferir estrutura e fontes.'})
        result['pending'].append('Geração falhou; a última versão válida permanece no histórico.')
        return
    result['outline'] = {'version_id': str(uuid4()), 'review_status': 'pending', 'proposal': proposal}
    if result.get('generator'):
        result['generator']['status'] = 'validated'


def get_outline(project_id, version_id, store, runs):
    for run in runs:
        outline = (run.get('result') or {}).get('outline')
        if outline and outline['version_id'] == version_id:
            break
    else:
        raise ValueError('Projeto/versão de outline inexistente.')
    reviews = []
    with closing(sqlite3.connect(store)) as database:
        if database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'").fetchone():
            reviews = [json.loads(row[0]) for row in database.execute(
                'SELECT record FROM reviews WHERE project_id=? AND version_id=? ORDER BY rowid',
                (project_id, version_id))]
    return {'project_id': project_id, 'run_id': run['run_id'],
            'outline': outline | {'review_status': reviews[-1]['decision'] if reviews else 'pending'},
            'reviews': reviews}


def review_outline(project_id, version_id, decision, reason, store, runs):
    get_outline(project_id, version_id, store, runs)
    if decision == 'request-changes' and not reason.strip():
        raise ValueError('Pedido de ajustes exige justificativa.')
    record = {'project_id': project_id, 'version_id': version_id, 'decision': decision,
              'reason': reason, 'created_at': datetime.now(UTC).isoformat()}
    with closing(sqlite3.connect(store)) as database, database:
        database.execute('CREATE TABLE IF NOT EXISTS reviews '
                         '(project_id TEXT NOT NULL, version_id TEXT NOT NULL, record TEXT NOT NULL)')
        database.execute('INSERT INTO reviews VALUES (?, ?, ?)',
                         (project_id, version_id, json.dumps(record, ensure_ascii=False)))
    return record
