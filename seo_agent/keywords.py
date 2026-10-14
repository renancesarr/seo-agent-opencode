"""Descoberta determinística de palavras-chave no corpus extraído."""

from collections import Counter
from datetime import datetime, UTC
from itertools import combinations
import re
from uuid import uuid4


DEFAULT_LIMIT = 50
MIN_NGRAM_OCCURRENCES = 2
MIN_COOCCURRENCE_PAGES = 2

TOKEN_PATTERN = re.compile(r'[^\W_]+')
QUESTION_PATTERN = re.compile(r'[^.!?]*\?')

# Lista mínima em pt-BR, só palavras puramente gramaticais (artigos, preposições,
# conjunções e cópulas): delimitam as bordas de conteúdo dos n-gramas e evitam que
# o topo da cauda longa seja lixo prepositivo ("de horta", "em casa"). Interrogativos
# (como, quando, onde) ficam fora de propósito: encabeçam cauda longa valiosa.
STOPWORDS_PT_BR = frozenset(
    'a o as os um uma uns umas ao aos à às de do da dos das em no na nos nas num numa '
    'por pelo pela pelos pelas para pra com sem sob sobre entre e ou nem que se não já '
    'ser é são foi era tem ter há'.split())


def _tokens(text):
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if len(token) >= 2]


def _normalized_keyword(text):
    return ' '.join(_tokens(text))


def _question_terms(text):
    return {_normalized_keyword(segment) for segment in QUESTION_PATTERN.findall(text or '')} - {''}


def _ngrams(tokens):
    for size in (2, 3):
        for start in range(len(tokens) - size + 1):
            window = tokens[start:start + size]
            if window[0] not in STOPWORDS_PT_BR and window[-1] not in STOPWORDS_PT_BR:
                yield ' '.join(window)


def _latest_project_keywords(runs):
    for run in reversed(runs):
        keywords = (run.get('project') or {}).get('keywords')
        if keywords:
            return list(keywords)
    return []


def discover_keywords(project_id, runs, store, *, limit=DEFAULT_LIMIT):
    """Descobre palavras-chave no texto extraído mais recente, sem LLM e sem rede.

    Cada termo descoberto sai com as URLs-fonte e a execução de extração de
    origem; termo sem fonte no corpus não existe. URL com falha na extração
    fica fora da descoberta, com a falha registrada, sem derrubar as demais.
    """
    if limit < 0:
        raise ValueError('O limite de termos não pode ser negativo.')
    from seo_agent.extract import extraction_inputs
    extraction_run, valid, excluded = extraction_inputs(runs, purpose='descobrir palavras-chave')
    project_keywords = _latest_project_keywords(runs)
    covered = {_normalized_keyword(keyword) for keyword in project_keywords}
    ngram_occurrences = Counter()
    ngram_sources = {}
    pair_sources = {}
    question_sources = {}
    for extraction in valid:
        url = extraction['url']
        text = (extraction.get('page') or {}).get('text') or ''
        tokens = _tokens(text)
        for term in _ngrams(tokens):
            ngram_occurrences[term] += 1
            ngram_sources.setdefault(term, set()).add(url)
        contents = {token for token in tokens if token not in STOPWORDS_PT_BR}
        for pair in combinations(sorted(contents), 2):
            pair_sources.setdefault(pair, set()).add(url)
        # O texto preservado já contém o texto dos headings, então perguntas de
        # heading ("Como plantar?") aparecem aqui como qualquer segmento com "?".
        for term in _question_terms(text):
            question_sources.setdefault(term, set()).add(url)
    items = [{'kind': 'long_tail', 'term': term, 'frequency': frequency,
              'sources': sorted(ngram_sources[term]), 'is_new': term not in covered}
             for term, frequency in ngram_occurrences.items() if frequency >= MIN_NGRAM_OCCURRENCES]
    items += [{'kind': 'co_occurrence', 'term': f'{first} + {second}', 'frequency': len(urls),
               'sources': sorted(urls), 'is_new': f'{first} + {second}' not in covered}
              for (first, second), urls in pair_sources.items()
              if len(urls) >= MIN_COOCCURRENCE_PAGES]
    items += [{'kind': 'question', 'term': term, 'frequency': len(urls),
               'sources': sorted(urls), 'is_new': term not in covered}
              for term, urls in question_sources.items()]
    items.sort(key=lambda item: (-item['frequency'], item['term'], item['kind']))
    record = {'run_id': str(uuid4()), 'project_id': project_id,
              'created_at': datetime.now(UTC).isoformat(),
              'status': 'discovered' if valid else 'empty',
              'result': {'extraction_run_id': extraction_run['run_id'],
                         'project_keywords': project_keywords,
                         'discovered': items[:limit], 'excluded': excluded}}
    from seo_agent.store import save_run
    save_run(record, store)
    return record
