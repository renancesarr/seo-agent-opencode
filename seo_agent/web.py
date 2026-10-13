"""Busca e inspeção web com evidências observadas, sem inferência de LLM."""

from datetime import datetime, UTC
import json
import re
from urllib.parse import urlencode, urlsplit, urlunsplit


def search_web(query, *, endpoint='http://127.0.0.1:8080', language='pt-BR', limit=5, fetch=None):
    """Consulta a API JSON do SearXNG explicitamente configurado pelo operador."""
    if not query.strip():
        raise ValueError('Informe uma consulta não vazia.')
    if not 1 <= limit <= 20:
        raise ValueError('O limite de resultados deve estar entre 1 e 20.')
    parsed_endpoint = urlsplit(endpoint)
    if (parsed_endpoint.scheme not in {'http', 'https'} or not parsed_endpoint.hostname
            or parsed_endpoint.username is not None or parsed_endpoint.password is not None
            or parsed_endpoint.query or parsed_endpoint.fragment):
        raise ValueError('Informe um endpoint http/https sem credenciais, query ou fragmento.')
    if fetch is None:
        from seo_agent.http import fetch_url
        fetch = fetch_url
    search_url = endpoint.rstrip('/') + '/search?' + urlencode({
        'q': query, 'format': 'json', 'language': language,
    })
    response = fetch(search_url, allow_private=True)
    if response.status == 403:
        raise ValueError('SearXNG retornou 403. Confira search.formats: [html, json] e o acesso à instância.')
    if response.status != 200:
        raise ValueError(f'SearXNG retornou HTTP {response.status}. Verifique a instância configurada.')
    try:
        payload = json.loads(response.text())
    except ValueError as error:
        raise ValueError('SearXNG não retornou JSON válido. Confira endpoint e search.formats.') from error
    if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
        raise ValueError('Resposta SearXNG inválida: results deve ser uma lista.')
    results, seen = [], set()
    for position, item in enumerate(payload['results'], 1):
        if not isinstance(item, dict) or not isinstance(item.get('url'), str):
            continue
        try:
            url = urlsplit(item['url'])
            if url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password:
                continue
            normalized = urlunsplit(url._replace(fragment=''))
        except ValueError:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        engines = item.get('engines', [])
        results.append({
            'url': normalized,
            'title': item.get('title') if isinstance(item.get('title'), str) else '',
            'snippet': item.get('content') if isinstance(item.get('content'), str) else '',
            'engines': [engine for engine in engines if isinstance(engine, str)] if isinstance(engines, list) else [],
            'observed_position': position,
        })
        if len(results) == limit:
            break
    return {
        'query': query, 'language': language, 'provider': 'searxng',
        'source_url': search_url, 'retrieved_at': datetime.now(UTC).isoformat(),
        'results': results, 'unresponsive_engines': payload.get('unresponsive_engines', []),
    }


def _resource(url, fetch):
    """Uma falha auxiliar é evidência de coleta incompleta, não conteúdo."""
    try:
        response = fetch(url)
    except (OSError, ValueError) as error:
        return {'requested_url': url, 'error': str(error)}, None
    result = {'requested_url': url, 'url': response.url, 'http_status': response.status}
    if response.status != 200:
        result['error'] = f'HTTP {response.status}'
        return result, None
    return result, response.text()


