"""Small OS adapters shared by the GUI and macOS preflight checks."""
import os
from pathlib import Path
import subprocess
import sys


def resource_path(*parts):
    # PyInstaller sets __file__ inside its bundle on both Windows and macOS.
    return Path(__file__).resolve().parent.joinpath(*parts)


def install_instructions():
    if sys.platform == 'darwin':
        if getattr(sys, 'frozen', False):
            return 'build_macos.command (build a new app)'
        return 'install_macos.command'
    return 'install.bat'


def open_directory(path):
    path = str(Path(path).expanduser().resolve())
    if sys.platform == 'win32':
        os.startfile(path)
    else:
        subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', path],
                       check=True, timeout=10, capture_output=True)


def scroll_units(delta):
    if not delta:
        return 0
    if sys.platform == 'darwin':
        return -max(-8, min(8, int(delta)))
    return -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)


def ffmpeg_path():
    bundled = resource_path('bin', 'ffmpeg')
    if sys.platform == 'darwin' and bundled.is_file():
        return str(bundled)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()
