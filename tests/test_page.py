"""Aceite da extração estática de HTML pela interface pública."""

import json
import unittest

from seo_agent.page import extract_page


class PageExtraction(unittest.TestCase):
    def test_extracts_metadata_and_visible_text_without_script_or_hidden_content(self):
        page = extract_page('''
            <html lang="pt-BR"><head>
              <title> Guia   de hortas </title>
              <meta name="description" content=" Cultive  em casa. ">
              <style>.anything { color: red }</style>
            </head><body>
              <h1>Horta <em>em casa</em></h1>
              <p>Cultive alimentos inter<strong>nacionais</strong>.</p>
              <div hidden><h2>Oculto</h2><p>Segredo</p></div>
              <script>window.secret = 'invisível';</script>
              <template><p>Modelo invisível</p></template>
            </body></html>
        ''', 'https://example.org/guia')
        self.assertEqual(page['title'], 'Guia de hortas')
        self.assertEqual(page['description'], 'Cultive em casa.')
        self.assertEqual(page['language'], 'pt-BR')
        self.assertEqual(page['headings'], [{'level': 1, 'text': 'Horta em casa'}])
        self.assertEqual(page['text'], 'Horta em casa Cultive alimentos internacionais.')

    def test_resolves_http_links_and_metadata_using_first_base_href(self):
        page = extract_page('''
            <html><head>
              <base href="https://example.org/guias/">
              <base href="https://ignored.example/">
              <link rel="canonical" href="horta">
              <link rel="alternate" hreflang="en" href="../en/garden">
              <meta name="robots" content="noindex, follow">
              <meta property="og:title" content="Guia de hortas">
              <meta name="twitter:card" content="summary">
            </head><body>
              <a href="plantar" rel="nofollow sponsored">Como <b>plantar</b></a>
              <a href="//other.example/curso">Curso</a>
              <a href="mailto:info@example.org">Contato</a>
              <a href="javascript:alert(1)">Ação</a>
              <div hidden><a href="secreto">Oculto</a></div>
            </body></html>
        ''', 'https://example.org/inicio')
        self.assertEqual(page['canonical'], 'https://example.org/guias/horta')
        self.assertEqual(page['hreflang'], [{'language': 'en', 'url': 'https://example.org/en/garden'}])
        self.assertEqual(page['robots'], ['noindex, follow'])
        self.assertEqual(page['social'], {'og:title': 'Guia de hortas', 'twitter:card': 'summary'})
        self.assertEqual(page['links'], [
            {'url': 'https://example.org/guias/plantar', 'text': 'Como plantar',
             'rel': ['nofollow', 'sponsored'], 'internal': True},
            {'url': 'https://other.example/curso', 'text': 'Curso', 'rel': [], 'internal': False},
        ])

    def test_extracts_json_ld_objects_and_reports_invalid_blocks_without_losing_valid_data(self):
        page = extract_page('''
            <head>
              <script type="application/ld+json">{"@type":"Article","name":"Horta"}</script>
              <script type="application/ld+json">[{"@type":"Organization"}]</script>
              <script type="application/ld+json">{broken</script>
              <script type="application/ld+json">42</script>
              <script type="application/ld+json">{"value":NaN}</script>
            </head><body><h1>Guia</h1></body>
        ''', 'https://example.org/')
        self.assertEqual(page['structured_data'], [
            {'@type': 'Article', 'name': 'Horta'}, {'@type': 'Organization'},
        ])
        self.assertEqual(len(page['structured_data_errors']), 3)
        self.assertTrue(all(isinstance(error, str) and error for error in page['structured_data_errors']))
        self.assertEqual(page['text'], 'Guia')

    def test_distinguishes_missing_alt_from_decorative_images(self):
        page = extract_page('''
            <head><title>Horta</title><meta name="description" content="Guia.">
              <base href="https://example.org/guias/">
              <link rel="canonical" href="horta"></head>
            <body><h1>Horta</h1>
              <img src="folha.svg" alt="">
              <img src="plantas.jpg" alt="Vasos de plantas">
              <img src="foto.jpg">
              <div hidden><img src="oculta.jpg"></div>
            </body>
        ''', 'https://example.org/')
        self.assertEqual(page['images'], [
            {'src': 'https://example.org/guias/folha.svg', 'alt': ''},
            {'src': 'https://example.org/guias/plantas.jpg', 'alt': 'Vasos de plantas'},
            {'src': 'https://example.org/guias/foto.jpg', 'alt': None},
        ])
        self.assertEqual(len(page['issues']), 1)
        self.assertEqual(page['issues'][0]['code'], 'image_alt_missing')
        self.assertEqual(page['issues'][0]['evidence']['src'], 'https://example.org/guias/foto.jpg')

    def test_reports_objective_missing_elements_and_invalid_json_ld_without_a_score(self):
        page = extract_page('<p>Conteúdo.</p><script type="application/ld+json">{bad</script>',
                            'https://example.org/')
        self.assertEqual({issue['code'] for issue in page['issues']}, {
            'title_missing', 'description_missing', 'h1_missing', 'canonical_missing', 'invalid_json_ld',
        })
        for issue in page['issues']:
            self.assertEqual(set(issue), {'code', 'severity', 'message', 'evidence'})
            self.assertTrue(issue['message'])
            self.assertTrue(issue['evidence'])
        self.assertEqual(page['text'], 'Conteúdo.')
        self.assertNotIn('score', page)
        json.dumps(page, allow_nan=False)

    def test_keeps_line_breaks_in_captured_text_and_ignores_inert_template_metadata(self):
        page = extract_page('''
            <head><title>Horta</title><meta name="description" content="Guia."></head>
            <body><template>
              <base href="https://wrong.example/">
              <meta name="description" content="Não é a descrição da página">
              <script type="application/ld+json">{"@type":"NotOnPage"}</script>
            </template>
            <h1>Como<br>plantar</h1>
            <a href="horta"><span>Horta</span><div>local</div></a>
            </body>
        ''', 'https://example.org/')
        self.assertEqual(page['description'], 'Guia.')
        self.assertEqual(page['headings'], [{'level': 1, 'text': 'Como plantar'}])
        self.assertEqual(page['links'], [
            {'url': 'https://example.org/horta', 'text': 'Horta local', 'rel': [], 'internal': True},
        ])
        self.assertEqual(page['structured_data'], [])
        self.assertEqual(page['text'], 'Como plantar Horta local')

    def test_extracts_dates_and_authors_from_metadata_and_time_elements(self):
        page = extract_page('''
            <head>
              <meta name="author" content=" Maria Silva ">
              <meta property="article:published_time" content="2026-01-15T08:00:00+00:00">
              <meta property="article:modified_time" content="2026-02-01T10:30:00+00:00">
              <meta name="author" content="">
            </head><body>
              <time datetime=" 2026-01-15 ">15 de janeiro</time>
              <div hidden><time datetime="2099-01-01">Oculto</time></div>
            </body>
        ''', 'https://example.org/')
        self.assertEqual(page['authors'], [{'source': 'meta:author', 'value': 'Maria Silva'}])
        self.assertEqual(page['dates'], [
            {'source': 'meta:article:published_time', 'value': '2026-01-15T08:00:00+00:00'},
            {'source': 'meta:article:modified_time', 'value': '2026-02-01T10:30:00+00:00'},
            {'source': 'time', 'value': '2026-01-15'},
        ])

    def test_extracts_dates_and_authors_from_json_ld_including_graph(self):
        page = extract_page('''
            <head>
              <script type="application/ld+json">{"@type":"Article",
                "datePublished": "2026-03-01", "dateModified": "2026-03-02", "dateCreated": "2026-02-28",
                "author": [{"@type": "Person", "name": " Maria Silva "}, "João Souza", {"@type": "Organization"}]}</script>
              <script type="application/ld+json">{"@graph": [{"@type": "BlogPosting",
                "datePublished": "2026-03-01", "author": {"name": "Ana Lima"}}]}</script>
            </head>
        ''', 'https://example.org/')
        self.assertEqual(page['dates'], [
            {'source': 'json_ld:datePublished', 'value': '2026-03-01'},
            {'source': 'json_ld:dateModified', 'value': '2026-03-02'},
            {'source': 'json_ld:dateCreated', 'value': '2026-02-28'},
        ])
        self.assertEqual(page['authors'], [
            {'source': 'json_ld:author', 'value': 'Maria Silva'},
            {'source': 'json_ld:author', 'value': 'João Souza'},
            {'source': 'json_ld:author', 'value': 'Ana Lima'},
        ])

    def test_reports_noindex_metadata_with_its_agent_scope(self):
        page = extract_page('''<head>
            <meta name="robots" content="NOINDEX, follow">
            <meta name="googlebot" content="none">
            <meta name="googlebot" content="index, nofollow">
            </head>''', 'https://example.org/')
        observations = [issue for issue in page['issues'] if issue['code'] == 'meta_noindex']
        self.assertEqual([issue['evidence'] for issue in observations], [
            {'agent': 'robots', 'content': 'NOINDEX, follow'},
            {'agent': 'googlebot', 'content': 'none'},
        ])
        self.assertTrue(all(issue['severity'] == 'info' for issue in observations))
        self.assertEqual(page['robots'], ['NOINDEX, follow'])


if __name__ == '__main__':
    unittest.main()
