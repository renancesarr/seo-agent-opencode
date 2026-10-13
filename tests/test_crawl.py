"""Processo automático com busca, fronteira de domínio e navegador substituível."""

import json
import unittest
from types import SimpleNamespace
from urllib.parse import urlsplit

from seo_agent.web import crawl_web


def page_response(url, html, status=200):
    return SimpleNamespace(url=url, status=status, headers={'content-type': 'text/html'},
        body=html.encode(), redirects=[], ip_addresses=['93.184.216.34'], tls=None,
        text=lambda: html)


class Browser:
    def __init__(self, screens):
        self.screens = screens
        self.visited = []

    def render(self, url, viewport, evidence_dir, *, locale="pt-BR", navigation_path=None):
        self.visited.append((url, viewport['name']))
        return self.screens[url] | {'status': 'ok', 'viewport': viewport,
            'screenshot': f'{urlsplit(url).path}-{viewport["name"]}.png',
            'navigation_steps': [{'url': step['url'], 'action': 'open' if index == 0 else 'click_internal_link',
                'label': step['label'], 'result': 'loaded'} for index, step in enumerate(navigation_path or [])]}


class CrawlTests(unittest.TestCase):
    def test_discovers_pages_follows_observed_internal_links_and_compares_viewports(self):
        html = {
            'https://garden.example/': '<title>Hortas</title><h1>Hortas</h1><a href="/buscar">Buscar hortas</a>'
                                       '<a href="https://external.example/">External</a>',
            'https://garden.example/buscar': '<title>Buscar</title><h1>Resultados</h1><a href="/detalhe">Detalhes</a>',
            'https://garden.example/detalhe': '<title>Detalhe</title><h1>Horta central</h1>',
            'https://other.example/': '<h1>Outro domínio</h1>',
            'https://garden.example/robots.txt': 'User-agent: *\nAllow: /',
            'https://garden.example/sitemap.xml': '<urlset/>',
            'https://other.example/robots.txt': 'User-agent: *\nDisallow: /',
        }
        def fetch(url, **options):
            if '/search?' in url:
                return page_response(url, json.dumps({'results': [
                    {'url': 'https://garden.example/', 'title': 'Hortas'},
                    {'url': 'https://other.example/', 'title': 'Outro'},
                ]}), status=200)
            if url not in html:
                raise AssertionError(f'URL não prevista: {url}')
            return page_response(url, html[url], status=404 if url.endswith('/sitemap.xml') else 200)
        screens = {url: {'title': 'JS ' + urlsplit(url).path, 'text': 'Conteúdo hidratado por JavaScript',
                         'headings': [{'level': 1, 'text': 'Experiência'}], 'links': [], 'controls': []}
                   for url in html if not url.endswith(('/robots.txt', '/sitemap.xml'))}
        screens['https://garden.example/']['links'] = [
            {'url': 'https://garden.example/buscar', 'text': 'Buscar hortas', 'internal': True}]
        screens['https://garden.example/buscar']['links'] = [
            {'url': 'https://garden.example/detalhe', 'text': 'Detalhes', 'internal': True}]
        browser = Browser(screens)
        result = crawl_web('como plantar', limit=2, max_pages=4, fetch=fetch, browser=browser,
                           evidence_dir='evidence')
        self.assertEqual([page['url'] for page in result['pages']], [
            'https://garden.example/', 'https://other.example/',
            'https://garden.example/buscar', 'https://garden.example/detalhe',
        ])
        self.assertFalse(any('external.example' in url for url, _ in browser.visited))
        self.assertEqual(len(browser.visited), 6)
        self.assertEqual([screen['name'] for screen in result['viewports']], ['desktop', 'mobile'])
        garden_page = result['pages'][0]
        self.assertEqual([screen['text'] for screen in garden_page['renderings']], [
            'Conteúdo hidratado por JavaScript', 'Conteúdo hidratado por JavaScript'])
        self.assertEqual(garden_page['navigation_path'], [
            {'url': 'https://garden.example/', 'via': 'search_result', 'label': 'Resultado da busca'},
        ])
        detalle = result['pages'][3]
        self.assertEqual(detalle['navigation_path'][-1], {
            'url': 'https://garden.example/detalhe', 'via': 'internal_link', 'label': 'Detalhes',
        })
        self.assertEqual(result['journeys'][0]['status'], 'observed_page_sequence')
        self.assertIn('Não representa sessão real', result['journeys'][0]['limitations'])

    def test_skips_page_when_robots_denies_crawl_without_opening_it_in_browser(self):
        requested = []
        def fetch(url, **options):
            requested.append(url)
            if url.endswith('/robots.txt'):
                return page_response(url, 'User-agent: *\nDisallow: /', 200)
            if url.endswith('/sitemap.xml'):
                return page_response(url, '', 404)
            return page_response(url, '<h1>Não visitar</h1>')
        browser = Browser({})
        result = crawl_web('private', limit=1, max_pages=2,
            fetch=lambda url, **opts: (page_response(url, '{"results": []}', 200)
                if '/search?' in url else fetch(url, **opts)),
            browser=browser)
        # A busca vazia não inventa URLs, portanto não consulta robots nem navegador.
        self.assertEqual(result['pages'], [])
        self.assertEqual(browser.visited, [])

    def test_reports_empty_search_without_starting_browser(self):
        browser = Browser({})
        result = crawl_web('nothing', limit=2, browser=browser,
            fetch=lambda url, **opts: page_response(url, '{"results": []}'))
        self.assertEqual(result['pages'], [])
        self.assertEqual(result['journeys'], [])
        self.assertEqual(browser.visited, [])

    def test_rejects_unbounded_limits_before_search(self):
        def unexpected(*args, **kwargs):
            self.fail('Limites inválidos não devem pesquisar')
        for limit, max_pages in [(0, 1), (1, 0), (21, 1), (1, 21)]:
            with self.subTest(limit=limit, max_pages=max_pages), self.assertRaises(ValueError):
                crawl_web('horta', limit=limit, max_pages=max_pages, fetch=unexpected)


if __name__ == '__main__':
    unittest.main()
