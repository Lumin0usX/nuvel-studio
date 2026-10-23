"""Package gallery-dl as its own CLI, isolated from the proprietary GUI process."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import subprocess
import sys


def verify_tool(executable):
    """Keep native loader diagnostics visible when the isolated engine cannot start."""
    result = subprocess.run([str(executable), '--config-ignore', '--list-modules'], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=60,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode or not result.stdout.strip():
        details = result.stderr.strip() or result.stdout.strip() or 'No extractor output was returned.'
        raise RuntimeError('The packaged image-post engine failed its CLI test '
                           f'(exit code {result.returncode}):\n{details}')


def build_tool(output):
    import gallery_dl
    import PyInstaller.__main__
    source = Path(gallery_dl.__file__).resolve().parent
    work = Path(output) / 'gallery-build'
    work.mkdir(parents=True)
    entry = work / 'gallery_cli.py'
    entry.write_text('import gallery_dl\nif __name__ == "__main__":\n    raise SystemExit(gallery_dl.main())\n', encoding='utf-8')
    args = [str(entry), '--name', 'gallery-dl', '--console', '--onefile', '--noupx',
            '--distpath', str(work / 'dist'), '--workpath', str(work / 'work'), '--specpath', str(work),
            '--collect-all', 'gallery_dl', '--collect-all', 'certifi', '--collect-all', 'requests',
            '--copy-metadata', 'gallery-dl']
    if sys.platform == 'darwin':
        args.extend(['--target-arch', 'arm64'])
    PyInstaller.__main__.run(args)
    executable = work / 'dist' / ('gallery-dl.exe' if sys.platform == 'win32' else 'gallery-dl')
    verify_tool(executable)
    notices = work / 'gallery-dl-source'
    shutil.copytree(source, notices / 'gallery_dl', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    metadata = distribution('gallery-dl')
    for item in metadata.files:
        if str(item).endswith('/licenses/LICENSE'):
            shutil.copy2(metadata.locate_file(item), notices / 'LICENSE')
    (notices / 'BUILD.txt').write_text('gallery-dl ' + metadata.version + '\n'
        'Upstream: https://github.com/mikf/gallery-dl\n'
        'Separate CLI built with PyInstaller --console --onefile --collect-all gallery_dl '
        '--collect-all certifi --collect-all requests --copy-metadata gallery-dl\n'
        'Entry: import gallery_dl; gallery_dl.main()\n', encoding='utf-8')
    return executable, notices
