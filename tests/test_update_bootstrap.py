# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""The stable launcher must fetch before invoking the current build updater."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from update_bootstrap import UpdateError, main


class BootstrapWorkflowTests(unittest.TestCase):
    def run_bootstrap(self, args=(), update_error=None, returncode=0):
        output = io.StringIO()
        with patch('update_bootstrap.update_source', side_effect=update_error) as update, \
             patch('update_bootstrap.subprocess.run', return_value=subprocess.CompletedProcess([], returncode)) as run, \
             redirect_stdout(output), redirect_stderr(output):
            result = main(list(args))
        return result, update, run, output.getvalue()

    def test_fetch_completes_before_a_fresh_process_runs_the_updater(self):
        events = []
        with patch('update_bootstrap.update_source', side_effect=lambda _: events.append('fetch')), \
             patch('update_bootstrap.subprocess.run',
                   side_effect=lambda *a, **k: events.append('build') or subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(main([]), 0)
        self.assertEqual(events, ['fetch', 'build'])
        self.assertEqual(Path(run.call_args.args[0][-2]).name, 'update_project.py')
        self.assertEqual(run.call_args.args[0][-1], '--build-current')

    def test_failed_fetch_never_launches_the_build(self):
        result, _, run, output = self.run_bootstrap(update_error=UpdateError('offline'))
        self.assertEqual(result, 1)
        run.assert_not_called()
        self.assertIn('offline', output)

    def test_check_mode_never_fetches(self):
        result, update, run, _ = self.run_bootstrap(['--check'])
        self.assertEqual(result, 0)
        update.assert_not_called()
        self.assertEqual(run.call_args.args[0][-1], '--check')

    def test_build_failure_is_reported_without_retrying_or_resetting(self):
        result, update, run, _ = self.run_bootstrap(returncode=7)
        self.assertEqual(result, 7)
        update.assert_called_once()
        run.assert_called_once()

    def test_legacy_build_flag_uses_the_same_update_flow(self):
        result, update, run, _ = self.run_bootstrap(['--build'])
        self.assertEqual(result, 0)
        update.assert_called_once()
        self.assertEqual(run.call_args.args[0][-1], '--build-current')


if __name__ == '__main__':
    unittest.main()
