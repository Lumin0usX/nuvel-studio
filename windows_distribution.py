"""Verify a console-free Windows bundle and publish it with a stable shortcut."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import uuid
import zipfile

from create_windows_launcher import create_launcher
from desktop_launcher import WindowsJob
from app_version import DISPLAY_NAME
from update_installer import executable_in


EXECUTABLE = DISPLAY_NAME + '.exe'
SHORTCUT = DISPLAY_NAME + '.lnk'
OLD_SHORTCUT = 'YTDL Studio.lnk'
FOLDER = 'app-windows'
MARKER = '.studio-build.json'


def check_gui_executable(executable):
    """PE optional-header Subsystem must be Windows GUI (2), not Console (3)."""
    with Path(executable).open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b'MZ':
            raise RuntimeError('The build did not produce a Windows executable.')
        offset = struct.unpack_from('<I', header, 60)[0]
        if not 64 <= offset <= 1024 * 1024:
            raise RuntimeError('The executable has an invalid PE header.')
        stream.seek(offset)
        pe = stream.read(96)
    if len(pe) < 96 or pe[:4] != b'PE\x00\x00' or struct.unpack_from('<H', pe, 92)[0] != 2:
        raise RuntimeError('The build is not a console-free Windows GUI executable.')


def verify_app(folder, *, legacy=False):
    executable = ((Path(folder) / 'YTDL Studio.exe') if legacy else
                  executable_in(folder, 'windows-x64')).resolve()
    check_gui_executable(executable)
    # This outer job also reaps a self-test if the supervisor itself cannot start.
    job = WindowsJob()
    process = None
    try:
        with tempfile.TemporaryDirectory(prefix='ytdl-exe-check-') as temporary:
            proof = Path(temporary) / 'result.json'
            process = subprocess.Popen([str(executable), '--self-test', '--smoke-result', str(proof)],
                                       cwd=folder, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            job.assign(process.pid)
            result = process.wait(timeout=120)
            if result:
                raise RuntimeError('The packaged interface failed its startup test. The previous app was kept.')
            try:
                data = json.loads(proof.read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                raise RuntimeError('The packaged interface did not confirm startup. The previous app was kept.') from exc
            if not isinstance(data, dict) or data.get('ok') is not True or data.get('console_attached') is not False or \
                    Path(data.get('executable', '')).resolve() != executable:
                raise RuntimeError('The packaged interface returned an invalid startup result.')
    finally:
        job.close()
        if process and process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def archive_bundle(folder, destination):
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(folder.rglob('*')):
            if item.is_file():
                archive.write(item, Path('YTDL Studio') / item.relative_to(folder))


def _check_current(folder):
    if not folder.exists() and not folder.is_symlink():
        return
    if folder.is_symlink():
        raise RuntimeError('Refusing to replace a linked application folder: ' + str(folder))
    try:
        data = json.loads((folder / MARKER).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise RuntimeError('Refusing to replace an unrecognized folder: ' + str(folder)) from exc
    if not isinstance(data, dict) or data.get('product') != 'YTDL Studio' or data.get('platform') not in ('windows', 'windows-x64'):
        raise RuntimeError('Refusing to replace an unrelated application: ' + str(folder))


def publish_build(project, built_folder):
    project, built_folder = Path(project).resolve(), Path(built_folder).resolve()
    if not built_folder.is_relative_to(project / 'dist'):
        raise ValueError('The Windows build must be inside this project\'s dist folder.')
    current, shortcut = project / FOLDER, project / SHORTCUT
    old_shortcut = project / OLD_SHORTCUT
    _check_current(current)
    for path in (shortcut, old_shortcut):
        if path.exists() and not path.is_file() and not path.is_symlink():
            raise RuntimeError('Refusing to replace an unrelated shortcut folder: ' + str(path))
    shortcuts = [shortcut] + ([old_shortcut] if old_shortcut.exists() or old_shortcut.is_symlink() else [])
    identifier = uuid.uuid4().hex[:12]
    backups, installed = [], []
    with tempfile.TemporaryDirectory(prefix='.studio-publish-', dir=project) as temporary:
        staging = Path(temporary)
        candidate = staging / 'YTDL Studio'
        shutil.copytree(built_folder, candidate)
        verify_app(candidate)
        if (candidate / 'YTDL Studio.exe').is_file():
            verify_app(candidate, legacy=True)
        from update_installer import write_marker
        write_marker(candidate, 'windows-x64')
        archive = staging / 'YTDL-Studio-Windows-x64.zip'
        archive_bundle(candidate, archive)
        for path in shortcuts:
            create_launcher(project, target=current / EXECUTABLE, shortcut=staging / path.name)
        try:
            for old in (current, *shortcuts):
                if old.exists() or old.is_symlink():
                    backup = built_folder.parent / f'previous-{identifier}-{old.name}'
                    old.rename(backup)
                    backups.append((old, backup))
            replacements = [(candidate, current)] + [(staging / path.name, path) for path in shortcuts]
            for source, destination in replacements:
                source.rename(destination)
                installed.append((destination, source))
            os.replace(archive, built_folder.parent / archive.name)
        except BaseException:
            for destination, original in reversed(installed):
                destination.rename(original)
            for original, backup in reversed(backups):
                backup.rename(original)
            raise
    return current / EXECUTABLE
