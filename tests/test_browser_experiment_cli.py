from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from seo_agent.__main__ import main


class BrowserExperimentCLI(unittest.TestCase):
    def test_dynamic_markers_in_script_do_not_prove_rendered_content(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(__file__).resolve().parents[1] / 'examples/browser-fixtures'
            def fetch(url, **options):
                request = json.loads(options['body'])
                name = request['url'].rsplit('/', 1)[1]
                payload = {'success': True, 'result': {'content': (source / name).read_text()}, 'meta': {'status': 200}}
                return SimpleNamespace(status=200, headers={}, text=lambda: json.dumps(payload))
            with redirect_stdout(io.StringIO()) as output:
                main(['browser-experiment', '--fixtures', str(source / 'manifest.json'), '--output', directory],
                     environment={'CLOUDFLARE_ACCOUNT_ID': 'a' * 32, 'CLOUDFLARE_API_TOKEN': 'fixture'}, fetch=fetch)
            captures = json.loads(output.getvalue())['captures']
            self.assertEqual(len(captures), 60)
            self.assertTrue(all(c['expected_text_complete'] for c in captures if c['scenario'] == 'static'))
            self.assertTrue(all(not c['expected_text_complete'] for c in captures if c['scenario'] != 'static'))

    def test_missing_credentials_never_calls_service(self):
        with tempfile.TemporaryDirectory() as directory:
            fixtures = Path(directory) / 'fixtures.json'
            fixtures.write_text(json.dumps([{'name': 'static', 'url': 'https://example.org/', 'expected_text': ['STATIC']}]))
            with redirect_stdout(io.StringIO()) as output:
                main(['browser-experiment', '--fixtures', str(fixtures), '--output', directory],
                     environment={}, fetch=lambda *a, **k: self.fail('Não chamar Cloudflare sem chave.'))
            self.assertEqual(json.loads(output.getvalue())['status'], 'credentials_missing')

    def test_reports_five_captures_and_never_confuses_api_status_with_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            fixtures = Path(directory) / 'fixtures.json'
            fixtures.write_text(json.dumps([{'name': 'static', 'url': 'https://example.org/', 'expected_text': ['STATIC']}]))
            calls = []
            def fetch(url, **options):
                calls.append(url)
                payload = {'success': True, 'result': {'content': '<h1>STATIC</h1>'},
                           'meta': {'status': 404 if 'kitesurf' in url else 200}}
                return SimpleNamespace(status=200, headers={'x-browser-ms-used': '12'}, text=lambda: json.dumps(payload))
            with redirect_stdout(io.StringIO()) as output:
                main(['browser-experiment', '--fixtures', str(fixtures), '--output', directory],
                     environment={'CLOUDFLARE_ACCOUNT_ID': 'a' * 32, 'CLOUDFLARE_API_TOKEN': 'fixture'}, fetch=fetch)
            report = json.loads(output.getvalue())
            self.assertEqual(len(calls), 10)
            self.assertEqual(len(report['captures']), 10)
            kitesurf = [item for item in report['captures'] if item['engine'] == 'kitesurf']
            self.assertTrue(all(not item['destination_200'] for item in kitesurf))
            self.assertTrue(all(item['api_status'] == 200 for item in kitesurf))
            self.assertEqual(len(list(Path(directory).glob('*.html'))), 10)


if __name__ == '__main__':
    unittest.main()
