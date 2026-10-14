"""Score de relevância das fontes e temas do corpus, por ML clássico local.

Método: ranking linear determinístico sobre sinais auditáveis já extraídos
(regra de pontuação com pesos fixos, da mesma família do classificador do
`classify`). É suficiente nesta etapa porque não existe corpus rotulado para
treinar modelos, os sinais têm interpretação causal direta na qualidade da
fonte e toda saída publica os fatores com valores e pesos — o operador entende
por que uma página ficou à frente e pode corrigir pesos sem caixa-preta.
Totalmente determinístico: sem aleatoriedade nem semente.
"""

from datetime import datetime, UTC
from uuid import uuid4


SUBSTANTIAL_TEXT_WORDS = 300
STRUCTURED_HEADINGS = 3
INBOUND_LINKS_CAP = 3

# Pesos fixos por sinal; a soma das contribuições é o score da fonte.
WEIGHTS = {
    'has_author': 1,
    'has_date': 1,
    'substantial_text': 3,
    'structured_headings': 2,
    'structured_data': 2,
    'inbound_links': 1,
}


def _inbound_links(valid):
    """Links recebidos de páginas distintas do corpus, derivados da própria extração.

    Espelha a semântica deduplicada das relações `links_to` da rede: cada página
    de origem conta um voto por destino, independentemente de quantas âncoras.
    Derivar do `valid` (em vez da rede persistida) mantém o score sempre coerente
    com a execução de extração pontuada e dispensa `network build` antes do rank.
    """
    corpus = {extraction['url'] for extraction in valid}
    voters = {url: set() for url in corpus}
    for extraction in valid:
        url = extraction['url']
        for link in (extraction.get('page') or {}).get('links') or []:
            target = link.get('url')
            if target in corpus and target != url:
                voters[target].add(url)
    return {url: len(pages) for url, pages in voters.items()}


def rank_source(extraction, inbound):
    """Pontua uma extração válida com os sinais observados e os pesos fixos.

    A justificativa é inspecionável: cada fator sai com o sinal, o valor
    observado, o peso aplicado e os pontos que contribuiu — o score é a soma
    dos pontos. Página sem texto utilizável vira pendência com motivo, não erro.
    """
    url = extraction['url']
    page = extraction.get('page') or {}
    text_words = len((page.get('text') or '').split())
    if text_words == 0:
        return {'url': url, 'reason': 'Página sem texto utilizável para pontuar.'}
    headings = len(page.get('headings') or [])
    structured_data = len(page.get('structured_data') or [])
    observed = {
        'has_author': bool(page.get('authors')),
        'has_date': bool(page.get('dates')),
        'substantial_text': text_words,
        'structured_headings': headings,
        'structured_data': structured_data,
        'inbound_links': inbound,
    }
    active = {
        'has_author': observed['has_author'],
        'has_date': observed['has_date'],
        'substantial_text': text_words >= SUBSTANTIAL_TEXT_WORDS,
        'structured_headings': headings >= STRUCTURED_HEADINGS,
        'structured_data': structured_data >= 1,
    }
    factors = []
    score = 0
    for signal, weight in WEIGHTS.items():
        count = min(inbound, INBOUND_LINKS_CAP) if signal == 'inbound_links' else int(bool(active[signal]))
        points = weight * count
        score += points
        factors.append({'signal': signal, 'value': observed[signal], 'weight': weight, 'points': points})
    return {'url': url, 'score': score, 'factors': factors}


def rank_project(project_id, runs, store):
    """Pontua a relevância das fontes e temas da extração mais recente, sem LLM e sem rede.

    URL com falha na extração fica fora do ranking, com a falha registrada em
    `excluded`, sem derrubar as demais. Fonte sem texto utilizável vira pendência
    explícita com motivo — não é erro: o registro sai `partial` para revisão.
    """
    from seo_agent.extract import extraction_inputs
    extraction_run, valid, excluded = extraction_inputs(runs, purpose='pontuar a relevância')
    inbound = _inbound_links(valid)
    ranked = [rank_source(extraction, inbound[extraction['url']]) for extraction in valid]
    scored = sorted((item for item in ranked if 'score' in item),
                    key=lambda item: (-item['score'], item['url']))
    pending = sorted((item for item in ranked if 'reason' in item), key=lambda item: item['url'])
    themes = _themes(valid, {item['url']: item['score'] for item in scored})
    status = 'empty' if not valid else ('partial' if pending else 'ranked')
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(), 'status': status,
              'result': {'extraction_run_id': extraction_run['run_id'],
                         'sources': scored + pending, 'themes': themes, 'excluded': excluded}}
    from seo_agent.store import save_run
    save_run(record, store)
    return record


def _themes(valid, score_by_url):
    """Agrega em temas os scores das fontes que os cobrem, com as URLs-fonte.

    O tema é o texto normalizado dos headings (o mesmo critério de `term` da
    rede); o score do tema é a soma dos scores das fontes que tratam o tema.
    """
    sources = {}
    for extraction in valid:
        url = extraction['url']
        if url not in score_by_url:
            continue
        for heading in (extraction.get('page') or {}).get('headings') or []:
            term = ' '.join((heading.get('text') or '').split()).lower()
            if term:
                sources.setdefault(term, set()).add(url)
    themes = [{'term': term, 'score': sum(score_by_url[url] for url in urls),
               'sources': sorted(urls, key=lambda url: (-score_by_url[url], url))}
              for term, urls in sources.items()]
    return sorted(themes, key=lambda theme: (-theme['score'], theme['term']))
