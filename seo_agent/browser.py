"""Captura páginas renderizadas em contextos Chromium descartáveis."""

from contextlib import contextmanager
import hashlib
import ipaddress
from pathlib import Path
import shutil
from urllib.parse import urlsplit


VIEWPORTS = [
    {'name': 'desktop', 'width': 1365, 'height': 900, 'is_mobile': False},
    {'name': 'mobile', 'width': 390, 'height': 844, 'is_mobile': True},
]


class BrowserSession:
    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise RuntimeError('Instale as dependências do navegador: pip install -r requirements-browser.txt e python3 -m playwright install chromium.') from error
        executable = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
        self.engine = sync_playwright().start()
        bundled = self.engine.chromium.executable_path
        self.executable = executable or (bundled if Path(bundled).is_file() else None)
        if not self.executable:
            self.engine.stop()
            raise RuntimeError('Chromium não encontrado. Execute python3 -m playwright install chromium.')
        self.browsers = {}
        return self

    def __exit__(self, *_):
        try:
            for browser in self.browsers.values():
                browser.close()
        finally:
            self.engine.stop()

    def _browser_for(self, hostname, pinned_ip):
        key = hostname, pinned_ip
        if key not in self.browsers:
            address_rule = f'[{pinned_ip}]' if ':' in pinned_ip else pinned_ip
            rules = f'MAP {hostname} {address_rule}, MAP * ~NOTFOUND'
            try:
                self.browsers[key] = self.engine.chromium.launch(
                    executable_path=self.executable, headless=True,
                    args=[f'--host-resolver-rules={rules}', '--disable-background-networking'],
                )
            except Exception:
                raise RuntimeError(
                    'Não foi possível iniciar Chromium. Verifique a instalação e as dependências do sistema.'
                ) from None
        return self.browsers[key]

    def render(self, url, viewport, evidence_dir, *, locale='pt-BR', navigation_path=None):
        try:
            from seo_agent.http import fetch_url
            navigation_path = navigation_path or [{'url': url, 'via': 'direct', 'label': 'URL informada'}]
            response = fetch_url(url)
            if response.status != 200:
                raise ValueError(f'HTTP {response.status}')
            content_type = response.headers.get('content-type', '').split(';', 1)[0].lower()
            if content_type not in {'text/html', 'application/xhtml+xml'}:
                raise ValueError(f'Conteúdo não HTML: {content_type}')
            final_url = response.url
            parsed = urlsplit(final_url)
            addresses = [ipaddress.ip_address(value) for value in response.ip_addresses]
            pinned_ip = str(next((ip for ip in addresses if ip.version == 4), addresses[0]))
            if not all(ip.is_global for ip in addresses):
                raise ValueError('Destino do navegador precisa usar somente IPs públicos.')
            hostname = parsed.hostname.encode('idna').decode('ascii').lower()
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            origin = (parsed.scheme, hostname, port)
            width, height = viewport['width'], viewport['height']
            browser = self._browser_for(hostname, pinned_ip)
            context = browser.new_context(
                viewport={'width': width, 'height': height}, device_scale_factor=1,
                is_mobile=viewport['is_mobile'], has_touch=viewport['is_mobile'],
                locale=locale, timezone_id='America/Sao_Paulo', service_workers='block',
                accept_downloads=False,
            )
            blocked_requests = []

            def guard_request(route):
                target = urlsplit(route.request.url)
                target_port = target.port or (443 if target.scheme == 'https' else 80)
                allowed = ((target.scheme, target.hostname, target_port) == origin
                           and route.request.method in {'GET', 'HEAD'})
                if allowed:
                    route.continue_()
                else:
                    if len(blocked_requests) < 100:
                        blocked_requests.append({'url': route.request.url,
                                                 'method': route.request.method})
                    route.abort('blockedbyclient')

            context.route('**/*', guard_request)
            context.route_web_socket('**/*', lambda route: route.close())
            page = context.new_page()
            start = fetch_url(navigation_path[0]['url']) if navigation_path[0]['url'] != url else response
            start_url = start.url
            start_parts = urlsplit(start_url)
            start_origin = (start_parts.scheme, start_parts.hostname.encode('idna').decode('ascii').lower(),
                            start_parts.port or (443 if start_parts.scheme == 'https' else 80))
            if start_origin != origin:
                raise ValueError('Origem da página inicial difere da origem do destino.')
            page.goto(start_url, wait_until='domcontentloaded', timeout=20000)
            page.wait_for_function("document.readyState !== 'loading' && document.body", timeout=5000)
            page.wait_for_timeout(600)
            navigation_steps = [{'url': start_url, 'action': 'open', 'result': 'loaded'}]
            for step in navigation_path[1:]:
                expected = step['url']
                target_parts = urlsplit(expected)
                target_origin = (target_parts.scheme, target_parts.hostname.encode('idna').decode('ascii').lower(),
                                 target_parts.port or (443 if target_parts.scheme == 'https' else 80))
                if target_origin != origin:
                    raise ValueError(f"Passo de navegação fora da origem permitida: {expected}")
                anchor_indexes = page.locator('a[href]').evaluate_all(
                    "(anchors, target) => anchors.map((anchor, index) => "
                    "({index, href: anchor.href, visible: anchor.getClientRects().length > 0})) "
                    ".filter(anchor => anchor.visible && anchor.href === target) "
                    ".map(anchor => anchor.index)",
                    expected,
                )
                if not anchor_indexes:
                    raise ValueError(f"Link não visível na página de origem: {expected}")
                page.locator('a[href]').nth(anchor_indexes[0]).click(timeout=7000)
                page.wait_for_timeout(600)
                actual = urlsplit(page.url)._replace(fragment='').geturl()
                target = urlsplit(expected)._replace(fragment='').geturl()
                if actual != target:
                    raise ValueError(f"O link levou a {actual}, esperado {target}.")
                navigation_steps.append({'url': expected, 'action': 'click_internal_link',
                                         'label': step['label'], 'result': 'loaded'})
            page_data = page.evaluate('''() => {
                const visible = node => !!(node.getClientRects().length) && getComputedStyle(node).visibility !== 'hidden';
                const text = node => (node.innerText || '').replace(/\\s+/g, ' ').trim();
                return {
                    title: document.title || null,
                    description: document.querySelector('meta[name="description"]')?.content || null,
                    url: location.href,
                    text: text(document.body),
                    headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
                        .filter(visible).map(node => ({level: Number(node.tagName.slice(1)), text: text(node)})),
                    links: [...document.querySelectorAll('a[href]')].filter(visible).map(node => ({
                        url: node.href, text: text(node), rel: (node.rel || '').split(/\\s+/).filter(Boolean)
                    })).slice(0, 200),
                    controls: [...document.querySelectorAll('a[href],button,input,select,textarea,[role="button"],[role="link"]')]
                        .filter(visible).map(node => ({
                            role: node.getAttribute('role') || node.tagName.toLowerCase(),
                            label: node.getAttribute('aria-label') || node.innerText || node.title || '',
                            type: node.type || null
                        })).slice(0, 100)
                };
            }''')
            digest = hashlib.sha256(final_url.encode()).hexdigest()[:16]
            destination = Path(evidence_dir) / digest / f"{viewport['name']}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(destination), full_page=False, animations='disabled', timeout=10000)
            return {
                'status': 'ok', 'url': page_data['url'], 'http_status': 200,
                'navigation_steps': navigation_steps,
                'blocked_requests': blocked_requests,
                'viewport': {'name': viewport['name'], 'width': width, 'height': height,
                             'is_mobile': viewport['is_mobile']},
                **page_data,
                'text': page_data['text'][:12000], 'text_truncated': len(page_data['text']) > 12000,
                'screenshot': str(destination),
            }
        except Exception as error:
            return {'status': 'error', 'url': url,
                    'navigation_steps': locals().get('navigation_steps', []),
                    'error': f'{type(error).__name__}: {str(error)[:500]}',
                    'viewport': {'name': viewport['name'], 'width': viewport['width'],
                                 'height': viewport['height'], 'is_mobile': viewport['is_mobile']}}
        finally:
            if 'context' in locals():
                context.close()


@contextmanager
def browser_session():
    with BrowserSession() as session:
        yield session
