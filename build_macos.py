"""Build on an Apple Silicon Mac; no cross-compilation from Windows."""
from pathlib import Path
import subprocess
import sys
import shutil
from datetime import datetime


def main():
    from check_macos import main as preflight
    preflight()
    import imageio_ffmpeg
    import PyInstaller.__main__
    project = Path(__file__).resolve().parent
    # A fresh output directory preserves previous builds.
    output = project / 'dist' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    staging = output / 'build-input'
    staging.mkdir(parents=True)
    bundled_ffmpeg = staging / 'ffmpeg'
    shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(), bundled_ffmpeg)
    bundled_ffmpeg.chmod(0o755)
    PyInstaller.__main__.run([
        str(project / 'ytdl_studio.py'), '--name', 'YTDL Studio',
        '--windowed', '--onedir', '--target-arch', 'arm64',
        '--osx-bundle-identifier', 'local.ytdlstudio.app',
        '--distpath', str(output), '--workpath', str(output / 'work'),
        '--specpath', str(output),
        '--add-data', str(project / 'assets') + ':assets',
        '--add-data', str(project / 'ui') + ':ui',
        '--add-binary', str(bundled_ffmpeg) + ':bin',
        '--collect-all', 'yt_dlp', '--collect-all', 'yt_dlp_ejs',
        '--collect-all', 'curl_cffi', '--collect-all', 'certifi',
        '--collect-all', 'webview', '--hidden-import', 'webview.platforms.cocoa',
        '--exclude-module', 'gallery_dl',  # gallery-dl is a separate external CLI
        '--collect-all', 'PIL',
        '--copy-metadata', 'yt-dlp',
    ])
    app = output / 'YTDL Studio.app'
    # A packaged smoke test opens the new WebKit interface.
    subprocess.run([str(app / 'Contents/MacOS/YTDL Studio'), '--self-test'], check=True)
    subprocess.run(['/usr/bin/ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                    str(app), str(output / 'YTDL-Studio-macOS-arm64.zip')], check=True)
    print('Built and smoke-tested:', app)
    print('This local build is ad-hoc signed, not notarized for public distribution.')


if __name__ == '__main__':
    main()
