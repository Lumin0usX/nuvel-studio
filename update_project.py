"""Folder-based source updater. Uses the user's existing Git credentials."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from update_bootstrap import ORIGINS, UpdateError, update_source


def main(argv=None):
    parser = argparse.ArgumentParser(description='Update the NÜVEL Studio source folder on Windows or macOS.')
    parser.add_argument('--build', action='store_true', help='Compatibility option: updates always build the app.')
    parser.add_argument('--check', action='store_true', help='Check Python, pip and Git without updating or installing.')
    parser.add_argument('--build-current', action='store_true',
                        help='Build the checked-out source; used after the bootstrap has verified an update.')
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
        if not args.build_current:
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
