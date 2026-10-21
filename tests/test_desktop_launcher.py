"""Exercise real hidden Windows sessions, process ownership and native-only startup."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import desktop_launcher as launcher
import glass_app


class DesktopLauncherTests(unittest.TestCase):
    def test_missing_native_bridge_does_not_start_a_hidden_browser_server(self):
        with patch.dict(sys.modules, {'webview': None}), \
                patch.object(glass_app, '_serve') as serve, patch.object(glass_app, 'StudioAPI') as api:
            with self.assertRaisesRegex(RuntimeError, 'requires pywebview'):
                glass_app.main(native_only=True)
        serve.assert_not_called()
        api.assert_not_called()

    def test_startup_failure_is_logged_and_reported_with_log_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(launcher, 'logs_directory', return_value=Path(temporary)), \
                    patch.object(launcher, 'supervise', side_effect=RuntimeError('fixture startup failure')), \
                    patch.object(launcher, 'notify_error') as notify:
                self.assertEqual(launcher.launch(), 1)
            logs = list(Path(temporary).glob('studio-*.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('fixture startup failure', logs[0].read_text(encoding='utf-8'))
            self.assertIn(str(logs[0]), notify.call_args.args[0])

    def test_mac_applet_reports_failure_once_in_its_own_dialog(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(launcher, 'logs_directory', return_value=Path(temporary)), \
                    patch.object(launcher, 'supervise', return_value=1), \
                    patch.object(launcher, 'notify_error') as notify:
                self.assertEqual(launcher.launch(applet=True), 1)
                notify.assert_not_called()

    def test_closing_busy_window_requires_confirmation_then_cancels(self):
        for confirmation in (False, True):
            with self.subTest(confirmation=confirmation):
                api = Mock()
                api.snapshot.return_value = {'phase': 'downloading'}
                api._preferences = {'language': 'en'}
                window = Mock()
                window.create_confirmation_dialog.return_value = confirmation
                bridge = Mock()
                bridge.create_window.return_value = window
                handlers = []
                window.events.closing.__iadd__ = lambda _, handler: handlers.append(handler)
                with patch.dict(sys.modules, {'webview': bridge}), patch.object(glass_app, 'StudioAPI', return_value=api):
                    glass_app.main(native_only=True)
                    self.assertEqual(handlers[0](), confirmation)
                self.assertEqual(api.cancel_download.call_count, int(confirmation))
                api._cancel.set.assert_called_once()

    def test_mac_launcher_uses_local_compiler_and_keeps_paths_as_arguments(self):
        import create_macos_launcher
        with patch.object(create_macos_launcher.sys, 'platform', 'darwin'), \
                patch.object(create_macos_launcher.subprocess, 'run') as run, redirect_stdout(io.StringIO()):
            create_macos_launcher.main()
        args = run.call_args.args[0]
        self.assertEqual(args[0], '/usr/bin/osacompile')
        self.assertEqual(Path(args[2]).name, 'YTDL Studio Launcher.app')
        self.assertEqual(Path(args[3]).name, 'macos_launcher.applescript')


@unittest.skipUnless(sys.platform == 'win32', 'Windows process and console APIs required')
class HiddenWindowsSessionTests(unittest.TestCase):
    def test_generated_shortcut_opens_pythonw_without_a_console(self):
        from create_windows_launcher import create_launcher
        with tempfile.TemporaryDirectory(prefix="YTDL ไทย & launcher '") as temporary:
            project = Path(temporary)
            result = project / 'shortcut-result.json'
            (project / 'desktop_launcher.py').write_text('''
import ctypes, json
from pathlib import Path
Path(__file__).with_name('shortcut-result.json').write_text(json.dumps({
    'console': int(ctypes.windll.kernel32.GetConsoleWindow()), 'folder': str(Path.cwd())}))
''', encoding='utf-8')
            shortcut = create_launcher(project)
            self.assertTrue(shortcut.is_file())
            os.startfile(shortcut)
            deadline = time.monotonic() + 10
            while not result.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(result.is_file(), 'The generated shortcut did not run')
            state = json.loads(result.read_text())
            self.assertEqual(state['console'], 0)
            self.assertEqual(Path(state['folder']), project)

    def test_pythonw_session_has_no_console_and_reaps_a_remaining_worker(self):
        import ctypes
        from ctypes import wintypes
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        if not pythonw.is_file():
            self.skipTest('pythonw.exe is not installed')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        with tempfile.TemporaryDirectory(prefix='YTDL ไทย launcher ') as temporary:
            project = Path(temporary)
            shutil.copyfile(launcher.__file__, project / 'desktop_launcher.py')
            (project / 'glass_app.py').write_text('''
import ctypes, json, subprocess, sys, time
from pathlib import Path
def main(native_only=False):
    assert native_only
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                             creationflags=subprocess.CREATE_NO_WINDOW)
    Path('session.json').write_text(json.dumps({'worker': child.pid,
        'console': int(ctypes.windll.kernel32.GetConsoleWindow()),
        'native_only': native_only, 'usable_stdout': sys.stdout is not None}))
    while not Path('close-window').exists():
        time.sleep(.05)
    print('fixture native window closed')
''', encoding='utf-8')
            env = dict(os.environ, LOCALAPPDATA=str(project / 'local-app-data'))
            parent = subprocess.Popen([str(pythonw), str(project / 'desktop_launcher.py')], env=env,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            worker_handle = None
            try:
                deadline = time.monotonic() + 15
                ready = project / 'session.json'
                while not ready.exists() and parent.poll() is None and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(ready.exists(), 'Windowless session failed; inspect fixture logs')
                state = json.loads(ready.read_text())
                self.assertEqual(state['console'], 0)
                self.assertTrue(state['native_only'])
                self.assertTrue(state['usable_stdout'])
                worker_handle = kernel.OpenProcess(0x00100000, False, state['worker'])
                self.assertTrue(worker_handle)
                (project / 'close-window').touch()
                self.assertEqual(parent.wait(timeout=10), 0)
                self.assertEqual(kernel.WaitForSingleObject(worker_handle, 5000), 0,
                                 'Download subprocess survived closing the GUI')
                logs = list((project / 'local-app-data/YTDLStudio/logs').glob('*.log'))
                self.assertIn('fixture native window closed', logs[0].read_text(encoding='utf-8'))
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait(timeout=5)
                if worker_handle:
                    kernel.CloseHandle(worker_handle)


if __name__ == '__main__':
    unittest.main()
