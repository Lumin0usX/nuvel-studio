"""Run on the target Mac before launching or packaging."""
import platform
import subprocess
import sys


def main():
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        raise SystemExit('Requires macOS and native ARM64 Python; do not use Rosetta.')
    if sys.version_info < (3, 12):
        raise SystemExit('Install Python 3.12 or newer.')
    import webview
    import WebKit
    import yt_dlp
    import curl_cffi
    from platform_runtime import ffmpeg_path, resource_path
    from download_engine import PLATFORMS
    for _, _, slug, _ in PLATFORMS:
        assert resource_path('assets', 'platforms', slug + '.png').is_file()
    for filename in ('index.html', 'studio.css', 'i18n.js', 'studio.js', 'theme.js', 'appearance.js', 'fonts.js', 'fonts.css', 'font-catalog.js'):
        assert resource_path('ui', filename).is_file()
    from font_assets import check_font_assets
    check_font_assets()
    executable = ffmpeg_path()
    architecture = subprocess.check_output(['/usr/bin/file', executable], text=True)
    if 'arm64' not in architecture:
        raise SystemExit('FFmpeg must contain ARM64 code: ' + architecture)
    subprocess.run([executable, '-version'], check=True, capture_output=True)
    print(f'OK: native ARM64 Python, WebKit, {len(PLATFORMS)} icons, yt-dlp, curl-cffi and FFmpeg')


if __name__ == '__main__':
    main()
