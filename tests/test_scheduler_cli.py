from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, UTC
import io
import json
from pathlib import Path
import tempfile
import unittest

from seo_agent.__main__ import main


class SchedulerCLI(unittest.TestCase):
    def test_due_slots_survive_restart_and_recovery_runs_only_latest_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = {'id': 'horta', 'business_context': 'Loja', 'audience': 'Moradores', 'language': 'pt-BR',
                       'geography': 'Brasil', 'keywords': ['horta'], 'content_goal': 'Guia'}
            (root / 'project.json').write_text(json.dumps(project))
            config = {'project': 'project.json', 'store': 'history.sqlite3', 'hours': ['08:00', '20:00'],
                      'timezone': 'America/Sao_Paulo', 'max_queries': 10, 'max_pages': 20, 'max_seconds': 900,
                      'recovery': 'once', 'model': 'ollama/fixture', 'no_searxng': True, 'interval_seconds': 60}
            path = root / 'schedule.json'
            path.write_text(json.dumps(config))
            calls = []
            def worker(command, timeout):
                calls.append((command, timeout))
                return {'run_id': 'controlled-run', 'status': 'collected'}
            def tick(now):
                with redirect_stdout(io.StringIO()) as output:
                    main(['schedule-tick', '--config', str(path)], clock=lambda: now, worker=worker)
                return json.loads(output.getvalue())
            first = tick(datetime(2026, 10, 13, 11, 0, tzinfo=UTC))
            self.assertEqual(first['slot'], '2026-10-13T08:00:00-03:00')
            self.assertEqual(tick(datetime(2026, 10, 13, 12, 0, tzinfo=UTC))['status'], 'already_claimed')
            latest = tick(datetime(2026, 10, 16, 23, 0, tzinfo=UTC))
            self.assertEqual(latest['slot'], '2026-10-16T20:00:00-03:00')
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][1], 900)
            self.assertIn('run', calls[0][0])
            interval_flag = calls[0][0].index('--interval-seconds')
            self.assertEqual(calls[0][0][interval_flag + 1], '60')
            def failed_worker(*args):
                raise ValueError('timeout simulado')
            with redirect_stdout(io.StringIO()) as output:
                main(['schedule-tick', '--config', str(path)],
                     clock=lambda: datetime(2026, 10, 17, 11, 0, tzinfo=UTC), worker=failed_worker)
            self.assertEqual(json.loads(output.getvalue())['status'], 'failed')
            with redirect_stdout(io.StringIO()) as output:
                main(['notices', '--project-id', 'horta', '--store', str(root / 'history.sqlite3')])
            self.assertEqual(json.loads(output.getvalue())['notices'][0]['kind'], 'failure')
            config['recovery'] = 'skip'
            path.write_text(json.dumps(config))
            self.assertEqual(tick(datetime(2026, 10, 18, 11, 5, tzinfo=UTC))['status'], 'not_due')

    def test_invalid_config_does_not_start_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'schedule.json'
            path.write_text('{}')
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['schedule-tick', '--config', str(path)], worker=lambda *a: self.fail('Não iniciar worker.'))


if __name__ == '__main__':
    unittest.main()
