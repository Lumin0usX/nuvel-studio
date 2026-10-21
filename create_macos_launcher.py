"""Compile a small Finder launcher; Python and the source stay in the Git folder."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != 'darwin':
        raise SystemExit('Create this launcher on macOS, using install_macos.command.')
    project = Path(__file__).resolve().parent
    app = project / 'YTDL Studio Launcher.app'
    subprocess.run(['/usr/bin/osacompile', '-o', str(app),
                    str(project / 'macos_launcher.applescript')], check=True, capture_output=True)
    print('Windowless launcher:', app)
    print('Keep this launcher in the project folder. A Finder alias may be placed elsewhere.')


if __name__ == '__main__':
    main()
