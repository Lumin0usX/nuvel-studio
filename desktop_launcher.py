"""Windowless source launcher. Own the GUI's process tree, not its download engine."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import os
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import traceback


PROJECT = Path(__file__).resolve().parent


def logs_directory():
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'YTDLStudio/logs'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Logs/YTDLStudio'
    return Path.home() / '.local/state/YTDLStudio/logs'


def notify_error(message):
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'NÜVEL Studio', 0x10)
    elif sys.platform == 'darwin':
        # Pass text as an argument, never interpolate it into AppleScript code.
        subprocess.run(['/usr/bin/osascript', '-e',
                        'on run argv\ndisplay alert "NÜVEL Studio" message (item 1 of argv) as critical\nend run',
                        message], check=False, capture_output=True)


class WindowsJob:
    """A non-inherited, kill-on-close Job Object containing only this launch's GUI."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('min_working_set', ctypes.c_size_t),
                        ('max_working_set', ctypes.c_size_t), ('active_processes', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                        ('scheduling', wintypes.DWORD)]

        class IOCounts(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ('reads', 'writes', 'other', 'read_bytes', 'write_bytes', 'other_bytes')]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [('basic', BasicLimits), ('io', IOCounts),
                        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                        ('peak_process_memory', ctypes.c_size_t), ('peak_job_memory', ctypes.c_size_t)]

        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                    ctypes.c_void_p, wintypes.DWORD]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.api.OpenProcess.restype = wintypes.HANDLE
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, pid):
        import ctypes
        process = self.api.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.api.AssignProcessToJobObject(self.handle, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.api.CloseHandle(process)

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def stop_process_group(pid):
    """macOS child starts a private session; never signal the launcher's own group."""
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(.05)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def supervise(command, log, gate):
    """The child cannot start the GUI or any workers before ownership is established."""
    job = WindowsJob() if sys.platform == 'win32' else None
    process = None
    try:
        process = subprocess.Popen(command, cwd=PROJECT, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log,
                                   env=dict(os.environ, YTDL_UPDATE_HANDOFF=str(gate.parent / 'update.json')),
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                                   start_new_session=sys.platform != 'win32')
        if job:
            job.assign(process.pid)
        gate.write_text('ready', encoding='ascii')
        return process.wait()
    finally:
        if process:
            if job:
                job.close()  # Includes FFmpeg/gallery processes even after the GUI exits.
                if process.poll() is None:
                    process.kill()
            else:
                stop_process_group(process.pid)
            process.wait(timeout=5)
        elif job:
            job.close()


def native_child(gate, log_path, self_test=False, smoke_result=None):
    deadline = time.monotonic() + 15
    while not gate.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError('The desktop launcher did not finish setting up this session.')
        time.sleep(.05)
    # pythonw has None for sys.stdout/stderr: provide real streams for dependencies.
    with log_path.open('a', encoding='utf-8', buffering=1) as log, \
            redirect_stdout(log), redirect_stderr(log):
        try:
            if sys.platform == 'darwin':
                from check_macos import main as preflight
                preflight()
            from glass_app import main
            if self_test:
                sys.argv.append('--self-test')
                if smoke_result and '--smoke-result' not in sys.argv:
                    sys.argv.extend(['--smoke-result', str(smoke_result)])
            main(native_only=True)
            return 0
        except Exception:
            traceback.print_exc()
            return 1


def launch(self_test=False, applet=False, check=False, smoke_result=None):
    log_path = None
    try:
        directory = logs_directory()
        directory.mkdir(parents=True, exist_ok=True)
        log_path = directory / f'studio-{datetime.now():%Y%m%d-%H%M%S}-{os.getpid()}.log'
        with log_path.open('a', encoding='utf-8', buffering=1) as log, \
                redirect_stdout(log), redirect_stderr(log):
            try:
                print(f'NÜVEL Studio desktop launcher | Python {sys.version.split()[0]}', flush=True)
                if check:
                    import webview  # noqa: F401 - verify the native bridge without opening a window
                    from glass_app import main  # noqa: F401
                    print('Native launcher dependencies: OK', flush=True)
                    return 0
                with tempfile.TemporaryDirectory(prefix='ytdl-session-') as temporary:
                    gate = Path(temporary) / 'ready'
                    # The supervisor uses pythonw. The GUI uses python.exe with
                    # CREATE_NO_WINDOW so gallery-dl inherits usable pipe streams.
                    executable = Path(sys.executable)
                    if sys.platform == 'win32' and executable.name.lower() == 'pythonw.exe':
                        executable = executable.with_name('python.exe')
                    command = [str(executable)]
                    if not getattr(sys, 'frozen', False):
                        command.append(str(PROJECT / 'desktop_launcher.py'))
                    command.extend(['--native-child', str(gate), str(log_path)])
                    if self_test:
                        command.append('--self-test')
                        if smoke_result:
                            command.extend(['--smoke-result', str(smoke_result)])
                    result = supervise(command, log, gate)
                    handoff = gate.parent / 'update.json'
                    if result == 0 and handoff.is_file() and getattr(sys, 'frozen', False) and not self_test:
                        from update_installer import launch_helper
                        launch_helper(Path(json.loads(handoff.read_text(encoding='utf-8'))['plan']))
                if result:
                    raise RuntimeError(f'The native interface exited with code {result}.')
                print('Session closed; owned child processes stopped.', flush=True)
                return 0
            except Exception:
                traceback.print_exc()
                raise
    except Exception:
        if not applet and not check and not self_test:
            message = 'NÜVEL Studio could not start or closed unexpectedly.'
            if getattr(sys, 'frozen', False):
                message += '\nReopen the app. If this continues, reinstall the application.'
            else:
                hint = 'install_macos.command' if sys.platform == 'darwin' else 'install.bat'
                message += f'\nRun {hint} if dependencies are missing.'
            message += f'\n\nLog: {log_path}' if log_path else '\nThe startup log could not be created.'
            notify_error(message)
        return 1


def main():
    if sys.argv[1:2] == ['--apply-update']:
        from update_installer import helper_main
        return helper_main(sys.argv[2], sys.argv[3])
    smoke_result = None
    if '--smoke-result' in sys.argv:
        smoke_result = Path(sys.argv[sys.argv.index('--smoke-result') + 1])
    if sys.argv[1:2] == ['--native-child']:
        return native_child(Path(sys.argv[2]), Path(sys.argv[3]), '--self-test' in sys.argv[4:], smoke_result)
    return launch('--self-test' in sys.argv, '--applet' in sys.argv, '--check' in sys.argv, smoke_result)


if __name__ == '__main__':
    raise SystemExit(main())
