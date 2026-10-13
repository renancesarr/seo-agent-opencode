"""Comparação conservadora de evidências e avisos locais por projeto."""

import hashlib
import json


def compare_evidence(project, result, runs):
    previous_run = next((run for run in reversed(runs)
                     if (run.get('result') or {}).get('outline')), None)
    previous = previous_run['result'] if previous_run else None
    def signatures(collection):
        return {source['url']: {field: source['page'].get(field) for field in
                               ('title', 'description', 'text', 'headings', 'structured_data')}
                for source in collection.get('sources', [])}
    before, after = signatures(previous or {}), signatures(result)
    comparison = {'added': sorted(after.keys() - before.keys()),
                  'changed': sorted(url for url in after.keys() & before.keys() if after[url] != before[url]),
                  'unavailable': sorted(before.keys() - after.keys()),
                  'project_changed': bool(previous_run and previous_run['project'] != project),
                  'basis': 'Conteúdo textual, título, descrição, headings e JSON-LD; mudanças requerem revisão humana.'}
    result['comparison'] = comparison
    if previous and not comparison['added'] and not comparison['changed'] and not comparison['project_changed']:
        result['outline'] = previous['outline']
        if comparison['unavailable']:
            result['pending'].append('Fontes anteriores indisponíveis; manter versão válida e investigar coleta.')
        return False
    return True


def add_notices(record, runs):
    result = record['result']
    if result is None:
        return
    known = {notice['key'] for run in runs for notice in (run.get('result') or {}).get('notices', [])}
    notices = []
    def notice(kind, detail, version_id=None):
        key = hashlib.sha256(json.dumps([kind, detail], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if key not in known:
            notices.append({'key': key, 'kind': kind, 'detail': detail, 'run_id': record['run_id'],
                            'version_id': version_id, 'created_at': record['created_at']})
            known.add(key)
    outline = result.get('outline')
    if outline:
        notice('outline', {'version_id': outline['version_id'], 'message': 'Versão disponível para revisão.'}, outline['version_id'])
    for error in result.get('errors', []):
        notice('failure', error, outline['version_id'] if outline else None)
    result['notices'] = notices
