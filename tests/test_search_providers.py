"""Contratos dos adaptadores de busca, com HTTP controlado e sem chaves reais."""

import json
import base64
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
import tempfile
from unittest.mock import patch

from seo_agent.search_providers import configured_providers


def reply(payload, status=200):
    return SimpleNamespace(status=status, text=lambda: json.dumps(payload))


class ConfiguredProvidersTests(unittest.TestCase):
    def test_all_configured_apis_report_authentication_failure_without_leaking_keys(self):
        environment = {
            'BRAVE_SEARCH_API_KEY': 'secret', 'GOOGLE_SEARCH_API_KEY': 'secret', 'GOOGLE_SEARCH_ENGINE_ID': 'engine',
            'MOJEEK_API_KEY': 'secret', 'YDC_API_KEY': 'secret', 'KAGI_API_KEY': 'secret',
            'SERPAPI_API_KEY': 'secret', 'SERPER_API_KEY': 'secret',
            'YANDEX_SEARCH_API_KEY': 'secret', 'YANDEX_FOLDER_ID': 'folder',
            'DATAFORSEO_LOGIN': 'login', 'DATAFORSEO_PASSWORD': 'secret',
        }
        providers = configured_providers(environment, fetch=lambda url, **options: reply({'error': 'secret'}, status=401))
        self.assertEqual({provider.name for provider in providers}, {
            'brave', 'google', 'mojeek', 'you', 'kagi', 'serpapi', 'serper', 'dataforseo', 'yandex'})
        for provider in providers:
            with self.subTest(provider=provider.name), self.assertRaises(ValueError) as caught:
                provider('igrejas')
            self.assertNotIn('secret', str(caught.exception))

    def test_http_200_with_malformed_serp_payload_is_not_reported_as_empty_success(self):
        for field in ['SERPAPI_API_KEY', 'SERPER_API_KEY']:
            with self.subTest(field=field):
                provider = configured_providers({field: 'secret'}, fetch=lambda url, **kw: reply({}))[0]
                with self.assertRaises(ValueError):
                    provider('igrejas')

    def test_empty_and_incomplete_credentials_never_enter_the_search_cycle(self):
        def unexpected(*args, **kwargs):
            self.fail('Provedor sem credenciais não deve acessar HTTP.')
        self.assertEqual(configured_providers({}, fetch=unexpected), [])
        self.assertEqual(configured_providers({
            'BRAVE_SEARCH_API_KEY': ' ', 'GOOGLE_SEARCH_API_KEY': 'key',
            'DATAFORSEO_LOGIN': 'login', 'YANDEX_FOLDER_ID': 'folder',
        }, fetch=unexpected), [])

    def test_dotenv_is_loaded_without_execution_and_exported_values_take_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / '.env'
            env_file.write_text("BRAVE_SEARCH_API_KEY='from-file'\nGOOGLE_SEARCH_API_KEY=\n", encoding='utf-8')
            def fetch(url, **options):
                self.assertEqual(options['headers']['X-Subscription-Token'], 'from-process')
                return reply({'web': {'results': []}})
            with patch.dict('os.environ', {'BRAVE_SEARCH_API_KEY': 'from-process'}, clear=True):
                providers = configured_providers(env_file=env_file, fetch=fetch)
                self.assertEqual([provider.name for provider in providers], ['brave'])
                self.assertEqual(providers[0]('igrejas'), [])

    def test_only_configured_brave_is_called_and_returns_normalized_results(self):
        calls = []
        def fetch(url, **options):
            calls.append(url)
            self.assertEqual(options['headers']['X-Subscription-Token'], 'test-key')
            return reply({'web': {'results': [
                {'title': 'Ficha', 'url': 'https://example.org/igreja', 'description': 'Resumo'}
            ]}})
        providers = configured_providers({'BRAVE_SEARCH_API_KEY': 'test-key'}, fetch=fetch)
        self.assertEqual([provider.name for provider in providers], ['brave'])
        self.assertEqual(providers[0]('igrejas Morrinhos'), [{
            'title': 'Ficha', 'url': 'https://example.org/igreja', 'snippet': 'Resumo',
            'buscador': ['brave'],
        }])
        self.assertEqual(len(calls), 1)

    def test_google_requires_key_and_engine_and_requests_brazilian_results(self):
        def fetch(url, **options):
            self.assertEqual(parse_qs(urlsplit(url).query), {
                'key': ['key'], 'cx': ['engine'], 'q': ['igrejas'], 'gl': ['br'],
                'hl': ['pt-BR'], 'num': ['10'],
            })
            return reply({'items': [{'title': 'Igreja', 'link': 'https://example.org', 'snippet': 'Fonte'}]})
        providers = configured_providers({
            'GOOGLE_SEARCH_API_KEY': 'key', 'GOOGLE_SEARCH_ENGINE_ID': 'engine',
        }, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas'), [{'title': 'Igreja', 'url': 'https://example.org',
                                                  'snippet': 'Fonte', 'buscador': ['google']}])

    def test_mojeek_returns_its_independent_index(self):
        def fetch(url, **options):
            params = parse_qs(urlsplit(url).query)
            self.assertEqual(params['api_key'], ['key'])
            self.assertEqual(params['rb'], ['BR'])
            self.assertEqual(params['lb'], ['PT'])
            return reply({'response': {'status': 'OK', 'results': [
                {'url': 'https://example.org', 'title': 'Ficha', 'desc': 'Resumo'}]}})
        providers = configured_providers({'MOJEEK_API_KEY': 'key'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas')[0]['buscador'], ['mojeek'])

    def test_you_uses_post_api_and_web_results(self):
        def fetch(url, **options):
            self.assertEqual(url, 'https://ydc-index.io/v1/search')
            self.assertEqual(options['method'], 'POST')
            self.assertEqual(options['headers']['X-API-Key'], 'key')
            self.assertEqual(json.loads(options['body']), {
                'query': 'igrejas', 'count': 10, 'country': 'BR', 'language': 'pt-BR'})
            return reply({'results': {'web': [{'url': 'https://example.org', 'title': 'Ficha', 'description': 'Fonte'}]}})
        providers = configured_providers({'YDC_API_KEY': 'key'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas')[0]['buscador'], ['you'])

    def test_kagi_uses_v1_search_with_bearer_authentication(self):
        def fetch(url, **options):
            self.assertEqual(url, 'https://kagi.com/api/v1/search')
            self.assertEqual(options['headers']['Authorization'], 'Bearer key')
            self.assertEqual(json.loads(options['body']), {'query': 'igrejas', 'workflow': 'search', 'limit': 10})
            return reply({'data': {'search': [{'url': 'https://example.org', 'title': 'Ficha', 'snippet': 'Fonte'}]}})
        providers = configured_providers({'KAGI_API_KEY': 'key'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas')[0]['buscador'], ['kagi'])

    def test_serpapi_attributes_google_results_and_not_the_api_vendor(self):
        def fetch(url, **options):
            self.assertEqual(urlsplit(url).hostname, 'serpapi.com')
            self.assertEqual(parse_qs(urlsplit(url).query), {
                'api_key': ['key'], 'engine': ['google'], 'q': ['igrejas'],
                'gl': ['br'], 'hl': ['pt'], 'google_domain': ['google.com.br'],
            })
            return reply({'organic_results': [{'link': 'https://example.org', 'title': 'Ficha'}]})
        providers = configured_providers({'SERPAPI_API_KEY': 'key'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas')[0]['buscador'], ['google'])

    def test_yandex_decodes_xml_results_after_key_and_folder_are_configured(self):
        xml = '<yandexsearch><response><results><grouping><group><doc><url>https://example.org</url>' \
              '<title>Igreja <hlword>local</hlword></title><passages><passage>Fonte</passage></passages>' \
              '</doc></group></grouping></results></response></yandexsearch>'
        def fetch(url, **options):
            self.assertEqual(url, 'https://searchapi.api.cloud.yandex.net/v2/web/search')
            self.assertEqual(options['headers']['Authorization'], 'Api-Key key')
            body = json.loads(options['body'])
            self.assertEqual(body['folderId'], 'folder')
            self.assertEqual(body['query'], {'searchType': 'SEARCH_TYPE_COM', 'queryText': 'igrejas'})
            self.assertEqual(body['responseFormat'], 'FORMAT_XML')
            return reply({'rawData': base64.b64encode(xml.encode()).decode()})
        providers = configured_providers({'YANDEX_SEARCH_API_KEY': 'key', 'YANDEX_FOLDER_ID': 'folder'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas'), [{'title': 'Igreja local', 'url': 'https://example.org',
                                                  'snippet': 'Fonte', 'buscador': ['yandex']}])

    def test_dataforseo_uses_both_credentials_and_only_organic_items(self):
        def fetch(url, **options):
            self.assertEqual(url, 'https://api.dataforseo.com/v3/serp/google/organic/live/advanced')
            self.assertEqual(options['headers']['Authorization'], 'Basic ' + base64.b64encode(b'login:password').decode())
            self.assertEqual(json.loads(options['body']), [{
                'keyword': 'igrejas', 'location_name': 'Brazil', 'language_code': 'pt', 'depth': 10}])
            return reply({'status_code': 20000, 'tasks': [{'status_code': 20000, 'result': [{'items': [
                {'type': 'organic', 'title': 'Ficha', 'url': 'https://example.org'},
                {'type': 'paid', 'title': 'Anuncio', 'url': 'https://ad.example.org'},
            ]}]}]})
        providers = configured_providers({'DATAFORSEO_LOGIN': 'login', 'DATAFORSEO_PASSWORD': 'password'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas'), [{'title': 'Ficha', 'url': 'https://example.org',
                                                  'snippet': '', 'buscador': ['google']}])

    def test_serper_posts_google_query_with_brazilian_locale(self):
        def fetch(url, **options):
            self.assertEqual(url, 'https://google.serper.dev/search')
            self.assertEqual(options['headers']['X-API-KEY'], 'key')
            self.assertEqual(json.loads(options['body']), {'q': 'igrejas', 'gl': 'br', 'hl': 'pt-br', 'num': 10})
            return reply({'organic': [{'link': 'https://example.org', 'title': 'Ficha'}]})
        providers = configured_providers({'SERPER_API_KEY': 'key'}, fetch=fetch)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]('igrejas')[0]['buscador'], ['google'])


if __name__ == '__main__':
    unittest.main()
