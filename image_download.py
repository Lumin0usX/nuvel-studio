# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Image transfers and an isolated gallery-dl CLI adapter (never imported here)."""
from collections import deque
import importlib.util
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
from image_quality import resize_image
from download_engine import IMAGE_MODULES, PLATFORM_DOMAINS
from output_names import validate_output_name, save_named_file

EXTENSIONS = ('jpg', 'jpeg', 'png', 'webp', 'gif', 'avif', 'heic', 'heif', 'bmp', 'tif', 'tiff', 'jxl', 'ico')
MAX_IMAGE_BYTES = 256 * 1024 * 1024
MARKER = 'STUDIO_IMAGE_SAVED:'
CREATE_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def gallery_command():
    if getattr(sys, 'frozen', False):
        from platform_runtime import resource_path
        bundled = resource_path('bin', 'gallery-dl.exe' if sys.platform == 'win32' else 'gallery-dl')
        if bundled.is_file():
            return [str(bundled)]
    if not getattr(sys, 'frozen', False) and importlib.util.find_spec('gallery_dl'):
        return [sys.executable, '-m', 'gallery_dl']
    # A local Windows build keeps its external CLI in the managed build environment.
    # Portable distributions still use an independently installed gallery-dl CLI.
    if getattr(sys, 'frozen', False) and sys.platform == 'win32':
        app_folder = Path(sys.executable).resolve().parent
        if app_folder.name == 'nuvel-windows':
            managed = app_folder.parent / '.venv-windows-build/Scripts/gallery-dl.exe'
            if managed.is_file():
                return [str(managed)]
    executable = shutil.which('gallery-dl')
    candidates = [Path(sysconfig.get_path('scripts')) / ('gallery-dl.exe' if sys.platform == 'win32' else 'gallery-dl'),
                  Path.home() / '.local/bin/gallery-dl', Path('/opt/homebrew/bin/gallery-dl'),
                  Path('/usr/local/bin/gallery-dl'),
                  Path.home() / 'Library/Python/3.12/bin/gallery-dl',
                  Path.home() / 'Library/Python/3.13/bin/gallery-dl']
    if executable:
        return [executable]
    for path in candidates:
        if path.is_file():
            return [str(path)]
    return None


def image_support():
    """Report locally installed extractor modules, not live-site availability."""
    command = gallery_command()
    if not command:
        return dict(available=False, modules=[])
    try:
        result = subprocess.run(command + ['--config-ignore', '--list-modules'],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=15, creationflags=CREATE_FLAGS)
        if result.returncode:
            return dict(available=False, modules=[])
        return dict(available=True, modules=result.stdout.split())
    except (OSError, subprocess.SubprocessError):
        return dict(available=False, modules=[])


def check_cancel(cancel):
    if cancel.is_set():
        raise RuntimeError('หยุดดาวน์โหลดภาพแล้ว')


