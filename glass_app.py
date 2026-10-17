"""Liquid Glass desktop shell, with an authenticated local-browser fallback."""
import base64
import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from download_engine import PLATFORMS, platform_support, download_error
from platform_runtime import resource_path, ffmpeg_path, open_directory


class StudioAPI:
    def __init__(self):
        self._window = None
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._state = dict(phase='idle', percent=0, title='', detail='', speed='', eta='',
                           folder=str(Path.home() / 'Downloads'), history=[], error='')
        self._platforms = []
        self._version = ''
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        version, states = platform_support()
        platforms = []
        for name, key, slug, color in PLATFORMS:
            icon = resource_path('assets', 'platforms', slug + '.png')
            platforms.append(dict(name=name, slug=slug, color=color, status=states[name],
                                  icon='data:image/png;base64,' + base64.b64encode(icon.read_bytes()).decode()))
        with self._lock:
            self._platforms = platforms
            self._version = version

    def _update(self, **values):
        with self._lock:
            self._state.update(values)

    def snapshot(self):
        with self._lock:
            return dict(**copy.deepcopy(self._state), platforms=self._platforms, version=self._version)

    def choose_folder(self):
        if self._window is None:
            return dict(error='พิมพ์เส้นทางโฟลเดอร์ในช่องปลายทางได้เลย')
        import webview
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return dict(path=result[0] if result else '')

    def choose_cookies(self):
        if self._window is None:
            return dict(error='พิมพ์เส้นทางไฟล์ cookies.txt ในช่องได้เลย')
        import webview
        result = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                                 file_types=('Cookies (*.txt)',))
        return dict(path=result[0] if result else '')

    def open_folder(self, path=''):
        folder = Path(path or self._state['folder']).expanduser()
        if not folder.is_dir():
            return dict(error='ไม่พบโฟลเดอร์นี้')
        try:
            open_directory(folder)
            return dict(ok=True)
        except (OSError, subprocess.SubprocessError) as exc:
            return dict(error=str(exc))

    def start_download(self, options):
        if not isinstance(options, dict):
            return dict(error='ข้อมูลการดาวน์โหลดไม่ถูกต้อง')
        with self._lock:
            if self._state['phase'] in ('connecting', 'downloading', 'processing', 'cancelling'):
                return dict(error='มีงานกำลังทำอยู่ กรุณารอให้งานเสร็จก่อน')
            url = str(options.get('url', '')).strip()
            try:
                parsed = urlsplit(url)
                if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
                    raise ValueError()
            except ValueError:
                return dict(error='วางลิงก์คลิปที่ขึ้นต้นด้วย https://')
            folder = Path(str(options.get('folder', '')).strip()).expanduser()
            if not str(options.get('folder', '')).strip() or not folder.is_dir():
                return dict(error='เลือกโฟลเดอร์ปลายทางที่มีอยู่ก่อน')
            mode = options.get('mode', 'video')
            if mode not in ('video', 'audio'):
                return dict(error='เลือกรูปแบบ MP4 หรือ MP3')
            cookies = options.get('cookies', 'none')
            if cookies not in ('none', 'file', 'chrome', 'edge', 'firefox', 'brave', 'opera', 'vivaldi'):
                return dict(error='ตัวเลือก cookies ไม่ถูกต้อง')
            cookie_path = str(options.get('cookie_path', '')).strip()
            if cookies == 'file' and not Path(cookie_path).is_file():
                return dict(error='ไม่พบไฟล์ cookies.txt')
            self._cancel.clear()
            self._update(phase='connecting', percent=0, title=parsed.hostname, detail='กำลังอ่านข้อมูลคลิป',
                         speed='', eta='', error='', folder=str(folder.resolve()), mode=mode)
            threading.Thread(target=self._download, args=(url, str(folder.resolve()), mode, cookies, cookie_path), daemon=True).start()
            return dict(ok=True)

    def cancel_download(self):
        with self._lock:
            if self._state['phase'] in ('connecting', 'downloading', 'processing'):
                self._cancel.set()
                self._update(phase='cancelling', detail='กำลังหยุด · หากกำลังแปลงไฟล์จะรอให้ขั้นตอนนี้จบ')
        return dict(ok=True)

    def _download(self, url, folder, mode, cookies, cookie_path):
        try:
            import yt_dlp
            def check_cancel():
                if self._cancel.is_set():
                    raise RuntimeError('Download cancelled')
            def progress(data):
                check_cancel()
                title = data.get('info_dict', {}).get('title') or self._state['title']
                if data['status'] == 'downloading':
                    total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
                    percent = min(100, data.get('downloaded_bytes', 0) * 100 / total) if total else 0
                    speed, eta = data.get('speed'), data.get('eta')
                    self._update(phase='downloading', percent=percent, title=title, detail='กำลังดาวน์โหลด',
                                 speed=f'{speed / 1048576:.1f} MB/s' if speed else '',
                                 eta=f'{int(eta)//60}:{int(eta)%60:02d}' if eta is not None else '')
                elif data['status'] == 'finished':
                    self._update(phase='processing', title=title, detail='กำลังเตรียมไฟล์ให้พร้อม', speed='', eta='')
            def postprocess(data):
                check_cancel()
                self._update(phase='processing', detail='กำลังรวมภาพและเสียง หรือแปลงไฟล์', speed='', eta='')
            opts = dict(outtmpl=os.path.join(folder, '%(title).150B [%(extractor_key)s-%(id)s].%(ext)s'),
                        noplaylist=True, progress_hooks=[progress], postprocessor_hooks=[postprocess],
                        windowsfilenames=sys.platform == 'win32', quiet=True, ffmpeg_location=ffmpeg_path())
            if mode == 'audio':
                opts.update(format='bestaudio/best', postprocessors=[dict(key='FFmpegExtractAudio', preferredcodec='mp3', preferredquality='192')])
            else:
                opts.update(format='bestvideo*+bestaudio/best', merge_output_format='mp4',
                            postprocessors=[dict(key='FFmpegVideoConvertor', preferedformat='mp4')])
            if cookies not in ('none', 'file'):
                opts['cookiesfrombrowser'] = (cookies,)
            with yt_dlp.YoutubeDL(opts) as ydl:
                if cookies == 'file':
                    from yt_dlp.cookies import YoutubeDLCookieJar
                    jar = YoutubeDLCookieJar(cookie_path)
                    jar.load(ignore_discard=True, ignore_expires=True)
                    jar.filename = None
                    ydl.cookiejar = jar
                check_cancel()
                if ydl.download([url]):
                    raise RuntimeError('ดาวน์โหลดไม่สำเร็จ ลองใช้ลิงก์คลิปโดยตรง')
                check_cancel()
            with self._lock:
                history = [dict(title=self._state['title'], mode=mode, folder=folder,
                                time=time.strftime('%H:%M'))] + self._state['history'][:7]
                self._update(phase='done', percent=100, detail='บันทึกไฟล์เรียบร้อยแล้ว', history=history)
        except Exception as exc:
            if self._cancel.is_set():
                self._update(phase='cancelled', detail='หยุดแล้ว · ไฟล์บางส่วนอาจยังอยู่ในโฟลเดอร์', speed='', eta='')
            else:
                self._update(phase='error', detail='ดาวน์โหลดไม่สำเร็จ', error=download_error(exc), speed='', eta='')


