"""Busca batch com transportes injetáveis, sem rede."""

import json
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from seo_agent.search_batch import BraveSearchProvider, collect_pages, run_queries


def response(url, status=200, body=''):
    return SimpleNamespace(url=url, status=status, text=lambda: body)


class BraveProviderTests(unittest.TestCase):
    def test_sends_key_and_normalizes_results_without_exposing_credential(self):
        calls = []
        def fetch(url, **options):
            calls.append((url, options))
            return response(url, body=json.dumps({'web': {'results': [
                {'title': 'Igreja', 'url': 'https://example.org/igreja', 'description': 'Ficha'}
            ]}}))
        provider = BraveSearchProvider('secret', fetch=fetch)
        results = provider.search('igreja em Morrinhos')
        self.assertEqual(parse_qs(urlsplit(calls[0][0]).query), {
            'q': ['igreja em Morrinhos'], 'country': ['BR'], 'search_lang': ['pt-br'],
            'count': ['20'], 'result_filter': ['web'],
        })
        self.assertEqual(calls[0][1]['headers']['X-Subscription-Token'], 'secret')
        self.assertEqual(results, [{'title': 'Igreja', 'url': 'https://example.org/igreja',
                                    'snippet': 'Ficha', 'buscador': ['brave']}])

    def test_rejects_empty_credentials_and_bad_payload(self):
        with self.assertRaisesRegex(ValueError, 'chave'):
            BraveSearchProvider(' ')
        provider = BraveSearchProvider('secret', fetch=lambda url, **kw: response(url, body='{}'))
        with self.assertRaisesRegex(ValueError, 'inválida'):
            provider.search('igreja')


class CollectionTests(unittest.TestCase):
    def test_groups_only_http_200_and_deduplicates_urls_across_queries(self):
        queries = ['igrejas Morrinhos', 'igrejas católicas Morrinhos']
        results = {
            queries[0]: [{'title': 'Igreja', 'url': 'https://www.example.org/a#x', 'buscador': ['brave']}],
            queries[1]: [{'title': 'Outra grafia', 'url': 'https://www.example.org/a', 'buscador': ['searxng']}],
        }
        fetched = []
        def fetch(url):
            fetched.append(url)
            return response(url, status=200 if url.endswith('/a') else 404)
        groups = collect_pages(queries, [lambda query: results[query]], fetch_page=fetch)
        self.assertEqual(fetched, ['https://www.example.org/a'])
        self.assertEqual(groups, [{'domain': 'example.org', 'urli': [
            {'title': 'Igreja', 'url': 'https://www.example.org/a'}],
            'searches': queries, 'buscador': ['brave', 'searxng']}])

    def test_preserves_redirect_evidence_and_skips_failed_urls_without_retry(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return response('https://final.example.org/a', status=404 if url.endswith('bad') else 200)
        def search(query):
            return [{'title': 'Ficha', 'url': 'https://start.example.org/a', 'buscador': ['brave']},
                    {'title': 'Erro', 'url': 'https://start.example.org/bad', 'buscador': ['brave']},
                    {'title': 'URL final', 'url': 'https://final.example.org/a', 'buscador': ['google']}]
        result = run_queries(['a', 'b'], [search], fetch_page=fetch, wait=lambda seconds: None)
        self.assertEqual(result, [{'domain': 'final.example.org', 'urli': [
            {'title': 'Ficha', 'url': 'https://final.example.org/a'}],
            'searches': ['a', 'b'], 'buscador': ['brave', 'google']}])
        self.assertEqual(calls, ['https://start.example.org/a', 'https://start.example.org/bad'])

    def test_waits_between_queries_but_not_after_last(self):
        calls, waits = [], []
        run_queries(['a', 'b', 'c'], [lambda query: calls.append(query) or []],
                    wait=waits.append, interval_seconds=300)
        self.assertEqual(calls, ['a', 'b', 'c'])
        self.assertEqual(waits, [300, 300])

    def test_provider_failure_is_recorded_and_other_providers_continue(self):
        errors = []
        def failed(query):
            raise ValueError('HTTP 401')
        def available(query):
            return [{'title': 'Ficha', 'url': 'https://example.org', 'buscador': ['google']}]
        groups = run_queries(['igrejas'], [failed, available],
                             fetch_page=lambda url: response(url), on_error=errors.append)
        self.assertEqual(groups[0]['buscador'], ['google'])
        self.assertEqual(errors, [{'query': 'igrejas', 'provider': 'failed', 'error': 'HTTP 401'}])

    def test_no_configured_provider_does_not_wait_or_access_pages(self):
        def unexpected(*args):
            self.fail('Sem provedores, o ciclo não deve começar.')
        self.assertEqual(run_queries(['a', 'b'], [], fetch_page=unexpected, wait=unexpected), [])


if __name__ == '__main__':
    unittest.main()
