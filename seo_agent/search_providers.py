"""Seleciona somente APIs com credenciais completas, antes de pesquisar."""

import json
import base64
import os
from pathlib import Path
import re
import shlex
from functools import partial
from urllib.parse import urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from seo_agent.search_batch import BraveSearchProvider


class ProviderError(ValueError):
    """Mensagem controlada: não inclui tokens, URLs autenticadas ou corpo remoto."""


class SearchProvider:
    def __init__(self, name, search):
        self.name = name
        self.search = search

    def __call__(self, query):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Informe uma consulta não vazia.')
        try:
            return self.search(query)
        except ProviderError as error:
            raise ValueError(f'{self.name}: {error}') from None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise ValueError(f'{self.name}: falha na API ou resposta inválida.') from None


def _json(fetch, url, *, params=None, headers=None, body=None):
    if fetch is None:
        from seo_agent.http import fetch_url
        fetch = fetch_url
    if params:
        url += '?' + urlencode(params)
    options = {'headers': {'Accept': 'application/json'} | (headers or {})}
    if body is not None:
        options.update(method='POST', body=json.dumps(body, ensure_ascii=False).encode('utf-8'))
        options['headers']['Content-Type'] = 'application/json'
    response = fetch(url, **options)
    if response.status != 200:
        raise ProviderError(f'HTTP {response.status}.')
    payload = json.loads(response.text())
    if not isinstance(payload, dict) or payload.get('error') or payload.get('errors'):
        raise ProviderError('Resposta inválida ou erro do provedor.')
    return payload


def _normalize(items, engines, *, url_field='url', snippet_field='snippet'):
    if not isinstance(items, list):
        raise ProviderError('Resposta inválida: resultados devem ser uma lista.')
    results, seen = [], set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(url_field), str):
            continue
        try:
            parsed = urlsplit(item[url_field])
            if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None):
                continue
            url = urlunsplit(parsed._replace(fragment=''))
        except ValueError:
            continue
        if url in seen:
            continue
        seen.add(url)
        results.append({'title': item.get('title') if isinstance(item.get('title'), str) else '',
                        'url': url, 'snippet': item.get(snippet_field) if isinstance(item.get(snippet_field), str) else '',
                        'buscador': engines})
    return results


def _google(query, environment, fetch):
    payload = _json(fetch, 'https://customsearch.googleapis.com/customsearch/v1', params={
        'key': environment['GOOGLE_SEARCH_API_KEY'], 'cx': environment['GOOGLE_SEARCH_ENGINE_ID'],
        'q': query, 'gl': 'br', 'hl': 'pt-BR', 'num': 10,
    })
    items = payload.get('items')
    if items is None and payload.get('searchInformation', {}).get('totalResults') == '0':
        items = []
    return _normalize(items, ['google'], url_field='link')


def _mojeek(query, environment, fetch):
    payload = _json(fetch, 'https://www.mojeek.com/search', params={
        'api_key': environment['MOJEEK_API_KEY'], 'q': query, 'fmt': 'json',
        'rb': 'BR', 'lb': 'PT', 't': 10,
    })['response']
    if payload.get('status') != 'OK':
        raise ProviderError('API retornou erro.')
    return _normalize(payload.get('results'), ['mojeek'], snippet_field='desc')


def _you(query, environment, fetch):
    payload = _json(fetch, 'https://ydc-index.io/v1/search',
                    headers={'X-API-Key': environment['YDC_API_KEY']}, body={
                        'query': query, 'count': 10, 'country': 'BR', 'language': 'pt-BR',
                    })
    return _normalize(payload['results'].get('web', []), ['you'], snippet_field='description')


def _kagi(query, environment, fetch):
    payload = _json(fetch, 'https://kagi.com/api/v1/search',
                    headers={'Authorization': 'Bearer ' + environment['KAGI_API_KEY']},
                    body={'query': query, 'workflow': 'search', 'limit': 10})
    return _normalize(payload['data'].get('search', []), ['kagi'])


def _serpapi(query, environment, fetch):
    payload = _json(fetch, 'https://serpapi.com/search.json', params={
        'api_key': environment['SERPAPI_API_KEY'], 'engine': 'google', 'q': query,
        'gl': 'br', 'hl': 'pt', 'google_domain': 'google.com.br',
    })
    if payload.get('search_metadata', {}).get('status') == 'Error':
        raise ProviderError('API retornou erro.')
    items = payload.get('organic_results')
    if items is None and payload.get('search_metadata', {}).get('status') == 'Success':
        items = []
    return _normalize(items, ['google'], url_field='link')


