"""Extração estática de HTML; não executa JavaScript nem avalia CSS."""

from html.parser import HTMLParser
import json
from urllib.parse import urljoin, urlsplit


VOID_TAGS = set('area base br col embed hr img input link meta param source track wbr'.split())
BLOCK_TAGS = set('address article aside blockquote br div dl dt dd footer form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table td th tr ul'.split())
HEADINGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
DATE_META = {'article:published_time', 'article:modified_time'}


def _normalize(text):
    return ' '.join(text.split())


def _http_url(href, base):
    if not href:
        return None
    try:
        resolved = urljoin(base, href.strip())
        parsed = urlsplit(resolved)
        if parsed.scheme in {'http', 'https'} and parsed.hostname:
            return resolved
    except ValueError:
        pass
    return None


def _reject_json_constant(value):
    raise ValueError(f'Constante JSON inválida: {value}.')


JSON_LD_DATES = ('datePublished', 'dateModified', 'dateCreated')


def _json_ld_objects(structured_data):
    for block in structured_data:
        graph = block.get('@graph')
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    yield item
        yield block


def _signal_values(value):
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, str) and item.strip():
            yield item.strip()
        elif isinstance(item, dict):
            name = item.get('name')
            if isinstance(name, str) and name.strip():
                yield name.strip()


def _unique_signals(signals):
    seen = set()
    unique = []
    for item in signals:
        key = (item['source'], item['value'])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.page = {
            'title': None, 'description': None, 'language': None, 'canonical': None,
            'headings': [], 'robots': [], 'social': {}, 'hreflang': [], 'links': [],
            'dates': [], 'authors': [],
            'structured_data': [], 'structured_data_errors': [],
            'images': [], 'issues': [],
        }
        self.stack = []
        self.text = []
        self.base_href = None
        self.json_ld_count = 0

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if any(frame['tag'] == 'template' for frame in self.stack):
            if tag not in VOID_TAGS:
                self.stack.append({'tag': tag, 'hidden': True, 'parts': None, 'attrs': attrs})
            return
        hidden = bool(self.stack and self.stack[-1]['hidden'])
        hidden = hidden or tag in {'head', 'script', 'style', 'template'} or 'hidden' in attrs
        if tag == 'html':
            self.page['language'] = attrs.get('lang') or None
        if tag == 'base' and self.base_href is None and 'href' in attrs:
            self.base_href = attrs['href'] or ''
        if tag == 'meta':
            name = (attrs.get('name') or attrs.get('property') or '').lower()
            content = _normalize(attrs.get('content') or '')
            if name == 'description':
                self.page['description'] = content or None
            elif name == 'robots' and content:
                self.page['robots'].append(content)
            elif name.startswith(('og:', 'twitter:')):
                self.page['social'][name] = content
            if name == 'author' and content:
                self.page['authors'].append({'source': 'meta:author', 'value': content})
            if name in DATE_META and content:
                self.page['dates'].append({'source': f'meta:{name}', 'value': content})
            if name in {'robots', 'googlebot'} and {'noindex', 'none'} & set(content.lower().replace(',', ' ').split()):
                self.page['issues'].append({
                    'code': 'meta_noindex', 'severity': 'info',
                    'message': 'Metadado declara restrição de indexação para o agente indicado.',
                    'evidence': {'agent': name, 'content': content},
                })
        if tag == 'link':
            rel = (attrs.get('rel') or '').lower().split()
            if 'canonical' in rel and self.page['canonical'] is None:
                self.page['canonical'] = attrs.get('href')
            if 'alternate' in rel and attrs.get('hreflang'):
                self.page['hreflang'].append({'language': attrs['hreflang'], 'url': attrs.get('href')})
        if tag == 'img' and not hidden:
            self.page['images'].append({
                'src': attrs.get('src'), 'alt': (attrs['alt'] or '') if 'alt' in attrs else None,
            })
        if tag == 'time' and not hidden:
            datetime_value = _normalize(attrs.get('datetime') or '')
            if datetime_value:
                self.page['dates'].append({'source': 'time', 'value': datetime_value})
        if tag in BLOCK_TAGS and not hidden:
            self._separate_text()
        capture = tag == 'title' or (tag in HEADINGS | {'a'} and not hidden)
        capture = capture or (tag == 'script' and (attrs.get('type') or '').lower() == 'application/ld+json')
        if tag not in VOID_TAGS:
            self.stack.append({'tag': tag, 'hidden': hidden, 'parts': [] if capture else None, 'attrs': attrs})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data):
        visible = not self.stack or not self.stack[-1]['hidden']
        if visible:
            self.text.append(data)
        for frame in self.stack:
            if frame['parts'] is not None and (visible or frame['tag'] in {'title', 'script'}):
                frame['parts'].append(data)

    def _separate_text(self):
        self.text.append(' ')
        for frame in self.stack:
            if frame['parts'] is not None and frame['tag'] != 'script':
                frame['parts'].append(' ')

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]['tag'] == tag:
                while len(self.stack) > index:
                    self._finish(self.stack.pop())
                break

    def _finish(self, frame):
        tag = frame['tag']
        if frame['parts'] is not None:
            text = _normalize(''.join(frame['parts']))
            if tag == 'title' and self.page['title'] is None:
                self.page['title'] = text or None
            elif tag in HEADINGS:
                self.page['headings'].append({'level': int(tag[1]), 'text': text})
            elif tag == 'a':
                self.page['links'].append({
                    'url': frame['attrs'].get('href'), 'text': text,
                    'rel': (frame['attrs'].get('rel') or '').lower().split(),
                })
            elif tag == 'script':
                self.json_ld_count += 1
                try:
                    value = json.loads(''.join(frame['parts']), parse_constant=_reject_json_constant)
                    objects = value if isinstance(value, list) else [value]
                    if not all(isinstance(item, dict) for item in objects):
                        raise ValueError('Esperado objeto JSON-LD ou lista de objetos.')
                    self.page['structured_data'].extend(objects)
                except ValueError as error:
                    self.page['structured_data_errors'].append(f'Bloco JSON-LD {self.json_ld_count}: {error}')
        if tag in BLOCK_TAGS and not frame['hidden']:
            self._separate_text()


