"""Staged native updates. Never execute a script supplied by a release archive."""
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile

from app_version import VERSION, version_tuple
from release_client import UpdateError

MARKER = '.studio-build.json'
APP_ID = 'local.ytdlstudio.app'


def marker_path(bundle, key):
    return Path(bundle) / (MARKER if key == 'windows-x64' else 'Contents/Resources/studio-build.json')


def platform_key():
    import platform
    if sys.platform == 'win32' and platform.machine().lower() in ('amd64', 'x86_64'):
        return 'windows-x64'
    if sys.platform == 'darwin' and platform.machine().lower() in ('arm64', 'aarch64'):
        return 'macos-arm64'
    return ''


def installed_bundle():
    if not getattr(sys, 'frozen', False):
        return None
    executable = Path(sys.executable).resolve()
    if sys.platform == 'win32':
        return executable.parent
    if sys.platform == 'darwin' and executable.parent.name == 'MacOS':
        return executable.parent.parent.parent
    return None


def executable_in(bundle, key):
    return Path(bundle) / ('YTDL Studio.exe' if key == 'windows-x64' else 'Contents/MacOS/YTDL Studio')


def check_bundle(bundle, key, version=None):
    bundle = Path(bundle)
    if bundle.is_symlink() or not bundle.is_dir():
        raise UpdateError('invalid_package')
    try:
        marker = json.loads(marker_path(bundle, key).read_text(encoding='utf-8'))
        if marker['product'] != 'YTDL Studio' or marker['platform'] != key:
            raise ValueError()
        version_tuple(marker['version'])
        if version is not None and marker['version'] != version:
            raise ValueError()
        if key == 'macos-arm64':
            with (bundle / 'Contents/Info.plist').open('rb') as stream:
                if plistlib.load(stream).get('CFBundleIdentifier') != APP_ID:
                    raise ValueError()
        if not executable_in(bundle, key).is_file():
            raise ValueError()
    except (OSError, ValueError, TypeError, KeyError, plistlib.InvalidFileException):
        raise UpdateError('invalid_package') from None


