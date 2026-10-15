"""Classificação de tipos de conteúdo do corpus extraído, pela CLI pública e sem rede."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from seo_agent.__main__ import main


GUIA_HTML = '''<html lang="pt-BR"><head><title>Guia: horta em apartamentos pequenos</title>
<script type="application/ld+json">{"@type": "BlogPosting", "author": {"name": "Marina Alves"},
"datePublished": "2026-02-10"}</script></head><body>
<h1>Horta em apartamentos pequenos</h1>
<p>Cultivar uma horta em apartamento pequeno começa pela escolha dos cantos que
recebem luz direta pela manhã, porque a maioria das folhas comestíveis precisa de
quatro horas de sol no mínimo para crescer com folhas firmes e sabor marcante.
Janelas de leste varandas protegidas do vento e prateleiras junto ao vidro são os
pontos mais valiosos de qualquer planta urbana, e medir esse recurso antes de
comprar o primeiro vaso evita o erro clássico de encher a casa de mudas que
estiolam em cantos escuros semanas depois da compra impulsiva da feira.</p>
<h2>Escolhendo os vasos</h2>
<p>Vasos fundos servem raízes de tomate e cenoura enquanto recipientes largos e
rasos acomodam melhor as folhas de alface rúcula e cebolinha que ocupam a
superfície. Cada vaso precisa de furos de drenagem generosos e um prato para
conter o excesso de água da rega, porque água parada nas raízes apodrece o sistema
inteiro em poucos dias de calor. Misturar um terço de composto orgânico ao
substrato comercial deixa a estrutura leve porosa e rica em microrganismos que
sustentam o crescimento das hortaliças sem adubações químicas agressivas.</p>
<h2>Luz e rega</h2>
<p>A rega deve ser feita sempre no início da manhã diretamente no solo e nunca
sobre as folhas, porque folhas molhadas em ambiente fechado favorecem fungos que
abrem buracos circulares nas folhas e se espalham pelas plantas vizinhas. O teste
do dedo indica o momento exato: enfie o dedo dois centímetros no substrato e
regue apenas quando estiver seco na ponta. No inverno o intervalo entre regas
dobra e no verão épocas de vento quente podem exigir duas verificações diárias
para manter a umidade estável da zona das raízes sempre úmida nunca encharcada.</p>
<h2>Pragas comuns</h2>
<p>Pulgões cochonilhas e ácaros são as pragas mais frequentes dos apartamentos e
aparecem primeiro nos brotos novos tenros da ponta dos ramos. Retirá-los com jato
suave de água e aplicar sabão neutro diluído a cada três dias interrompe o ciclo
das colônias antes que atinjam escala de infestação. Plantar tagetes e manjericão
entre as folhas comestíveis confunde os insetos com o cheiro forte e reduz a
pressão naturalmente sem venenos que deixam resíduos nas folhas da família.</p>
<a href="https://example.org/plantar">Como plantar mudas</a>
</body></html>'''

DIRETORIO_HTML = '''<html lang="pt-BR"><head><title>Diretório: igrejas em Goiânia</title>
<script type="application/ld+json">{"@type": "ItemList"}</script></head><body>
<h1>Igrejas em Goiânia</h1>
<p>Lista por região da cidade.</p>
<ul>
<li><a href="https://example.org/igreja-a">Igreja Batista Central de Goiânia</a></li>
<li><a href="https://example.org/igreja-b">Igreja Presbiteriana do Setor Bueno</a></li>
<li><a href="https://example.org/igreja-c">Igreja Assembleia de Deus Campinas</a></li>
<li><a href="https://example.org/igreja-d">Paróquia Nossa Senhora do Rosário</a></li>
<li><a href="https://example.org/igreja-e">Igreja Metodista Central de Goiânia</a></li>
<li><a href="https://example.org/igreja-f">Comunidade Lutheran do Norte Goiano</a></li>
<li><a href="https://example.org/igreja-g">Igreja Adventista do Setor Oeste</a></li>
<li><a href="https://example.org/igreja-h">Igreja Batista Ebenézer Jardim Goiás</a></li>
<li><a href="https://example.org/igreja-i">Paróquia Santa Rita de Cássia Sul</a></li>
<li><a href="https://example.org/igreja-j">Igreja Universal do Reino Setor Marista</a></li>
<li><a href="https://example.org/igreja-k">Igreja Congregacional Campinas Norte</a></li>
<li><a href="https://example.org/igreja-l">Catedral Metropolitana de Goiânia Centro</a></li>
<li><a href="https://example.org/igreja-m">Igreja do Evangelho Quadrangular Bueno</a></li>
<li><a href="https://example.org/igreja-n">Igreja Cristã Maranata Setor Coimbra</a></li>
<li><a href="https://example.org/igreja-o">Igreja Renascer em Cristo Jardim América</a></li>
</ul>
</body></html>'''

FICHA_HTML = '''<html lang="pt-BR"><head><title>Paróquia Nossa Senhora Aparecida</title>
<script type="application/ld+json">{"@type": "Organization",
"name": "Paróquia Nossa Senhora Aparecida"}</script></head><body>
<h1>Paróquia Nossa Senhora Aparecida</h1>
<p>Comunidade católica do Setor Oeste de Goiânia. Missas dominicais às 8h e 19h,
secretaria aberta de terça a sexta.</p>
<a href="https://example.org/facebook">Facebook da paróquia</a>
<a href="https://example.org/mapa">Mapa de acesso</a>
</body></html>'''

VAZIA_HTML = '<html lang="pt-BR"><head><title>Página vazia</title></head><body></body></html>'

AGENDA_HTML = '''<html lang="pt-BR"><head><title>Agenda semanal</title></head><body>
<h1>Agenda da semana</h1>
<p>A agenda da comunidade reúne os encontros planejados para os próximos dias,
com horários e locais conferidos pelos organizadores de cada pastoral antes da
publicação mensal desta página informativa simples.</p>
<a href="/a">Colunas</a> <a href="/b">Estudos</a> <a href="/c">Grupos</a>
<a href="/d">Juventude</a> <a href="/e">Coro</a> <a href="/f">Eventos</a>
</body></html>'''


class ClassifyCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = self.directory / 'history.sqlite3'
        self.project_file = self.directory / 'project.json'
        self.project = {'id': 'igrejas', 'business_context': 'Diretório de igrejas',
                        'audience': 'Fiéis locais', 'language': 'pt-BR', 'geography': 'Goiás',
                        'keywords': ['igrejas'], 'content_goal': 'Mapear comunidades'}
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
        return self.invoke('extract', '--project-id', 'igrejas', '--store', str(self.store))

    def extracted_sources(self):
        from seo_agent.page import extract_page
        return [
            {'id': 'fonte-guia', 'url': 'https://example.org/guia',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(GUIA_HTML, 'https://example.org/guia')},
            {'id': 'fonte-diretorio', 'url': 'https://example.org/diretorio',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(DIRETORIO_HTML, 'https://example.org/diretorio')},
            {'id': 'fonte-ficha', 'url': 'https://example.org/ficha',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(FICHA_HTML, 'https://example.org/ficha')},
        ]

    def extra_source(self, identifier, html):
        from seo_agent.page import extract_page
        url = f'https://example.org/{identifier}'
        return {'id': f'fonte-{identifier}', 'url': url,
                'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': extract_page(html, url)}

    def test_classify_without_any_collected_urls_points_to_search_first(self):
        self.invoke('prepare', '--project', str(self.project_file), '--store', str(self.store))
        error = self.invoke_error('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertIn('Nenhuma URL coletada', error)
        self.assertIn('run', error)
        self.assertNotIn('Traceback', error)
        runs = self.invoke('history', '--project-id', 'igrejas', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 1)

    def test_classify_after_collection_without_extraction_points_to_extract(self):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': self.extracted_sources()})
        error = self.invoke_error('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertIn('Nenhuma extração registrada', error)
        self.assertIn('extract', error)
        self.assertNotIn('Traceback', error)

    def test_known_type_fixtures_are_classified_correctly(self):
        self.record_extraction(self.extracted_sources())
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertEqual(record['status'], 'classified')
        self.assertEqual({item['url']: item['type'] for item in record['result']['classifications']}, {
            'https://example.org/guia': 'article',
            'https://example.org/diretorio': 'listing',
            'https://example.org/ficha': 'profile',
        })

    def test_classification_publishes_signals_and_scores_as_justification(self):
        self.record_extraction(self.extracted_sources())
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        by_url = {item['url']: item for item in record['result']['classifications']}
        guia = by_url['https://example.org/guia']
        self.assertEqual(guia['signals'], {'text_words': 364, 'headings': 4, 'links': 1,
                                           'linked_words_ratio': 0.0082,
                                           'structured_types': ['BlogPosting'],
                                           'has_author': True, 'has_date': True})
        self.assertEqual(guia['scores'], {'article': 10, 'listing': 0, 'profile': 0})
        diretorio = by_url['https://example.org/diretorio']
        self.assertEqual(diretorio['signals']['links'], 15)
        self.assertEqual(diretorio['signals']['structured_types'], ['ItemList'])
        self.assertEqual(diretorio['scores'], {'article': 0, 'listing': 8, 'profile': 0})
        ficha = by_url['https://example.org/ficha']
        self.assertEqual(ficha['signals']['structured_types'], ['Organization'])
        self.assertEqual(ficha['scores'], {'article': 0, 'listing': 0, 'profile': 6})
        for item in record['result']['classifications']:
            self.assertEqual(item['type'], max(item['scores'], key=item['scores'].get))

    def test_record_persists_referencing_extraction_run_in_url_order(self):
        extraction = self.record_extraction(self.extracted_sources())
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertNotEqual(record['run_id'], extraction['run_id'])
        self.assertTrue(record['created_at'])
        self.assertEqual(record['result']['extraction_run_id'], extraction['run_id'])
        urls = [item['url'] for item in record['result']['classifications']]
        self.assertEqual(urls, sorted(urls))
        runs = self.invoke('history', '--project-id', 'igrejas', '--store', str(self.store))['runs']
        self.assertEqual(runs[-1], record)

    def test_reclassification_over_same_extraction_is_identical(self):
        self.record_extraction(self.extracted_sources())
        first = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        second = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertEqual(first['result'], second['result'])
        self.assertEqual(first['status'], second['status'])
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertNotEqual(first['created_at'], second['created_at'])

    def test_page_without_usable_text_is_pending_unclassified_not_error(self):
        self.record_extraction(self.extracted_sources() + [self.extra_source('vazia', VAZIA_HTML)])
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertEqual(record['status'], 'partial')
        by_url = {item['url']: item for item in record['result']['classifications']}
        self.assertEqual(by_url['https://example.org/vazia'],
                         {'url': 'https://example.org/vazia', 'type': 'unclassified',
                          'reason': 'Página sem texto utilizável para classificar.'})
        self.assertEqual(by_url['https://example.org/guia']['type'], 'article')

    def test_page_without_any_classification_signal_is_pending_unclassified(self):
        self.record_extraction([self.extra_source('agenda', AGENDA_HTML)])
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertEqual(record['status'], 'partial')
        [item] = record['result']['classifications']
        self.assertEqual(item['url'], 'https://example.org/agenda')
        self.assertEqual(item['type'], 'unclassified')
        self.assertEqual(item['reason'], 'Nenhum sinal de classificação presente na página.')

    def test_partial_failure_excludes_url_and_keeps_others_classified(self):
        sources = self.extracted_sources() + [
            {'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None},
        ]
        self.record_extraction(sources)
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertEqual(record['status'], 'classified')
        self.assertEqual([item['url'] for item in record['result']['classifications']],
                         ['https://example.org/diretorio', 'https://example.org/ficha',
                          'https://example.org/guia'])
        self.assertEqual(record['result']['excluded'], [
            {'url': 'https://example.org/broken', 'failures': [
                {'stage': 'page', 'error': 'Página preservada ausente ou ilegível no histórico desta fonte.'}]},
        ])

    def test_extraction_without_valid_sources_is_empty_status_not_error(self):
        self.record_extraction([{'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
                                 'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None}])
        record = self.invoke('classify', '--project-id', 'igrejas', '--store', str(self.store))
        self.assertEqual(record['status'], 'empty')
        self.assertEqual(record['result']['classifications'], [])
        self.assertEqual(len(record['result']['excluded']), 1)

    def test_score_tie_resolves_alphabetically_deterministically(self):
        from seo_agent.classify import classify_source
        page = {
            'text': ' '.join(['horta'] * 320 + ['como plantar mudas em vasos'] * 10),
            'headings': [{'level': 2, 'text': f'Tema {number}'} for number in range(3)],
            'links': [{'url': f'https://example.org/l{number}', 'text': 'guia de horta em vasos ' * 4}
                      for number in range(12)],
            'authors': [], 'dates': [], 'structured_data': [],
        }
        first = classify_source({'url': 'https://example.org/empate', 'page': page})
        second = classify_source({'url': 'https://example.org/empate', 'page': page})
        self.assertEqual(first['scores'], {'article': 5, 'listing': 5, 'profile': 0})
        self.assertEqual(first['type'], 'article')
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