def image_extension(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'webp'
    if data[4:8] == b'ftyp':
        brands = data[8:40]
        if b'avif' in brands or b'avis' in brands:
            return 'avif'
        if any(brand in brands for brand in (b'heic', b'heix', b'mif1', b'hevc')):
            return 'heic'
    if data.startswith((b'II*\x00', b'MM\x00*')):
        return 'tiff'
    if data.startswith(b'BM'):
        return 'bmp'
    if data.startswith((b'\xff\x0a', b'\x00\x00\x00\x0cJXL \r\n\x87\n')):
        return 'jxl'
    if data.startswith(b'\x00\x00\x01\x00'):
        return 'ico'
    return None


def is_direct_url(url):
    return Path(unquote(urlsplit(url).path)).suffix.lower().lstrip('.') in EXTENSIONS


def _safe_stem(url):
    name = unquote(urlsplit(url).path.rsplit('/', 1)[-1])
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', Path(name).stem)[:100].strip(' .')
    if not stem or re.fullmatch(r'(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])', stem.split('.')[0]):
        stem = 'image'
    return stem


def download_direct(url, folder, cancel, update, cookies='none', cookie_path='', output_name=''):
    """Return None for HTML/non-images; never save an HTML page as an image."""
    check_cancel(cancel)
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 NUVEL-Studio', 'Accept': 'image/*,*/*;q=0.5'})
    # Cookie handling is explicitly opt-in. yt-dlp's jar is read in memory only.
    if cookies != 'none':
        from yt_dlp.cookies import YoutubeDLCookieJar, extract_cookies_from_browser
        if cookies == 'file':
            jar = YoutubeDLCookieJar(cookie_path)
            jar.load(ignore_discard=True, ignore_expires=True)
            jar.filename = None
        else:
            jar = extract_cookies_from_browser(cookies)
        from urllib.request import build_opener, HTTPCookieProcessor
        open_request = build_opener(HTTPCookieProcessor(jar)).open
    else:
        open_request = urlopen
    with open_request(request, timeout=20) as response:
        check_cancel(cancel)
        first = response.read(65536)
        extension = image_extension(first)
        if not extension:
            return None
        try:
            total = int(response.headers.get('Content-Length', 0))
        except (ValueError, TypeError):
            total = 0
        if total > MAX_IMAGE_BYTES:
            raise RuntimeError('ไฟล์ภาพใหญ่เกิน 256 MB')
        started = time.monotonic()
        received = 0
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=folder, prefix='.studio-image-', suffix='.part', delete=False) as output:
                temporary = Path(output.name)
                block = first
                while block:
                    check_cancel(cancel)
                    received += len(block)
                    if received > MAX_IMAGE_BYTES:
                        raise RuntimeError('ไฟล์ภาพใหญ่เกิน 256 MB')
                    output.write(block)
                    elapsed = max(time.monotonic() - started, .01)
                    update(phase='downloading', title=f'{output_name or _safe_stem(url)}.{extension}',
                           detail='กำลังดาวน์โหลดภาพต้นฉบับ', percent=min(99, received * 100 / total) if total else 0,
                           progress_known=total > 0, speed=f'{received / elapsed / 1048576:.1f} MB/s', eta='')
                    block = response.read(65536)
            check_cancel(cancel)
            if total and received != total:
                raise RuntimeError('ดาวน์โหลดภาพไม่ครบ ลองใหม่อีกครั้ง')
            stem = output_name or _safe_stem(url)
            for number in range(10000):
                name = f'{stem}{" (" + str(number) + ")" if number else ""}.{extension}'
                target = Path(folder) / name
                try:
                    destination = target.open('xb')
                except FileExistsError:
                    continue
                try:
                    with destination, temporary.open('rb') as source:
                        shutil.copyfileobj(source, destination)
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
                return dict(count=1, folder=str(folder), title=name)
            raise RuntimeError('มีชื่อไฟล์ซ้ำมากเกินไป ลองเลือกโฟลเดอร์ใหม่')
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def gallery_args(command, url, folder, cookies, cookie_path):
    args = command + ['--config-ignore', '--no-input', '--no-colors', '--quiet',
                      '--http-timeout', '20', '--retries', '2', '--windows-filenames',
                      '-D', str(folder), '--filter', f'extension.lower() in {EXTENSIONS!r}',
                      '--Print', 'after:' + MARKER + '{_path}']
    if cookies == 'file':
        args.extend(['--cookies', cookie_path])
    elif cookies != 'none':
        args.extend(['--cookies-from-browser', cookies])
    return args + ['--', url]


