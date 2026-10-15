"""Persistência de execuções no repositório local (SQLite) do projeto."""

from contextlib import closing
import json
import sqlite3


def save_run(record, store, *, before_insert=None):
    """Garante a tabela de execuções e insere o registro.

    `before_insert(database)` roda na mesma transação, antes do INSERT,
    quando a gravação precisa consultar execuções anteriores (avisos).
    """
    store.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(store)) as database, database:
        database.execute(
            'CREATE TABLE IF NOT EXISTS runs '
            '(id TEXT PRIMARY KEY, project_id TEXT NOT NULL, record TEXT NOT NULL)')
        if before_insert is not None:
            before_insert(database)
        database.execute('INSERT INTO runs (id, project_id, record) VALUES (?, ?, ?)',
                         (record['run_id'], record['project_id'],
                          json.dumps(record, ensure_ascii=False)))
