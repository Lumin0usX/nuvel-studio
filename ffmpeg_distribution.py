"""Fail-closed packaging gate for a separately built, source-bearing LGPL CLI.

This checks supplied evidence; it cannot prove provenance or legal compliance.
Source developers may still use imageio-ffmpeg locally. Redistributed packages
must explicitly select an audited bundle; there is no GPL-binary fallback.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

from dependency_audit import digest, ffmpeg_evidence
from media_quality import lgpl_encoder_options


def _file(root, relative):
    path = root / relative
    if (not relative or Path(relative).is_absolute() or '\\' in relative
            or '..' in Path(relative).parts or re.match(r'^[A-Za-z]:', relative)):
        raise RuntimeError('FFmpeg manifest contains an invalid relative path.')
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink() or not path.is_file():
        raise RuntimeError('FFmpeg bundle file is missing or outside its directory: ' + relative)
    return path


def validate_bundle(root, target):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or manifest.get('target') != target:
        raise RuntimeError('FFmpeg evidence does not match this build target.')
    filename = 'ffmpeg.exe' if target == 'windows-x64' else 'ffmpeg'
    if target not in ('macos-arm64', 'windows-x64') or manifest.get('binary') != filename:
        raise RuntimeError('Unsupported FFmpeg bundle target or binary name.')
    files = manifest.get('files', {})
    if not isinstance(files, dict) or filename not in files:
        raise RuntimeError('FFmpeg bundle has no binary hash.')
    for name, sha in files.items():
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha) or digest(_file(root, name)) != sha:
            raise RuntimeError('FFmpeg bundle hash mismatch: ' + name)
    actual_files = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise RuntimeError('FFmpeg evidence bundle must not contain symlinks.')
        if path.is_file() and path != root / 'manifest.json':
            actual_files.add(path.relative_to(root).as_posix())
    if actual_files != set(files):
        raise RuntimeError('Every FFmpeg bundle file must be included in its hash manifest.')
    roles = manifest.get('materials', {})
    for role in ('ffmpeg_source', 'ffmpeg_license', 'build_script', 'build_log', 'library_inventory'):
        name = roles.get(role, '')
        if name not in files or not name.startswith('source/'):
            raise RuntimeError('FFmpeg bundle lacks source/build material: ' + role)
    libraries = json.loads(_file(root, roles['library_inventory']).read_text(encoding='utf-8'))
    if not isinstance(libraries, list) or not libraries:
        raise RuntimeError('FFmpeg linked-library inventory is missing.')
    for library in libraries:
        if not library.get('name') or not library.get('license'):
            raise RuntimeError('Every linked library needs an identity and license.')
        # System SDK/runtime components are not copied into this CLI bundle.
        if library.get('system') is True:
            continue
        for role in ('source', 'license_file'):
            if library.get(role) not in files or not library[role].startswith('source/'):
                raise RuntimeError('Linked library is missing matching source/license: ' + library['name'])
    report = ffmpeg_evidence(_file(root, filename))
    config = shlex.split(report['configuration'])
    if (not config or report['gpl_enabled'] or report['nonfree_enabled'] or report['version3_enabled']
            or any(flag in config for flag in ('--enable-libx264', '--enable-libx265', '--enable-libfdk-aac'))):
        raise RuntimeError('Distribution requires an LGPL build without GPL, version3 or nonfree components.')
    for flag in ('--disable-gpl', '--disable-nonfree', '--disable-version3', '--disable-autodetect'):
        if flag not in config:
            raise RuntimeError('FFmpeg build must explicitly configure ' + flag)
    linked_names = {library['name'] for library in libraries if not library.get('system')}
    for flag in config:
        if flag.startswith('--enable-lib') and flag.removeprefix('--enable-') not in linked_names:
            raise RuntimeError('Enabled FFmpeg library is absent from the source inventory: ' + flag)
    license_text = ''.join(report['outputs']['license'].values())
    if not re.search(r'GNU Lesser General Public License', license_text, re.I):
        raise RuntimeError('FFmpeg does not identify its executable as LGPL.')
    # Hashes only establish that supplied files match their manifest. A reviewer
    # must also establish that these sources actually produced this executable.
    return _file(root, filename), root / 'source', report


def selected_bundle(target):
    directory = os.environ.get('NUVEL_FFMPEG_BUNDLE', '')
    if not directory:
        raise RuntimeError('Set NUVEL_FFMPEG_BUNDLE to a source-bearing LGPL FFmpeg bundle. '
                           'The imageio-ffmpeg GPL binary will not be redistributed. '
                           'See legal/FFMPEG-LGPL.md.')
    return validate_bundle(Path(directory).expanduser().resolve(), target)


def verify_media(executable, target):
    """Encode/decode local generated media; a version string is insufficient."""
    def run(*args):
        try:
            subprocess.run([str(executable), '-hide_banner', '-nostdin', '-v', 'error', *args],
                           check=True, capture_output=True, timeout=45,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b'No encoder diagnostic returned.').decode('utf-8', errors='replace')
            raise RuntimeError('FFmpeg media acceptance failed; existing app kept.\n' + detail[-4000:]) from exc
    with tempfile.TemporaryDirectory(prefix='nuvel-codec-check-') as temporary:
        root = Path(temporary)
        source, video, audio = root / 'source.mkv', root / 'video.mp4', root / 'audio.mp3'
        run('-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=10',
            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
            '-t', '0.3', '-c:v', 'ffv1', '-c:a', 'flac', str(source))
        encoder = lgpl_encoder_options(target)
        run('-i', str(source), *encoder, '-pix_fmt', 'yuv420p', '-c:a', 'aac',
            '-b:a', '192k', '-movflags', '+faststart', str(video))
        run('-i', str(video), '-vn', '-c:a', 'libmp3lame', '-b:a', '192k', str(audio))
        for path in (video, audio):
            if not path.is_file() or not path.stat().st_size:
                raise RuntimeError('FFmpeg did not create the required codec-check output.')
            run('-i', str(path), '-f', 'null', '-')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--target', required=True, choices=('macos-arm64', 'windows-x64'))
    parser.add_argument('--verify-media', action='store_true')
    args = parser.parse_args()
    binary, _, report = validate_bundle(args.bundle, args.target)
    if args.verify_media:
        verify_media(binary, args.target)
    print('LGPL evidence gate passed:', binary.name, report['sha256'])
    print('Source correspondence, dependencies and final packaged bytes still require review.')


if __name__ == '__main__':
    main()
