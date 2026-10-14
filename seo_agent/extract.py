"""Extração total e determinística das fontes já preservadas no histórico."""

from datetime import datetime, UTC
from uuid import uuid4


NO_SOURCES_MESSAGE = ('Nenhuma URL coletada no histórico deste projeto; '
                      'execute a busca (comando run) antes de extrair.')


def extract_source(url, source):
    page = source.get('page')
    extraction = {'url': url, 'source_id': source.get('id'), 'retrieved_at': source.get('retrieved_at'),
                  'failures': []}
    if not isinstance(page, dict) or not page:
        extraction['failures'].append({
            'stage': 'page',
            'error': 'Página preservada ausente ou ilegível no histórico desta fonte.',
        })
        return extraction
    extraction['page'] = page
    for error in page.get('structured_data_errors') or []:
        extraction['failures'].append({'stage': 'structured_data', 'error': error})
    return extraction


def extract_project(project_id, runs, store):
    """Extrai cada URL coletada sem LLM e sem rede, registrando a execução.

    A extração reaproveita o conteúdo preservado pelas execuções de busca; para
    URLs repetidas vale a página preservada mais recente. A ausência de um sinal
    (por exemplo, sem autor) não é falha; falha é a página preservada não ser legível.
    """
    pages = {}
    for run in runs:
        for source in (run.get('result') or {}).get('sources', []):
            if isinstance(source, dict) and isinstance(source.get('url'), str) and source['url']:
                pages[source['url']] = source
    if not pages:
        return {'project_id': project_id, 'status': 'no_sources', 'message': NO_SOURCES_MESSAGE}
    extractions = [extract_source(url, pages[url]) for url in sorted(pages)]
    status = 'partial' if any(item['failures'] for item in extractions) else 'extracted'
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(), 'status': status,
              'result': {'extractions': extractions}}
    from seo_agent.store import save_run
    save_run(record, store)
    return record
