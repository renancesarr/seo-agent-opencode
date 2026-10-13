"""Execução por projeto: descoberta e evidências persistíveis, sem análise inventada."""

from datetime import datetime, UTC
import hashlib

from seo_agent.page import extract_page
from seo_agent.search_batch import normalize_url, run_queries
from seo_agent.search_providers import SearchProvider


def collect_project(project, providers, *, fetch=None, max_pages=10, max_queries=10, interval_seconds=300, wait=None):
    if max_pages < 1 or max_queries < 1 or interval_seconds < 0:
        raise ValueError('Informe limites positivos e intervalo não negativo.')
    if fetch is None:
        from seo_agent.http import fetch_url
        fetch = fetch_url
    queries = list(dict.fromkeys(f'{keyword.strip()} {project["geography"].strip()}'
                                for keyword in project['keywords']))
    candidates, sources, errors, cache = {}, {}, [], {}
    if providers and len(queries) > max_queries:
        errors.append({'stage': 'budget', 'error': 'Limite de consultas atingido; consultas restantes não executadas.'})
    queries = queries[:max_queries]
    attempts = 0

    def candidate(item, query=None, reason=None):
        try:
            url = normalize_url(item['url'])
        except (KeyError, ValueError, TypeError):
            errors.append({'stage': 'discovery', 'error': 'URL de candidato inválida.'})
            return None
        entry = candidates.setdefault(url, {'url': url, 'title': item.get('title', ''),
                                           'searches': [], 'buscador': [], 'selection_reasons': []})
        if query is not None and query not in entry['searches']:
            entry['searches'].append(query)
        for engine in item.get('buscador', []):
            if engine not in entry['buscador']:
                entry['buscador'].append(engine)
        reason = reason or 'Resultado retornado para a consulta do projeto; relevância editorial ainda não avaliada.'
        if reason not in entry['selection_reasons']:
            entry['selection_reasons'].append(reason)
        return url

    def read(url):
        nonlocal attempts
        url = normalize_url(url)
        if url in cache:
            response = cache[url]
            if isinstance(response, Exception):
                raise response
            return response
        if attempts >= max_pages:
            error = ValueError('Limite de páginas atingido.')
            cache[url] = error
            errors.append({'stage': 'read', 'url': url, 'error': str(error)})
            raise error
        attempts += 1
        try:
            response = fetch(url)
        except (OSError, ValueError):
            error = ValueError('Falha ao ler a página pública.')
            cache[url] = error
            errors.append({'stage': 'read', 'url': url, 'error': str(error)})
            raise error from None
        cache[url] = response
        if response.status != 200:
            errors.append({'stage': 'read', 'url': url, 'http_status': response.status,
                           'error': 'A página não respondeu HTTP 200.'})
            return response
        final = normalize_url(response.url)
        cache[final] = response
        content_type = response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
        if content_type not in {'text/html', 'application/xhtml+xml'}:
            errors.append({'stage': 'read', 'url': final, 'error': 'Conteúdo não HTML.'})
            return response
        sources.setdefault(final, {'id': hashlib.sha256(final.encode()).hexdigest(),
                                  'requested_url': url, 'url': final, 'http_status': 200,
                                  'retrieved_at': datetime.now(UTC).isoformat(),
                                  'javascript_rendered': False, 'page': extract_page(response.text(), final)})
        return response

    for field in ('sources', 'competitors'):
        for seed in project.get(field, []):
            url = candidate({'url': seed, 'title': '', 'buscador': []},
                            reason=f'URL indicada pelo operador em {field}.')
            if url is not None:
                try:
                    read(url)
                except (OSError, ValueError):
                    pass

    def observe(provider):
        def search(query):
            items = provider(query)
            for item in items:
                candidate(item, query=query)
            return items
        return SearchProvider(getattr(provider, 'name', getattr(provider, '__name__', 'search')), search)

    groups = run_queries(queries, [observe(provider) for provider in providers], fetch_page=read,
                         interval_seconds=interval_seconds, wait=wait,
                         on_error=lambda error: errors.append({'stage': 'search'} | error))
    for url, entry in candidates.items():
        response = cache.get(url)
        if response is not None and not isinstance(response, Exception):
            entry['http_status'] = response.status
            entry['final_url'] = response.url
            if response.status == 200 and response.url in sources:
                entry['source_id'] = sources[response.url]['id']
    result = {'queries': queries if providers else [], 'groups': groups,
              'candidates': list(candidates.values()), 'sources': list(sources.values()), 'errors': errors}
    result['pending'] = [] if sources else ['Nenhuma fonte HTML HTTP 200 foi lida; análise e outline pendentes.']
    status = ('partial' if errors else 'collected') if sources else 'no_evidence'
    return status, result
