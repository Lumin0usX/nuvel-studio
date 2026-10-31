import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from repository_audit import audit, scan


class RepositoryAuditTests(unittest.TestCase):
    def test_values_are_never_in_report(self):
        token = 'ghp_' + 'A' * 36
        report = scan(('credential=' + token).encode(), 'fixture.txt')
        self.assertEqual(report[0]['kind'], 'github_token')
        self.assertNotIn(token, json.dumps(report))

    def test_json_and_unquoted_environment_values_are_redacted(self):
        value = ''.join(chr(code) for code in range(65, 91))
        for text in [json.dumps(dict(api_key=value)), 'API_KEY=' + value]:
            report = scan(text.encode(), '.env')
            self.assertTrue(any(item['kind'] == 'possible_secret_assignment' for item in report))
            self.assertNotIn(value, json.dumps(report))

    def test_deleted_and_unreachable_credentials_are_scanned_without_changing_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*args, input=None):
                return subprocess.run(['git', '-C', str(root), '-c', 'user.name=Audit fixture',
                                       '-c', 'user.email=audit@example.invalid', *args], input=input,
                                      check=True, capture_output=True).stdout
            git('init')
            token = 'ghp_' + 'B' * 36
            (root / 'deleted.txt').write_text(token)
            git('add', 'deleted.txt'); git('commit', '-m', 'Fixture')
            git('rm', 'deleted.txt'); git('commit', '-m', 'Delete fixture')
            git('hash-object', '-w', '--stdin', input=('-----BEGIN ' + 'PRIVATE KEY-----').encode())
            before = git('rev-parse', 'HEAD')
            result = audit(root)
            self.assertEqual(git('rev-parse', 'HEAD'), before)
            self.assertFalse(result['shallow'])
            self.assertTrue(any(item['kind'] == 'github_token' and item['object'] for item in result['findings']))
            self.assertTrue(any(item['kind'] == 'private_key' for item in result['findings']))
            self.assertNotIn(token, json.dumps(result))
