"""Rodadas explícitas e limitadas; nenhuma instalação/ativação automática."""

from contextlib import contextmanager, closing
from datetime import datetime, UTC, timedelta
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@contextmanager
def project_lock(store, project_id):
    store = store.resolve()
    directory = store.parent / (store.name + '.locks')
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / project_id).open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Projeto já possui uma execução em andamento.') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_worker(command, timeout):
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          start_new_session=True) as process:
        try:
            stdout, _ = process.communicate(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            if isinstance(error, KeyboardInterrupt):
                raise
            raise ValueError('Rodada excedeu max_seconds; processo interrompido.') from None
        if process.returncode:
            raise ValueError('Worker falhou; conferir configuração, dependências ou execução concorrente.')
        return json.loads(stdout)


def schedule_tick(config_file, *, clock=None, worker=None):
    from seo_agent.__main__ import validate_project, prepare_run
    config = json.loads(config_file.read_text(encoding='utf-8'))
    fields = {'project', 'store', 'hours', 'timezone', 'max_queries', 'max_pages', 'max_seconds',
              'recovery', 'model', 'no_searxng', 'env_file'}
    if not isinstance(config, dict) or config.keys() - fields:
        raise ValueError('Configuração de agendamento inválida.')
    for field in ('project', 'store', 'timezone', 'model'):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError(f'Agendamento exige {field}.')
    if not isinstance(config.get('hours'), list) or not config['hours'] or any(
            not isinstance(hour, str) or not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', hour) for hour in config['hours']):
        raise ValueError('Agendamento exige hours no formato HH:MM.')
    if config.get('recovery') not in {'once', 'skip'}:
        raise ValueError('Defina recovery: once ou skip.')
    for field in ('max_queries', 'max_pages', 'max_seconds'):
        if type(config.get(field)) is not int or config[field] < 1:
            raise ValueError(f'Agendamento exige {field} inteiro positivo.')
    if '/' not in config['model'] or type(config.get('no_searxng', False)) is not bool:
        raise ValueError('Defina modelo provedor/modelo e no_searxng booleano.')
    try:
        zone = ZoneInfo(config['timezone'])
    except ZoneInfoNotFoundError:
        raise ValueError('Fuso horário desconhecido.') from None
    project_file = (config_file.parent / config['project']).resolve()
    store = (config_file.parent / config['store']).resolve()
    project = validate_project(json.loads(project_file.read_text(encoding='utf-8')))
    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise ValueError('Relógio exige timezone.')
    now = now.astimezone(zone)
    slots = [datetime.combine(day, datetime.strptime(hour, '%H:%M').time(), zone)
             for day in (now.date() - timedelta(days=1), now.date()) for hour in config['hours']]
    slot = max(value for value in slots if value <= now)
    if config['recovery'] == 'skip' and now.replace(second=0, microsecond=0) != slot:
        return {'status': 'not_due'}
    slot = slot.isoformat()
    store.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(store)) as database, database:
        database.execute('CREATE TABLE IF NOT EXISTS schedule_slots '
                         '(project_id TEXT, slot TEXT, record TEXT, PRIMARY KEY(project_id, slot))')
        cursor = database.execute('INSERT OR IGNORE INTO schedule_slots VALUES (?, ?, ?)',
                                  (project['id'], slot, json.dumps({'status': 'claimed'})))
        if not cursor.rowcount:
            return {'status': 'already_claimed', 'slot': slot}
    command = [sys.executable, '-B', '-m', 'seo_agent', 'run', '--project', str(project_file),
               '--store', str(store), '--model', config['model'], '--max-pages', str(config['max_pages']),
               '--max-queries', str(config['max_queries'])]
    if config.get('no_searxng'):
        command.append('--no-searxng')
    command += ['--env-file', str((config_file.parent / config.get('env_file', '.env')).resolve())]
    interrupted = False
    try:
        result = (worker or run_worker)(command, config['max_seconds'])
        record = {'status': 'executed', 'slot': slot, 'run_id': result['run_id'], 'run_status': result['status']}
    except (OSError, ValueError, KeyError, KeyboardInterrupt) as error:
        interrupted = isinstance(error, KeyboardInterrupt)
        failed = prepare_run(project, store, status='failed', result={'sources': [],
            'errors': [{'stage': 'scheduler', 'error': 'Rodada falhou ou excedeu tempo; investigar dependências, limites e concorrência.'}],
            'pending': ['Últimos resultados válidos preservados.']})
        record = {'status': 'interrupted' if interrupted else 'failed', 'slot': slot, 'run_id': failed['run_id']}
    with closing(sqlite3.connect(store)) as database, database:
        database.execute('UPDATE schedule_slots SET record=? WHERE project_id=? AND slot=?',
                         (json.dumps(record), project['id'], slot))
    if interrupted:
        raise KeyboardInterrupt
    return record
