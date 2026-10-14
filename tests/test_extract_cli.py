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


if __name__ == '__main__':
    unittest.main()