def download_gallery(url, folder, cancel, update, cookies='none', cookie_path='', quality='best', output_name=''):
    command = gallery_command()
    if not command:
        raise RuntimeError('โหลดภาพจากโพสต์ต้องติดตั้ง gallery-dl: รันตัวติดตั้งของแอปอีกครั้ง '
                           '(Mac .app: ติดตั้ง gallery-dl แยกด้วย pipx install gallery-dl หรือ brew install gallery-dl)')
    check_cancel(cancel)
    # Isolate extractor paths and collisions until files are ready, then place
    # the completed images directly in the selected destination.
    job_folder = Path(tempfile.mkdtemp(dir=folder, prefix='.studio-images-'))
    saved_paths, targets = [], []
    try:
        _run_gallery(command, url, folder, job_folder, cancel, update, cookies, cookie_path, quality, saved_paths)
    finally:
        # Keep completed images even when a later image fails or is cancelled.
        # A failed copy leaves its staged original available for recovery.
        # Cancellation can leave completion messages unread; gallery-dl's
        # unfinished transfers still have .part extensions and are excluded.
        known = {path.resolve() for path in saved_paths}
        for path in sorted(job_folder.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.suffix.lower().lstrip('.') in EXTENSIONS and \
                    path.resolve().is_relative_to(job_folder.resolve()) and path.resolve() not in known:
                saved_paths.append(path)
                known.add(path.resolve())
        for number, path in enumerate(saved_paths, 1):
            stem = path.stem
            if output_name:
                stem = output_name + (f'-{number:03d}' if len(saved_paths) > 1 else '')
            target = save_named_file(path, folder, stem)
            targets.append(target)
            path.unlink()
        shutil.rmtree(job_folder)
    title = f'ภาพจาก {urlsplit(url).hostname} ({len(targets)} ภาพ)'
    if output_name:
        title = targets[0].name if len(targets) == 1 else output_name
    return dict(count=len(targets), folder=str(folder), title=title)


def _run_gallery(command, url, folder, job_folder, cancel, update, cookies, cookie_path, quality, saved_paths):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    process = subprocess.Popen(gallery_args(command, url, job_folder, cookies, cookie_path),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               text=True, encoding='utf-8', errors='replace', env=env,
                               creationflags=CREATE_FLAGS)
    events = queue.Queue(maxsize=256)
    stop_reader = threading.Event()
    def read_output():
        try:
            for line in process.stdout:
                while not stop_reader.is_set():
                    try:
                        events.put(line.rstrip(), timeout=.1)
                        break
                    except queue.Full:
                        pass
                if stop_reader.is_set():
                    break
        finally:
            process.stdout.close()
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    saved = set()
    errors = deque(maxlen=8)
    update(phase='downloading', progress_known=False, percent=0, speed='', eta='',
           folder=str(folder), detail='กำลังค้นหาและดาวน์โหลดภาพจากโพสต์')
    try:
        while process.poll() is None or reader.is_alive() or not events.empty():
            check_cancel(cancel)
            try:
                line = events.get(timeout=.1)
            except queue.Empty:
                continue
            if line.startswith(MARKER):
                path = Path(line[len(MARKER):])
                if path.is_file() and path.resolve().is_relative_to(job_folder.resolve()) and path.suffix.lower().lstrip('.') in EXTENSIONS:
                    if str(path.resolve()) not in saved:
                        saved_paths.append(path)
                        resize_image(path, quality, cancel)
                    saved.add(str(path.resolve()))
                    update(title=f'ภาพจาก {urlsplit(url).hostname}', image_count=len(saved),
                           detail=f'บันทึกแล้ว {len(saved)} ภาพ · กำลังตรวจสอบภาพถัดไป')
            elif line:
                errors.append(line[-1000:])
        check_cancel(cancel)
        if process.returncode:
            raise RuntimeError(f'โหลดได้ {len(saved)} ภาพ แต่งานยังไม่สมบูรณ์\n' + '\n'.join(errors))
        if not saved:
            raise RuntimeError('ไม่พบภาพในลิงก์นี้ ลองใช้ลิงก์โพสต์/อัลบั้มภาพโดยตรง '
                               'หรือเลือกบัญชีที่เปิดโพสต์นี้ได้')
    finally:
        stop_reader.set()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        reader.join(timeout=1)


def download_images(url, folder, cancel, update, cookies='none', cookie_path='', quality='best', output_name=''):
    output_name = validate_output_name(output_name)
    # Known file links use streaming without needing the optional gallery CLI.
    # Extensionless links are probed only on hosts without gallery support.
    host = urlsplit(url).hostname.lower()
    gallery_hosts = tuple(domain for slug in IMAGE_MODULES for domain in PLATFORM_DOMAINS[slug])
    direct = is_direct_url(url)
    if direct or not any(host == domain or host.endswith('.' + domain) for domain in gallery_hosts):
        result = download_direct(url, folder, cancel, update, cookies, cookie_path, output_name=output_name)
        if result:
            if quality != 'best':
                update(phase='processing', progress_known=False, speed='', eta='', detail='กำลังปรับขนาดภาพตามที่เลือก')
                resize_image(Path(result['folder']) / result['title'], quality, cancel)
            return result
        if direct:
            raise RuntimeError('ลิงก์นี้ไม่ได้ส่งไฟล์ภาพที่รองรับ อาจเป็นหน้าเข้าสู่ระบบหรือไฟล์ชนิดอื่น')
    return download_gallery(url, folder, cancel, update, cookies, cookie_path, quality=quality, output_name=output_name)
