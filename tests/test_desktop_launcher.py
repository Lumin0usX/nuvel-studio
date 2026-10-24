"""Exercise real hidden Windows sessions, process ownership and native-only startup."""
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

    def test_incomplete_packaged_app_never_falls_back_to_a_hidden_server(self):
        with patch.dict(sys.modules, {'webview': None}), patch.object(sys, 'frozen', True, create=True), \
                patch.object(glass_app, '_serve') as serve, patch.object(glass_app, 'StudioAPI') as api:
            with self.assertRaisesRegex(RuntimeError, 'bundle is incomplete'):
                glass_app.main()
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

    def test_packaged_supervisor_restarts_the_executable_and_forwards_startup_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            proof = Path(temporary) / 'result.json'
            with patch.object(launcher, 'logs_directory', return_value=Path(temporary)), \
                    patch.object(sys, 'frozen', True, create=True), \
                    patch.object(launcher, 'supervise', return_value=0) as supervise:
                self.assertEqual(launcher.launch(self_test=True, smoke_result=proof), 0)
            command = supervise.call_args.args[0]
            self.assertEqual(command[0], sys.executable)
            self.assertEqual(command[1], '--native-child')
            self.assertNotIn(str(launcher.PROJECT / 'desktop_launcher.py'), command)
            self.assertEqual(command[-2:], ['--smoke-result', str(proof)])

    def test_update_helper_starts_only_after_the_owned_gui_session_has_ended(self):
        order = []
        def closed_gui(command, log, gate):
            (gate.parent / 'update.json').write_text(json.dumps({'plan': 'prepared-plan.json'}))
            order.append('gui session closed')
            return 0
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(launcher, 'logs_directory', return_value=Path(temporary)), \
                patch.object(sys, 'frozen', True, create=True), \
                patch.object(launcher, 'supervise', side_effect=closed_gui), \
                patch('update_installer.launch_helper', side_effect=lambda path: order.append('helper started')):
            self.assertEqual(launcher.launch(), 0)
        self.assertEqual(order, ['gui session closed', 'helper started'])

    def test_uninstall_helper_runs_after_gui_shutdown_for_source_and_packaged_apps(self):
        for frozen in (False, True):
            with self.subTest(frozen=frozen):
                order = []
                def closed_gui(command, log, gate):
                    (gate.parent / 'update.json').write_text(json.dumps({
                        'action': 'uninstall', 'plan': 'prepared-uninstall.json'}))
                    order.append('gui session closed')
                    return 0
                with tempfile.TemporaryDirectory() as temporary, \
                     patch.object(launcher, 'logs_directory', return_value=Path(temporary)), \
                     patch.object(sys, 'frozen', frozen, create=True), \
                     patch.object(launcher, 'supervise', side_effect=closed_gui), \
                     patch('app_uninstall.launch_helper', side_effect=lambda path: order.append('uninstall helper started')), \
                     patch('update_installer.launch_helper') as update:
                    self.assertEqual(launcher.launch(), 0)
                update.assert_not_called()
                self.assertEqual(order, ['gui session closed', 'uninstall helper started'])

    def test_closing_busy_window_requires_confirmation_then_cancels(self):
        for confirmation in (False, True):
            with self.subTest(confirmation=confirmation):
                api = Mock()
                api._uninstall_plan = None
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

    def test_native_startup_proof_requires_a_bridge_round_trip_and_window_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            proof = Path(temporary) / 'startup.json'
            api, window, bridge = Mock(), Mock(), Mock()
            api.snapshot.return_value = {'phase': 'idle'}
            bridge.create_window.return_value = window
            loaded = []
            window.events.loaded.__iadd__ = lambda _, handler: loaded.append(handler)
            window.events.closing.__iadd__ = lambda _, handler: None
            window.evaluate_js.side_effect = [True, None, True]
            def run_window(**kwargs):
                loaded[0]()
                window.destroy.assert_called_once()
                self.assertFalse(proof.exists(), 'Startup proof was written before the window loop ended')
            bridge.start.side_effect = run_window
            with patch.dict(sys.modules, {'webview': bridge}), \
                    patch.object(glass_app, 'StudioAPI', return_value=api), \
                    patch.object(glass_app.threading, 'Thread'), \
                    patch.object(glass_app.subprocess, 'run'), \
                    patch.object(glass_app, 'ffmpeg_path', return_value='ffmpeg'), \
                    patch.object(sys, 'argv', ['studio', '--self-test', '--smoke-result', str(proof)]):
                glass_app.main(native_only=True)
            self.assertTrue(json.loads(proof.read_text())['ok'])
            self.assertTrue(any('api.snapshot().then' in call.args[0] for call in window.evaluate_js.call_args_list))

    def test_closed_window_without_ready_ui_does_not_produce_success_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            proof = Path(temporary) / 'startup.json'
            window, bridge = Mock(), Mock()
            bridge.create_window.return_value = window
            window.events.loaded.__iadd__ = lambda _, handler: None
            window.events.closing.__iadd__ = lambda _, handler: None
            with patch.dict(sys.modules, {'webview': bridge}), patch.object(glass_app, 'StudioAPI'), \
                    patch.object(glass_app.threading, 'Thread'), patch.object(glass_app.subprocess, 'run'), \
                    patch.object(glass_app, 'ffmpeg_path', return_value='ffmpeg'), \
                    patch.object(sys, 'argv', ['studio', '--self-test', '--smoke-result', str(proof)]):
                with self.assertRaisesRegex(RuntimeError, 'did not become ready'):
                    glass_app.main(native_only=True)
            self.assertFalse(proof.exists())


