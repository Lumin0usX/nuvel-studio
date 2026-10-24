"""Build on an Apple Silicon Mac; no cross-compilation from Windows."""
from pathlib import Path
import os
import plistlib
import subprocess
import sys
import shutil
import unicodedata
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
        str(project / 'nuvel_studio.py'), '--name', DISPLAY_NAME,
        '--windowed', '--onedir', '--target-arch', 'arm64',
        '--osx-bundle-identifier', 'local.nuvelstudio.app',
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
    # codesign identifies the main executable using macOS's decomposed filename
    # form. A composed Ü on disk can be sealed as nested code and then change
    # during signing. Rename through a distinct path so APFS stores the NFD form.
    executable_name = unicodedata.normalize('NFD', DISPLAY_NAME)
    executable = app / 'Contents/MacOS' / DISPLAY_NAME
    temporary_executable = executable.with_name('.studio-main-renaming')
    executable.rename(temporary_executable)
    temporary_executable.rename(executable.with_name(executable_name))
    info_path = app / 'Contents/Info.plist'
    with info_path.open('rb') as stream:
        info = plistlib.load(stream)
    info.update(CFBundleVersion=VERSION, CFBundleShortVersionString=VERSION,
                CFBundleName=DISPLAY_NAME, CFBundleDisplayName=DISPLAY_NAME,
                CFBundleExecutable=executable_name)
    with info_path.open('wb') as stream:
        plistlib.dump(info, stream)
    from update_installer import write_marker
    write_marker(app, 'macos-arm64')
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(project / name, app / 'Contents/Resources' / name)
    from macos_distribution import sign_bundle
    sign_bundle(app)
    if os.environ.get('CI'):
        from macos_distribution import verify_app, archive_bundle
        verify_app(app)
        archive_bundle(app, output / 'NUVEL-Studio-macOS-arm64.zip')
        print('Verified macOS release archive:', output / 'NUVEL-Studio-macOS-arm64.zip')
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