def _serve(api):
    """Fallback has no external listening port and requires a random session token."""
    token = secrets.token_urlsafe(32)
    ui_root = resource_path('ui')
    allowed = {'snapshot', 'start_download', 'cancel_download', 'open_folder', 'choose_folder', 'choose_cookies'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def _reply(self, code, data, content_type='application/json'):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                return self._reply(403, {})
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/studio.css': ('studio.css', 'text/css'), '/studio.js': ('studio.js', 'text/javascript')}
            entry = files.get(urlsplit(self.path).path)
            if not entry:
                return self._reply(404, {})
            return self._reply(200, (ui_root / entry[0]).read_bytes(), entry[1])
        def do_POST(self):
            if self.headers.get('X-Studio-Token') != token or self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                return self._reply(403, {})
            method = self.path.removeprefix('/api/')
            if method not in allowed:
                return self._reply(404, {})
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 <= length <= 32768:
                    raise ValueError()
                args = json.loads(self.rfile.read(length) or b'[]')
                if not isinstance(args, list):
                    raise ValueError()
                result = getattr(api, method)(*args)
                self._reply(200, result)
            except Exception:
                self._reply(400, dict(error='คำขอไม่ถูกต้อง'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}/#{token}'


def main():
    api = StudioAPI()
    try:
        import webview
    except ImportError:
        if '--self-test' in sys.argv:
            raise SystemExit('pywebview is required to test the packaged app')
        server, url = _serve(api)
        print('Liquid Glass UI is running locally. Close this terminal to stop it.')
        candidates = []
        if sys.platform == 'win32':
            for base in (os.environ.get('PROGRAMFILES', ''), os.environ.get('PROGRAMFILES(X86)', '')):
                if base:
                    candidates.extend([Path(base) / 'Microsoft/Edge/Application/msedge.exe', Path(base) / 'Google/Chrome/Application/chrome.exe'])
        elif sys.platform == 'darwin':
            candidates.append(Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'))
        browser = next((path for path in candidates if path.is_file()), None)
        if browser:
            subprocess.Popen([str(browser), '--app=' + url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif not webbrowser.open(url):
            print('Open this local address:', url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()
        return
    window = webview.create_window('YTDL Studio', str(resource_path('ui', 'index.html')),
                                   js_api=api, width=1240, height=860, min_size=(780, 640),
                                   background_color='#e5e9f3', vibrancy=sys.platform == 'darwin')
    api._window = window
    def closing():
        if api.snapshot()['phase'] in ('connecting', 'downloading', 'processing', 'cancelling'):
            return window.create_confirmation_dialog('กำลังดาวน์โหลด', 'ปิดแอปและหยุดงานนี้หรือไม่?')
    window.events.closing += closing
    if '--self-test' in sys.argv:
        subprocess.run([ffmpeg_path(), '-version'], check=True, capture_output=True)
        tested = threading.Event()
        def smoke_test():
            try:
                ok = window.evaluate_js('Boolean(window.studioReady && document.querySelector("#download"))')
                if not ok:
                    os._exit(1)
                tested.set()
            finally:
                window.destroy()
        def timeout():
            if not tested.wait(30):
                os._exit(1)
        window.events.loaded += smoke_test
        threading.Thread(target=timeout, daemon=True).start()
    webview.start(gui='edgechromium' if sys.platform == 'win32' else None)


if __name__ == '__main__':
    main()
