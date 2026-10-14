"""Descoberta de palavras-chave do corpus extraído, pela CLI pública e sem rede."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from seo_agent.__main__ import main


HORTA_HTML = '''<html lang="pt-BR"><head><title>Guia de horta em casa</title></head><body>
<h1>Horta em casa</h1>
<p>Uma horta em casa cabe na varanda: escolha horta em casa com vasos fundos.</p>
<h2>Como plantar em vaso?</h2>
<p>Prepare o substrato antes. Quanto tempo leva para germinar em casa? Depende da temperatura.</p>
</body></html>'''

PLANTAR_HTML = '''<html lang="pt-BR"><head><title>Como plantar mudas</title></head><body>
<h1>Como plantar mudas</h1>
<p>Quem quer horta em casa precisa de adubo organico: horta em casa pede adubo organico a cada trinta dias.</p>
<h2>Quando regar?</h2>
<p>Regue pela manhã. Quanto tempo leva para germinar? Poucos dias.</p>
</body></html>'''


class KeywordsCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = self.directory / 'history.sqlite3'
        self.project_file = self.directory / 'project.json'
        self.project = {'id': 'horta', 'business_context': 'Loja de plantas',
                        'audience': 'Moradores locais', 'language': 'pt-BR', 'geography': 'Brasil',
                        'keywords': ['horta', 'adubo organico'], 'content_goal': 'Planejar guias úteis'}
        self.project_file.write_text(json.dumps(self.project), encoding='utf-8')

    def invoke(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(list(arguments))
        return json.loads(stdout.getvalue())

    def invoke_error(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(list(arguments))
        self.assertEqual(raised.exception.code, 2)
        return stderr.getvalue()

    def record_extraction(self, sources):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': sources})
        return self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))

    def extracted_sources(self):
        from seo_agent.page import extract_page
        return [
            {'id': 'fonte-horta', 'url': 'https://example.org/horta',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(HORTA_HTML, 'https://example.org/horta')},
            {'id': 'fonte-plantar', 'url': 'https://example.org/plantar',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(PLANTAR_HTML, 'https://example.org/plantar')},
        ]

    def test_discover_without_any_collected_urls_points_to_search_first(self):
        self.invoke('prepare', '--project', str(self.project_file), '--store', str(self.store))
        error = self.invoke_error('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma URL coletada', error)
        self.assertIn('run', error)
        self.assertNotIn('Traceback', error)
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 1)

    def test_discover_after_collection_without_extraction_points_to_extract(self):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': self.extracted_sources()})
        error = self.invoke_error('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma extração registrada', error)
        self.assertIn('extract', error)
        self.assertNotIn('Traceback', error)

    def discovered(self, record, kind, term):
        matches = [item for item in record['result']['discovered']
                   if item['kind'] == kind and item['term'] == term]
        self.assertEqual(len(matches), 1, f'Esperava um item {kind} {term!r}: {matches}')
        return matches[0]

    def test_discover_long_tail_ngrams_with_frequency_and_corpus_sources(self):
        extraction = self.record_extraction(self.extracted_sources())
        record = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'discovered')
        self.assertEqual(record['project_id'], 'horta')
        self.assertNotEqual(record['run_id'], extraction['run_id'])
        self.assertTrue(record['created_at'])
        self.assertEqual(record['result']['extraction_run_id'], extraction['run_id'])
        horta, plantar = 'https://example.org/horta', 'https://example.org/plantar'
        horta_em_casa = self.discovered(record, 'long_tail', 'horta em casa')
        self.assertEqual(horta_em_casa['frequency'], 5)
        self.assertEqual(horta_em_casa['sources'], [horta, plantar])
        como_plantar = self.discovered(record, 'long_tail', 'como plantar')
        self.assertEqual(como_plantar['frequency'], 2)
        self.assertEqual(como_plantar['sources'], [horta, plantar])
        adubo = self.discovered(record, 'long_tail', 'adubo organico')
        self.assertEqual(adubo['frequency'], 2)
        self.assertEqual(adubo['sources'], [plantar])
        terms = [item['term'] for item in record['result']['discovered']]
        self.assertNotIn('vasos fundos', terms)
        self.assertNotIn('em casa', terms)
        self.assertNotIn('com vasos', terms)
        self.assertNotIn('para germinar', terms)
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(runs[-1], record)

    def test_discovery_marks_new_terms_against_project_keywords(self):
        self.project['keywords'] = ['Horta', 'ADUBO ORGANICO!']
        self.record_extraction(self.extracted_sources())
        record = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['result']['project_keywords'], ['Horta', 'ADUBO ORGANICO!'])
        self.assertFalse(self.discovered(record, 'long_tail', 'adubo organico')['is_new'])
        self.assertTrue(self.discovered(record, 'long_tail', 'horta em casa')['is_new'])
        self.assertTrue(self.discovered(record, 'long_tail', 'como plantar')['is_new'])

    def test_questions_found_in_page_text_come_with_sources(self):
        self.record_extraction(self.extracted_sources())
        record = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        horta, plantar = 'https://example.org/horta', 'https://example.org/plantar'
        pergunta_horta = self.discovered(record, 'question', 'como plantar em vaso')
        self.assertEqual(pergunta_horta['frequency'], 1)
        self.assertEqual(pergunta_horta['sources'], [horta])
        self.assertEqual(
            self.discovered(record, 'question', 'quanto tempo leva para germinar em casa')['sources'],
            [horta])
        self.assertEqual(
            self.discovered(record, 'question', 'quanto tempo leva para germinar')['sources'], [plantar])
        self.assertEqual(self.discovered(record, 'question', 'quando regar')['sources'], [plantar])
        questions = [item['term'] for item in record['result']['discovered'] if item['kind'] == 'question']
        self.assertEqual(questions, ['como plantar em vaso', 'quando regar',
                                     'quanto tempo leva para germinar',
                                     'quanto tempo leva para germinar em casa'])

    def test_co_occurring_terms_across_pages_come_with_both_sources(self):
        self.record_extraction(self.extracted_sources())
        record = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        horta, plantar = 'https://example.org/horta', 'https://example.org/plantar'
        pair = self.discovered(record, 'co_occurrence', 'casa + horta')
        self.assertEqual(pair['frequency'], 2)
        self.assertEqual(pair['sources'], [horta, plantar])
        self.assertEqual(self.discovered(record, 'co_occurrence', 'quanto + tempo')['sources'],
                         [horta, plantar])
        terms = [item['term'] for item in record['result']['discovered']
                 if item['kind'] == 'co_occurrence']
        self.assertNotIn('adubo + organico', terms)
        self.assertNotIn('vasos + fundos', terms)

    def test_rediscovery_over_same_extraction_is_identical(self):
        self.record_extraction(self.extracted_sources())
        first = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        second = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(first['result'], second['result'])
        self.assertEqual(first['status'], second['status'])
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertNotEqual(first['created_at'], second['created_at'])

    def test_limit_flag_caps_output_to_the_leading_terms(self):
        self.record_extraction(self.extracted_sources())
        full = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertGreater(len(full['result']['discovered']), 3)
        capped = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store),
                             '--limit', '3')
        self.assertEqual(capped['result']['discovered'], full['result']['discovered'][:3])
        empty = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store),
                            '--limit', '0')
        self.assertEqual(empty['result']['discovered'], [])

    def test_negative_limit_is_rejected(self):
        self.record_extraction(self.extracted_sources())
        error = self.invoke_error('keywords', '--project-id', 'horta', '--store', str(self.store),
                                  '--limit', '-1')
        self.assertIn('limite de termos não pode ser negativo', error)
        self.assertNotIn('Traceback', error)

    def test_partial_failure_excludes_url_and_keeps_others_with_provenance(self):
        sources = self.extracted_sources() + [
            {'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None},
        ]
        self.record_extraction(sources)
        record = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'discovered')
        self.assertEqual(record['result']['excluded'], [
            {'url': 'https://example.org/broken', 'failures': [
                {'stage': 'page', 'error': 'Página preservada ausente ou ilegível no histórico desta fonte.'}]},
        ])
        corpus = {'https://example.org/horta', 'https://example.org/plantar'}
        for item in record['result']['discovered']:
            self.assertTrue(item['sources'], f'Termo sem fonte: {item}')
            self.assertTrue(set(item['sources']) <= corpus, f'Fonte fora do corpus: {item}')
        self.assertNotIn('https://example.org/broken',
                         json.dumps(record['result']['discovered']))

    def test_extraction_without_valid_sources_is_empty_status_not_error(self):
        self.record_extraction([{'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
                                 'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None}])
        record = self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'empty')
        self.assertEqual(record['result']['discovered'], [])
        self.assertEqual(len(record['result']['excluded']), 1)


if __name__ == '__main__':
    unittest.main()
