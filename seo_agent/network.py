"""Rede de conhecimento das extrações, consultável offline com fonte por fato."""

from datetime import datetime, UTC
from uuid import uuid4


NO_EXTRACTION_MESSAGE = ('Nenhuma extração registrada no histórico deste projeto; '
                         'execute o comando extract antes de construir a rede.')
NO_NETWORK_MESSAGE = ('Nenhuma rede registrada no histórico deste projeto; '
                      'execute o comando network build antes de consultar.')


def latest_extraction(runs):
    for run in reversed(runs):
        extractions = (run.get('result') or {}).get('extractions')
        if extractions is not None:
            return extractions
    return None


def build_network(project_id, runs, store):
    """Deriva a rede da extração registrada mais recente, sem LLM e sem rede.

    Páginas legíveis viram entidades e relações (links entre páginas do corpus e
    termos dos headings) com a URL-fonte em cada fato; URL com falha de extração
    fica fora da rede, com a falha registrada, sem derrubar as demais.
    """
    extractions = latest_extraction(runs)
    if extractions is None:
        raise ValueError(NO_EXTRACTION_MESSAGE)
    valid = [extraction for extraction in extractions if not extraction.get('failures')]
    excluded = sorted(({'url': extraction['url'], 'failures': extraction['failures']}
                       for extraction in extractions if extraction.get('failures')),
                      key=lambda item: item['url'])
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
            term = ' '.join((heading.get('text') or '').split()).lower()
            if not term:
                continue
            terms.setdefault(term, set()).add(url)
            relate({'type': 'has_term', 'from': url, 'to': term, 'sources': [url]})
        for link in page.get('links') or []:
            target = link.get('url')
            if target in pages and target != url:
                relate({'type': 'links_to', 'from': url, 'to': target, 'sources': [url]})
    entities.extend({'type': 'term', 'id': term, 'sources': sorted(urls)}
                    for term, urls in sorted(terms.items()))
    relations = sorted(relations, key=lambda relation: (relation['type'], relation['from'], relation['to']))
    status = 'built' if pages else 'empty'
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(), 'status': status,
              'result': {'network': {'entities': entities, 'relations': relations},
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
    das páginas; o tamanho acompanha a estrutura da rede, não o corpus bruto.
    """
    pages = [entity for entity in network['entities'] if entity['type'] == 'page']
    terms = [entity for entity in network['entities'] if entity['type'] == 'term']
    links = [relation for relation in network['relations'] if relation['type'] == 'links_to']
    term_relations = [relation for relation in network['relations'] if relation['type'] == 'has_term']
    top_terms = sorted(({'term': entity['id'], 'pages': len(entity['sources']),
                         'sources': entity['sources']} for entity in terms),
                       key=lambda item: (-item['pages'], item['term']))
    return {
        'counts': {'pages': len(pages), 'terms': len(terms),
                   'page_links': len(links), 'term_relations': len(term_relations)},
        'top_terms': top_terms,
        'page_links': [{'from': relation['from'], 'to': relation['to'],
                        'sources': relation['sources']} for relation in links],
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
