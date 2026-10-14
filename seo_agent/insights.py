"""Insights por LLM sobre a rede compacta do corpus, nunca páginas cruas."""

from datetime import datetime, UTC
from uuid import uuid4


NO_NETWORK_MESSAGE = ('Nenhuma rede registrada no histórico deste projeto; '
                      'execute o comando network build antes de gerar insights.')
EMPTY_NETWORK_MESSAGE = ('A rede registrada não tem páginas; colete fontes legíveis (comando run), '
                         'extraia (extract) e reconstrua a rede (network build) antes de gerar insights.')
NO_GENERATOR_MESSAGE = ('Nenhum gerador de insights configurado; a rede compacta e as análises '
                        'disponíveis foram entregues e os insights não foram gerados.')


def insights_inputs(runs):
    """Guarda de entrada: exige rede construída sobre fontes válidas.

    Sem URLs coletadas aponta a busca (`run`); sem extração aponta `extract`
    (guarda comum); sem rede aponta `network build`; rede sem páginas manda
    reconstruir o corpus — insight ancorado não existe sem páginas.
    """
    from seo_agent.extract import extraction_inputs
    extraction_inputs(runs, purpose='gerar insights')
    from seo_agent.network import latest_network
    network_run = latest_network(runs)
    if network_run is None:
        raise ValueError(NO_NETWORK_MESSAGE)
    network = network_run['result']['network']
    if not any(entity['type'] == 'page' for entity in network['entities']):
        raise ValueError(EMPTY_NETWORK_MESSAGE)
    return network_run


def _latest_analysis(runs, marker, extraction_run_id):
    """Última execução da análise identificada por `marker`, na mesma extração da rede."""
    for run in reversed(runs):
        result = run.get('result') or {}
        if marker in result and result.get('extraction_run_id') == extraction_run_id:
            return run
    return None


def build_knowledge(network_run, runs):
    """Monta o conhecimento compacto: rede compacta + análises disponíveis.

    A entrada da LLM nunca contém texto de página — apenas agregados com fontes.
    Keywords, classify e rank enriquecem quando existem para a mesma execução de
    extração da rede (mesma época do corpus); ausências viram pendências
    informadas em `missing_analyses`, sem bloquear a geração.
    """
    from seo_agent.network import compact_network
    network = network_run['result']['network']
    extraction_run_id = network_run['result']['extraction_run_id']
    knowledge = {'network': compact_network(network)}
    origins = {'extraction_run_id': extraction_run_id, 'network_run_id': network_run['run_id'],
               'keywords_run_id': None, 'classify_run_id': None, 'rank_run_id': None}
    missing = []
    keywords_run = _latest_analysis(runs, 'discovered', extraction_run_id)
    if keywords_run:
        origins['keywords_run_id'] = keywords_run['run_id']
        knowledge['keywords'] = {'project_keywords': keywords_run['result']['project_keywords'],
                                 'discovered': keywords_run['result']['discovered']}
    else:
        missing.append('keywords')
    classify_run = _latest_analysis(runs, 'classifications', extraction_run_id)
    if classify_run:
        origins['classify_run_id'] = classify_run['run_id']
        knowledge['classifications'] = [{'url': item['url'], 'type': item['type']}
                                        for item in classify_run['result']['classifications']]
    else:
        missing.append('classify')
    rank_run = _latest_analysis(runs, 'themes', extraction_run_id)
    if rank_run:
        origins['rank_run_id'] = rank_run['run_id']
        knowledge['rankings'] = {
            'sources': [{'url': item['url'], 'score': item['score']}
                        for item in rank_run['result']['sources'] if 'score' in item],
            'themes': rank_run['result']['themes']}
    else:
        missing.append('rank')
    knowledge['missing_analyses'] = missing
    return knowledge, origins


def generate_insights(project_id, runs, store, generate=None):
    network_run = insights_inputs(runs)
    knowledge, origins = build_knowledge(network_run, runs)
    project = next((run['project'] for run in reversed(runs) if run.get('project')), None)
    result = origins | {'knowledge': knowledge}
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(), 'status': None, 'result': result}
    if generate is None:
        record['status'] = 'no_model'
        result['message'] = NO_GENERATOR_MESSAGE
    else:
        result['insights'] = generate(project, result)
        record['status'] = 'generated'
    from seo_agent.store import save_run
    save_run(record, store)
    return record
