# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import build_windows
from app_version import DISPLAY_NAME


class WindowsBuildWorkflowTests(unittest.TestCase):
    def test_packaged_branding_flows_through_the_real_publication_code(self):
        """Mock native tools, then exercise actual file copying, shortcuts and ZIP layout."""
        import windows_distribution
        source = Path(build_windows.__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='NÜVEL ไทย build ') as temporary:
            project = Path(temporary).resolve()
            (project / 'assets/branding').mkdir(parents=True)
            shutil.copy2(source / 'assets/branding/app-icon.ico', project / 'assets/branding/app-icon.ico')
            (project / 'ui').mkdir()
            for name in ('index.html', 'studio.css', 'i18n.js', 'studio.js', 'theme.js',
                         'appearance.js', 'fonts.js', 'fonts.css', 'font-catalog.js'):
                (project / 'ui' / name).write_text('UI fixture')
            for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
                (project / name).write_text('notice fixture')
            ffmpeg = project / 'ffmpeg-engine.exe'
            ffmpeg.write_bytes(b'FFmpeg fixture')
            gallery = project / 'gallery-engine.exe'
            gallery.write_bytes(b'gallery fixture')
            gallery_source = project / 'gallery-source'
            gallery_source.mkdir()
            old_shortcut = project / windows_distribution.SHORTCUT
            old_shortcut.write_bytes(b'old shortcut')
            recorded = {}
            def package(args):
                recorded['args'] = args
                output = Path(args[args.index('--distpath') + 1])
                name = args[args.index('--name') + 1]
                folder = output / name
                folder.mkdir()
                (folder / (name + '.exe')).write_bytes(b'native GUI fixture')
                recorded['version'] = Path(args[args.index('--version-file') + 1]).read_text(encoding='utf-8')
            def shortcut(project, target, shortcut):
                self.assertEqual(target.name, DISPLAY_NAME + '.exe')
                shortcut.write_text(str(target), encoding='utf-8')
            core = SimpleNamespace(CoreWebView2Environment=SimpleNamespace(GetAvailableBrowserVersionString=lambda: 'fixture'))
            pyinstaller = ModuleType('PyInstaller')
            pyinstaller.__path__ = []
            pyinstaller.__main__ = ModuleType('PyInstaller.__main__')
            pyinstaller.__main__.run = Mock(side_effect=package)
            with patch.object(build_windows, 'PROJECT', project), \
                    patch.dict(sys.modules, {'webview.platforms.edgechromium': Mock(), 'Microsoft.Web.WebView2.Core': core,
                                            'PyInstaller': pyinstaller, 'PyInstaller.__main__': pyinstaller.__main__}), \
                    patch('ffmpeg_distribution.selected_bundle', return_value=(ffmpeg, gallery_source, {})), \
                    patch('ffmpeg_distribution.verify_media') as media_check, \
                    patch('build_gallery_tool.build_tool', return_value=(gallery, gallery_source)), \
                    patch.object(build_windows.subprocess, 'CREATE_NO_WINDOW', 0, create=True), \
                    patch.object(build_windows.subprocess, 'run'), \
                    patch.object(windows_distribution, 'verify_app') as verify, \
                    patch.object(windows_distribution, 'create_launcher', side_effect=shortcut), \
                    patch.dict(build_windows.os.environ, {'CI': ''}), redirect_stdout(io.StringIO()):
                build_windows.build()
            args = recorded['args']
            media_check.assert_called_once_with(ffmpeg, 'windows-x64')
            self.assertEqual(args[args.index('--name') + 1], DISPLAY_NAME)
            self.assertIn('--windowed', args)
            self.assertIn(str(gallery_source) + ';third-party/ffmpeg/source', args)
            self.assertEqual(Path(args[args.index('--icon') + 1]).suffix, '.ico')
            self.assertIn("StringStruct('ProductName', 'NÜVEL Studio')", recorded['version'])
            self.assertIn("StringStruct('FileDescription', 'NÜVEL Studio')", recorded['version'])
            import ast
            ast.parse(recorded['version'], mode='eval')
            self.assertEqual(verify.call_count, 1)
            installed = project / 'nuvel-windows'
            self.assertEqual((installed / 'NÜVEL Studio.exe').read_bytes(), b'native GUI fixture')
            self.assertTrue((project / 'NÜVEL Studio.lnk').is_file())
            self.assertEqual(old_shortcut.read_text(encoding='utf-8'), str(installed / 'NÜVEL Studio.exe'))
            import zipfile
            archive, = project.glob('dist/*/NUVEL-Studio-Windows-x64.zip')
            with zipfile.ZipFile(archive) as package:
                self.assertEqual([name for name in package.namelist() if name.endswith('.exe')],
                                 ['NÜVEL Studio/NÜVEL Studio.exe'])
                self.assertIn('NÜVEL Studio/NÜVEL Studio.exe', package.namelist())

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
        with tempfile.TemporaryDirectory(prefix='NÜVEL build ไทย ') as temporary:
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

    def test_redirected_build_output_preserves_the_umlaut(self):
        script = "import os\nassert os.environ['PYTHONIOENCODING'] == 'utf-8'\nprint('NÜVEL Studio')\n"
        result = self.run_batch(script, '--check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('NÜVEL Studio', result.stdout)

    def test_build_failure_returns_failure_instead_of_success(self):
        result = self.run_batch("print('SIMULATED_BUILD_FAILURE')\nraise SystemExit(1)\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Build failed', result.stdout)

    def test_packaged_shortcut_can_be_prepared_before_the_application_is_installed(self):
        from create_windows_launcher import create_launcher
        with tempfile.TemporaryDirectory(prefix="NUVEL shortcut ไทย & '") as temporary:
            project = Path(temporary)
            planned = project / 'nuvel-windows/NÜVEL Studio.exe'
            shortcut = create_launcher(project, target=planned)
            self.assertFalse(planned.exists())
            self.assertTrue(shortcut.is_file())
            self.assertGreater(shortcut.stat().st_size, 100)


if __name__ == '__main__':
    unittest.main()
