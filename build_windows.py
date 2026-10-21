"""One-step isolated Windows build; only a verified bundle replaces the current app."""
import argparse
from datetime import datetime
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import venv


PROJECT = Path(__file__).resolve().parent


def check_python():
    if sys.platform != 'win32' or struct.calcsize('P') != 8 or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Build on Windows using 64-bit x64 Python.')
    if sys.version_info < (3, 10):
        raise RuntimeError('Python 3.10 or newer is required to build the application.')


def prepare():
    environment = PROJECT / '.venv-windows-build'
    # Repair/create our generated build environment without touching the user's Python packages.
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / 'Scripts/python.exe'
    subprocess.run([str(python), '-m', 'pip', 'install', '--upgrade', '-r', str(PROJECT / 'requirements.txt'),
                    'pyinstaller>=6.16,<7'], cwd=PROJECT, check=True)
    subprocess.run([str(python), str(PROJECT / 'build_windows.py'), '--run-build'], cwd=PROJECT, check=True)


def build():
    import webview  # noqa: F401 - fail before building if the native bridge is missing
    import webview.platforms.edgechromium  # noqa: F401 - validate the bundled .NET bridge
    from Microsoft.Web.WebView2.Core import CoreWebView2Environment
    if not CoreWebView2Environment.GetAvailableBrowserVersionString():
        raise RuntimeError('Microsoft Edge WebView2 Runtime is required.')
    import imageio_ffmpeg
    import PyInstaller.__main__
    from download_engine import PLATFORMS
    for _, _, slug, _ in PLATFORMS:
        if not (PROJECT / 'assets/platforms' / (slug + '.png')).is_file():
            raise RuntimeError('A required platform icon is missing: ' + slug)
    for filename in ('index.html', 'studio.css', 'i18n.js', 'studio.js'):
        if not (PROJECT / 'ui' / filename).is_file():
            raise RuntimeError('A required UI resource is missing: ' + filename)
    output = PROJECT / 'dist' / datetime.now().strftime('windows-%Y%m%d-%H%M%S-%f')
    staging = output / 'build-input'
    staging.mkdir(parents=True)
    ffmpeg = staging / 'ffmpeg.exe'
    shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(), ffmpeg)
    subprocess.run([str(ffmpeg), '-version'], check=True, capture_output=True, timeout=10,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    PyInstaller.__main__.run([
        str(PROJECT / 'desktop_launcher.py'), '--name', 'YTDL Studio', '--windowed', '--onedir', '--noupx',
        '--distpath', str(output), '--workpath', str(output / 'work'), '--specpath', str(output),
        '--add-data', str(PROJECT / 'assets') + ';assets', '--add-data', str(PROJECT / 'ui') + ';ui',
        '--add-binary', str(ffmpeg) + ';bin',
        '--collect-all', 'yt_dlp', '--collect-all', 'yt_dlp_ejs', '--collect-all', 'curl_cffi',
        '--collect-all', 'certifi', '--collect-all', 'webview', '--collect-all', 'pythonnet',
        '--collect-all', 'clr_loader', '--hidden-import', 'webview.platforms.winforms',
        '--hidden-import', 'webview.platforms.edgechromium', '--collect-all', 'PIL',
        '--copy-metadata', 'yt-dlp', '--exclude-module', 'gallery_dl', '--exclude-module', 'imageio_ffmpeg',
        '--exclude-module', 'tkinter', '--exclude-module', 'PyQt5', '--exclude-module', 'PyQt6',
        '--exclude-module', 'PySide2', '--exclude-module', 'PySide6',
    ])
    bundle = output / 'YTDL Studio'
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(PROJECT / name, bundle / name)
    from windows_distribution import publish_build
    executable = publish_build(PROJECT, bundle)
    try:
        subprocess.run(['explorer.exe', '/select,', str(PROJECT / 'YTDL Studio.lnk')], check=False)
    except OSError:
        pass  # Revealing the shortcut is optional; publication already succeeded.
    print('Build complete. Verified native interface without a console:', executable)
    print('Open the YTDL Studio shortcut in the project folder.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Build the Windows desktop application.')
    parser.add_argument('--run-build', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--check', action='store_true', help='Check build Python without installing or building.')
    args = parser.parse_args(argv)
    try:
        check_python()
        if args.check:
            print('Windows build Python: OK. No files were changed.')
        elif args.run_build:
            build()
        else:
            prepare()
        return 0
    except Exception as exc:
        print('Windows build stopped: ' + str(exc), file=sys.stderr)
        print('The existing app and shortcut were kept unless a new build passed all checks.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Windows build interrupted. The previous app was kept.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