def unpack(archive, destination, key):
    """Validate every path/link before extraction, including native framework symlinks."""
    root_name = 'YTDL Studio' if key == 'windows-x64' else 'YTDL Studio.app'
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as package:
        items = package.infolist()
        if len(items) > 100000 or sum(item.file_size for item in items) > 4 * 1024**3:
            raise UpdateError('invalid_package')
        links, names = {}, set()
        for item in items:
            name = item.orig_filename
            parts = PurePosixPath(name).parts
            if '\\' in name or ':' in name or name.startswith('/') or not parts or '..' in parts or \
                    any(part.endswith((' ', '.')) or any(ord(c) < 32 for c in part) for part in parts):
                raise UpdateError('invalid_package')
            if parts[0] == '__MACOSX' and key == 'macos-arm64':
                if stat.S_IFMT(item.external_attr >> 16) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise UpdateError('invalid_package')
                continue
            if parts[0] != root_name or item.flag_bits & 1 or name.casefold().rstrip('/') in names:
                raise UpdateError('invalid_package')
            names.add(name.casefold().rstrip('/'))
            if key == 'windows-x64' and any(re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part) or
                                             any(c in '<>"|?*' for c in part) for part in parts):
                raise UpdateError('invalid_package')
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                if key != 'macos-arm64' or item.file_size > 4096:
                    raise UpdateError('invalid_package')
                target = package.read(item).decode('utf-8')
                if not target or target.startswith('/') or '\\' in target:
                    raise UpdateError('invalid_package')
                normalized = PurePosixPath(posixpath.normpath(str(PurePosixPath(name).parent / target)))
                if not normalized.parts or normalized.parts[0] != root_name or '..' in normalized.parts:
                    raise UpdateError('invalid_package')
                links[PurePosixPath(name)] = target
            elif stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise UpdateError('invalid_package')
        folded_links = {str(path).casefold() for path in links}
        for item in items:
            path = PurePosixPath(item.filename)
            if path.parts[0] == '__MACOSX':
                continue
            if any(str(parent).casefold() in folded_links for parent in path.parents):
                raise UpdateError('invalid_package')
        # Resolve symlink chains on the actual staged tree before trusting the bundle.
        if key == 'macos-arm64' and sys.platform == 'darwin':
            subprocess.run(['/usr/bin/ditto', '-x', '-k', str(archive), str(destination)],
                           check=True, capture_output=True, timeout=180)
        else:
            for item in items:
                path = PurePosixPath(item.filename)
                if path.parts[0] == '__MACOSX':
                    continue
                output = destination.joinpath(*path.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                if path in links:
                    output.symlink_to(links[path])
                elif item.is_dir():
                    output.mkdir(exist_ok=True)
                else:
                    with package.open(item) as source, output.open('xb') as target:
                        shutil.copyfileobj(source, target)
                    if sys.platform != 'win32':
                        output.chmod((item.external_attr >> 16 & 0o777) or 0o644)
        bundle = destination / root_name
        for path in bundle.rglob('*'):
            if path.is_symlink():
                try:
                    resolved = path.resolve(strict=True)
                except (OSError, RuntimeError):
                    raise UpdateError('invalid_package') from None
                if not resolved.is_relative_to(bundle):
                    raise UpdateError('invalid_package')
        return bundle


def write_marker(bundle, key):
    marker_path(bundle, key).write_text(json.dumps(dict(product='YTDL Studio', platform=key, version=VERSION)),
                                     encoding='utf-8')


def verify_native(bundle, key):
    if key == 'windows-x64':
        from windows_distribution import verify_app
    else:
        from macos_distribution import verify_app
    verify_app(bundle)


def stage_update(current, archive, stage, key, version):
    check_bundle(current, key)
    candidate = unpack(archive, stage / 'new', key)
    check_bundle(candidate, key, version)
    verify_native(candidate, key)
    helper = stage / 'helper' / current.name
    helper.parent.mkdir()
    if key == 'macos-arm64':
        subprocess.run(['/usr/bin/ditto', str(current), str(helper)], check=True, capture_output=True, timeout=180)
    else:
        shutil.copytree(current, helper)
    plan = dict(schema=1, target=str(current), candidate=str(candidate), platform=key, version=version)
    plan_path = stage / 'plan.json'
    plan_path.write_text(json.dumps(plan), encoding='utf-8')
    if sys.platform != 'win32':
        plan_path.chmod(0o600)
    return plan_path


def read_plan(plan_path):
    plan_path = Path(plan_path).resolve()
    stage = plan_path.parent
    try:
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        target, candidate = Path(plan['target']), Path(plan['candidate'])
        key = plan['platform']
        expected_name = 'YTDL Studio' if key == 'windows-x64' else 'YTDL Studio.app'
        if plan['schema'] != 1 or key not in ('windows-x64', 'macos-arm64') or \
                not stage.name.startswith('.ytdl-update-') or not target.is_absolute() or \
                target.parent.resolve() != stage.parent or target.resolve() == stage or \
                candidate != stage / 'new' / expected_name or target.is_symlink():
            raise ValueError()
        check_bundle(target, key)
        check_bundle(candidate, key, plan['version'])
        current_version = json.loads(marker_path(target, key).read_text(encoding='utf-8'))['version']
        if version_tuple(plan['version']) <= version_tuple(current_version):
            raise ValueError()
        return plan
    except (OSError, ValueError, KeyError, TypeError):
        raise UpdateError('invalid_package') from None


def restart(bundle, key):
    if key == 'macos-arm64':
        subprocess.Popen(['/usr/bin/open', '-n', str(bundle)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen([str(executable_in(bundle, key))], cwd=bundle,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def replace_bundle(plan_path):
    """Called by a detached copy AFTER the previous UI/supervisor has exited."""
    plan = read_plan(plan_path)
    stage = Path(plan_path).resolve().parent
    target, candidate, key = Path(plan['target']), Path(plan['candidate']), plan['platform']
    backup = stage / 'previous'
    # Windows bootloader/.NET files can take a moment to release after GUI shutdown.
    for attempt in range(60):
        try:
            target.rename(backup)
            break
        except PermissionError:
            if attempt == 59:
                raise UpdateError('install_locked') from None
            time.sleep(.5)
    installed = False
    try:
        candidate.rename(target)
        installed = True
        verify_native(target, key)
        restart(target, key)
    except BaseException:
        if installed:
            target.rename(candidate)
        backup.rename(target)
        restart(target, key)
        raise
    # Keep this backup/helper. Only completed older update directories may be cleaned.
    (stage / 'result.json').write_text(json.dumps(dict(ok=True, version=plan['version'])), encoding='utf-8')
    cleanup_completed(target, stage, key)


def cleanup_completed(target, active_stage, key):
    parent = target.parent.resolve()
    try:
        current_version = version_tuple(json.loads(marker_path(target, key).read_text(encoding='utf-8'))['version'])
    except (OSError, ValueError, TypeError, KeyError):
        return
    for old in parent.glob('.ytdl-update-*'):
        try:
            # Resolve and constrain every recursive delete to our adjacent staging folders.
            if old.is_symlink() or old.resolve().parent != parent or old.resolve() == active_stage.resolve():
                continue
            result = json.loads((old / 'result.json').read_text(encoding='utf-8'))
            plan = json.loads((old / 'plan.json').read_text(encoding='utf-8'))
            if result.get('ok') is not True or Path(plan['target']).resolve() != target.resolve() or \
                    plan['platform'] != key or version_tuple(result['version']) >= current_version:
                continue
            check_bundle(old / 'previous', key)
            check_bundle(old / 'helper' / target.name, key)
            shutil.rmtree(old)
        except (OSError, ValueError, KeyError, TypeError, UpdateError):
            pass  # Locked helpers or unrecognized folders are left alone.


def launch_helper(plan_path):
    plan = read_plan(plan_path)
    helper = Path(plan_path).parent / 'helper' / Path(plan['target']).name
    executable = executable_in(helper, plan['platform'])
    command = [str(executable), '--apply-update', str(plan_path), str(os.getpid())]
    subprocess.Popen(command, cwd=helper, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                     start_new_session=sys.platform != 'win32')


def wait_for_parent(pid):
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = api.OpenProcess(0x00100000, False, pid)
        if handle:
            try:
                if api.WaitForSingleObject(handle, 60000) != 0:
                    raise UpdateError('install_locked')
            finally:
                api.CloseHandle(handle)
    else:
        for _ in range(120):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(.5)
        raise UpdateError('install_locked')


def helper_main(plan_path, pid):
    try:
        read_plan(plan_path)
        wait_for_parent(int(pid))
        replace_bundle(plan_path)
        return 0
    except Exception:
        from desktop_launcher import notify_error
        notify_error('The update could not be installed. Your previous app and downloaded files were kept. '
                     'Close other copies of YTDL Studio and reopen the app to try again.')
        return 1
