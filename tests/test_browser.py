"""Smoke de Chromium opcional sobre conteúdo e assets servidos em loopback."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from seo_agent.browser import BrowserSession, VIEWPORTS
from seo_agent.http import Response

HAS_BROWSER = importlib.util.find_spec('playwright') is not None and bool(
    shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome'))


@unittest.skipUnless(HAS_BROWSER, 'Instale requirements-browser.txt e Chromium para o smoke local.')
class ChromiumRendering(unittest.TestCase):
    def test_renders_client_content_in_each_viewport_and_stores_screenshots(self):
        requested = []
        denied_origin_requests = []

        class DeniedHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                denied_origin_requests.append(('GET', self.path))
                self.send_response(200); self.end_headers()

            def do_POST(self):
                denied_origin_requests.append(('POST', self.path))
                self.send_response(200); self.end_headers()

            def log_message(self, *args):
                pass

        denied_server = ThreadingHTTPServer(('127.0.0.1', 0), DeniedHandler)
        denied_thread = Thread(target=denied_server.serve_forever, daemon=True)
        denied_thread.start()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requested.append(self.path)
                page_html = f'''<!doctype html><meta name=viewport content='width=device-width, initial-scale=1'>
                <title>Initial</title><body><script>
                setTimeout(() => {{
                  if (location.pathname === '/child') {{document.body.innerHTML = '<h1>Detalhes</h1>'; return;}}
                  document.body.innerHTML = (matchMedia('(max-width: 600px)').matches
                    ? '<h1>Compact</h1>' : '<h1>Wide</h1>')
                    + '<p>Detalhe renderizado</p><a href="/child">Abrir detalhes</a>';
                }}, 100);
                fetch('http://127.0.0.1:{denied_server.server_port}/private').catch(() => {{}});
                fetch('/submit', {{method: 'POST'}}).catch(() => {{}});
                </script></body>'''.encode()
                self.send_response(200)
                self.send_header('content-type', 'text/html; charset=utf-8')
                self.send_header('content-length', str(len(page_html)))
                self.end_headers()
                self.wfile.write(page_html)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://seo.fixture.test:{server.server_port}/'
        metadata = Response(url, 200, {'content-type': 'text/html'}, b'fixture', [],
                            ['127.0.0.1'], None)

        class TestAddress:
            version = 4
            is_global = True

            def __str__(self):
                return '127.0.0.1'
        try:
            with TemporaryDirectory() as temporary, \
                    patch('seo_agent.http.fetch_url', side_effect=lambda target: metadata.__class__(
                        target, 200, metadata.headers, metadata.body, [], metadata.ip_addresses, None)), \
                    patch('seo_agent.browser.ipaddress.ip_address', return_value=TestAddress()), \
                    BrowserSession() as browser:
                rendered = [browser.render(url, viewport, temporary) for viewport in VIEWPORTS]
                self.assertEqual([item['status'] for item in rendered], ['ok', 'ok'])
                self.assertEqual([item['headings'][0]['text'] for item in rendered], ['Wide', 'Compact'])
                self.assertIn('Detalhe renderizado', rendered[0]['text'])
                for item in rendered:
                    image = Path(item['screenshot'])
                    self.assertTrue(image.is_relative_to(Path(temporary)))
                    self.assertGreater(image.stat().st_size, 100)
                child = f'{url}child'
                journey = browser.render(child, VIEWPORTS[0], temporary,
                    navigation_path=[
                        {'url': url, 'via': 'search_result', 'label': 'Resultado'},
                        {'url': child, 'via': 'internal_link', 'label': 'Abrir detalhes'},
                    ])
                self.assertEqual(journey['status'], 'ok', journey)
                self.assertEqual(journey['headings'][0]['text'], 'Detalhes')
                self.assertEqual(journey['navigation_steps'][1]['action'], 'click_internal_link')
                self.assertEqual(journey['navigation_steps'][1]['result'], 'loaded')
                self.assertIn('/child', requested)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            denied_server.shutdown()
            denied_server.server_close()
            denied_thread.join(timeout=2)
            self.assertEqual(denied_origin_requests, [])


if __name__ == '__main__':
    unittest.main()
