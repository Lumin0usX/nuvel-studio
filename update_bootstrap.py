# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Small source-update entry point, independent of the application and build code.

Keep this bootstrap backward compatible: double-click launchers fetch a verified
fast-forward first, then run the freshly updated build orchestrator.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


ORIGINS = frozenset({
    'https://github.com/lumin0usx/nuvel-studio',
    'git@github.com:lumin0usx/nuvel-studio',
    'ssh://git@github.com/lumin0usx/nuvel-studio',
    # Existing clones retain the original URL after the GitHub repository rename.
    # These are exact migration aliases, not a general bypass of the allowlist.
    'https://github.com/lumin0usx/ytdl-studio',
    'git@github.com:lumin0usx/ytdl-studio',
    'ssh://git@github.com/lumin0usx/ytdl-studio',
})


class UpdateError(RuntimeError):
    pass


def fallback_origin(origin):
    """Try the other known name using the same Git transport and credentials."""
    if origin not in ORIGINS:
        return None
    prefix, name = origin.rsplit('/', 1)
    # Both SSH forms and HTTPS end in /<repository>.
    previous = 'ytdl-studio'
    current = 'nuvel-studio'
    return prefix + '/' + (current if name == previous else previous) + '.git'


def update_source(project, allowed_origins=ORIGINS):
    """Fast-forward main only; leave local edits and diverged history untouched."""
    project = Path(project).resolve()
    if not shutil.which('git'):
        raise UpdateError('Git was not found. Install Git for Windows or the macOS Command Line Tools, then retry.')

    def git(*args):
        try:
            return subprocess.run(['git', '-C', str(project), *args], check=True,
                                  capture_output=True, text=True, encoding='utf-8',
                                  errors='replace', timeout=120).stdout.strip()
        except subprocess.TimeoutExpired as exc:
            raise UpdateError('Git timed out. Check your connection and GitHub access, then retry.') from exc
        except subprocess.CalledProcessError as exc:
            raise UpdateError((exc.stderr or exc.stdout or 'Git failed.').strip()) from exc

    try:
        root = Path(git('rev-parse', '--show-toplevel')).resolve()
    except UpdateError as exc:
        raise UpdateError('This folder is not an accessible Git clone. Clone the private repository first.\n' + str(exc)) from exc
    if root != project:
        raise UpdateError('Run the updater from the root of the NÜVEL Studio Git clone.')
    branch = git('branch', '--show-current')
    if branch != 'main':
        raise UpdateError('Updates require the main branch. Switch branches manually before retrying.')
    origin = git('config', '--get', 'remote.origin.url').lower().rstrip('/').removesuffix('.git')
    if origin not in allowed_origins:
        raise UpdateError('Origin is not the NÜVEL Studio repository. Check your Git remote configuration.')
    changes = git('status', '--porcelain', '--untracked-files=normal')
    if changes:
        raise UpdateError('Local changes or untracked files were found. Save/commit or move them before updating.\n'
                          'The updater will not discard files:\n' + changes)
    # Also refuse an unfinished merge/rebase/cherry-pick, even with a clean tree.
    for name in ('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'REVERT_HEAD'):
        marker = Path(git('rev-parse', '--git-path', name))
        if not marker.is_absolute():
            marker = project / marker
        if marker.exists():
            raise UpdateError('A Git operation is unfinished. Finish it before updating.')
    before = git('rev-parse', 'HEAD')
    print('Checking GitHub for updates...', flush=True)
    try:
        git('fetch', '--no-tags', 'origin', 'refs/heads/main')
    except UpdateError as original_error:
        fallback = fallback_origin(origin)
        if fallback is None or fallback.removesuffix('.git') not in allowed_origins:
            raise UpdateError('Could not fetch updates. Check your connection and access to the private repository.\n'
                              'No update was applied.\n' + str(original_error)) from original_error
        print('The configured origin could not provide the update. Trying the alternate project URL...', flush=True)
        try:
            git('fetch', '--no-tags', fallback, 'refs/heads/main')
        except UpdateError as fallback_error:
            raise UpdateError('Could not fetch updates from either project URL. Check your connection and '
                              'access to the private repository.\nNo update was applied.\n'
                              'Origin: ' + str(original_error) + '\nAlternate: ' + str(fallback_error)) from fallback_error
    target = git('rev-parse', 'FETCH_HEAD')
    if before == target:
        print('Source is already up to date (' + before[:8] + ').', flush=True)
        return False
    try:
        git('merge-base', '--is-ancestor', before, target)
    except UpdateError as exc:
        raise UpdateError('Local main has commits that are not on GitHub, or history has diverged.\n'
                          'No update was applied. Resolve the history manually; no reset was performed.') from exc
    # Git also checks edits made during the fetch and refuses conflicting files.
    git('merge', '--ff-only', '--no-autostash', '--no-overwrite-ignore', target)
    print('Source updated: ' + before[:8] + ' -> ' + target[:8], flush=True)
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description='Fetch and run the current NÜVEL Studio source updater.')
    parser.add_argument('--check', action='store_true', help='Check prerequisites without fetching or building.')
    parser.add_argument('--build', action='store_true', help='Compatibility option: updates always build the app.')
    args = parser.parse_args(argv)
    if sys.platform not in ('darwin', 'win32'):
        parser.error('Run update.bat on Windows or update_macos.command on macOS.')
    project = Path(__file__).resolve().parent
    try:
        if not args.check:
            update_source(project)
        # A new process reads the updated orchestrator, rather than continuing
        # to execute its old definitions after Git changes the source on disk.
        mode = '--check' if args.check else '--build-current'
        result = subprocess.run([sys.executable, '-u', str(project / 'update_project.py'), mode], cwd=project)
        return result.returncode
    except UpdateError as exc:
        print('\nUpdate stopped:\n' + str(exc), file=sys.stderr)
    except OSError as exc:
        print('\nCould not start the updated build component: ' + str(exc), file=sys.stderr)
    except KeyboardInterrupt:
        print('\nUpdate interrupted. Your existing app was kept.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())

