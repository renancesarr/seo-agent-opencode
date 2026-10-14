"""Extração determinística das URLs coletadas, pela CLI pública e sem rede."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from seo_agent.__main__ import main


GUIDE_HTML = '''
<html lang="pt-BR"><head>
  <title>Guia de hortas</title>
  <meta name="description" content=" Cultive  em casa. ">
  <meta name="author" content="Maria Silva">
  <meta property="article:published_time" content="2026-01-15T08:00:00+00:00">
  <link rel="canonical" href="https://example.org/guide">
  <meta property="og:title" content="Guia de hortas">
  <script type="application/ld+json">{"@type": "Article", "datePublished": "2026-01-15",
    "author": {"@type": "Person", "name": "Maria Silva"}}</script>
</head><body>
  <h1>Horta em casa</h1>
  <time datetime="2026-01-15">15 de janeiro</time>
  <p>Cultive alimentos em vasos.</p>
  <a href="/plantar">Como plantar</a>
  <img src="vasos.jpg" alt="Vasos de plantas">
</body></html>
'''


class ExtractCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = self.directory / 'history.sqlite3'
        self.project_file = self.directory / 'project.json'
        self.project = {'id': 'horta', 'business_context': 'Loja de plantas',
                        'audience': 'Moradores locais', 'language': 'pt-BR', 'geography': 'Brasil',
                        'keywords': ['horta'], 'content_goal': 'Planejar guias úteis'}
        self.project_file.write_text(json.dumps(self.project), encoding='utf-8')

    def invoke(self, *arguments, **services):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            main(list(arguments), **services)
        return json.loads(stdout.getvalue())

    def collect(self, html=GUIDE_HTML):
        def search(query):
            return [{'url': 'https://example.org/guide', 'title': 'Guia', 'buscador': ['fixture']}]
        def fetch(url):
            return SimpleNamespace(url=url, status=200, headers={'content-type': 'text/html'},
                                   text=lambda: html)
        return self.invoke('run', '--project', str(self.project_file), '--store', str(self.store),
                           '--interval-seconds', '0', providers=[search], fetch=fetch)

    def test_project_without_collected_urls_reports_no_sources_and_records_nothing(self):
        prepared = self.invoke('prepare', '--project', str(self.project_file), '--store', str(self.store))
        result = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(result['status'], 'no_sources')
        self.assertIn('run', result['message'])
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(runs, [prepared])

    def test_unknown_project_history_without_store_is_also_no_sources(self):
        result = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(result['status'], 'no_sources')
        self.assertFalse(self.store.exists())

    def test_extracts_all_deterministic_signals_per_url_and_preserves_execution(self):
        collected = self.collect()
        source = collected['result']['sources'][0]
        record = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'extracted')
        self.assertEqual(record['project_id'], 'horta')
        self.assertNotEqual(record['run_id'], collected['run_id'])
        self.assertTrue(record['created_at'])
        [extraction] = record['result']['extractions']
        self.assertEqual(extraction['url'], 'https://example.org/guide')
        self.assertEqual(extraction['source_id'], source['id'])
        self.assertEqual(extraction['retrieved_at'], source['retrieved_at'])
        self.assertEqual(extraction['failures'], [])
        page = extraction['page']
        self.assertEqual(page['title'], 'Guia de hortas')
        self.assertEqual(page['description'], 'Cultive em casa.')
        self.assertEqual(page['language'], 'pt-BR')
        self.assertEqual(page['canonical'], 'https://example.org/guide')
        self.assertEqual(page['headings'], [{'level': 1, 'text': 'Horta em casa'}])
        self.assertIn('Cultive alimentos em vasos.', page['text'])
        self.assertEqual(page['authors'], [
            {'source': 'meta:author', 'value': 'Maria Silva'},
            {'source': 'json_ld:author', 'value': 'Maria Silva'},
        ])
        self.assertEqual(page['dates'], [
            {'source': 'meta:article:published_time', 'value': '2026-01-15T08:00:00+00:00'},
            {'source': 'time', 'value': '2026-01-15'},
            {'source': 'json_ld:datePublished', 'value': '2026-01-15'},
        ])
        self.assertEqual(page['links'], [
            {'url': 'https://example.org/plantar', 'text': 'Como plantar', 'rel': [], 'internal': True},
        ])
        self.assertEqual(page['images'], [
            {'src': 'https://example.org/vasos.jpg', 'alt': 'Vasos de plantas'},
        ])
        self.assertEqual(page['structured_data'], [
            {'@type': 'Article', 'datePublished': '2026-01-15',
             'author': {'@type': 'Person', 'name': 'Maria Silva'}},
        ])
        self.assertEqual(page['social'], {'og:title': 'Guia de hortas'})
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(runs, [collected, record])

    def test_partial_failure_by_url_preserves_others_and_absence_is_not_error(self):
        from seo_agent.__main__ import prepare_run
        from seo_agent.page import extract_page
        sources = [
            {'id': 'fonte-valida', 'url': 'https://example.org/valid',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page('<title>Simples</title><p>Sem autor e sem datas.</p>',
                                  'https://example.org/valid')},
            {'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None},
        ]
        prepare_run(self.project, self.store, status='partial', result={'sources': sources})
        record = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'partial')
        self.assertEqual([item['url'] for item in record['result']['extractions']],
                         ['https://example.org/broken', 'https://example.org/valid'])
        broken, valid = record['result']['extractions']
        self.assertEqual(valid['failures'], [])
        self.assertEqual(valid['page']['authors'], [])
        self.assertEqual(valid['page']['dates'], [])
        self.assertNotIn('page', broken)
        self.assertEqual(broken['source_id'], 'fonte-quebrada')
        self.assertEqual(broken['failures'], [
            {'stage': 'page', 'error': 'Página preservada ausente ou ilegível no histórico desta fonte.'},
        ])
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[-1], record)

    def test_empty_preserved_page_is_a_page_failure_not_readable(self):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='partial', result={'sources': [
            {'id': 'fonte-vazia', 'url': 'https://example.org/empty',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': {}}]})
        record = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'partial')
        [extraction] = record['result']['extractions']
        self.assertNotIn('page', extraction)
        self.assertEqual(extraction['failures'], [
            {'stage': 'page', 'error': 'Página preservada ausente ou ilegível no histórico desta fonte.'},
        ])

    def test_invalid_structured_data_surfaces_as_stage_failure_without_breaking_the_url(self):
        from seo_agent.__main__ import prepare_run
        from seo_agent.page import extract_page
        page = extract_page('<title>Guia</title><p>Texto válido.</p>'
                            '<script type="application/ld+json">{invalido</script>',
                            'https://example.org/guide')
        self.assertTrue(page['structured_data_errors'])
        prepare_run(self.project, self.store, status='collected', result={'sources': [
            {'id': 'fonte-json-ld', 'url': 'https://example.org/guide',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': page}]})
        record = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'partial')
        [extraction] = record['result']['extractions']
        self.assertIn('page', extraction)
        [failure] = extraction['failures']
        self.assertEqual(failure['stage'], 'structured_data')
        self.assertEqual(failure['error'], page['structured_data_errors'][0])

    def test_reexecution_over_same_sources_is_identical_and_uses_latest_preserved_page(self):
        self.collect()
        second = self.collect(html='<title>Guia nova</title><h1>Horta</h1><p>Conteúdo atualizado.</p>')
        first_extract = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        second_extract = self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(first_extract['result'], second_extract['result'])
        self.assertEqual(first_extract['status'], second_extract['status'])
        self.assertNotEqual(first_extract['run_id'], second_extract['run_id'])
        self.assertNotEqual(first_extract['created_at'], second_extract['created_at'])
        [extraction] = first_extract['result']['extractions']
        self.assertEqual(extraction['page']['title'], 'Guia nova')
        self.assertEqual(extraction['retrieved_at'], second['result']['sources'][0]['retrieved_at'])
        self.assertEqual(len(self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']), 4)


if __name__ == '__main__':
    unittest.main()
