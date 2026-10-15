"""Score de relevância de fontes e temas, pela CLI pública e sem rede."""

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

COLEGA_HTML = '''<html lang="pt-BR"><head><title>Pragas comuns em varandas</title>
<meta name="author" content="Rita Souza">
<meta property="article:published_time" content="2026-03-05">
</head><body>
<h1>Pragas comuns em varandas</h1>
<p>Observar as folhas toda semana revela os primeiros sinais de pulgão e
cochonilha antes que as colônias cresçam, porque pragas de varanda se instalam
primeiro nos brotos novos e se espalham rápido nos vasos vizinhos.</p>
<h2>Pragas comuns</h2>
<p>Jato suave de água e sabão neutro diluído a cada três dias interrompem o ciclo
das pragas sem venenos, mantendo as folhas livres de resíduos.</p>
<a href="https://example.org/guia">Guia de horta em apartamentos pequenos</a>
</body></html>'''

HUB_HTML = '''<html lang="pt-BR"><head><title>Diretório de jardins</title>
<script type="application/ld+json">{"@type": "ItemList"}</script></head><body>
<h1>Diretório de jardins</h1>
<p>Endereços de lojas e guias de jardinagem urbana.</p>
<ul>
<li><a href="https://example.org/guia">Guia de horta em apartamentos pequenos</a></li>
<li><a href="https://example.org/ficha">Loja de jardinagem central</a></li>
</ul>
</body></html>'''

FICHA_HTML = '''<html lang="pt-BR"><head><title>Loja de jardinagem central</title>
<script type="application/ld+json">{"@type": "Organization",
"name": "Loja de jardinagem central"}</script></head><body>
<h1>Loja de jardinagem central</h1>
<p>Loja de insumos e ferramentas de jardinagem no centro da cidade, aberta de
segunda a sábado, com entrega de substratos e vasos por telefone.</p>
<a href="https://example.org/facebook">Facebook da loja</a>
<a href="https://example.org/mapa">Mapa de acesso</a>
</body></html>'''

VAZIA_HTML = '<html lang="pt-BR"><head><title>Página vazia</title></head><body></body></html>'


class RankCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.store = self.directory / 'history.sqlite3'
        self.project_file = self.directory / 'project.json'
        self.project = {'id': 'horta', 'business_context': 'Loja de plantas',
                        'audience': 'Moradores locais', 'language': 'pt-BR', 'geography': 'Brasil',
                        'keywords': ['horta'], 'content_goal': 'Priorizar o que escrever'}
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

    def ranked_sources(self):
        """Corpus com relevância conhecida: guia > ficha > colega = hub (empate alfabético)."""
        from seo_agent.page import extract_page
        return [
            {'id': 'fonte-guia', 'url': 'https://example.org/guia',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(GUIA_HTML, 'https://example.org/guia')},
            {'id': 'fonte-colega', 'url': 'https://example.org/colega',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(COLEGA_HTML, 'https://example.org/colega')},
            {'id': 'fonte-hub', 'url': 'https://example.org/hub',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(HUB_HTML, 'https://example.org/hub')},
            {'id': 'fonte-ficha', 'url': 'https://example.org/ficha',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(FICHA_HTML, 'https://example.org/ficha')},
        ]

    def extra_source(self, identifier, html):
        from seo_agent.page import extract_page
        url = f'https://example.org/{identifier}'
        return {'id': f'fonte-{identifier}', 'url': url,
                'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': extract_page(html, url)}

    def test_rank_without_any_collected_urls_points_to_search_first(self):
        self.invoke('prepare', '--project', str(self.project_file), '--store', str(self.store))
        error = self.invoke_error('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma URL coletada', error)
        self.assertIn('run', error)
        self.assertNotIn('Traceback', error)
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(len(runs), 1)

    def test_rank_after_collection_without_extraction_points_to_extract(self):
        from seo_agent.__main__ import prepare_run
        prepare_run(self.project, self.store, status='collected', result={'sources': self.ranked_sources()})
        error = self.invoke_error('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertIn('Nenhuma extração registrada', error)
        self.assertIn('extract', error)
        self.assertNotIn('Traceback', error)

    def test_known_relevance_fixtures_rank_in_expected_order(self):
        self.record_extraction(self.ranked_sources())
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'ranked')
        self.assertEqual(record['project_id'], 'horta')
        self.assertEqual([(item['url'], item['score']) for item in record['result']['sources']], [
            ('https://example.org/guia', 11),
            ('https://example.org/ficha', 3),
            ('https://example.org/colega', 2),
            ('https://example.org/hub', 2),
        ])
        self.assertEqual(record['result']['excluded'], [])

    def test_rank_persists_referencing_extraction_run(self):
        extraction = self.record_extraction(self.ranked_sources())
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertNotEqual(record['run_id'], extraction['run_id'])
        self.assertTrue(record['created_at'])
        self.assertEqual(record['result']['extraction_run_id'], extraction['run_id'])
        runs = self.invoke('history', '--project-id', 'horta', '--store', str(self.store))['runs']
        self.assertEqual(runs[-1], record)

    def test_link_with_fragment_counts_as_inbound_vote(self):
        from seo_agent.page import extract_page
        html = ('<html><body><h1>Guia</h1><p>Veja os horários completos em outra página.</p>'
                '<a href="https://example.org/hub#horarios">Horários</a></body></html>')
        sources = [
            {'id': 'fonte-guia', 'url': 'https://example.org/guia',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page(html, 'https://example.org/guia')},
            {'id': 'fonte-hub', 'url': 'https://example.org/hub',
             'retrieved_at': '2026-03-01T00:00:00+00:00',
             'page': extract_page('<html><body><h1>Hub</h1><p>Conteúdo do hub.</p></body></html>',
                                  'https://example.org/hub')},
        ]
        self.record_extraction(sources)
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        by_url = {item['url']: item for item in record['result']['sources']}
        inbound = [factor for factor in by_url['https://example.org/hub']['factors']
                   if factor['signal'] == 'inbound_links']
        self.assertEqual(inbound[0]['value'], 1)
        self.assertEqual(inbound[0]['points'], 1)

    def test_score_publishes_factors_with_values_and_weights(self):
        self.record_extraction(self.ranked_sources())
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        by_url = {item['url']: item for item in record['result']['sources']}
        self.assertEqual(by_url['https://example.org/guia']['factors'], [
            {'signal': 'has_author', 'value': True, 'weight': 1, 'points': 1},
            {'signal': 'has_date', 'value': True, 'weight': 1, 'points': 1},
            {'signal': 'substantial_text', 'value': 364, 'weight': 3, 'points': 3},
            {'signal': 'structured_headings', 'value': 4, 'weight': 2, 'points': 2},
            {'signal': 'structured_data', 'value': 1, 'weight': 2, 'points': 2},
            {'signal': 'inbound_links', 'value': 2, 'weight': 1, 'points': 2},
        ])
        hub = by_url['https://example.org/hub']
        self.assertEqual([factor['points'] for factor in hub['factors']], [0, 0, 0, 0, 2, 0])
        for item in record['result']['sources']:
            self.assertEqual(item['score'], sum(factor['points'] for factor in item['factors']))

    def test_theme_scores_aggregate_source_scores_with_source_urls(self):
        self.record_extraction(self.ranked_sources())
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['result']['themes'], [
            {'term': 'pragas comuns', 'score': 13,
             'sources': ['https://example.org/guia', 'https://example.org/colega']},
            {'term': 'escolhendo os vasos', 'score': 11, 'sources': ['https://example.org/guia']},
            {'term': 'horta em apartamentos pequenos', 'score': 11, 'sources': ['https://example.org/guia']},
            {'term': 'luz e rega', 'score': 11, 'sources': ['https://example.org/guia']},
            {'term': 'loja de jardinagem central', 'score': 3, 'sources': ['https://example.org/ficha']},
            {'term': 'diretório de jardins', 'score': 2, 'sources': ['https://example.org/hub']},
            {'term': 'pragas comuns em varandas', 'score': 2, 'sources': ['https://example.org/colega']},
        ])

    def test_page_without_usable_text_is_pending_not_error(self):
        self.record_extraction(self.ranked_sources() + [self.extra_source('vazia', VAZIA_HTML)])
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'partial')
        by_url = {item['url']: item for item in record['result']['sources']}
        self.assertEqual(by_url['https://example.org/vazia'],
                         {'url': 'https://example.org/vazia',
                          'reason': 'Página sem texto utilizável para pontuar.'})
        self.assertEqual(by_url['https://example.org/guia']['score'], 11)
        self.assertEqual(record['result']['sources'][-1]['url'], 'https://example.org/vazia')
        theme_sources = [url for theme in record['result']['themes'] for url in theme['sources']]
        self.assertNotIn('https://example.org/vazia', theme_sources)

    def test_partial_failure_excludes_url_and_keeps_others_ranked(self):
        sources = self.ranked_sources() + [
            {'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
             'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None},
        ]
        self.record_extraction(sources)
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'ranked')
        self.assertEqual([item['url'] for item in record['result']['sources']],
                         ['https://example.org/guia', 'https://example.org/ficha',
                          'https://example.org/colega', 'https://example.org/hub'])
        self.assertEqual(record['result']['excluded'], [
            {'url': 'https://example.org/broken', 'failures': [
                {'stage': 'page', 'error': 'Página preservada ausente ou ilegível no histórico desta fonte.'}]},
        ])

    def test_extraction_without_valid_sources_is_empty_status_not_error(self):
        self.record_extraction([{'id': 'fonte-quebrada', 'url': 'https://example.org/broken',
                                 'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': None}])
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(record['status'], 'empty')
        self.assertEqual(record['result']['sources'], [])
        self.assertEqual(record['result']['themes'], [])
        self.assertEqual(len(record['result']['excluded']), 1)

    def test_rerank_over_same_extraction_is_identical(self):
        self.record_extraction(self.ranked_sources())
        first = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        second = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual(first['result'], second['result'])
        self.assertEqual(first['status'], second['status'])
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertNotEqual(first['created_at'], second['created_at'])

    def test_score_tie_between_identical_pages_resolves_by_url(self):
        page = {'title': 'Empate', 'headings': [{'level': 1, 'text': 'Empate'}],
                'links': [], 'authors': [], 'dates': [], 'structured_data': [],
                'text': 'Página idêntica publicada em dois endereços para conferir o desempate.'}
        sources = [{'id': f'fonte-{name}', 'url': f'https://example.org/{name}',
                    'retrieved_at': '2026-03-01T00:00:00+00:00', 'page': dict(page)}
                   for name in ('empate-b', 'empate-a')]
        self.record_extraction(sources)
        record = self.invoke('rank', '--project-id', 'horta', '--store', str(self.store))
        self.assertEqual([(item['url'], item['score']) for item in record['result']['sources']],
                         [('https://example.org/empate-a', 0), ('https://example.org/empate-b', 0)])


if __name__ == '__main__':
    unittest.main()