def extract_page(html: str, url: str) -> dict:
    """Extrai HTML recebido, sem DOM renderizado ou reparo completo de HTML5.

    Visibilidade considera tags e hidden, não CSS. O chamador limita o tamanho
    da entrada. JSON-LD é validado como JSON, sem validar seu vocabulário/schema.
    """
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    while parser.stack:
        parser._finish(parser.stack.pop())
    page = parser.page
    base = _http_url(parser.base_href, url) or url
    for block in _json_ld_objects(page['structured_data']):
        for key in JSON_LD_DATES:
            for value in _signal_values(block.get(key)):
                page['dates'].append({'source': f'json_ld:{key}', 'value': value})
        for name in _signal_values(block.get('author')):
            page['authors'].append({'source': 'json_ld:author', 'value': name})
    page['dates'] = _unique_signals(page['dates'])
    page['authors'] = _unique_signals(page['authors'])
    page['canonical'] = _http_url(page['canonical'], base)
    page['hreflang'] = [item | {'url': resolved} for item in page['hreflang']
                        if (resolved := _http_url(item['url'], base))]
    page['links'] = [item | {'url': resolved, 'internal': urlsplit(resolved).hostname == urlsplit(url).hostname}
                     for item in page['links'] if (resolved := _http_url(item['url'], base))]
    page['images'] = [item | {'src': _http_url(item['src'], base) or item['src']} for item in page['images']]
    for field in ('title', 'description', 'canonical'):
        if page[field] is None:
            page['issues'].append({
                'code': f'{field}_missing', 'severity': 'warning',
                'message': f'{field} ausente ou sem valor utilizável no HTML.',
                'evidence': {'field': field, 'value': None},
            })
    if not any(heading['level'] == 1 for heading in page['headings']):
        page['issues'].append({
            'code': 'h1_missing', 'severity': 'warning', 'message': 'Nenhum H1 visível encontrado no HTML.',
            'evidence': {'h1_count': 0},
        })
    for image in page['images']:
        if image['alt'] is None:
            page['issues'].append({
                'code': 'image_alt_missing', 'severity': 'warning',
                'message': 'Imagem sem atributo alt; verificar sua função no conteúdo.',
                'evidence': {'src': image['src']},
            })
    for error in page['structured_data_errors']:
        page['issues'].append({
            'code': 'invalid_json_ld', 'severity': 'error',
            'message': 'Bloco JSON-LD inválido.', 'evidence': {'error': error},
        })
    return page | {'text': _normalize(''.join(parser.text))}
