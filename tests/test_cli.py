"""Aceite da interface de configuração e preparação, sem rede ou modelos."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectCLI(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.config = self.directory / 'project.json'
        self.database = self.directory / 'history.sqlite3'
        self.project = {
            'id': 'horta-local',
            'business_context': 'Loja de plantas e insumos para hortas.',
            'audience': 'Pessoas cultivando alimentos em casa.',
            'language': 'pt-BR',
            'geography': 'Goiás, Brasil',
            'keywords': ['horta em apartamento'],
            'content_goal': 'Ajudar a iniciar uma horta em pouco espaço.',
        }

    def invoke(self, *arguments):
        return subprocess.run(
            [sys.executable, '-B', '-m', 'seo_agent', *arguments],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def write_project(self, project=None):
        self.config.write_text(json.dumps(self.project if project is None else project), encoding='utf-8')

    def test_accepts_distinct_businesses_without_a_published_domain(self):
        for identifier, context in [
            ('horta-local', 'Loja de plantas e insumos para hortas.'),
            ('aulas-musica', 'Escola de música para iniciantes.'),
        ]:
            with self.subTest(identifier=identifier):
                project = self.project | {'id': identifier, 'business_context': context}
                self.write_project(project)
                result = self.invoke('validate', '--project', str(self.config))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['project'], project)
                self.assertFalse(self.database.exists())


    def test_rejects_invalid_configuration_with_an_actionable_field_error(self):
        cases = []
        for field in ['id', 'business_context', 'audience', 'language', 'geography', 'content_goal', 'keywords']:
            missing = self.project.copy()
            del missing[field]
            cases.append((field, missing))
            cases.append((field, self.project | {field: '  '}))
        for value in [[], ['  '], [7], 'horta', None]:
            cases.append(('keywords', self.project | {'keywords': value}))
        cases.extend([
            ('id', self.project | {'id': '../outro-projeto'}),
            ('business_context', self.project | {'business_context': ['loja']}),
            ('domains', self.project | {'domains': 'exemplo.org'}),
            ('competitors', self.project | {'competitors': [False]}),
            ('sources', self.project | {'sources': ['']}),
            ('keywrods', self.project | {'keywrods': ['erro de digitação']}),
        ])
        for field, project in cases:
            with self.subTest(field=field, value=project.get(field)):
                self.write_project(project)
                result = self.invoke('validate', '--project', str(self.config))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(field, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')

    def test_prepared_runs_persist_snapshots_and_keep_projects_separate(self):
        records = []
        projects = [
            self.project | {
                'domains': ['horta.example'],
                'competitors': ['https://concorrente.example/guias'],
                'sources': ['https://fonte.example/plantas'],
            },
            self.project | {'id': 'aulas-musica', 'business_context': 'Escola de música.'},
            self.project | {'keywords': ['horta em pequenos espaços']},
        ]
        for project in projects:
            self.write_project(project)
            result = self.invoke('prepare', '--project', str(self.config), '--store', str(self.database))
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record['project_id'], project['id'])
            self.assertEqual(record['project'], project)
            self.assertEqual(record['status'], 'prepared')
            self.assertIsNone(record['result'])
            self.assertTrue(record['created_at'])
            records.append(record)
        self.assertEqual(len({record['run_id'] for record in records}), 3)
        for identifier, expected in [('horta-local', [records[0], records[2]]), ('aulas-musica', [records[1]])]:
            history = self.invoke('history', '--project-id', identifier, '--store', str(self.database))
            self.assertEqual(history.returncode, 0, history.stderr)
            self.assertEqual(json.loads(history.stdout), {'project_id': identifier, 'runs': expected})

    def test_history_rejects_invalid_project_identifiers(self):
        for identifier in ['', '../outro-projeto', "' OR 1=1 --"]:
            with self.subTest(identifier=identifier):
                result = self.invoke('history', '--project-id', identifier, '--store', str(self.database))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('id', result.stderr)
                self.assertFalse(self.database.exists())

    def test_input_errors_do_not_create_history(self):
        invalid = self.project.copy()
        del invalid['keywords']
        for content in [None, b'{', b'[]', b'null', b'\xff', json.dumps(invalid).encode()]:
            with self.subTest(content=content):
                if content is None:
                    self.config.unlink(missing_ok=True)
                else:
                    self.config.write_bytes(content)
                result = self.invoke('prepare', '--project', str(self.config), '--store', str(self.database))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertTrue(result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertFalse(self.database.exists())

    def test_rejected_preparation_preserves_existing_history(self):
        self.write_project()
        prepared = self.invoke('prepare', '--project', str(self.config), '--store', str(self.database))
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.write_project({})
        rejected = self.invoke('prepare', '--project', str(self.config), '--store', str(self.database))
        self.assertEqual(rejected.returncode, 2, rejected.stderr)
        result = self.invoke('history', '--project-id', 'horta-local', '--store', str(self.database))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['runs'], [json.loads(prepared.stdout)])

    def test_history_of_unknown_project_does_not_create_store(self):
        store = self.directory / 'not-created' / 'history.sqlite3'
        result = self.invoke('history', '--project-id', 'unknown', '--store', str(store))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'project_id': 'unknown', 'runs': []})
        self.assertFalse(store.parent.exists())

    def test_web_commands_reject_invalid_input_without_network_or_traceback(self):
        for args, message in [
            (['search', '--query', ' '], 'consulta'),
            (['search', '--query', 'OpenCode', '--limit', '0'], 'limite'),
            (['inspect', '--url', 'file:///etc/passwd'], 'http'),
            (['crawl', '--query', ' '], 'consulta'),
            (['crawl', '--query', 'horta', '--limit', '99'], '20'),
            (['crawl', '--query', 'horta', '--max-pages', '0'], '20'),
        ]:
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(result.stdout, '')

if __name__ == '__main__':
    unittest.main()
