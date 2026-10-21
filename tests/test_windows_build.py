from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import build_windows


class WindowsBuildWorkflowTests(unittest.TestCase):
    def test_prepare_uses_only_the_generated_environment_for_dependencies_and_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            with patch.object(build_windows, 'PROJECT', project), \
                    patch.object(build_windows.venv, 'EnvBuilder') as environment, \
                    patch.object(build_windows.subprocess, 'run') as run:
                build_windows.prepare()
            environment.return_value.create.assert_called_once_with(project / '.venv-windows-build')
            python = str(project / '.venv-windows-build/Scripts/python.exe')
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args_list[0].args[0][:5], [python, '-m', 'pip', 'install', '--upgrade'])
            self.assertEqual(run.call_args_list[1].args[0], [python, str(project / 'build_windows.py'), '--run-build'])

    def test_dependency_failure_does_not_start_packaging(self):
        with patch.object(build_windows.venv, 'EnvBuilder'), \
                patch.object(build_windows.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['pip'])) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                build_windows.prepare()
        self.assertEqual(run.call_count, 1)

    def test_check_mode_does_not_install_or_build(self):
        with patch.object(build_windows, 'check_python'), patch.object(build_windows, 'prepare') as prepare, \
                patch.object(build_windows, 'build') as build, redirect_stdout(io.StringIO()):
            self.assertEqual(build_windows.main(['--check']), 0)
        prepare.assert_not_called()
        build.assert_not_called()

    def test_failed_preparation_returns_failure_and_never_claims_build_complete(self):
        output = io.StringIO()
        with patch.object(build_windows, 'check_python'), \
                patch.object(build_windows, 'prepare', side_effect=RuntimeError('fixture dependency failure')), \
                redirect_stderr(output), redirect_stdout(output):
            self.assertEqual(build_windows.main([]), 1)
        self.assertIn('build stopped', output.getvalue())
        self.assertNotIn('Build complete', output.getvalue())


@unittest.skipUnless(sys.platform == 'win32', 'Windows batch and shortcut APIs required')
class WindowsBuildEntryTests(unittest.TestCase):
    def run_batch(self, script, *args):
        with tempfile.TemporaryDirectory(prefix='YTDL build ไทย ') as temporary:
            folder = Path(temporary)
            shutil.copyfile(Path(__file__).resolve().parents[1] / 'build_windows.bat', folder / 'build_windows.bat')
            (folder / 'build_windows.py').write_text(script, encoding='utf-8')
            return subprocess.run(['cmd.exe', '/d', '/c', 'build_windows.bat', *args], cwd=folder,
                                  input='\n', text=True, encoding='utf-8', errors='replace',
                                  capture_output=True, timeout=15)

    def test_check_is_forwarded_without_a_pause(self):
        result = self.run_batch("import sys\nassert sys.argv[1:] == ['--check']\nprint('CHECK_OK')\n", '--check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CHECK_OK', result.stdout)
        self.assertNotIn('Press any key', result.stdout)

    def test_build_failure_returns_failure_instead_of_success(self):
        result = self.run_batch("print('SIMULATED_BUILD_FAILURE')\nraise SystemExit(1)\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Build failed', result.stdout)

    def test_packaged_shortcut_can_be_prepared_before_the_application_is_installed(self):
        from create_windows_launcher import create_launcher
        with tempfile.TemporaryDirectory(prefix="YTDL shortcut ไทย & '") as temporary:
            project = Path(temporary)
            planned = project / 'app-windows/YTDL Studio.exe'
            shortcut = create_launcher(project, target=planned)
            self.assertFalse(planned.exists())
            self.assertTrue(shortcut.is_file())
            self.assertGreater(shortcut.stat().st_size, 100)


if __name__ == '__main__':
    unittest.main()
