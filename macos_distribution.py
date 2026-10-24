"""Verify the Finder launch path, then publish a complete app without replacing a working build early."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import uuid
import unicodedata

from app_version import DISPLAY_NAME


APP_NAME = DISPLAY_NAME + '.app'
BUNDLE_ID = 'local.nuvelstudio.app'


def sign_bundle(app):
    # PyInstaller signs individual binaries, but a copied Python.org framework
    # can retain a resource seal for files not included in the frozen app.
    # Refresh framework containers inside-out, then the app, and verify all code.
    # https://developer.apple.com/library/archive/technotes/tn2206/
    app = Path(app)
    frameworks = sorted((app / 'Contents/Frameworks').rglob('*.framework'),
                        key=lambda path: len(path.parts), reverse=True)
    commands = [['/usr/bin/codesign', '--force', '--sign', '-', str(path)]
                for path in frameworks if not path.is_symlink()]
    commands.extend([
        ['/usr/bin/codesign', '--force', '--sign', '-', str(app)],
        ['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)],
    ])
    for command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=120)
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or b'No codesign diagnostic was returned.')
            if isinstance(details, bytes):
                details = details.decode('utf-8', errors='replace')
            raise RuntimeError(f'Bundle signing/verification failed (exit {exc.returncode}): {details.strip()}') from exc


def verify_app(app):
    """LaunchServices success alone is not proof that the UI or Python bridge loaded."""
    with tempfile.TemporaryDirectory(prefix='nuvel-launch-check-') as temporary:
        proof = Path(temporary) / 'result.json'
        try:
            subprocess.run(['/usr/bin/open', '-n', '-W', str(app), '--args', '--self-test',
                            '--smoke-result', str(proof)], check=True, timeout=120, capture_output=True)
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or b'No LaunchServices output was returned.')
            if isinstance(details, bytes):
                details = details.decode('utf-8', errors='replace')
            raise RuntimeError('The native startup launch failed '
                               f'(exit code {exc.returncode}): {details.strip()} '
                               'The previous app was kept.') from exc
        try:
            result = json.loads(proof.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise RuntimeError('The built app did not complete its native startup test. The previous app was kept.') from exc
        from update_installer import executable_in
        expected = executable_in(app, 'macos-arm64').resolve()
        try:
            matching_executable = Path(result.get('executable', '')).samefile(expected)
        except (OSError, TypeError, ValueError):
            matching_executable = False
        if result.get('ok') is not True or not matching_executable:
            raise RuntimeError('The built app returned an invalid startup result. The previous app was kept.')


def copy_bundle(source, destination):
    # Preserve the framework symlinks, permissions and extended attributes.
    subprocess.run(['/usr/bin/ditto', str(source), str(destination)], check=True, capture_output=True)


def archive_bundle(app, destination):
    app, destination = Path(app), Path(destination)
    if unicodedata.normalize('NFC', app.name) != APP_NAME:
        raise ValueError('The archive must contain ' + APP_NAME)
    subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                    str(app), str(destination)], check=True, capture_output=True)


def _exists(path):
    return path.exists() or path.is_symlink()


def _check_existing(path, project):
    if not _exists(path):
        return
    if path.is_symlink():
        target = path.resolve()
        if target != project / APP_NAME and not target.is_relative_to(project / 'dist'):
            raise RuntimeError('Refusing to replace an unrelated app link: ' + str(path))
        return
    try:
        with (path / 'Contents/Info.plist').open('rb') as stream:
            info = plistlib.load(stream)
    except (OSError, ValueError, plistlib.InvalidFileException) as exc:
        raise RuntimeError('Refusing to replace an unrecognized folder: ' + str(path)) from exc
    if info.get('CFBundleIdentifier') != BUNDLE_ID:
        raise RuntimeError('Refusing to replace an unrelated application: ' + str(path))


def publish_build(project, built_app):
    project, built_app = Path(project).resolve(), Path(built_app).resolve()
    if unicodedata.normalize('NFC', built_app.name) != APP_NAME or not built_app.is_relative_to(project / 'dist'):
        raise ValueError('The build must be a ' + APP_NAME + ' inside this project\'s dist folder.')
    current = project / APP_NAME
    _check_existing(current, project)
    identifier = uuid.uuid4().hex[:12]
    backups = []
    installed = []
    with tempfile.TemporaryDirectory(prefix='.studio-publish-', dir=project) as temporary:
        staging = Path(temporary)
        candidate = staging / APP_NAME
        copy_bundle(built_app, candidate)
        # Test after relocation, through the same OS route as a Finder double-click.
        verify_app(candidate)
        archive = staging / 'NUVEL-Studio-macOS-arm64.zip'
        archive_bundle(candidate, archive)
        try:
            for old in (current,):
                if _exists(old):
                    # Both source and destination are verified inside this workspace.
                    backup = built_app.parent / f'previous-{identifier}-{old.name}'
                    old.rename(backup)
                    backups.append((old, backup))
            candidate.rename(current)
            installed.append((current, candidate))
            os.replace(archive, built_app.parent / archive.name)
        except BaseException:
            for destination, original in reversed(installed):
                destination.rename(original)
            for original, backup in reversed(backups):
                backup.rename(original)
            raise
    return current
