"""Busca em provedores e coleta páginas com resposta HTTP 200."""

import json
import os
from time import sleep
from urllib.parse import urlencode, urlsplit, urlunsplit


class BraveSearchProvider:
    """Adaptador da API oficial Brave Search Web."""

    def __init__(self, api_key=None, *, fetch=None):
        self.api_key = api_key if api_key is not None else os.environ.get('BRAVE_SEARCH_API_KEY', '')
        if not self.api_key.strip():
            raise ValueError('Configure a chave BRAVE_SEARCH_API_KEY para usar a busca Brave.')
        if fetch is None:
            from seo_agent.http import fetch_url
            fetch = fetch_url
        self.fetch = fetch

    def search(self, query):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Informe uma consulta não vazia.')
        url = 'https://api.search.brave.com/res/v1/web/search?' + urlencode({
            'q': query, 'country': 'BR', 'search_lang': 'pt-br', 'count': 20,
            'result_filter': 'web',
        })
        response = self.fetch(url, headers={'X-Subscription-Token': self.api_key})
        if response.status != 200:
            raise ValueError(f'Brave Search retornou HTTP {response.status}.')
        try:
            payload = json.loads(response.text())
        except ValueError as error:
            raise ValueError('Brave Search não retornou JSON válido.') from error
        results = payload.get('web', {}).get('results') if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise ValueError('Resposta Brave Search inválida: web.results deve ser uma lista.')
        normalized = []
        for item in results:
            if not isinstance(item, dict) or not isinstance(item.get('url'), str):
                continue
            try:
                parsed = urlsplit(item['url'])
                if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
                    continue
                target = urlunsplit(parsed._replace(fragment=''))
            except ValueError:
                continue
            normalized.append({'title': item.get('title', ''), 'url': target,
                               'snippet': item.get('description', ''), 'buscador': ['brave']})
        return normalized


def _url_key(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError('URL inválida para coleta.')
    host = (parsed.hostname or '').lower()
    if ':' in host:
        host = '[' + host + ']'
    netloc = host + (f':{parsed.port}' if parsed.port else '')
    return urlunsplit(parsed._replace(netloc=netloc, fragment=''))


def _domain(url):
    host = (urlsplit(url).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host


def collect_pages(queries, providers, *, fetch_page=None, on_error=None):
    """Agrupa páginas acessíveis HTTP 200 por domínio e reúne evidências."""
    if fetch_page is None:
        from seo_agent.http import fetch_url
        fetch_page = fetch_url
    groups, checked = {}, {}
    for query in queries:
        for provider in providers:
            try:
                results = provider(query)
            except (OSError, ValueError) as error:
                if on_error is not None:
                    on_error({'query': query, 'provider': getattr(provider, 'name', getattr(provider, '__name__', 'search')),
                              'error': str(error)})
                continue
            for result in results:
                url = result.get('url')
                if not isinstance(url, str):
                    continue
                try:
                    key = _url_key(url)
                except ValueError:
                    continue
                if key in checked:
                    group = checked[key]
                    if group is not None:
                        _append_evidence(group, query, result.get('buscador', []))
                    continue
                checked[key] = None
                try:
                    response = fetch_page(key)
                except (OSError, ValueError):
                    continue
                if response.status != 200:
                    continue
                try:
                    final_url = _url_key(response.url)
                except ValueError:
                    continue
                domain = _domain(final_url)
                if not domain:
                    continue
                group = groups.setdefault(domain, {
                    'domain': domain, 'urli': [], 'searches': [], 'buscador': [],
                })
                if not any(item['url'] == final_url for item in group['urli']):
                    group['urli'].append({'title': result.get('title', ''), 'url': final_url})
                checked[key] = checked[final_url] = group
                _append_evidence(group, query, result.get('buscador', []))
    return list(groups.values())


def _append_evidence(group, query, providers):
    if query not in group['searches']:
        group['searches'].append(query)
    for provider in providers:
        if provider not in group['buscador']:
            group['buscador'].append(provider)


def run_queries(queries, providers, *, fetch_page=None, interval_seconds=300, wait=None, on_error=None):
    """Executa consultas sequencialmente e espera apenas entre consultas completas."""
    if interval_seconds < 0:
        raise ValueError('O intervalo entre consultas não pode ser negativo.')
    if not providers:
        return []
    if wait is None:
        wait = sleep
    def scheduled_queries():
        for index, query in enumerate(queries):
            if index:
                wait(interval_seconds)
            yield query

    return collect_pages(scheduled_queries(), providers, fetch_page=fetch_page, on_error=on_error)
