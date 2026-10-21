"""Verify the Finder launch path, then publish a complete app without replacing a working build early."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import uuid


APP_NAME = 'YTDL Studio.app'
LEGACY_NAME = 'YTDL Studio Launcher.app'
BUNDLE_ID = 'local.ytdlstudio.app'


def verify_app(app):
    """LaunchServices success alone is not proof that the UI or Python bridge loaded."""
    with tempfile.TemporaryDirectory(prefix='ytdl-launch-check-') as temporary:
        proof = Path(temporary) / 'result.json'
        subprocess.run(['/usr/bin/open', '-n', '-W', str(app), '--args', '--self-test',
                        '--smoke-result', str(proof)], check=True, timeout=120, capture_output=True)
        try:
            result = json.loads(proof.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise RuntimeError('The built app did not complete its native startup test. The previous app was kept.') from exc
        expected = (app / 'Contents/MacOS/YTDL Studio').resolve()
        if result.get('ok') is not True or Path(result.get('executable', '')).resolve() != expected:
            raise RuntimeError('The built app returned an invalid startup result. The previous app was kept.')


def copy_bundle(source, destination):
    # Preserve the framework symlinks, permissions and extended attributes.
    subprocess.run(['/usr/bin/ditto', str(source), str(destination)], check=True, capture_output=True)


def archive_bundle(app, destination):
    subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                    str(app), str(destination)], check=True, capture_output=True)


def _exists(path):
    return path.exists() or path.is_symlink()


def _check_existing(path, project, legacy=False):
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
    is_app = info.get('CFBundleIdentifier') == BUNDLE_ID
    is_old_launcher = legacy and info.get('CFBundleExecutable') == 'applet' and \
        (path / 'Contents/Resources/Scripts/main.scpt').is_file()
    if not (is_app or is_old_launcher):
        raise RuntimeError('Refusing to replace an unrelated application: ' + str(path))


def publish_build(project, built_app):
    project, built_app = Path(project).resolve(), Path(built_app).resolve()
    if built_app.name != APP_NAME or not built_app.is_relative_to(project / 'dist'):
        raise ValueError('The build must be a YTDL Studio.app inside this project\'s dist folder.')
    current, legacy = project / APP_NAME, project / LEGACY_NAME
    _check_existing(current, project)
    _check_existing(legacy, project, legacy=True)
    had_legacy = _exists(legacy)
    identifier = uuid.uuid4().hex[:12]
    backups = []
    installed = []
    with tempfile.TemporaryDirectory(prefix='.studio-publish-', dir=project) as temporary:
        staging = Path(temporary)
        candidate = staging / APP_NAME
        copy_bundle(built_app, candidate)
        # Test after relocation, through the same OS route as a Finder double-click.
        verify_app(candidate)
        archive = staging / 'YTDL-Studio-macOS-arm64.zip'
        archive_bundle(candidate, archive)
        legacy_link = staging / LEGACY_NAME
        if had_legacy:
            legacy_link.symlink_to(APP_NAME, target_is_directory=True)
        try:
            for old in (current, legacy) if had_legacy else (current,):
                if _exists(old):
                    # Both source and destination are verified inside this workspace.
                    backup = built_app.parent / f'previous-{identifier}-{old.name}'
                    old.rename(backup)
                    backups.append((old, backup))
            candidate.rename(current)
            installed.append((current, candidate))
            if had_legacy:
                legacy_link.rename(legacy)
                installed.append((legacy, legacy_link))
            os.replace(archive, built_app.parent / archive.name)
        except BaseException:
            for destination, original in reversed(installed):
                destination.rename(original)
            for original, backup in reversed(backups):
                backup.rename(original)
            raise
    return current
