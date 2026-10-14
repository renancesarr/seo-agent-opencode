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


def _crawler_permission(url, fetch):
    from urllib.robotparser import RobotFileParser

    parsed = urlsplit(url)
    origin = urlunsplit((parsed.scheme, parsed.netloc, '', '', ''))
    result, text = _resource(origin + '/robots.txt', fetch)
    if result.get('http_status') == 404:
        return True, result
    if result.get('http_status') != 200 or text is None or '<html' in text.lower():
        return False, result
    result['text'] = text
    if re.search(r'^\s*(?:allow|disallow)\s*:.*[*$]', text, re.IGNORECASE | re.MULTILINE):
        result['error'] = 'Padrão robots com * ou $ não é avaliado automaticamente.'
        return False, result
    rules = RobotFileParser()
    rules.set_url(origin + '/robots.txt')
    rules.parse(text.splitlines())
    return rules.can_fetch('SEOAgent', url), result


def crawl_web(query, *, endpoint='http://127.0.0.1:8080', language='pt-BR', limit=5,
              max_pages=6, evidence_dir='data/browser-evidence', fetch=None, browser=None):
    """Busca, coleta links do mesmo host e observa-os em viewports separados."""
    from seo_agent.browser import VIEWPORTS, browser_session
    if not 1 <= limit <= 20 or not 1 <= max_pages <= 20:
        raise ValueError('O limite de busca e o total de páginas devem estar entre 1 e 20.')
    if fetch is None:
        from seo_agent.http import fetch_url
        fetch = fetch_url
    cache = {}

    def cached_fetch(url, **options):
        key = url, options.get('allow_private', False)
        if key not in cache:
            cache[key] = fetch(url, **options)
        return cache[key]

    discovery = search_web(query, endpoint=endpoint, language=language, limit=limit,
                           fetch=cached_fetch)
    pages, journeys, queue, seen = [], [], [], set()
    for item in discovery['results']:
        queue.append((item['url'], [{'url': item['url'], 'via': 'search_result',
                                     'label': 'Resultado da busca'}]))
    permission_cache = {}

    def can_read(url):
        parts = urlsplit(url)
        origin = urlunsplit((parts.scheme, parts.netloc, '', '', ''))
        if origin not in permission_cache:
            permission_cache[origin] = _crawler_permission(url, cached_fetch)
        allowed, robots = permission_cache[origin]
        if allowed and url != robots.get('checked_url'):
            rules = RobotFileParser()
            rules.set_url(origin + '/robots.txt')
            rules.parse((robots.get('text') or '').splitlines())
            allowed = rules.can_fetch('SEOAgent', url)
        return allowed, robots

    from urllib.robotparser import RobotFileParser
    domain_counts = {}
    browser_context = browser_session() if browser is None and queue else None
    browser = browser_context.__enter__() if browser_context else browser
    try:
        while queue and len(pages) < max_pages:
            url, path = queue.pop(0)
            try:
                parsed = urlsplit(url)
                if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username:
                    continue
                normalized = urlunsplit(parsed._replace(fragment=''))
                if normalized in seen:
                    continue
                seen.add(normalized)
                requested_host = (parsed.hostname or '').lower()
                if domain_counts.get(requested_host, 0) >= 3:
                    continue
                allowed, robots = can_read(normalized)
                if not allowed:
                    pages.append({'url': normalized, 'status': 'skipped_robots', 'robots': robots,
                                  'navigation_path': path, 'renderings': []})
                    continue
                report = inspect_page(normalized, fetch=cached_fetch)
                final_url = report['http']['url']
                hostname = (urlsplit(final_url).hostname or '').lower()
                domain_counts[requested_host] = domain_counts.get(requested_host, 0) + 1
                renderings = [browser.render(final_url, viewport, evidence_dir, locale=language,
                                             navigation_path=path)
                              for viewport in VIEWPORTS]
                page = {
                    'url': final_url, 'requested_url': normalized,
                    'status': 'ok' if report['status'] == 'ok' and all(
                        screen.get('status') == 'ok' for screen in renderings) else 'partial',
                    'inspection': report,
                    'renderings': renderings, 'navigation_path': path,
                }
                pages.append(page)
                if report['page'] is None:
                    continue
                if renderings and renderings[0].get('status') == 'ok':
                    observed_links = renderings[0]['links']
                else:
                    observed_links = report['page']['links']
                final_parts = urlsplit(final_url)
                page_origin = (final_parts.scheme, final_parts.hostname, final_parts.port or
                               (443 if final_parts.scheme == 'https' else 80))
                for link in observed_links:
                    target = link['url']
                    target_parts = urlsplit(target)
                    target_origin = (target_parts.scheme, target_parts.hostname, target_parts.port or
                                     (443 if target_parts.scheme == 'https' else 80))
                    if (link.get('internal', True) and target_origin == page_origin and target not in seen):
                        queue.append((target, path + [{'url': target, 'via': 'internal_link',
                            'label': link['text'][:200] or 'Link sem texto'}]))
            except (OSError, ValueError) as error:
                pages.append({'url': url, 'status': 'error', 'error': str(error)[:500],
                              'navigation_path': path, 'renderings': []})
        for page in pages:
            if (page.get('inspection', {}).get('page') is not None
                    and any(screen.get('status') == 'ok' for screen in page['renderings'])):
                journeys.append({
                    'status': 'observed_page_sequence',
                    'navigation_path': page['navigation_path'],
                    'result_url': page['url'],
                    'viewports': [rendering['viewport']['name'] for rendering in page['renderings']
                                  if rendering.get('status') == 'ok'],
                    'limitations': 'Não representa sessão real nem intenção confirmada de visitantes.',
                })
    finally:
        if browser_context:
            browser_context.__exit__(None, None, None)
    for page in pages:
        desktop = next((rendering for rendering in page.get('renderings', [])
                        if rendering.get('viewport', {}).get('name') == 'desktop'), None)
        mobile = next((rendering for rendering in page.get('renderings', [])
                       if rendering.get('viewport', {}).get('name') == 'mobile'), None)
        if desktop and mobile and desktop.get('status') == mobile.get('status') == 'ok':
            desktop_headings = [heading['text'] for heading in desktop['headings']]
            mobile_headings = [heading['text'] for heading in mobile['headings']]
            desktop_links = {(link['url'], link['text']) for link in desktop['links']}
            mobile_links = {(link['url'], link['text']) for link in mobile['links']}
            desktop_controls = {control['label'] for control in desktop['controls'] if control['label']}
            mobile_controls = {control['label'] for control in mobile['controls'] if control['label']}
            page['viewport_comparison'] = {
                'title_changed': desktop['title'] != mobile['title'],
                'desktop_only_headings': [text for text in desktop_headings if text not in mobile_headings],
                'mobile_only_headings': [text for text in mobile_headings if text not in desktop_headings],
                'desktop_only_links': [{'url': url, 'text': text} for url, text in sorted(desktop_links - mobile_links)],
                'mobile_only_links': [{'url': url, 'text': text} for url, text in sorted(mobile_links - desktop_links)],
                'desktop_only_controls': sorted(desktop_controls - mobile_controls),
                'mobile_only_controls': sorted(mobile_controls - desktop_controls),
                'text_length': {'desktop': len(desktop['text']), 'mobile': len(mobile['text'])},
                'screenshot_visual_diff_computed': False,
            }
    return {
        'query': query, 'language': language, 'discovery': discovery,
        'viewports': VIEWPORTS, 'max_pages': max_pages, 'pages': pages, 'journeys': journeys,
    }
