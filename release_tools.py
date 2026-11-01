# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Assemble and publish only complete, versioned native release artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unicodedata

from app_version import VERSION, DISPLAY_NAME, version_tuple
from release_client import ASSETS, MANIFEST
from update_installer import marker_path


def collect(project, platform_key, destination):
    import zipfile
    project, destination = Path(project), Path(destination)
    matches = sorted((project / 'dist').rglob(ASSETS[platform_key]), key=lambda path: path.stat().st_mtime)
    if not matches:
        raise RuntimeError('No verified native build archive was found.')
    archive = matches[-1]
    root = 'NÜVEL Studio' if platform_key == 'windows-x64' else 'NÜVEL Studio.app'
    with zipfile.ZipFile(archive) as package:
        expected = marker_path(Path(root), platform_key).as_posix()
        matches = [name for name in package.namelist() if unicodedata.normalize('NFC', name) == expected]
        if len(matches) != 1:
            raise RuntimeError('The archive must contain exactly one product marker.')
        marker = json.loads(package.read(matches[0]))
    if marker != dict(product='NÜVEL Studio', platform=platform_key, version=VERSION):
        raise RuntimeError('Build version does not match this release.')
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive, destination / archive.name)


def manifest(folder):
    folder = Path(folder)
    platforms = {}
    for key, name in ASSETS.items():
        path = folder / name
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        platforms[key] = dict(name=name, size=path.stat().st_size, sha256=digest.hexdigest())
    (folder / MANIFEST).write_text(json.dumps(dict(schema=1, version=VERSION, platforms=platforms), indent=2), encoding='utf-8')


def publish(folder, tag):
    version_tuple(tag)
    if tag != 'v' + VERSION:
        raise RuntimeError('The tag must match app_version.VERSION.')
    manifest(folder)  # Requires BOTH operating systems before creating any release.
    result = subprocess.run(['gh', 'release', 'view', tag, '--json', 'isDraft'], capture_output=True, text=True)
    if result.returncode == 0:
        if not json.loads(result.stdout)['isDraft']:
            raise RuntimeError('Refusing to overwrite a published release. Bump the version.')
    else:
        subprocess.run(['gh', 'release', 'create', tag, '--verify-tag', '--draft', '--title', DISPLAY_NAME + ' ' + VERSION,
                        '--generate-notes'], check=True)
    files = [str(Path(folder) / name) for name in (*ASSETS.values(), MANIFEST)]
    subprocess.run(['gh', 'release', 'upload', tag, *files, '--clobber'], check=True)
    subprocess.run(['gh', 'release', 'edit', tag, '--draft=false'], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('check-version', 'collect', 'manifest', 'publish'))
    parser.add_argument('--tag', default='')
    parser.add_argument('--platform', choices=ASSETS)
    parser.add_argument('--folder', default='release')
    args = parser.parse_args()
    if args.command == 'check-version':
        if args.tag != 'v' + VERSION:
            raise SystemExit('Tag must equal v' + VERSION + ' (app_version.py).')
    elif args.command == 'collect':
        collect(Path(__file__).resolve().parent, args.platform, args.folder)
    elif args.command == 'manifest':
        manifest(args.folder)
    else:
        publish(args.folder, args.tag)


if __name__ == '__main__':
    main()
