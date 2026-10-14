"""Classificação dos tipos de conteúdo das fontes extraídas, por ML clássico local.

Método: classificador linear de pontuação sobre indicadores binários derivados dos
sinais já extraídos (regra de pontuação com pesos fixos auditáveis, da família dos
classificadores lineares tipo perceptron/Naive Bayes com pesos definidos). É
suficiente nesta etapa porque não existe corpus rotulado para treinar modelos, os
indicadores têm interpretação causal direta no formato da página e toda saída
publica sinais e pontuações — o operador audita e corrige pesos sem caixa-preta.
Tipos: `article` (artigo/guia), `listing` (listagem/diretório) e `profile`
(ficha/institucional). Totalmente determinístico: sem aleatoriedade nem semente.
Empate de pontuação é resolvido em ordem alfabética do tipo.
"""

from datetime import datetime, UTC
from uuid import uuid4


ARTICLE_TYPES = frozenset({'Article', 'BlogPosting', 'NewsArticle'})
LISTING_TYPES = frozenset({'ItemList', 'CollectionPage'})
PROFILE_TYPES = frozenset({'ProfilePage', 'Person', 'Organization', 'LocalBusiness', 'AboutPage'})

LONG_PROSE_WORDS = 300
STRUCTURED_HEADINGS = 3
MANY_LINKS = 12
ANCHOR_HEAVY_RATIO = 0.5
SPARSE_MAX_WORDS = 300
SPARSE_MAX_LINKS = 5
SPARSE_MAX_HEADINGS = 2

# Pesos fixos por tipo e indicador; a soma dos indicadores ativos pondera o score.
WEIGHTS = {
    'article': {'long_prose': 3, 'structured_headings': 2, 'has_author': 1, 'has_date': 1,
                'type_article': 3},
    'listing': {'many_links': 3, 'anchor_heavy': 2, 'type_listing': 3},
    'profile': {'sparse': 3, 'type_profile': 3},
}


def _type_names(value):
    items = value if isinstance(value, list) else [value]
    return [item for item in items if isinstance(item, str) and item.strip()]


def _structured_types(page):
    names = set()
    for block in page.get('structured_data') or []:
        if not isinstance(block, dict):
            continue
        graph = block.get('@graph')
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    names.update(_type_names(item.get('@type')))
        names.update(_type_names(block.get('@type')))
    return sorted(names)


def classify_source(extraction):
    """Classifica uma extração válida em tipo de conteúdo, com justificativa.

    A justificativa é inspecionável: os sinais observados (com valores) e a
    pontuação de todos os tipos saem junto do rótulo. Página sem texto
    utilizável, ou sem nenhum indicador ativo, vira pendência `unclassified`
    com motivo — não é erro.
    """
    url = extraction['url']
    page = extraction.get('page') or {}
    text_words = len((page.get('text') or '').split())
    if text_words == 0:
        return {'url': url, 'type': 'unclassified', 'reason': 'Página sem texto utilizável para classificar.'}
    headings = len(page.get('headings') or [])
    links = page.get('links') or []
    linked_words = sum(len((link.get('text') or '').split()) for link in links)
    linked_words_ratio = round(linked_words / text_words, 4)
    structured_types = _structured_types(page)
    signals = {'text_words': text_words, 'headings': headings, 'links': len(links),
               'linked_words_ratio': linked_words_ratio, 'structured_types': structured_types,
               'has_author': bool(page.get('authors')), 'has_date': bool(page.get('dates'))}
    indicators = {
        'long_prose': text_words >= LONG_PROSE_WORDS,
        'structured_headings': headings >= STRUCTURED_HEADINGS,
        'has_author': signals['has_author'],
        'has_date': signals['has_date'],
        'type_article': bool(ARTICLE_TYPES.intersection(structured_types)),
        'many_links': len(links) >= MANY_LINKS,
        'anchor_heavy': linked_words_ratio >= ANCHOR_HEAVY_RATIO,
        'type_listing': bool(LISTING_TYPES.intersection(structured_types)),
        'sparse': (text_words <= SPARSE_MAX_WORDS and len(links) <= SPARSE_MAX_LINKS
                   and headings <= SPARSE_MAX_HEADINGS),
        'type_profile': bool(PROFILE_TYPES.intersection(structured_types)),
    }
    scores = {kind: sum(weight for indicator, weight in weights.items() if indicators[indicator])
              for kind, weights in WEIGHTS.items()}
    if max(scores.values()) == 0:
        return {'url': url, 'type': 'unclassified',
                'reason': 'Nenhum sinal de classificação presente na página.'}
    winner = min(kind for kind, score in scores.items() if score == max(scores.values()))
    return {'url': url, 'type': winner, 'signals': signals, 'scores': scores}


def classify_project(project_id, runs, store):
    """Classifica cada fonte da extração mais recente, sem LLM e sem rede.

    URL com falha na extração fica fora da classificação, com a falha registrada
    em `excluded`, sem derrubar as demais. Pendências `unclassified` não são
    erro: o registro sai `partial` para o operador revisá-las.
    """
    from seo_agent.extract import extraction_inputs
    extraction_run, valid, excluded = extraction_inputs(runs, purpose='classificar os tipos de conteúdo')
    classifications = [classify_source(extraction)
                       for extraction in sorted(valid, key=lambda item: item['url'])]
    if not valid:
        status = 'empty'
    elif any(item['type'] == 'unclassified' for item in classifications):
        status = 'partial'
    else:
        status = 'classified'
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(), 'status': status,
              'result': {'extraction_run_id': extraction_run['run_id'],
                         'classifications': classifications, 'excluded': excluded}}
    from seo_agent.store import save_run
    save_run(record, store)
    return record