def _domain_files(url, fetch):
    from urllib.robotparser import RobotFileParser
    from xml.etree import ElementTree

    parsed = urlsplit(url)
    origin = urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))
    robots, text = _resource(origin + '/robots.txt', fetch)
    robots.update({'allowed_for_agent': None, 'sitemaps': []})
    if text is not None:
        if '<html' in text.lower() or '<!doctype html' in text.lower():
            robots['error'] = 'robots.txt retornou HTML; regras não interpretadas.'
        else:
            rules = RobotFileParser()
            rules.parse(text.splitlines())
            robots.update({'text': text, 'allowed_for_agent': rules.can_fetch('SEOAgent', url),
                           'sitemaps': rules.site_maps() or [],
                           'evaluation_method': 'urllib.robotparser'})
            if re.search(r'^\s*(?:allow|disallow)\s*:.*[*$]', text, re.IGNORECASE | re.MULTILINE):
                robots['allowed_for_agent'] = None
                robots['evaluation_note'] = 'Padrões com * ou $ exigem outro avaliador; regras preservadas.'
    elif robots.get('http_status') == 404:
        robots['allowed_for_agent'] = True
    elif robots.get('http_status') in {401, 403}:
        robots['allowed_for_agent'] = False
    sitemap_url = origin + '/sitemap.xml'
    for candidate in robots['sitemaps']:
        try:
            target = urlsplit(candidate)
            if (target.scheme, target.netloc) == (parsed.scheme, parsed.netloc):
                sitemap_url = candidate
                break
        except ValueError:
            continue
    sitemap, xml = _resource(sitemap_url, fetch)
    sitemap.update({'kind': None, 'entries': []})
    if xml is not None:
        try:
            if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
                raise ValueError('DTD e entidades não são aceitos.')
            root = ElementTree.fromstring(xml)
            kind = root.tag.rsplit('}', 1)[-1]
            if kind not in {'urlset', 'sitemapindex'}:
                raise ValueError('Esperado urlset ou sitemapindex.')
            entries = []
            for entry in root:
                if entry.tag.rsplit('}', 1)[-1] != ('url' if kind == 'urlset' else 'sitemap'):
                    continue
                fields = {child.tag.rsplit('}', 1)[-1]: child.text for child in entry}
                if fields.get('loc'):
                    entries.append({'url': fields['loc'].strip(), 'last_modified': fields.get('lastmod')})
            sitemap.update({'kind': kind, 'entries': entries[:500],
                            'entry_count': len(entries), 'truncated': len(entries) > 500})
        except (ElementTree.ParseError, ValueError) as error:
            sitemap['error'] = f'Sitemap inválido: {error}'
    return robots, sitemap


def inspect_page(url, *, fetch=None):
    """Audita uma URL explícita e dois arquivos de descoberta, sem seguir links."""
    from seo_agent.page import extract_page
    if fetch is None:
        from seo_agent.http import fetch_url
        fetch = fetch_url
    response = fetch(url)
    parsed = urlsplit(response.url)
    content_type = response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    issues = []
    page = None
    if response.status != 200:
        issues.append({'code': 'http_error', 'severity': 'error',
                       'message': 'A página não respondeu HTTP 200.', 'evidence': str(response.status)})
    elif content_type not in {'text/html', 'application/xhtml+xml'}:
        issues.append({'code': 'unsupported_content', 'severity': 'error',
                       'message': 'Inspeção disponível apenas para HTML.', 'evidence': content_type})
    else:
        page = extract_page(response.text(), response.url)
        issues.extend(page['issues'])
    if parsed.scheme != 'https':
        issues.append({'code': 'http_without_tls', 'severity': 'warning',
                       'message': 'A URL final utiliza HTTP sem TLS.', 'evidence': response.url})
    robots_header = response.headers.get('x-robots-tag', '')
    if re.search(r'(?:^|[\s,:])(?:noindex|none)(?=$|[\s,;])', robots_header.lower()):
        issues.append({'code': 'http_noindex', 'severity': 'info',
                       'message': 'X-Robots-Tag declara restrição de indexação; confira seu escopo.',
                       'evidence': robots_header})
    robots, sitemap = _domain_files(response.url, fetch)
    return {
        'requested_url': url, 'retrieved_at': datetime.now(UTC).isoformat(),
        'status': 'partial' if page is None or 'error' in robots or 'error' in sitemap else 'ok',
        'javascript_rendered': False,
        'http': {'url': response.url, 'status': response.status, 'redirects': response.redirects,
                 'headers': {key: value for key, value in response.headers.items() if key in {
                     'content-type', 'content-language', 'x-robots-tag', 'link', 'last-modified',
                     'etag', 'cache-control', 'server', 'strict-transport-security'}},
                 'bytes': len(response.body)},
        'domain': {'hostname': parsed.hostname, 'ip_addresses': response.ip_addresses, 'tls': response.tls},
        'page': page, 'robots': robots, 'sitemap': sitemap, 'issues': issues,
    }
