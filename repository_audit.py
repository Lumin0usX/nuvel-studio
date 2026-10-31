"""Read-only local Git/working-tree audit. Reports locations, never secret values.

Heuristic detection is not proof that a repository is free of credentials.
Remote-only refs, GitHub artifacts, LFS payloads and external stores are outside
this local audit. No network requests or history changes are performed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess


PATTERNS = {
    'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{50,255})\b'),
    'aws_access_key_id': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'google_api_key': re.compile(r'\bAIza[A-Za-z0-9_-]{35}\b'),
    'slack_token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,255}\b'),
    'private_key': re.compile(r'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----'),
    'jwt': re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
    'credential_url': re.compile(r'https?://[^\s/<>"\x27:]{1,128}:[^\s/<>"\x27@]{4,255}@'),
    'service_secret': re.compile(r'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{28,255}|SG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})\b'),
    'cookie_record': re.compile(r'(?m)^(?:#HttpOnly_)?\.?[A-Za-z0-9.-]+\t(?:TRUE|FALSE)\t[^\t\n]+\t(?:TRUE|FALSE)\t\d+\t[^\t\n]+\t[^\n]+$'),
    'authorization_value': re.compile(r'''(?i)authorization["']?\s*[:=]\s*["']?(?:Basic|Bearer)\s+[A-Za-z0-9+/=_-]{16,512}'''),
}
ASSIGNMENT = re.compile(r'''(?im)^.{0,80}?(?:api[_-]?key|client[_-]?secret|password|access[_-]?token|refresh[_-]?token|secret[_-]?key)["']?\s*[=:]\s*["']([^"'\r\n]{12,512})["']''')
ENV_ASSIGNMENT = re.compile(r'(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:API_KEY|SECRET|PASSWORD|ACCESS_TOKEN|REFRESH_TOKEN|SECRET_KEY)\s*=\s*([^\s\x22\x27#]{12,512})')
EMAIL = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I)
HOME_PATH = re.compile(r'(?:/Users/|C:\\Users\\)[^/\\\s"\x27<>]+')
SKIP_DIRS = {'.git', 'dist', 'build', 'node_modules', '__pycache__', '.pytest_cache', '.preview-profile'}


def fingerprint(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]


def entropy(value):
    return -sum((value.count(char) / len(value)) * math.log2(value.count(char) / len(value)) for char in set(value))


def scan(data, location, oid=''):
    text = data.decode('utf-8', errors='replace')
    findings = []
    def add(kind, match, value=None):
        findings.append(dict(kind=kind, location=location, object=oid,
                             line=text.count('\n', 0, match.start()) + 1,
                             fingerprint=fingerprint(value or match.group())))
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            add(kind, match)
    if b'\x00' not in data:
        for match in list(ASSIGNMENT.finditer(text)) + list(ENV_ASSIGNMENT.finditer(text)):
            value = match[1]
            if entropy(value) >= 3.5 and not any(token in value.lower() for token in ('example', 'placeholder', '${', '{{')):
                add('possible_secret_assignment', match, value)
        for kind, pattern in [('email_identifier', EMAIL), ('local_home_path', HOME_PATH)]:
            for match in pattern.finditer(text):
                add(kind, match)
    return findings


def git(project, *args):
    result = subprocess.run(['git', '-C', str(project), *args], capture_output=True)
    if result.returncode:
        raise RuntimeError('A local Git inspection command failed; no history was changed.')
    return result.stdout


def audit(project, include_built_apps=False):
    project = Path(project).resolve()
    paths = {}
    for line in git(project, 'rev-list', '--objects', '--all', '--reflog').decode().splitlines():
        oid, _, path = line.partition(' ')
        if path:
            paths.setdefault(oid, path)
    objects = git(project, 'cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype) %(objectsize)').decode().splitlines()
    findings, skipped = [], []
    counts = dict(blob=0, commit=0, tag=0)
    for line in objects:
        oid, kind, size = line.split()
        if kind not in counts:
            continue
        if int(size) > 32 * 1024 * 1024:
            skipped.append(dict(object=oid, size=int(size), reason='size_limit'))
            continue
        counts[kind] += 1
        findings.extend(scan(git(project, 'cat-file', kind, oid), paths.get(oid, '<' + kind + ' object>'), oid))
    working_files = 0
    for directory, dirs, files in os.walk(project):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.startswith('.venv')
                   and (include_built_apps or not name.lower().endswith('.app'))
                   and name not in ('nuvel-windows', 'app-windows')]
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or path.suffix in ('.pyc', '.pyo'):
                continue
            size = path.stat().st_size
            if size > 32 * 1024 * 1024:
                skipped.append(dict(location=str(path.relative_to(project)), size=size, reason='size_limit'))
                continue
            working_files += 1
            findings.extend(scan(path.read_bytes(), str(path.relative_to(project))))
    config = Path(git(project, 'rev-parse', '--git-path', 'config').decode().strip())
    if not config.is_absolute():
        config = project / config
    if config.is_file():
        findings.extend(scan(config.read_bytes(), '.git/config'))
    identities = set(git(project, 'log', '--all', '--format=%ae%n%ce').decode().splitlines())
    return dict(schema=1, head=git(project, 'rev-parse', 'HEAD').decode().strip(),
                shallow=git(project, 'rev-parse', '--is-shallow-repository').strip() == b'true',
                local_objects=counts, working_files=working_files,
                local_refs=git(project, 'for-each-ref', '--format=%(refname)').decode().splitlines(),
                author_email_fingerprints=sorted(fingerprint(value.lower()) for value in identities if value),
                findings=findings, skipped=skipped,
                included_built_apps=include_built_apps,
                limits=['Heuristic detection; false positives and false negatives require review.',
                        'Local object database includes unreachable objects; remote-only refs are not fetched.',
                        'No GitHub release/Actions artifacts, LFS payloads, backups or OS/browser credential stores scanned.',
                        'Working-tree runtime/build folders are excluded; tracked historical objects are still scanned.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--include-built-apps', action='store_true', help='Also inspect project-root macOS app contents; reports dependency credentials too.')
    parser.add_argument('--fail-on-secrets', action='store_true', help='Fail on candidate secrets; public license emails and local paths do not fail this check.')
    args = parser.parse_args()
    report = audit(Path(__file__).resolve().parent, args.include_built_apps)
    output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding='utf-8')
        print('Redacted audit report written. Objects:', report['local_objects'], 'findings:', len(report['findings']))
    else:
        print(output, end='')
    if args.fail_on_secrets and (report['shallow'] or report['skipped'] or
            any(item['kind'] not in ('email_identifier', 'local_home_path') for item in report['findings'])):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
