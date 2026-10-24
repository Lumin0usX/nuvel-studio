"""Offline removal of a verified app bundle, never the source checkout or media."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time

from app_version import DISPLAY_NAME, version_tuple
from platform_runtime import resource_path
from update_installer import check_bundle, executable_in, installed_bundle, marker_path, platform_key


PREFIX = 'nuvel-uninstall-'
MEDIA_EXTENSIONS = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.mp3', '.m4a', '.aac', '.opus',
                    '.ogg', '.flac', '.wav', '.aiff', '.alac', '.m4b', '.m4v', '.mpg', '.mpeg',
                    '.ts', '.m2ts', '.flv', '.3gp', '.wmv', '.weba', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif',
                    '.heic', '.heif', '.bmp', '.tif', '.tiff', '.jxl'}


def inventory_path(target, key):
    return target / ('.studio-files.json' if key == 'windows-x64' else 'Contents/Resources/studio-files.json')


def _files(target):
    import unicodedata
    return {unicodedata.normalize('NFC', item.relative_to(target).as_posix())
            for item in target.rglob('*') if item.is_file() or item.is_symlink()}


def write_inventory(target, key):
    target = Path(target)
    path = inventory_path(target, key)
    own_name = path.relative_to(target).as_posix()
    data = dict(schema=1, product=DISPLAY_NAME, platform=key, files=sorted(_files(target) - {own_name}))
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def _protect_extra_files(target, key):
    inventory = inventory_path(target, key)
    if inventory.exists():
        if _linked(inventory) or inventory.stat().st_size > 8 * 1024**2:
            raise ValueError('Invalid installed-file inventory.')
        data = json.loads(inventory.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema') != 1 or data.get('product') != DISPLAY_NAME or data.get('platform') != key or \
                not isinstance(data.get('files'), list) or any(not isinstance(name, str) for name in data['files']):
            raise ValueError('Invalid installed-file inventory.')
        if _files(target) - set(data['files']) - {inventory.relative_to(target).as_posix()}:
            raise ValueError('The app contains extra files. Move them outside the app before uninstalling.')
    else:
        # Older builds have no inventory. Be conservative about media outside
        # the bundled UI/artwork; never blindly recycle a user's media folder.
        assets = ('_internal/assets/', '_internal/ui/', 'Contents/Resources/assets/',
                  'Contents/Resources/ui/', 'Contents/Frameworks/assets/', 'Contents/Frameworks/ui/')
        for item in target.rglob('*'):
            if item.is_file() and item.suffix.lower() in MEDIA_EXTENSIONS and \
                    not item.relative_to(target).as_posix().startswith(assets):
                raise ValueError('Media files were found inside the app. Move them outside before uninstalling.')


def _linked(path):
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.lstat(), 'st_file_attributes', 0) &
                    getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
    except FileNotFoundError:
        return False


def find_target(project=None):
    bundle = installed_bundle()
    if bundle is not None:
        return bundle
    project = Path(project or Path(__file__).resolve().parent)
    return project / ('nuvel-windows' if sys.platform == 'win32' else DISPLAY_NAME + '.app')


def validate_target(target, key, download_folders=()):
    target = Path(target).absolute()
    expected_names = {'windows-x64': ('nuvel-windows', DISPLAY_NAME),
                      'macos-arm64': (DISPLAY_NAME + '.app',)}
    import unicodedata
    if key not in expected_names or unicodedata.normalize('NFC', target.name) not in expected_names[key] or \
            _linked(target) or not target.is_dir() or (target / '.git').exists():
        raise ValueError('Choose a verified NÜVEL Studio application, not a source or linked folder.')
    if _linked(marker_path(target, key)) or _linked(target / ('_internal' if key == 'windows-x64' else 'Contents')):
        raise ValueError('Linked application resources cannot be uninstalled automatically.')
    try:
        check_bundle(target, key)
    except RuntimeError:
        # Read-only recognition of the already-branded 1.x installation.
        marker = json.loads(marker_path(target, key).read_text(encoding='utf-8'))
        if not isinstance(marker, dict) or marker.get('product') != 'YTDL Studio' or marker.get('platform') != key or \
                not ((1, 1, 2) <= version_tuple(marker.get('version', '')) < (2, 0, 0)) or \
                not executable_in(target, key).is_file():
            raise ValueError('This folder is not a recognized NÜVEL Studio installation.') from None
        if key == 'macos-arm64':
            import plistlib
            from macos_distribution import _is_previous_identity
            info = plistlib.loads((target / 'Contents/Info.plist').read_bytes())
            if not isinstance(info, dict) or not _is_previous_identity(target, info):
                raise ValueError('This app does not have the expected application identity.')
    allowed = ({DISPLAY_NAME + '.exe', '_internal', '.studio-build.json', '.studio-files.json', 'LICENSE',
                'THIRD_PARTY_NOTICES.md'} if key == 'windows-x64' else {'Contents', '.DS_Store'})
    if any(item.name not in allowed for item in target.iterdir()):
        raise ValueError('The app folder contains extra files. Move them outside the app before uninstalling.')
    from ui_preferences import preferences_path
    folders = list(download_folders)
    try:
        saved = json.loads(preferences_path().read_text(encoding='utf-8'))
        if isinstance(saved, dict) and isinstance(saved.get('folder'), str):
            folders.append(saved['folder'])
    except (OSError, ValueError):
        pass
    resolved = target.resolve()
    for folder in folders:
        if folder and Path(folder).expanduser().resolve().is_relative_to(resolved):
            raise ValueError('The download folder is inside the app. Move your media and choose another folder first.')
    _protect_extra_files(target, key)
    return target.resolve()


def stage_uninstall(target, key, remove_settings=False, download_folders=()):
    if type(remove_settings) is not bool:
        raise ValueError('Invalid settings-removal option.')
    target = validate_target(target, key, download_folders)
    stage = Path(tempfile.mkdtemp(prefix=PREFIX)).resolve()
    try:
        helper = stage / target.name
        # The helper has its own Python/runtime: packaged uninstall works offline
        # without a system Python, and Windows can release the original EXE.
        shutil.copytree(target, helper, symlinks=True)
        plan = dict(schema=1, target=str(target), platform=key, remove_settings=remove_settings,
                    marker_sha256=hashlib.sha256(marker_path(target, key).read_bytes()).hexdigest(),
                    download_folders=[str(folder) for folder in download_folders])
        plan_path = stage / 'plan.json'
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        if sys.platform != 'win32':
            plan_path.chmod(0o600)
        return plan_path
    except BaseException:
        shutil.rmtree(stage)
        raise


def read_plan(plan_path):
    path = Path(plan_path).absolute()
    stage = path.parent
    if path.name != 'plan.json' or _linked(path) or _linked(stage) or \
            stage.resolve().parent != Path(tempfile.gettempdir()).resolve() or not stage.name.startswith(PREFIX) or \
            path.stat().st_size > 65536:
        raise ValueError('Invalid uninstall plan location.')
    plan = json.loads(path.read_text(encoding='utf-8'))
    if plan.get('schema') != 1 or type(plan.get('remove_settings')) is not bool or \
            not isinstance(plan.get('download_folders'), list) or \
            any(not isinstance(folder, str) for folder in plan['download_folders']):
        raise ValueError('Invalid uninstall plan.')
    target = Path(plan['target'])
    if not target.is_absolute() or target.resolve().is_relative_to(stage.resolve()):
        raise ValueError('Invalid uninstall target.')
    validate_target(target, plan['platform'], plan['download_folders'])
    if hashlib.sha256(marker_path(target, plan['platform']).read_bytes()).hexdigest() != plan['marker_sha256']:
        raise ValueError('The installed app changed after uninstall was requested. Try again.')
    return plan


def launch_helper(plan_path):
    plan = read_plan(plan_path)
    stage = Path(plan_path).resolve().parent
    helper = stage / Path(plan['target']).name
    check = executable_in(helper, plan['platform'])
    if getattr(sys, 'frozen', False):
        command = [str(check), '--finish-uninstall', str(plan_path), str(os.getpid())]
    else:
        command = [sys.executable, str(resource_path('app_uninstall.py')), '--finish-uninstall',
                   str(plan_path), str(os.getpid())]
    subprocess.Popen(command, cwd=stage, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                     start_new_session=sys.platform != 'win32')


def _trash(path):
    path = Path(path)
    if _linked(path):
        raise ValueError('Linked items are not removed by the uninstaller.')
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Operation(ctypes.Structure):
            _fields_ = [('hwnd', wintypes.HWND), ('operation', wintypes.UINT),
                        ('source', wintypes.LPCWSTR), ('destination', wintypes.LPCWSTR),
                        ('flags', ctypes.c_ushort), ('aborted', wintypes.BOOL),
                        ('mappings', ctypes.c_void_p), ('title', wintypes.LPCWSTR)]
        operation = Operation(operation=3, source=str(path.resolve()) + '\0\0', flags=0x40 | 0x10 | 0x4000)
        function = ctypes.windll.shell32.SHFileOperationW
        function.argtypes = [ctypes.POINTER(Operation)]
        function.restype = ctypes.c_int
        result = function(ctypes.byref(operation))
        if result or operation.aborted:
            raise OSError('The app could not be moved to the Recycle Bin. Close other copies and try again.')
    elif sys.platform == 'darwin':
        script = '''use framework "Foundation"
on run argv
set manager to current application's NSFileManager's defaultManager()
set targetURL to current application's NSURL's fileURLWithPath:(item 1 of argv)
set {ok, resultingURL, errorInfo} to manager's trashItemAtURL:targetURL resultingItemURL:(reference) |error|:(reference)
if not (ok as boolean) then error (errorInfo's localizedDescription() as text)
end run'''
        subprocess.run(['/usr/bin/osascript', '-e', script, str(path)], check=True, capture_output=True)
    else:
        raise OSError('Uninstall is supported on Windows and macOS.')


def _shortcut_target(shortcut):
    if sys.platform != 'win32' or _linked(shortcut) or not shortcut.is_file():
        return None
    # Read only; never Save a shortcut or execute its arguments.
    literal = str(shortcut).replace("'", "''")
    script = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; $s=(New-Object -ComObject WScript.Shell).CreateShortcut('" + literal + "'); $s.TargetPath | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                             base64.b64encode(script.encode('utf-16le')).decode()],
                            check=True, capture_output=True, text=True, encoding='utf-8',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return Path(json.loads(result.stdout)).resolve()


def _remove_preferences():
    from ui_preferences import preferences_path
    from desktop_launcher import logs_directory
    from update_credentials import credential
    warnings = []
    files = [preferences_path(), *logs_directory().glob('studio-*.log')]
    for path in files:
        try:
            if path.is_file() and not _linked(path) and not _linked(path.parent):
                _trash(path)
        except Exception:
            warnings.append('Some preferences or logs could not be removed.')
    try:
        credential(delete=True)
    except Exception:
        warnings.append('Saved GitHub access could not be removed from the system credential store.')
    return warnings


def _running_app(executable):
    if sys.platform == 'win32':
        literal = str(executable).replace("'", "''")
        script = "@(Get-Process | Where-Object { $_.Path -eq '" + literal + "' }).Count"
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
                                 base64.b64encode(script.encode('utf-16le')).decode()],
                                check=True, capture_output=True, text=True, timeout=20,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return int(result.stdout.strip()) > 0
    result = subprocess.run(['/bin/ps', '-axo', 'comm='], check=True, capture_output=True, text=True, timeout=10)
    for command in result.stdout.splitlines():
        try:
            if Path(command.strip()).samefile(executable):
                return True
        except (OSError, ValueError):
            pass
    return False


def uninstall(plan_path):
    plan = read_plan(plan_path)
    target, key = Path(plan['target']), plan['platform']
    executable = executable_in(target, key).resolve()
    if _running_app(executable):
        raise RuntimeError('Another copy of NÜVEL Studio is still running. Close it before uninstalling.')
    shortcut = target.parent / (DISPLAY_NAME + '.lnk')
    matching_shortcut = False
    warnings = []
    if key == 'windows-x64':
        try:
            matching_shortcut = _shortcut_target(shortcut) == executable
        except Exception:
            warnings.append('The shortcut could not be checked and was kept.')
    _trash(target)
    if matching_shortcut:
        try:
            _trash(shortcut)
        except Exception:
            warnings.append('The app shortcut could not be removed.')
    if plan['remove_settings']:
        warnings.extend(_remove_preferences())
    return warnings


def cleanup_helper(stage):
    stage = Path(stage).absolute()
    if _linked(stage) or stage.resolve().parent != Path(tempfile.gettempdir()).resolve() or \
            not stage.name.startswith(PREFIX):
        raise ValueError('Invalid temporary uninstall folder.')
    if sys.platform == 'win32':
        # A frozen helper cannot unlink its own runtime on Windows. A native
        # process waits for it to exit, then checks the exact temporary path.
        literal = str(stage).replace("'", "''")
        script = ("$ErrorActionPreference='Stop'; Wait-Process -Id " + str(os.getpid()) +
                  " -Timeout 60 -ErrorAction SilentlyContinue; if (Get-Process -Id " + str(os.getpid()) +
                  " -ErrorAction SilentlyContinue) {exit}; $p='" + literal +
                  "'; $t=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\\'); "
                  "if ((Test-Path -LiteralPath $p) -and ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($p)) -eq $t) "
                  "-and ([IO.Path]::GetFileName($p) -like 'nuvel-uninstall-*') "
                  "-and -not ((Get-Item -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint)) "
                  "{ Remove-Item -LiteralPath $p -Recurse -Force }")
        subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden',
                          '-EncodedCommand', base64.b64encode(script.encode('utf-16le')).decode()],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    else:
        shutil.rmtree(stage)


def finish_uninstall(plan_path, parent_pid):
    from desktop_launcher import notify_error
    try:
        read_plan(plan_path)
        from update_installer import wait_for_parent
        wait_for_parent(int(parent_pid))
        # Allow native loaders a moment to release the original runtime.
        time.sleep(.3)
        warnings = uninstall(plan_path)
        message = 'NÜVEL Studio was moved to the Trash / Recycle Bin. Your downloaded media and source files were kept.'
        if warnings:
            message += '\n\n' + '\n'.join(dict.fromkeys(warnings))
        _message(message)
        return 0
    except Exception as exc:
        notify_error('Uninstall could not finish. Close other copies of the app and retry.\n\n' + str(exc))
        return 1
    finally:
        try:
            cleanup_helper(Path(plan_path).parent)
        except Exception:
            pass


def _message(message):
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, DISPLAY_NAME, 0x40)
    else:
        subprocess.run(['/usr/bin/osascript', '-e',
                        'on run argv\ndisplay alert "NÜVEL Studio" message (item 1 of argv)\nend run', message],
                       check=True, capture_output=True)


def _confirm(message):
    if sys.platform == 'win32':
        import ctypes
        return ctypes.windll.user32.MessageBoxW(None, message, DISPLAY_NAME, 0x24 | 0x100) == 6
    script = 'on run argv\ndisplay alert "NÜVEL Studio" message (item 1 of argv) buttons {"Cancel", "Continue"} default button "Cancel" cancel button "Cancel"\nend run'
    return subprocess.run(['/usr/bin/osascript', '-e', script, message], capture_output=True).returncode == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Uninstall the verified NÜVEL Studio app; keep media and source.')
    parser.add_argument('--check', action='store_true', help='Validate the app without changing files.')
    parser.add_argument('--check-result', metavar='FILE', help=argparse.SUPPRESS)
    parser.add_argument('--finish-uninstall', nargs=2, metavar=('PLAN', 'PARENT_PID'), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check_result and not args.check:
        parser.error('--check-result requires --check.')
    if args.finish_uninstall:
        return finish_uninstall(*args.finish_uninstall)
    try:
        key = platform_key()
        target = validate_target(find_target(), key)
        if args.check:
            if args.check_result:
                Path(args.check_result).write_text(json.dumps(dict(ok=True, target=str(target))), encoding='utf-8')
            if sys.stdout is not None:
                print('Verified uninstall target:', target)
            return 0
        if not _confirm('Close all copies of NÜVEL Studio and finish active downloads first.\n\n'
                        'Move this app to the Trash / Recycle Bin?\n' + str(target) +
                        '\n\nDownloaded media, source code and build backups will be kept.'):
            return 0
        remove_settings = _confirm('Also remove preferences, startup logs and saved GitHub release access?\n\n'
                                   'Choose Cancel to keep these settings.')
        plan = stage_uninstall(target, key, remove_settings)
        launch_helper(plan)
        return 0
    except Exception as exc:
        if args.check:
            if sys.stderr is not None:
                print('Uninstall check failed: ' + str(exc), file=sys.stderr)
            return 1
        from desktop_launcher import notify_error
        notify_error(str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
