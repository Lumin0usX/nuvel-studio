"""Inventory the local build environment and exact FFmpeg files, without downloads.

This collects evidence and license texts, not a legal clearance or a claim that
all corresponding source for a redistributed executable has been supplied.
"""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def ffmpeg_evidence(executable):
    executable = Path(executable)
    outputs = {}
    for name, argument in [('version', '-version'), ('license', '-L')]:
        result = subprocess.run([str(executable), argument], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', check=True, timeout=20,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        outputs[name] = dict(stdout=result.stdout, stderr=result.stderr)
    text = outputs['version']['stdout'] + outputs['version']['stderr']
    configuration = next((line.split('configuration:', 1)[1].strip() for line in text.splitlines()
                          if 'configuration:' in line), '')
    return dict(name=executable.name, sha256=digest(executable), size=executable.stat().st_size,
                configuration=configuration, gpl_enabled='--enable-gpl' in configuration,
                version3_enabled='--enable-version3' in configuration,
                nonfree_enabled='--enable-nonfree' in configuration, outputs=outputs,
                status='Evidence only; exact corresponding source, linked libraries and redistribution rights remain to be verified.')


def build_inventory(destination, executables):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    packages = []
    for package in sorted(metadata.distributions(), key=lambda item: item.metadata.get('Name', '').lower()):
        name, version = package.metadata.get('Name', 'unknown'), package.version
        record = dict(name=name, version=version, license_expression=package.metadata.get('License-Expression'),
                      license_metadata=package.metadata.get('License'), project_urls=package.metadata.get_all('Project-URL', []),
                      notices=[])
        component = re.sub(r'[^A-Za-z0-9_.-]', '_', name + '-' + version)
        for item in package.files or []:
            if not any(word in item.name.upper() for word in ('LICENSE', 'LICENCE', 'COPYING', 'NOTICE')):
                continue
            source = Path(package.locate_file(item))
            if not source.is_file():
                continue
            sha = digest(source)
            target = destination / 'licenses' / component / (sha[:12] + '-' + source.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            record['notices'].append(dict(path=target.relative_to(destination).as_posix(), sha256=sha))
        packages.append(record)
    report = dict(schema=1, python=sys.version, os=sys.platform, architecture=platform.machine(),
                  scope='Installed build-environment distributions; not a complete SBOM of any release artifact.',
                  packages=packages, ffmpeg=[ffmpeg_evidence(path) for path in executables],
                  status='Not certified for distribution. License copies alone do not satisfy corresponding-source obligations.')
    (destination / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, action='append', default=[])
    args = parser.parse_args()
    report = build_inventory(args.output, args.ffmpeg)
    print('Inventory:', len(report['packages']), 'distributions;', len(report['ffmpeg']),
          'FFmpeg files. Corresponding source and legal clearance are not verified.')


if __name__ == '__main__':
    main()
