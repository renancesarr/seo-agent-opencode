"""Rede de conhecimento derivada das extrações, pela CLI pública e sem rede."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from seo_agent.__main__ import main


HORTA_HTML = '''<html lang="pt-BR"><head><title>Guia de horta em casa</title></head><body>
<h1>Horta em casa</h1>
<p>Cultivar uma horta em casa exige escolher vasos com boa drenagem, posicionar as
plantas onde recebam sol da manhã e regar sem encharcar as raízes. Comece pelas
folhas fáceis, como alface e cebolinha, antes de investir em tomates e pimentas,
que pedem mais espaço, tutors e paciência contra pragas comuns de varanda.</p>
<h2>Como plantar</h2>
<p>Para plantar, prepare um substrato leve com terra vegetal e composto orgânico,
faça a cova com a profundidade do torrão da muda e firme o solo ao redor sem
compactar. Regue no dia do plantio e mantenha a umidade nos dias seguintes,
observando se as folhas mantêm cor firme e sem bordas ressecadas pelo calor.</p>
<a href="https://example.org/plantar">Como plantar</a>
<a href="https://externo.org/dicas">Dicas externas</a>
</body></html>'''

PLANTAR_HTML = '''<html lang="pt-BR"><head><title>Como plantar mudas</title></head><body>
<h1>Como plantar</h1>
<p>Plantar mudas em vaso começa pela escolha do recipiente: cada espécie pede uma
proporção entre raiz, altura e volume de água. Verifique os furos de drenagem
antes de adicionar argila expandida e deixe a muda se aclimatar à meia-sombra
por alguns dias antes de levá-la ao sol pleno, reduzindo o estresse de transplante.</p>
<h2>Adubar</h2>
<p>Adubar a cada trinta dias alterna cobertura orgânica com adubo líquido diluído,
sempre sobre o solo úmido, nunca seco, para não queimar as raízes finas próximas
à superfície. Sinais de falta de nutriente incluem folhas pálidas e crescimento
lento; excesso escurece as pontas e atrai fungos ao redor do colo da planta.</p>
<a href="/horta">Guia de horta</a>
</body></html>'''


class NetworkCLI(unittest.TestCase):
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

    def test_build_without_any_collected_urls_points_to_search_first(self):
        self.invoke('prepare', '--project', str(self.project_file), '--store', str(self.store))
        error = self.invoke_error('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma URL coletada', error)
        self.assertIn('run', error)
        self.assertNotIn('Traceback', error)
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 1)

    def test_build_after_collection_without_extraction_points_to_extract(self):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': self.extracted_sources()})
        error = self.invoke_error('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma extração registrada', error)
        self.assertIn('extract', error)
        self.assertNotIn('Traceback', error)

    def test_network_record_references_the_extraction_run_of_origin(self):
        extraction = self.record_extraction(self.extracted_sources())
        built = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(built['result']['extraction_run_id'], extraction['run_id'])
        rebuilt = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(rebuilt['result']['extraction_run_id'], extraction['run_id'])

    def test_compact_limits_terms_and_links_to_the_leading_ones(self):
        headings = ''.join(f'<h2>Tema diferente numero {number:02d}</h2>' for number in range(30))
        page = {'title': 'Muitos temas', 'headings': [{'level': 2, 'text': f'Tema diferente numero {number:02d}'}
                                                      for number in range(30)], 'links': [], 'text': 'x ' * 400}
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': [
            {'id': 'fonte-temas', 'url': 'https://example.org/temas',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': page}]})
        self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))
        self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        compact = self.invoke('network', 'query', '--project-id', 'horta', '--store', str(self.store),
                              '--compact')['compact']
        self.assertEqual(compact['counts']['terms'], 30)
        self.assertEqual(len(compact['top_terms']), 20)
        again = self.invoke('network', 'query', '--project-id', 'horta', '--store', str(self.store),
                            '--compact')['compact']
        self.assertEqual(compact['top_terms'], again['top_terms'])

    def test_build_derives_pages_terms_and_links_with_sources(self):
        extraction = self.record_extraction(self.extracted_sources())
        record = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'built')
        self.assertEqual(record['project_id'], 'horta')
        self.assertNotEqual(record['run_id'], extraction['run_id'])
        self.assertTrue(record['created_at'])
        network = record['result']['network']
        self.assertEqual(record['result']['excluded'], [])
        horta = 'https://example.org/horta'
        plantar = 'https://example.org/plantar'
        self.assertEqual(network['entities'], [
            {'type': 'page', 'id': horta, 'source_id': 'fonte-horta',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'sources': [horta]},
            {'type': 'page', 'id': plantar, 'source_id': 'fonte-plantar',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'sources': [plantar]},
            {'type': 'term', 'id': 'adubar', 'sources': [plantar]},
            {'type': 'term', 'id': 'como plantar', 'sources': [horta, plantar]},
            {'type': 'term', 'id': 'horta em casa', 'sources': [horta]},
        ])
        self.assertEqual(network['relations'], [
            {'type': 'has_term', 'from': horta, 'to': 'como plantar', 'sources': [horta]},
            {'type': 'has_term', 'from': horta, 'to': 'horta em casa', 'sources': [horta]},
            {'type': 'has_term', 'from': plantar, 'to': 'adubar', 'sources': [plantar]},
            {'type': 'has_term', 'from': plantar, 'to': 'como plantar', 'sources': [plantar]},
            {'type': 'links_to', 'from': horta, 'to': plantar, 'sources': [horta]},
            {'type': 'links_to', 'from': plantar, 'to': horta, 'sources': [plantar]},
        ])
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(runs[-1], record)

    def test_link_with_fragment_creates_relation_to_the_collected_page(self):
        from seo_agent.page import extract_page
        html = ('<html><body><h1>Guia</h1><p>Veja os horários completos em outra página.</p>'
                '<a href="https://example.org/plantar#horarios">Horários</a></body></html>')
        sources = [
            {'id': 'fonte-guia', 'url': 'https://example.org/guia',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(html, 'https://example.org/guia')},
            {'id': 'fonte-plantar', 'url': 'https://example.org/plantar',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page('<html><body><h1>Plantar</h1><p>Conteúdo.</p></body></html>',
                                  'https://example.org/plantar')},
        ]
        self.record_extraction(sources)
        record = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        relations = record['result']['network']['relations']
        self.assertIn({'type': 'links_to', 'from': 'https://example.org/guia',
                       'to': 'https://example.org/plantar', 'sources': ['https://example.org/guia']},
                      relations)

    def test_rebuild_over_same_extraction_is_identical(self):
        self.record_extraction(self.extracted_sources())
        first = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        second = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(first['result'], second['result'])
        self.assertEqual(first['status'], second['status'])
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertNotEqual(first['created_at'], second['created_at'])

    def test_partial_failure_excludes_url_with_recorded_failure_and_keeps_others(self):
        sources = self.extracted_sources() + [
            {'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None},
        ]
        self.record_extraction(sources)
        record = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'built')
        network = record['result']['network']
        urls = [entity['id'] for entity in network['entities'] if entity['type'] == 'page']
        self.assertEqual(urls, ['https://example.org/horta', 'https://example.org/plantar'])
        self.assertNotIn('https://example.org/broken', json.dumps(network))
        self.assertEqual(record['result']['excluded'], [
            {'url': 'https://example.org/broken', 'failures': [
                {'stage': 'page', 'error': 'Página preservada ausente ou ilegível no histórico desta fonte.'}]},
        ])

    def test_extraction_without_valid_sources_is_empty_status_not_error(self):
        self.record_extraction([{'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
                                 'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None}])
        record = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'empty')
        self.assertEqual(record['result']['network'], {'entities': [], 'relations': []})
        self.assertEqual(len(record['result']['excluded']), 1)

    def test_query_returns_persisted_network_verbatim(self):
        self.record_extraction(self.extracted_sources())
        built = self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        queried = self.invoke('network', 'query', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(queried, built)

    def test_query_without_network_fails_pointing_to_build(self):
        self.record_extraction(self.extracted_sources())
        error = self.invoke_error('network', 'query', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma rede registrada', error)
        self.assertIn('network build', error)
        self.assertNotIn('Traceback', error)

    def test_every_fact_in_full_and_compact_queries_carries_corpus_source_urls(self):
        sources = self.extracted_sources() + [
            {'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None},
        ]
        self.record_extraction(sources)
        self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        full = self.invoke('network', 'query', '--project-id', 'horta', '--store', str(self.store))
        compact = self.invoke('network', 'query', '--project-id', 'horta', '--store', str(self.store),
                              '--compact')
        network = full['result']['network']
        pages = {entity['id'] for entity in network['entities'] if entity['type'] == 'page'}
        ids = {entity['id'] for entity in network['entities']}
        facts = list(network['entities']) + list(network['relations']) \
            + list(compact['compact']['top_terms']) + list(compact['compact']['page_links'])
        for fact in facts:
            self.assertTrue(fact.get('sources'), f'Fato sem fonte: {fact}')
            self.assertTrue(set(fact['sources']) <= pages, f'Fonte fora do corpus: {fact}')
        for relation in network['relations']:
            self.assertIn(relation['from'], ids)
            self.assertIn(relation['to'], ids)
        self.assertNotEqual(pages, set())
        self.assertNotIn('https://example.org/broken', pages)

    def test_compact_query_is_smaller_than_raw_page_text(self):
        extraction = self.record_extraction(self.extracted_sources())
        self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        compact = self.invoke('network', 'query', '--project-id', 'horta', '--store', str(self.store),
                              '--compact')
        self.assertEqual(compact['status'], 'built')
        self.assertEqual(compact['compact']['counts'],
                         {'pages': 2, 'terms': 3, 'page_links': 2, 'term_relations': 4})
        [top_term] = [term for term in compact['compact']['top_terms'] if term['term'] == 'como plantar']
        self.assertEqual(top_term['pages'], 2)
        raw_text = sum(len(item['page']['text']) for item in extraction['result']['extractions'])
        self.assertLess(len(json.dumps(compact, ensure_ascii=False)), raw_text)


if __name__ == '__main__':
    unittest.main()
