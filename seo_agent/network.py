"""Rede de conhecimento das extrações, consultável offline com fonte por fato."""

from urllib.parse import urldefrag

from datetime import datetime, UTC
from uuid import uuid4


NO_NETWORK_MESSAGE = ('Nenhuma rede registrada no histórico deste projeto; '
                      'execute o comando network build antes de consultar.')

COMPACT_TERMS_LIMIT = 20
COMPACT_LINKS_LIMIT = 20


def _page_target(url):
    """Destino de um link sem o fragmento: `pagina#secao` aponta à página."""
    return urldefrag(url or '')[0]


def normalize_term(heading):
    """Critério único de termo/tema: texto do heading normalizado em minúsculas."""
    return ' '.join((heading.get('text') or '').split()).lower()


def build_network(project_id, runs, store):
    """Deriva a rede da extração registrada mais recente, sem LLM e sem rede.

    Páginas legíveis viram entidades e relações (links entre páginas do corpus e
    termos dos headings) com a URL-fonte em cada fato; URL com falha de extração
    fica fora da rede, com a falha registrada, sem derrubar as demais.
    """
    from seo_agent.extract import extraction_inputs
    extraction_run, valid, excluded = extraction_inputs(runs, purpose='construir a rede')
    pages = {extraction['url']: extraction for extraction in valid}
    entities = [{'type': 'page', 'id': url, 'source_id': extraction.get('source_id'),
                 'retrieved_at': extraction.get('retrieved_at'), 'sources': [url]}
                for url, extraction in sorted(pages.items())]
    terms = {}
    relations = []
    seen_relations = set()

    def relate(relation):
        key = (relation['type'], relation['from'], relation['to'])
        if key not in seen_relations:
            seen_relations.add(key)
            relations.append(relation)

    for url, extraction in sorted(pages.items()):
        page = extraction.get('page') or {}
        for heading in page.get('headings') or []:
            term = normalize_term(heading)
            if not term:
                continue
            terms.setdefault(term, set()).add(url)
            relate({'type': 'has_term', 'from': url, 'to': term, 'sources': [url]})
        for link in page.get('links') or []:
            target = _page_target(link.get('url'))
            if target in pages and target != url:
                relate({'type': 'links_to', 'from': url, 'to': target, 'sources': [url]})
    entities.extend({'type': 'term', 'id': term, 'sources': sorted(urls)}
                    for term, urls in sorted(terms.items()))
    relations = sorted(relations, key=lambda relation: (relation['type'], relation['from'], relation['to']))
    status = 'built' if pages else 'empty'
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(), 'status': status,
              'result': {'extraction_run_id': extraction_run['run_id'],
                         'network': {'entities': entities, 'relations': relations},
                         'excluded': excluded}}
    from seo_agent.store import save_run
    save_run(record, store)
    return record


def latest_network(runs):
    for run in reversed(runs):
        if (run.get('result') or {}).get('network') is not None:
            return run
    return None


def compact_network(network):
    """Resume a rede em contagens e principais termos/relações, com fontes.

    Destinada a reduzir tokens: contém apenas fatos agregados, nunca o texto
    das páginas. Contagens cobrem a rede inteira; as listas trazem apenas os
    N líderes (mais páginas por termo, primeiros links na ordem alfabética
    determinística), mantendo o resumo limitado em corpora grandes.
    """
    pages = [entity for entity in network['entities'] if entity['type'] == 'page']
    terms = [entity for entity in network['entities'] if entity['type'] == 'term']
    links = [relation for relation in network['relations'] if relation['type'] == 'links_to']
    term_relations = [relation for relation in network['relations'] if relation['type'] == 'has_term']
    top_terms = sorted(({'term': entity['id'], 'pages': len(entity['sources']),
                         'sources': entity['sources']} for entity in terms),
                       key=lambda item: (-item['pages'], item['term']))[:COMPACT_TERMS_LIMIT]
    leading_links = sorted(({'from': relation['from'], 'to': relation['to'],
                             'sources': relation['sources']} for relation in links),
                           key=lambda item: (item['from'], item['to']))[:COMPACT_LINKS_LIMIT]
    return {
        'counts': {'pages': len(pages), 'terms': len(terms),
                   'page_links': len(links), 'term_relations': len(term_relations)},
        'top_terms': top_terms,
        'page_links': leading_links,
    }


def query_network(project_id, runs, *, compact=False):
    """Devolve a rede registrada, sem derivar nada novamente."""
    record = latest_network(runs)
    if record is None:
        raise ValueError(NO_NETWORK_MESSAGE)
    if compact:
        return {key: value for key, value in record.items() if key != 'result'} | {
            'compact': compact_network(record['result']['network'])}
    return record
