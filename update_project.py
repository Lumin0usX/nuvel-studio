"""Folder-based source updater. Uses the user's existing Git credentials."""
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
    except UpdateError as exc:
        raise UpdateError('Could not fetch updates. Check your connection and access to the private repository.\n'
                          'No update was applied.\n' + str(exc)) from exc
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
    parser = argparse.ArgumentParser(description='Update the NÜVEL Studio source folder on Windows or macOS.')
    parser.add_argument('--build', action='store_true', help='Compatibility option: updates always build the app.')
    parser.add_argument('--check', action='store_true', help='Check Python, pip and Git without updating or installing.')
    args = parser.parse_args(argv)
    if sys.platform not in ('darwin', 'win32'):
        parser.error('Run update.bat on Windows or update_macos.command on macOS.')
    project = Path(__file__).resolve().parent
    try:
        if args.check:
            if not shutil.which('git'):
                raise UpdateError('Git was not found. Install Git and reopen this updater.')
            subprocess.run(['git', '--version'], check=True)
            subprocess.run([sys.executable, '-m', 'pip', '--version'], check=True)
            print('NÜVEL Studio updater: OK. No updates were applied.', flush=True)
            return 0
        update_source(project)
        print('Updating dependencies and checking the environment...', flush=True)
        if sys.platform == 'win32':
            print('Building the updated Windows app...', flush=True)
            subprocess.run([sys.executable, str(project / 'build_windows.py')], cwd=project, check=True)
        else:
            print('Building the updated macOS app...', flush=True)
            subprocess.run(['/bin/bash', str(project / 'build_macos.command')], cwd=project, check=True)
        from app_version import DISPLAY_NAME
        launcher = DISPLAY_NAME + (' shortcut' if sys.platform == 'win32' else '.app')
        print('Update complete. Open ' + launcher + ' in the project folder.', flush=True)
        return 0
    except UpdateError as exc:
        print('\nUpdate stopped:\n' + str(exc), file=sys.stderr)
    except subprocess.CalledProcessError as exc:
        if args.check:
            print('\nUpdater check failed. See the error above; no updates were applied.', file=sys.stderr)
        else:
            print('\nSource is current, but installation/build failed (exit ' + str(exc.returncode)
                  + '). See the error above. You can rerun this updater to retry.', file=sys.stderr)
    except OSError as exc:
        print('\nCould not run an update component: ' + str(exc), file=sys.stderr)
    except KeyboardInterrupt:
        print('\nUpdate interrupted. Rerun the updater to check and finish the update.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
