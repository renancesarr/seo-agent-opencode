"""Insights por LLM sobre a rede compacta, pela CLI pública e sem rede."""

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


class InsightsCLI(unittest.TestCase):
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
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            main(list(arguments), **services)
        return json.loads(stdout.getvalue())

    def invoke_error(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(list(arguments))
        self.assertEqual(raised.exception.code, 2)
        return stderr.getvalue()

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

    def record_extraction(self, sources):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': sources})
        return self.invoke('extract', '--project-id', 'horta', '--store', str(self.store))

    def build_pipeline(self):
        """Corpus completo: extração -> rede -> keywords -> classify -> rank."""
        self.record_extraction(self.extracted_sources())
        self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        self.invoke('keywords', '--project-id', 'horta', '--store', str(self.store))
        self.invoke('classify', '--project-id', 'horta', '--store', str(self.store))
        return self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))

    def insights(self):
        return {'existing': [{'description': 'Guia e tutorial cobrem plantio em casa',
                              'justification': 'Duas páginas tratam como plantar',
                              'kind': 'observation',
                              'references': ['https://example.org/horta', 'https://example.org/plantar'],
                              'terms': ['como plantar']}],
                'gaps': [{'description': 'Sem conteúdo sobre adubação orgânica dedicada',
                          'justification': 'Termo aparece só em uma página',
                          'kind': 'hypothesis', 'references': [], 'terms': []}],
                'priorities': [{'description': 'Priorizar página agregando os guias',
                                'justification': 'Tema central com maior score',
                                'kind': 'observation',
                                'references': ['https://example.org/horta'], 'terms': []}],
                'pending': ['Validar demanda por adubação orgânica']}

    def test_insights_without_any_collected_urls_points_to_search_first(self):
        self.invoke('prepare', '--project', str(self.project_file), '--store', str(self.store))
        error = self.invoke_error('insights', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma URL coletada', error)
        self.assertIn('run', error)
        self.assertNotIn('Traceback', error)
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 1)

    def test_insights_after_collection_without_extraction_points_to_extract(self):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': self.extracted_sources()})
        error = self.invoke_error('insights', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma extração registrada', error)
        self.assertIn('extract', error)
        self.assertNotIn('Traceback', error)

    def test_insights_without_network_fails_pointing_to_network_build(self):
        self.record_extraction(self.extracted_sources())
        error = self.invoke_error('insights', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma rede registrada', error)
        self.assertIn('network build', error)
        self.assertNotIn('Traceback', error)
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 2)

    def test_insights_with_empty_network_fails_pointing_back_to_corpus(self):
        self.record_extraction([{'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
                                 'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None}])
        self.invoke('network', 'build', '--project-id', 'horta', '--store', str(self.store))
        error = self.invoke_error('insights', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('rede registrada não tem páginas', error)
        self.assertNotIn('Traceback', error)

    def test_generated_insights_are_anchored_and_persisted_with_origin_run_ids(self):
        self.build_pipeline()
        record = self.invoke('insights', '--project-id', 'horta', '--store', str(self.store),
                             generate=lambda project, result: self.insights())
        self.assertEqual(record['status'], 'generated')
        self.assertEqual(record['project_id'], 'horta')
        self.assertTrue(record['created_at'])
        self.assertEqual(record['result']['insights'], self.insights())
        runs = {run['status']: run for run in self.invoke(
            'history', '--project-id', 'horta', '--store', str(self.store))['runs']}
        self.assertEqual(record['result']['extraction_run_id'], runs['extracted']['run_id'])
        self.assertEqual(record['result']['network_run_id'], runs['built']['run_id'])
        self.assertEqual(record['result']['keywords_run_id'], runs['discovered']['run_id'])
        self.assertEqual(record['result']['classify_run_id'], runs['classified']['run_id'])
        self.assertEqual(record['result']['rank_run_id'], runs['ranked']['run_id'])

    def test_generator_receives_compact_knowledge_without_page_text(self):
        self.build_pipeline()
        received = []

        def generate(project, result):
            received.append((project, result))
            return self.insights()

        self.invoke('insights', '--project-id', 'horta', '--store', str(self.store), generate=generate)
        self.assertEqual(len(received), 1)
        project, result = received[0]
        self.assertEqual(project['id'], 'horta')
        payload = json.dumps({'project': project, 'result': result}, ensure_ascii=False)
        for raw in ('Cultivar uma horta em casa exige escolher vasos',
                    'Plantar mudas em vaso começa pela escolha'):
            self.assertNotIn(raw, payload)
        knowledge = result['knowledge']
        self.assertEqual(knowledge['network']['counts'],
                         {'pages': 2, 'terms': 3, 'page_links': 2, 'term_relations': 4})
        self.assertIn('top_terms', knowledge['network'])
        self.assertIn({'term': 'como plantar', 'pages': 2,
                       'sources': ['https://example.org/horta', 'https://example.org/plantar']},
                      knowledge['network']['top_terms'])

    def test_insights_execution_is_preserved_and_consultable_in_history(self):
        self.build_pipeline()
        record = self.invoke('insights', '--project-id', 'horta', '--store', str(self.store),
                             generate=lambda project, result: self.insights())
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(runs[-1], record)


if __name__ == '__main__':
    unittest.main()