@unittest.skipUnless(sys.platform == 'win32', 'Windows process and console APIs required')
class HiddenWindowsSessionTests(unittest.TestCase):
    def test_shortcut_arguments_preserve_spaces_unicode_and_quotes(self):
        from create_windows_launcher import create_launcher
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        with tempfile.TemporaryDirectory(prefix='nuvel shortcut args ') as temporary:
            project = Path(temporary)
            result = project / 'receipt with spaces.json'
            script = project / 'write receipt.py'
            script.write_text('import json, sys\nfrom pathlib import Path\n'
                              'Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\n', encoding='utf-8')
            values = ['NÜVEL ไทย', 'a value with spaces', 'a"quoted"value']
            shortcut = create_launcher(project, target=pythonw,
                                       launch_args=[str(script), str(result), *values])
            os.startfile(shortcut)
            deadline = time.monotonic() + 10
            while not result.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(result.is_file())
            self.assertEqual(json.loads(result.read_text()), values)

    def test_generated_shortcut_opens_pythonw_without_a_console(self):
        from create_windows_launcher import create_launcher
        with tempfile.TemporaryDirectory(prefix="NUVEL ไทย & launcher '") as temporary:
            project = Path(temporary).resolve()
            result = project / 'shortcut-result.json'
            (project / 'desktop_launcher.py').write_text('''
import ctypes, json, os
from pathlib import Path
result = Path(__file__).with_name('shortcut-result.json')
temporary = result.with_suffix('.tmp')
temporary.write_text(json.dumps({
    'console': int(ctypes.windll.kernel32.GetConsoleWindow()), 'folder': str(Path.cwd()), 'pid': os.getpid()}))
os.replace(temporary, result)
''', encoding='utf-8')
            shortcut = create_launcher(project)
            self.assertTrue(shortcut.is_file())
            os.startfile(shortcut)
            deadline = time.monotonic() + 10
            while not result.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(result.is_file(), 'The generated shortcut did not run')
            state = json.loads(result.read_text())
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.WaitForSingleObject.restype = wintypes.DWORD
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            process = kernel.OpenProcess(0x00100000, False, state['pid'])
            if process:
                try:
                    self.assertEqual(kernel.WaitForSingleObject(process, 5000), 0,
                                     'The shortcut fixture did not finish before cleanup')
                finally:
                    kernel.CloseHandle(process)
            elif ctypes.get_last_error() != 87:  # ERROR_INVALID_PARAMETER: process already exited.
                raise ctypes.WinError(ctypes.get_last_error())
            self.assertEqual(state['console'], 0)
            # The runner's TEMP may use RUNNER~1 while the launched process sees
            # the long profile name. Both must identify the same actual folder.
            self.assertEqual(Path(state['folder']).resolve(), project)

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
        with tempfile.TemporaryDirectory(prefix='NUVEL ไทย launcher ') as temporary:
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
                logs = list((project / 'local-app-data/NuvelStudio/logs').glob('*.log'))
                self.assertIn('fixture native window closed', logs[0].read_text(encoding='utf-8'))
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait(timeout=5)
                if worker_handle:
                    kernel.CloseHandle(worker_handle)


if __name__ == '__main__':
    unittest.main()
