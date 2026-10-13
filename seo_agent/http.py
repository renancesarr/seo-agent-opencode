"""HTTP com limites de leitura e destinos públicos validados."""

from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import Message
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import quote, urljoin, urlsplit, urlunsplit


@dataclass
class Response:
    url: str
    status: int
    headers: dict
    body: bytes
    redirects: list
    ip_addresses: list
    tls: dict | None

    def text(self):
        content_type = Message()
        content_type['content-type'] = self.headers.get('content-type', '')
        encoding = content_type.get_content_charset() or 'utf-8'
        try:
            return self.body.decode(encoding, errors='replace')
        except LookupError:
            return self.body.decode('utf-8', errors='replace')


def _require_public(address):
    ip = ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or ip.is_reserved:
        raise ValueError('Destino sem IP público: informe uma URL pública para leitura.')


def _fetch_once(url, *, allow_private):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError('URL inválida: confira o host e a porta.') from error
    if (parsed.scheme not in ('http', 'https') or not host or port == 0
            or parsed.username is not None or parsed.password is not None
            or '%' in host or any(ord(char) <= 32 or ord(char) == 127 for char in url)):
        raise ValueError('URL inválida: use http/https com host e sem credenciais ou espaços.')
    port = port or (443 if parsed.scheme == 'https' else 80)
    host = host.encode('idna').decode('ascii')
    if not allow_private:
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            _require_public(str(literal))
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError('Host sem endereço DNS: confira a URL e tente novamente.')
    if not allow_private:
        for entry in addresses:
            _require_public(entry[4][0])
    connection = http.client.HTTPConnection(host, port, timeout=15)
    sock = None
    try:
        for index, (family, kind, protocol, _, address) in enumerate(addresses):
            sock = socket.socket(family, kind, protocol)
            try:
                sock.settimeout(15)
                sock.connect(address)
                break
            except OSError:
                sock.close()
                if index == len(addresses) - 1:
                    raise
        tls = None
        if parsed.scheme == 'https':
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            certificate = sock.getpeercert()
            tls = {'expires_at': datetime.fromtimestamp(
                ssl.cert_time_to_seconds(certificate['notAfter']), timezone.utc,
            ).isoformat()}
        connection.sock = sock
        target = quote(urlunsplit(('', '', parsed.path or '/', parsed.query, '')),
                       safe="/%?:@!$&'()*+,;=-._~[]")
        connection.request('GET', target, headers={
            'User-Agent': 'SEOAgent/0.1', 'Accept-Encoding': 'identity',
        })
        with connection.getresponse() as incoming:
            headers = {name.lower(): incoming.getheader(name) for name, _ in incoming.getheaders()}
            if (headers.get('content-encoding', 'identity').strip().lower() not in ('', 'identity')
                    or headers.get('transfer-encoding', '').strip().lower() not in ('', 'chunked')):
                raise ValueError('Resposta comprimida não suportada: o servidor deve enviar sem compressão.')
            body = incoming.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise ValueError('Resposta excede 2 MiB: selecione uma página menor.')
            return Response(urlunsplit(parsed._replace(fragment='')), incoming.status,
                            headers, body, [], [entry[4][0] for entry in addresses], tls)
    finally:
        connection.close()
        if sock is not None:
            sock.close()


def fetch_url(url, *, allow_private=False):
    redirects = []
    while True:
        try:
            response = _fetch_once(url, allow_private=allow_private)
        except http.client.HTTPException as error:
            raise ValueError('Resposta HTTP inválida ou incompleta: confira o servidor e tente novamente.') from error
        except UnicodeError as error:
            raise ValueError('URL inválida: confira a codificação do host e do caminho.') from error
        location = response.headers.get('location')
        if response.status not in (301, 302, 303, 307, 308) or not location:
            response.redirects = redirects
            return response
        if allow_private:
            raise ValueError('Endpoint de busca redirecionou: configure sua URL final diretamente.')
        if len(redirects) >= 5:
            raise ValueError('Limite de 5 redirecionamentos: informe a URL final da página.')
        if any(ord(char) <= 32 or ord(char) == 127 for char in location):
            raise ValueError('Redirecionamento inválido: informe uma URL sem espaços ou controles.')
        destination = urljoin(response.url, location)
        redirects.append({'url': response.url, 'status': response.status, 'location': destination})
        url = destination
