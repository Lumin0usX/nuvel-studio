"""Build on an Apple Silicon Mac; no cross-compilation from Windows."""
from pathlib import Path
import os
import plistlib
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
    from app_version import VERSION, DISPLAY_NAME
    from build_gallery_tool import build_tool
    gallery, gallery_source = build_tool(output)
    PyInstaller.__main__.run([
        str(project / 'ytdl_studio.py'), '--name', DISPLAY_NAME,
        '--windowed', '--onedir', '--target-arch', 'arm64',
        '--osx-bundle-identifier', 'local.ytdlstudio.app',
        '--icon', str(project / 'assets/branding/app-icon.icns'),
        '--distpath', str(output), '--workpath', str(output / 'work'),
        '--specpath', str(output),
        '--add-data', str(project / 'assets') + ':assets',
        '--add-data', str(project / 'ui') + ':ui',
        '--add-binary', str(bundled_ffmpeg) + ':bin',
        '--add-binary', str(gallery) + ':bin',
        '--add-data', str(gallery_source) + ':third-party/gallery-dl',
        '--collect-all', 'yt_dlp', '--collect-all', 'yt_dlp_ejs',
        '--collect-all', 'curl_cffi', '--collect-all', 'certifi',
        '--collect-all', 'webview', '--hidden-import', 'webview.platforms.cocoa',
        '--exclude-module', 'gallery_dl',  # gallery-dl is a separate external CLI
        '--collect-all', 'PIL',
        '--copy-metadata', 'yt-dlp',
    ])
    app = output / (DISPLAY_NAME + '.app')
    # Old updaters locate this fixed executable path. Keep an alias while the
    # real Mach-O executable and process name use the new brand.
    (app / 'Contents/MacOS/YTDL Studio').symlink_to(DISPLAY_NAME)
    info_path = app / 'Contents/Info.plist'
    with info_path.open('rb') as stream:
        info = plistlib.load(stream)
    info.update(CFBundleVersion=VERSION, CFBundleShortVersionString=VERSION,
                CFBundleName=DISPLAY_NAME, CFBundleDisplayName=DISPLAY_NAME)
    with info_path.open('wb') as stream:
        plistlib.dump(info, stream)
    from update_installer import write_marker
    write_marker(app, 'macos-arm64')
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(project / name, app / 'Contents/Resources' / name)
    subprocess.run(['/usr/bin/codesign', '--force', '--deep', '--sign', '-', str(app)], check=True, capture_output=True)
    if os.environ.get('CI'):
        from macos_distribution import verify_app, archive_bundle
        verify_app(app)
        archive_bundle(app, output / 'YTDL-Studio-macOS-arm64.zip')
        print('Verified macOS release archive:', output / 'YTDL-Studio-macOS-arm64.zip')
        return
    from macos_distribution import publish_build
    installed = publish_build(project, app)
    print('Build complete. Verified through macOS LaunchServices:', installed)
    print('Open ' + installed.name + ' in the project folder. No Terminal is needed.')
    if not os.environ.get('CI'):
        subprocess.run(['/usr/bin/open', '-R', str(installed)], check=False)
    print('This local build is ad-hoc signed, not notarized for public distribution.')


if __name__ == '__main__':
    main()