def _serper(query, environment, fetch):
    payload = _json(fetch, 'https://google.serper.dev/search',
                    headers={'X-API-KEY': environment['SERPER_API_KEY']},
                    body={'q': query, 'gl': 'br', 'hl': 'pt-br', 'num': 10})
    items = payload.get('organic')
    if items is None and isinstance(payload.get('searchParameters'), dict):
        items = []
    return _normalize(items, ['google'], url_field='link')


def _dataforseo(query, environment, fetch):
    credentials = (environment['DATAFORSEO_LOGIN'] + ':' + environment['DATAFORSEO_PASSWORD']).encode('utf-8')
    payload = _json(fetch, 'https://api.dataforseo.com/v3/serp/google/organic/live/advanced',
                    headers={'Authorization': 'Basic ' + base64.b64encode(credentials).decode('ascii')},
                    body=[{'keyword': query, 'location_name': 'Brazil', 'language_code': 'pt', 'depth': 10}])
    if payload.get('status_code') != 20000 or not payload.get('tasks'):
        raise ProviderError('API retornou erro de tarefa.')
    items = []
    for task in payload['tasks']:
        if task.get('status_code') != 20000:
            raise ProviderError('API retornou erro de tarefa.')
        for result in task.get('result') or []:
            items.extend(item for item in result.get('items') or []
                         if isinstance(item, dict) and item.get('type') == 'organic')
    return _normalize(items, ['google'], snippet_field='description')


def _yandex(query, environment, fetch):
    payload = _json(fetch, 'https://searchapi.api.cloud.yandex.net/v2/web/search',
                    headers={'Authorization': 'Api-Key ' + environment['YANDEX_SEARCH_API_KEY']}, body={
                        'query': {'searchType': 'SEARCH_TYPE_COM', 'queryText': query},
                        'folderId': environment['YANDEX_FOLDER_ID'], 'responseFormat': 'FORMAT_XML',
                        'groupSpec': {'groupMode': 'GROUP_MODE_FLAT', 'groupsOnPage': '10', 'docsInGroup': '1'},
                    })
    xml = base64.b64decode(payload['rawData'], validate=True).decode('utf-8')
    if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
        raise ProviderError('XML inválido: DTD e entidades não são aceitos.')
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        raise ProviderError('XML inválido.') from None
    if root.find('.//error') is not None or root.find('.//results') is None:
        raise ProviderError('API retornou erro ou XML inválido.')
    items = []
    for document in root.findall('.//doc'):
        title = document.find('title')
        items.append({'url': document.findtext('url'),
                      'title': ''.join(title.itertext()) if title is not None else '',
                      'snippet': ' '.join(''.join(passage.itertext())
                                          for passage in document.findall('.//passage'))})
    return _normalize(items, ['yandex'])


def configured_providers(environment=None, *, env_file='.env', fetch=None):
    if environment is None:
        environment = {}
        path = Path(env_file)
        if path.exists():
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                match = re.fullmatch(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)', line)
                if match is None:
                    raise ValueError(f'Arquivo de ambiente inválido na linha {number}.')
                try:
                    values = shlex.split(match[2], comments=True)
                except ValueError:
                    raise ValueError(f'Valor inválido no arquivo de ambiente, linha {number}.') from None
                if len(values) > 1:
                    raise ValueError(f'Use aspas no valor da linha {number} do arquivo de ambiente.')
                environment[match[1]] = values[0] if values else ''
        environment.update(os.environ)
    providers = []
    if environment.get('BRAVE_SEARCH_API_KEY', '').strip():
        providers.append(SearchProvider('brave', BraveSearchProvider(
            environment['BRAVE_SEARCH_API_KEY'], fetch=fetch).search))
    for name, fields, search in [
        ('google', ('GOOGLE_SEARCH_API_KEY', 'GOOGLE_SEARCH_ENGINE_ID'), _google),
        ('mojeek', ('MOJEEK_API_KEY',), _mojeek),
        ('you', ('YDC_API_KEY',), _you),
        ('kagi', ('KAGI_API_KEY',), _kagi),
        ('serpapi', ('SERPAPI_API_KEY',), _serpapi),
        ('serper', ('SERPER_API_KEY',), _serper),
        ('dataforseo', ('DATAFORSEO_LOGIN', 'DATAFORSEO_PASSWORD'), _dataforseo),
        ('yandex', ('YANDEX_SEARCH_API_KEY', 'YANDEX_FOLDER_ID'), _yandex),
    ]:
        if all(environment.get(field, '').strip() for field in fields):
            providers.append(SearchProvider(name, partial(search, environment=environment, fetch=fetch)))
    return providers
