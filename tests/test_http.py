"""Transporte HTTP validado sem conexões reais."""

import io
import socket
import ssl
import unittest
from unittest.mock import Mock, patch

from seo_agent.http import Response, fetch_url


class HTTPFetch(unittest.TestCase):
    def setUp(self):
        self.dns = patch('socket.getaddrinfo').start()
        self.socket = patch('socket.socket').start()
        self.addCleanup(patch.stopall)
        self.dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))]
        self.connections = []

    def reply(self, body=b'page', status='200 OK', headers=()):
        connection = Mock()
        wire = (f'HTTP/1.1 {status}\r\nContent-Length: {len(body)}\r\n'
                + ''.join(f'{name}: {value}\r\n' for name, value in headers)
                + '\r\n').encode() + body
        connection.makefile.return_value = io.BytesIO(wire)
        self.connections.append(connection)
        self.socket.side_effect = self.connections
        return connection

    def test_fetches_from_the_resolved_ip_with_original_host_and_bounded_timeout(self):
        connection = self.reply(headers=[('Content-Type', 'text/html'),
                                        ('X-Robots-Tag', 'noindex'), ('X-Robots-Tag', 'nofollow')])
        result = fetch_url('http://example.org/guide?q=plants#intro')
        self.assertEqual(result.url, 'http://example.org/guide?q=plants')
        self.assertEqual(result.status, 200)
        self.assertEqual(result.body, b'page')
        self.assertEqual(result.headers['content-type'], 'text/html')
        self.assertEqual(result.headers['x-robots-tag'], 'noindex, nofollow')
        self.assertEqual(result.ip_addresses, ['93.184.216.34'])
        self.assertEqual(result.redirects, [])
        self.assertIsNone(result.tls)
        connection.connect.assert_called_once_with(('93.184.216.34', 80))
        connection.settimeout.assert_called_once_with(15)
        sent = b''.join(call.args[0] for call in connection.sendall.call_args_list)
        self.assertIn(b'GET /guide?q=plants HTTP/1.1\r\n', sent)
        self.assertIn(b'Host: example.org\r\n', sent)
        self.assertIn(b'User-Agent: SEOAgent/0.1\r\n', sent)
        self.assertIn(b'Accept-Encoding: identity\r\n', sent)
        self.assertEqual(self.dns.call_count, 1)
        connection.close.assert_called()

    def test_tries_another_validated_address_if_the_first_connection_fails(self):
        self.dns.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('2606:4700:4700::1111', 80, 0, 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80)),
        ]
        first = self.reply()
        first.connect.side_effect = OSError('IPv6 indisponível')
        second = self.reply(body=b'via IPv4')
        result = fetch_url('http://example.org/')
        self.assertEqual(result.body, b'via IPv4')
        first.close.assert_called()
        second.connect.assert_called_once_with(('93.184.216.34', 80))
        self.assertEqual(self.dns.call_count, 1)

    def test_revalidates_dns_even_when_redirect_keeps_the_hostname(self):
        self.dns.side_effect = [
            [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))],
            [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 80))],
        ]
        self.reply(status='302 Found', headers=[('Location', '/private')])
        with self.assertRaisesRegex(ValueError, 'públic'):
            fetch_url('http://example.org/')
        self.assertEqual(self.socket.call_count, 1)

    def test_rejects_invalid_urls_and_nonpublic_literal_ips_before_connecting(self):
        urls = [
            'file:///etc/passwd', 'ftp://example.org/file', 'example.org',
            'http://user:password@example.org/', 'http://example.org:invalid/',
            'http://example.org:0/', 'http://example.org/\r\nInjected: yes',
            'http://127.0.0.1/', 'http://10.0.0.1/', 'http://169.254.169.254/',
            'http://[::1]/', 'http://[fe80::1]/', 'http://[::ffff:127.0.0.1]/',
            'http://100.64.0.1/', 'http://224.0.0.1/',
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                fetch_url(url)
        self.socket.assert_not_called()

    def test_follows_relative_redirects_and_records_the_final_url(self):
        self.reply(status='302 Found', headers=[('Location', '/final')])
        self.reply(body=b'final page')
        result = fetch_url('http://example.org/start')
        self.assertEqual(result.url, 'http://example.org/final')
        self.assertEqual(result.body, b'final page')
        self.assertEqual(result.redirects, [{
            'url': 'http://example.org/start', 'status': 302,
            'location': 'http://example.org/final',
        }])
        self.assertEqual(self.dns.call_count, 2)

    def test_revalidates_private_destinations_after_redirects(self):
        self.reply(status='302 Found', headers=[('Location', 'http://127.0.0.1/private')])
        with self.assertRaisesRegex(ValueError, 'públic'):
            fetch_url('http://example.org/')
        self.assertEqual(self.socket.call_count, 1)

    def test_trusted_search_endpoint_can_be_local_but_cannot_redirect(self):
        self.dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 8080))]
        connection = self.reply(body=b'{"results": []}')
        result = fetch_url('http://127.0.0.1:8080/search?q=plants', allow_private=True)
        self.assertEqual(result.body, b'{"results": []}')
        connection.connect.assert_called_once_with(('127.0.0.1', 8080))
        self.connections.clear()
        self.reply(status='302 Found', headers=[('Location', 'http://other.example/search?q=plants')])
        with self.assertRaisesRegex(ValueError, 'redirecion'):
            fetch_url('http://127.0.0.1:8080/search?q=plants', allow_private=True)
        self.assertEqual(self.socket.call_count, 2)

    def test_restricted_headers_are_never_forwarded_across_redirects(self):
        self.reply(status='302 Found', headers=[('Location', 'http://other.example/search')])
        with self.assertRaisesRegex(ValueError, 'cabeçalhos restritos'):
            fetch_url('http://api.search.brave.com/res/v1/web/search',
                      headers={'X-Subscription-Token': 'secret'})
        self.assertEqual(self.socket.call_count, 1)

    def test_posts_json_with_credentials_and_never_replays_on_redirect(self):
        connection = self.reply(status='307 Temporary Redirect', headers=[('Location', '/other')])
        with self.assertRaisesRegex(ValueError, 'redirecion'):
            fetch_url('http://example.org/search', method='POST', body=b'{"q":"igrejas"}',
                      headers={'Authorization': 'Bearer key', 'Content-Type': 'application/json'})
        wire = b''.join(call.args[0] for call in connection.sendall.call_args_list)
        self.assertIn(b'POST /search HTTP/1.1', wire)
        self.assertTrue(wire.endswith(b'{"q":"igrejas"}'))
        self.assertEqual(self.socket.call_count, 1)

    def test_stops_after_five_redirects(self):
        for index in range(6):
            self.reply(status='302 Found', headers=[('Location', f'/page{index}')])
        with self.assertRaisesRegex(ValueError, '5 redirecion'):
            fetch_url('http://example.org/start')
        self.assertEqual(self.socket.call_count, 6)

    def test_rejects_payload_larger_than_two_mib(self):
        self.reply(body=b'x' * (2 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(ValueError, '2 MiB'):
            fetch_url('http://example.org/')

    def test_rejects_compressed_payload_when_identity_was_requested(self):
        self.reply(body=b'compressed', headers=[('Content-Encoding', 'gzip')])
        with self.assertRaisesRegex(ValueError, 'compress'):
            fetch_url('http://example.org/')

    def test_rejects_unsupported_transfer_encoding_and_duplicate_compression_headers(self):
        for headers in [[('Transfer-Encoding', 'gzip')],
                        [('Content-Encoding', 'gzip'), ('Content-Encoding', 'identity')]]:
            with self.subTest(headers=headers):
                self.connections.clear()
                self.reply(headers=headers)
                with self.assertRaisesRegex(ValueError, 'compress'):
                    fetch_url('http://example.org/')

    def test_reports_invalid_http_as_an_actionable_value_error(self):
        connection = self.reply()
        connection.makefile.return_value = io.BytesIO(b'not an HTTP response\r\n')
        with self.assertRaisesRegex(ValueError, 'HTTP'):
            fetch_url('http://example.org/')

    def test_percent_encodes_nonascii_path_and_query_without_losing_the_original_url(self):
        connection = self.reply()
        result = fetch_url('http://example.org/café?q=maçã')
        sent = b''.join(call.args[0] for call in connection.sendall.call_args_list)
        self.assertIn(b'GET /caf%C3%A9?q=ma%C3%A7%C3%A3 HTTP/1.1\r\n', sent)
        self.assertEqual(result.url, 'http://example.org/café?q=maçã')

    def test_https_validates_the_original_host_and_reports_certificate_expiry(self):
        self.dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
        connection = self.reply()
        connection.getpeercert.return_value = {'notAfter': 'Oct 13 12:00:00 2027 GMT'}
        with patch('ssl.SSLContext.wrap_socket', autospec=True, return_value=connection) as wrap:
            result = fetch_url('https://example.org/')
        context = wrap.call_args.args[0]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(wrap.call_args.kwargs['server_hostname'], 'example.org')
        connection.connect.assert_called_once_with(('93.184.216.34', 443))
        self.assertEqual(result.tls, {'expires_at': '2027-10-13T12:00:00+00:00'})

    def test_rejects_dns_answers_containing_any_nonpublic_address(self):
        for address in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '192.168.1.1', '::1']:
            with self.subTest(address=address):
                self.dns.return_value = [
                    (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80)),
                    (socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 80)),
                ]
                with self.assertRaisesRegex(ValueError, 'públic'):
                    fetch_url('http://example.org/')
        self.socket.assert_not_called()


class ResponseText(unittest.TestCase):
    def test_decodes_declared_charset_and_replaces_invalid_utf8(self):
        response = Response('https://example.org/', 200,
                            {'content-type': 'text/html; charset=iso-8859-1'},
                            b'caf\xe9', [], [], None)
        self.assertEqual(response.text(), 'café')
        response.headers = {'content-type': 'text/plain; charset=unknown-charset'}
        response.body = b'caf\xff'
        self.assertEqual(response.text(), 'caf\ufffd')


if __name__ == '__main__':
    unittest.main()
