"""Experimento isolado de Quick Actions: Kitesurf e Chromium remoto."""

import json
from pathlib import Path
import re
from statistics import median
from time import monotonic
from uuid import uuid4

from seo_agent.page import extract_page
from seo_agent.search_batch import normalize_url


def experiment(fixtures, output, environment, *, fetch=None):
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError('Informe uma lista não vazia de fixtures.')
    names = set()
    for fixture in fixtures:
        if (not isinstance(fixture, dict) or not isinstance(fixture.get('name'), str)
                or not re.fullmatch(r'[a-z0-9-]+', fixture['name']) or fixture['name'] in names
                or not isinstance(fixture.get('url'), str)
                or not isinstance(fixture.get('expected_text'), list) or not fixture['expected_text']
                or any(not isinstance(value, str) or not value.strip() for value in fixture['expected_text'])):
            raise ValueError('Fixture exige name e expected_text não vazios.')
        normalize_url(fixture['url'])
        names.add(fixture['name'])
    report = {'status': 'credentials_missing', 'captures': [], 'summary': {},
              'baseline': 'Chromium remoto do Browser Run; não substitui nem comprova o crawler local.',
              'recommendation': 'Não adotar antes do aceite remoto das fixtures e da busca compatível.'}
    account, token = (environment.get(key, '').strip() for key in ('CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN'))
    if not account or not token:
        return report
    if not re.fullmatch(r'[a-fA-F0-9]{32}', account):
        raise ValueError('CLOUDFLARE_ACCOUNT_ID deve conter 32 caracteres hexadecimais.')
    if fetch is None:
        from seo_agent.http import fetch_url
        fetch = fetch_url
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid4())
    for fixture in fixtures:
        for engine in ('chromium', 'kitesurf'):
            endpoint = f'https://api.cloudflare.com/client/v4/accounts/{account}/browser-run/snapshot'
            if engine == 'kitesurf':
                endpoint += '?browser=kitesurf'
            for index in range(5):
                capture = {'scenario': fixture['name'], 'engine': engine, 'attempt': index + 1,
                           'api_status': None, 'destination_status': None, 'destination_200': False}
                start = monotonic()
                try:
                    response = fetch(endpoint, method='POST', headers={'Authorization': 'Bearer ' + token,
                                     'Content-Type': 'application/json'}, body=json.dumps({
                        'url': fixture['url'], 'formats': ['content', 'markdown'],
                        'gotoOptions': {'waitUntil': 'networkidle0', 'timeout': 20000}}).encode())
                    capture['api_status'] = response.status
                    if response.status != 200:
                        raise ValueError('API não respondeu HTTP 200.')
                    payload = json.loads(response.text())
                    if not isinstance(payload, dict):
                        raise ValueError('Captura inválida.')
                    html = payload['result']['content']
                    if payload.get('success') is not True or not isinstance(html, str):
                        raise ValueError('Captura inválida.')
                    meta = payload.get('meta') or {}
                    if not isinstance(meta, dict):
                        raise ValueError('Metadados inválidos.')
                    capture['destination_status'] = meta.get('status')
                    capture['destination_200'] = capture['destination_status'] == 200
                    filename = output / f'{run_id}-{fixture["name"]}-{engine}-{index + 1}.html'
                    filename.write_text(html, encoding='utf-8')
                    capture['html_file'] = str(filename.resolve())
                    capture['seo'] = extract_page(html, fixture['url'])
                    capture['missing_text'] = [text for text in fixture['expected_text'] if text not in capture['seo']['text']]
                    capture['expected_text_complete'] = not capture['missing_text'] and capture['destination_200']
                    capture['browser_ms_used'] = response.headers.get('x-browser-ms-used')
                except (OSError, ValueError, KeyError, TypeError):
                    capture['error'] = 'Falha de captura; investigar credenciais, fixture ou resposta do serviço.'
                capture['wall_ms'] = round((monotonic() - start) * 1000, 2)
                report['captures'].append(capture)
    report['status'] = 'measured'
    for engine in ('chromium', 'kitesurf'):
        samples = [capture for capture in report['captures'] if capture['engine'] == engine]
        report['summary'][engine] = {'attempts': len(samples), 'wall_ms_median': median(c['wall_ms'] for c in samples),
                                    'complete': sum(bool(c.get('expected_text_complete')) for c in samples)}
    (output / f'{run_id}-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
