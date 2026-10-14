"""Busca e inspeção com respostas HTTP controladas, sem rede."""

import json
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from seo_agent.web import search_web, inspect_page


def response(url, body, status=200, content_type='text/html', headers=None):
    return SimpleNamespace(url=url, status=status, body=body.encode(),
                           headers={'content-type': content_type} | (headers or {}),
                           redirects=[], ip_addresses=['93.184.216.34'], tls=None,
                           text=lambda: body)


class SearchTests(unittest.TestCase):
    def test_search_preserves_query_evidence_and_deduplicates_urls(self):
        calls = []

        def fetch(url, **options):
            calls.append((url, options))
            return response(url, json.dumps({'results': [
                {'url': 'https://example.org/guia#top', 'title': 'Guia',
                 'content': 'Como plantar', 'engines': ['bing']},
                {'url': 'https://example.org/guia', 'title': 'Duplicado'},
                {'url': 'javascript:alert(1)'},
                {'url': 'https://other.example/artigo', 'title': 'Artigo'},
            ]}), content_type='application/json')

        result = search_web('horta em casa', limit=2, fetch=fetch)
        self.assertEqual(parse_qs(urlsplit(calls[0][0]).query),
                         {'q': ['horta em casa'], 'format': ['json'], 'language': ['pt-BR']})
        self.assertEqual(calls[0][1], {'allow_private': True})
        self.assertEqual(result['query'], 'horta em casa')
        self.assertEqual([item['observed_position'] for item in result['results']], [1, 4])
        self.assertEqual(result['results'][0]['url'], 'https://example.org/guia')
        self.assertEqual(result['results'][0]['snippet'], 'Como plantar')
        self.assertEqual(result['results'][0]['engines'], ['bing'])
        self.assertIn('retrieved_at', result)
        self.assertEqual(result['provider'], 'searxng')

    def test_search_reports_unavailable_json_or_malformed_provider_responses(self):
        for status, body, expected in [
            (403, 'Forbidden', 'search.formats'), (503, 'offline', 'HTTP 503'),
            (200, '<html>login</html>', 'JSON válido'), (200, '{}', 'results'),
        ]:
            with self.subTest(status=status, body=body):
                with self.assertRaisesRegex(ValueError, expected):
                    search_web('horta', fetch=lambda url, **kw: response(url, body, status))

    def test_empty_search_and_partial_engine_failure_remain_explicit(self):
        result = search_web('horta', fetch=lambda url, **kw: response(url,
            '{"results": [], "unresponsive_engines": [["bing", "timeout"]]}'))
        self.assertEqual(result['results'], [])
        self.assertEqual(result['unresponsive_engines'], [['bing', 'timeout']])

    def test_invalid_input_does_not_start_network(self):
        def unexpected(*args, **kwargs):
            self.fail('A entrada inválida não deve acessar a rede')
        for query, limit in [(' ', 5), ('horta', 0), ('horta', 21)]:
            with self.subTest(query=query, limit=limit), self.assertRaises(ValueError):
                search_web(query, limit=limit, fetch=unexpected)

    def test_rejects_endpoint_query_fragment_or_credentials_before_fetch(self):
        def unexpected(*args, **kwargs):
            self.fail('Endpoint inválido não deve acessar rede')
        for endpoint in ['http://localhost:8080/?q=x', 'http://localhost:8080/#x',
                         'http://user:password@localhost:8080', 'localhost:8080']:
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(ValueError, 'endpoint'):
                search_web('OpenCode', endpoint=endpoint, fetch=unexpected)


class InspectionTests(unittest.TestCase):
    def test_inspects_content_http_domain_robots_and_sitemap_without_crawling(self):
        calls = []
        pages = {
            'https://example.org/guia': response('https://example.org/guia',
                '<html lang="pt-BR"><head><title>Horta em casa</title></head>'
                '<body><h1>Plantar</h1><p>Use solo fértil.</p></body></html>',
                headers={'x-robots-tag': 'noindex'}),
            'https://example.org/robots.txt': response('https://example.org/robots.txt',
                'User-agent: *\nDisallow: /privado\nSitemap: https://example.org/mapa.xml',
                content_type='text/plain'),
            'https://example.org/mapa.xml': response('https://example.org/mapa.xml',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<url><loc>https://example.org/guia</loc><lastmod>2026-01-01</lastmod></url>'
                '</urlset>', content_type='application/xml'),
        }

        def fetch(url):
            calls.append(url)
            return pages[url]

        report = inspect_page('https://example.org/guia', fetch=fetch)
        self.assertEqual(report['status'], 'ok')
        self.assertEqual(report['page']['title'], 'Horta em casa')
        self.assertIn('Use solo fértil.', report['page']['text'])
        self.assertEqual(report['domain']['hostname'], 'example.org')
        self.assertEqual(report['domain']['ip_addresses'], ['93.184.216.34'])
        self.assertEqual(report['http']['headers']['x-robots-tag'], 'noindex')
        self.assertTrue(report['robots']['allowed_for_agent'])
        self.assertEqual(report['sitemap']['entries'], [
            {'url': 'https://example.org/guia', 'last_modified': '2026-01-01'}])
        self.assertEqual(report['sitemap']['kind'], 'urlset')
        self.assertEqual(calls, list(pages))
        self.assertFalse(report['javascript_rendered'])
        self.assertIn('http_noindex', [issue['code'] for issue in report['issues']])

    def test_auxiliary_failure_preserves_page_and_never_invents_sitemap_entries(self):
        def fetch(url):
            if url.endswith('/robots.txt'):
                raise OSError('timeout')
            if url.endswith('/sitemap.xml'):
                return response(url, '<html>Oops</html>')
            return response(url, '<h1>Conteúdo acessível</h1>')
        report = inspect_page('https://example.org/pagina', fetch=fetch)
        self.assertEqual(report['status'], 'partial')
        self.assertIn('Conteúdo acessível', report['page']['text'])
        self.assertIsNone(report['robots']['allowed_for_agent'])
        self.assertIn('timeout', report['robots']['error'])
        self.assertEqual(report['sitemap']['entries'], [])
        self.assertIn('inválido', report['sitemap']['error'])

    def test_index_is_reported_without_fetching_children_or_external_robots_sitemap(self):
        calls = []
        def fetch(url):
            calls.append(url)
            if url.endswith('/robots.txt'):
                return response(url, 'User-agent: *\nDisallow: /\nSitemap: https://foreign.example/s.xml')
            if url.endswith('/sitemap.xml'):
                return response(url, '<sitemapindex><sitemap><loc>https://example.org/child.xml</loc>'
                                '</sitemap></sitemapindex>')
            return response(url, '<h1>Página</h1>')
        report = inspect_page('https://example.org/pagina', fetch=fetch)
        self.assertFalse(report['robots']['allowed_for_agent'])
        self.assertEqual(report['sitemap']['kind'], 'sitemapindex')
        self.assertEqual(report['sitemap']['entries'][0]['url'], 'https://example.org/child.xml')
        self.assertEqual(calls, ['https://example.org/pagina', 'https://example.org/robots.txt',
                                 'https://example.org/sitemap.xml'])

    def test_http_errors_and_non_html_are_not_read_as_page_evidence(self):
        for status, content_type in [(404, 'text/html'), (200, 'application/pdf')]:
            with self.subTest(status=status, content_type=content_type):
                report = inspect_page('https://example.org/doc', fetch=lambda url:
                    response(url, 'Não é evidência da página', status, content_type))
                self.assertIsNone(report['page'])
                self.assertEqual(report['status'], 'partial')
                self.assertEqual(report['issues'][0]['severity'], 'error')

    def test_index_restrictions_preserve_bot_scopes_in_header_evidence(self):
        for header in ['noindex', 'follow, none', 'googlebot: none', 'bingbot: noindex']:
            with self.subTest(header=header):
                report = inspect_page('https://example.org/page', fetch=lambda url:
                    response(url, '<h1>Texto</h1>', headers={'x-robots-tag': header}))
                restriction = [issue for issue in report['issues'] if issue['code'] == 'http_noindex']
                self.assertEqual(len(restriction), 1)
                self.assertEqual(restriction[0]['evidence'], header)

    def test_robots_patterns_not_supported_by_evaluator_remain_unknown(self):
        def fetch(url):
            if url.endswith('/robots.txt'):
                return response(url, 'User-agent: *\nDisallow: /*?private=1$')
            if url.endswith('/sitemap.xml'):
                return response(url, '<urlset/>')
            return response(url, '<h1>Texto</h1>')
        report = inspect_page('https://example.org/page?private=1', fetch=fetch)
        self.assertIsNone(report['robots']['allowed_for_agent'])
        self.assertIn('evaluation_note', report['robots'])

    def test_sitemap_cap_and_dtd_rejection(self):
        for xml, error in [
            ('<!DOCTYPE urlset [<!ENTITY x "test">]><urlset/>', True),
            ('<urlset>' + ''.join(f'<url><loc>https://example.org/{i}</loc></url>'
                                 for i in range(501)) + '</urlset>', False),
        ]:
            def fetch(url):
                if url.endswith('/robots.txt'):
                    return response(url, '')
                if url.endswith('/sitemap.xml'):
                    return response(url, xml)
                return response(url, '<h1>Página</h1>')
            report = inspect_page('https://example.org/pagina', fetch=fetch)
            if error:
                self.assertIn('DTD', report['sitemap']['error'])
            else:
                self.assertEqual(len(report['sitemap']['entries']), 500)
                self.assertEqual(report['sitemap']['entry_count'], 501)
                self.assertTrue(report['sitemap']['truncated'])


if __name__ == '__main__':
    unittest.main()
