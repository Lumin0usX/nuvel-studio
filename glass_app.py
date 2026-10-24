"""Desktop shell, with an authenticated local-browser fallback."""
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

from download_engine import PLATFORMS, PLATFORM_DOMAINS, platform_modes, platform_support, download_error
from platform_runtime import resource_path, ffmpeg_path, open_directory
from image_download import download_images, image_support
from media_quality import validate_quality, quality_label, media_options, add_video_postprocessor
from ui_preferences import load_preferences, save_preferences
from app_updates import AppUpdates
from app_version import DISPLAY_NAME


class StudioAPI:
    def __init__(self):
        self._window = None
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._updates = AppUpdates()
        self._uninstall_plan = None
        self._preferences = load_preferences()
        self._state = dict(phase='idle', percent=0, title='', detail='', speed='', eta='',
                           folder=self._preferences.get('folder', str(Path.home() / 'Downloads')), history=[], error='',
                           progress_known=True, image_count=0)
        self._platforms = []
        self._version = ''
        self._image_engine = dict(available=False, modules=[])
        self._catalog_revision = secrets.token_hex(8)
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        version, states = platform_support()
        engine = image_support()
        platforms = []
        for name, key, slug, color in PLATFORMS:
            icon = resource_path('assets', 'platforms', slug + '.png')
            platforms.append(dict(name=name, slug=slug, color=color, status=states[name],
                                  domains=PLATFORM_DOMAINS[slug], **platform_modes(slug, states[name], engine),
                                  icon='data:image/png;base64,' + base64.b64encode(icon.read_bytes()).decode()))
        with self._lock:
            self._platforms = platforms
            self._version = version
            self._image_engine = engine
            self._catalog_revision = secrets.token_hex(8)

    def _update(self, **values):
        with self._lock:
            self._state.update(values)

    def snapshot(self, catalog_revision=None):
        with self._lock:
            result = dict(**copy.deepcopy(self._state), catalog_revision=self._catalog_revision,
                          preferences=copy.deepcopy(self._preferences), app_update=self._updates.snapshot())
            # Progress changes frequently; the engine catalog and its 50 icons do not.
            # No argument preserves the complete snapshot for existing clients/tests.
            if catalog_revision != self._catalog_revision:
                result.update(platforms=copy.deepcopy(self._platforms), version=self._version,
                              image_engine=copy.deepcopy(self._image_engine))
            return result

    def check_app_update(self):
        return self._updates.check()

    def connect_updates(self, token='', forget=False):
        return self._updates.connect(token, forget)

    def download_app_update(self):
        return self._updates.download()

    def cancel_app_update(self):
        self._updates.cancel.set()
        return dict(ok=True)

    def install_app_update(self):
        with self._lock:
            if self._state['phase'] in ('connecting', 'downloading', 'processing', 'cancelling'):
                return dict(error='download_active')
            if self._window is None:
                return dict(error='native_required')
            result = self._updates.request_install()
            if not result.get('error'):
                self._window.destroy()
            return result

    def open_update_access(self):
        webbrowser.open('https://github.com/settings/personal-access-tokens/new')
        return dict(ok=True)

    def uninstall_app(self, remove_settings=False):
        with self._lock:
            if self._window is None:
                return dict(error='native_required')
            if self._state['phase'] in ('connecting', 'downloading', 'processing', 'cancelling'):
                return dict(error='download_active')
            if self._updates.snapshot()['phase'] in ('checking', 'downloading', 'verifying', 'installing') or self._uninstall_plan:
                return dict(error='update_busy')
            try:
                from app_uninstall import find_target, platform_key, stage_uninstall
                self._uninstall_plan = stage_uninstall(find_target(), platform_key(), remove_settings,
                                                     [self._state['folder']])
            except Exception as exc:
                return dict(error=str(exc))
            self._window.destroy()
            return dict(ok=True)

    def save_preferences(self, values):
        try:
            with self._lock:
                self._preferences = save_preferences(values)
            return dict(ok=True)
        except (OSError, ValueError, TypeError) as exc:
            return dict(error=str(exc))

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

    def remove_history(self, record_id):
        """Remove only an in-memory record. Never touch downloaded files."""
        if not isinstance(record_id, str) or not record_id:
            return dict(error='ไม่พบรหัสประวัติ')
        with self._lock:
            self._state['history'] = [item for item in self._state['history'] if item.get('id') != record_id]
        return dict(ok=True)

    def analyze_url(self, options):
        """Read real metadata on a request thread; never start a transfer."""
        if not isinstance(options, dict):
            return dict(error='ข้อมูลลิงก์ไม่ถูกต้อง')
        url = str(options.get('url', '')).strip()
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValueError()
        except ValueError:
            return dict(error='ใช้ลิงก์แบบเต็มที่ขึ้นต้นด้วย https://')
        if options.get('mode') == 'image':
            return dict(unavailable=True, detail='โหมดภาพอ่านโพสต์หรืออัลบั้มเมื่อเริ่มดาวน์โหลด คุณภาพต้นฉบับจะเก็บไฟล์ตามที่ต้นทางส่งให้')
        cookies = options.get('cookies', 'none')
        if cookies not in ('none', 'file', 'chrome', 'edge', 'firefox', 'brave', 'opera', 'vivaldi'):
            return dict(error='ตัวเลือก cookies ไม่ถูกต้อง')
        try:
            import yt_dlp
            opts = dict(quiet=True, no_warnings=True, noplaylist=True, skip_download=True,
                        socket_timeout=12, retries=0, extractor_retries=0, cachedir=False,
                        playlist_items='1')
            if cookies not in ('none', 'file'):
                opts['cookiesfrombrowser'] = (cookies,)
            with yt_dlp.YoutubeDL(opts) as ydl:
                if cookies == 'file':
                    from yt_dlp.cookies import YoutubeDLCookieJar
                    jar = YoutubeDLCookieJar(str(options.get('cookie_path', '')))
                    jar.load(ignore_discard=True, ignore_expires=True)
                    jar.filename = None
                    ydl.cookiejar = jar
                info = ydl.extract_info(url, download=False)
            if not info or info.get('_type') in ('playlist', 'multi_video'):
                return dict(unavailable=True, detail='ใช้ลิงก์คลิปโดยตรงเพื่อดูตัวอย่าง · คุณยังลองดาวน์โหลดลิงก์นี้ได้')
            formats = info.get('formats') or []
            heights = sorted({int(f['height']) for f in formats if isinstance(f.get('height'), (int, float)) and f['height'] > 0})
            extensions = sorted({str(f['ext']) for f in formats if f.get('ext')})
            return dict(title=info.get('title') or '', thumbnail=info.get('thumbnail') or '',
                        source=info.get('extractor_key') or parsed.hostname,
                        duration=info.get('duration'), resolutions=heights, formats=extensions)
        except Exception as exc:
            return dict(error=download_error(exc))

    def start_download(self, options):
        if not isinstance(options, dict):
            return dict(error='ข้อมูลการดาวน์โหลดไม่ถูกต้อง')
        with self._lock:
            if self._updates.snapshot()['phase'] == 'installing':
                return dict(error='update_busy')
            if self._state['phase'] in ('connecting', 'downloading', 'processing', 'cancelling'):
                return dict(error='มีงานกำลังทำอยู่ กรุณารอให้งานเสร็จก่อน')
            url = str(options.get('url', '')).strip()
            try:
                parsed = urlsplit(url)
                if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
                    raise ValueError()
            except ValueError:
                return dict(error='วางลิงก์ที่ขึ้นต้นด้วย https://')
            folder = Path(str(options.get('folder', '')).strip()).expanduser()
            if not str(options.get('folder', '')).strip() or not folder.is_dir():
                return dict(error='เลือกโฟลเดอร์ปลายทางที่มีอยู่ก่อน')
            mode = options.get('mode', 'video')
            if mode not in ('video', 'audio', 'image'):
                return dict(error='เลือกวิดีโอ เสียง หรือภาพ')
            try:
                quality = validate_quality(mode, options.get('quality', 'best'))
            except ValueError as exc:
                return dict(error=str(exc))
            cookies = options.get('cookies', 'none')
            if cookies not in ('none', 'file', 'chrome', 'edge', 'firefox', 'brave', 'opera', 'vivaldi'):
                return dict(error='ตัวเลือก cookies ไม่ถูกต้อง')
            cookie_path = str(options.get('cookie_path', '')).strip()
            if cookies == 'file' and not Path(cookie_path).is_file():
                return dict(error='ไม่พบไฟล์ cookies.txt')
            self._cancel.clear()
            self._update(phase='connecting', percent=0, title=parsed.hostname, detail='กำลังอ่านข้อมูล',
                         progress_known=mode != 'image', image_count=0,
                         speed='', eta='', error='', folder=str(folder.resolve()), mode=mode,
                         quality=quality, quality_label=quality_label(mode, quality), source=parsed.hostname,
                         url=url, total_bytes=0, downloaded_bytes=0, history_id='')
            threading.Thread(target=self._download, args=(url, str(folder.resolve()), mode, cookies, cookie_path, quality), daemon=True).start()
            return dict(ok=True)

    def cancel_download(self):
        with self._lock:
            if self._state['phase'] in ('connecting', 'downloading', 'processing'):
                self._cancel.set()
                self._update(phase='cancelling', detail='กำลังหยุดดาวน์โหลดภาพ' if self._state.get('mode') == 'image'
                             else 'กำลังหยุด · หากกำลังแปลงไฟล์จะรอให้ขั้นตอนนี้จบ')
        return dict(ok=True)

    def _download(self, url, folder, mode, cookies, cookie_path, quality='best'):
        if mode == 'image':
            self._download_images(url, folder, cookies, cookie_path, quality)
            return
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
                                 progress_known=bool(total), total_bytes=total, downloaded_bytes=data.get('downloaded_bytes', 0),
                                 speed=f'{speed / 1048576:.1f} MB/s' if speed else '',
                                 eta=f'{int(eta)//60}:{int(eta)%60:02d}' if eta is not None else '')
                elif data['status'] == 'finished':
                    self._update(phase='processing', title=title, detail='กำลังเตรียมไฟล์ให้พร้อม', speed='', eta='')
            def postprocess(data):
                check_cancel()
                self._update(phase='processing', detail='กำลังรวมภาพและเสียง หรือแปลงไฟล์', speed='', eta='')
            # Audio extraction may remove its input after conversion. Never let
            # that intermediate file reuse an earlier video download's name.
            media_suffix = ' [audio]' if mode == 'audio' else ''
            opts = dict(outtmpl=os.path.join(folder, '%(title).150B [%(extractor_key)s-%(id)s]' + media_suffix + '.%(ext)s'),
                        noplaylist=True, progress_hooks=[progress], postprocessor_hooks=[postprocess],
                        windowsfilenames=sys.platform == 'win32', quiet=True, ffmpeg_location=ffmpeg_path())
            opts.update(media_options(mode, quality))
            if cookies not in ('none', 'file'):
                opts['cookiesfrombrowser'] = (cookies,)
            with yt_dlp.YoutubeDL(opts) as ydl:
                add_video_postprocessor(ydl, mode, check_cancel)
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
                history = [dict(id=secrets.token_hex(8), title=self._state['title'], mode=mode, folder=folder,
                                source=self._state.get('source', ''), status='done',
                                quality=quality, quality_label=quality_label(mode, quality),
                                time=time.strftime('%H:%M'))] + self._state['history'][:7]
                self._update(phase='done', percent=100, detail='บันทึกไฟล์เรียบร้อยแล้ว', history=history, history_id=history[0]['id'])
        except Exception as exc:
            if self._cancel.is_set():
                self._update(phase='cancelled', detail='หยุดแล้ว · ไฟล์บางส่วนอาจยังอยู่ในโฟลเดอร์', speed='', eta='')
            else:
                self._update(phase='error', detail='ดาวน์โหลดไม่สำเร็จ', error=download_error(exc), speed='', eta='')

    def _download_images(self, url, folder, cookies, cookie_path, quality='best'):
        try:
            result = download_images(url, folder, self._cancel, self._update, cookies, cookie_path, quality=quality)
            if self._cancel.is_set():
                raise RuntimeError('หยุดแล้ว')
            with self._lock:
                history = [dict(id=secrets.token_hex(8), title=result['title'], mode='image', folder=result['folder'],
                                source=self._state.get('source', ''), status='done',
                                count=result['count'], quality=quality, quality_label=quality_label('image', quality),
                                time=time.strftime('%H:%M'))] + self._state['history'][:7]
                self._update(phase='done', percent=100, progress_known=True, title=result['title'],
                             folder=result['folder'], image_count=result['count'], speed='', eta='',
                             detail=f"บันทึกแล้ว {result['count']} ภาพ", history=history, history_id=history[0]['id'])
        except Exception as exc:
            if self._cancel.is_set():
                self._update(phase='cancelled', detail='หยุดแล้ว · ภาพที่โหลดเสร็จยังอยู่ในโฟลเดอร์', speed='', eta='')
            else:
                self._update(phase='error', detail='ดาวน์โหลดภาพไม่สำเร็จ', error=str(exc), speed='', eta='')


def _serve(api):
    """Fallback has no external listening port and requires a random session token."""
    token = secrets.token_urlsafe(32)
    ui_root = resource_path('ui')
    from font_assets import font_catalog
    from branding import UI_BRAND_ASSETS
    font_files = {face['file'] for group in font_catalog()['languages'].values()
                  for font in group['fonts'] for face in font['files']}
    allowed = {'snapshot', 'start_download', 'cancel_download', 'open_folder', 'choose_folder', 'choose_cookies', 'analyze_url', 'remove_history', 'save_preferences',
               'check_app_update', 'connect_updates', 'download_app_update', 'cancel_app_update', 'install_app_update', 'open_update_access'}
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
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/studio.css': ('studio.css', 'text/css'), '/studio.js': ('studio.js', 'text/javascript'), '/i18n.js': ('i18n.js', 'text/javascript; charset=utf-8'), '/theme.js': ('theme.js', 'text/javascript; charset=utf-8')}
            files.update({'/fonts.js': ('fonts.js', 'text/javascript; charset=utf-8'),
                          '/appearance.js': ('appearance.js', 'text/javascript; charset=utf-8'),
                          '/font-catalog.js': ('font-catalog.js', 'text/javascript; charset=utf-8'),
                          '/fonts.css': ('fonts.css', 'text/css; charset=utf-8')})
            files.update({'/brand/' + name: ('brand/' + name, mime)
                          for name, mime in UI_BRAND_ASSETS.items()})
            path = urlsplit(self.path).path
            if path.startswith('/fonts/') and path.removeprefix('/fonts/') in font_files:
                return self._reply(200, (ui_root / path.lstrip('/')).read_bytes(), 'font/ttf')
            entry = files.get(path)
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


def main(native_only=False):
    try:
        import webview
    except ImportError:
        if getattr(sys, 'frozen', False):
            raise RuntimeError('The application bundle is incomplete. Reinstall ' + DISPLAY_NAME + '.')
        if native_only:
            raise RuntimeError('The windowless launcher requires pywebview. Run ' +
                               ('install_macos.command' if sys.platform == 'darwin' else 'install.bat'))
        if '--self-test' in sys.argv:
            raise SystemExit('pywebview is required to test the packaged app')
        api = StudioAPI()
        server, url = _serve(api)
        print(DISPLAY_NAME + ' is running locally. Close this terminal to stop it.')
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
    api = StudioAPI()
    window = webview.create_window(DISPLAY_NAME, str(resource_path('ui', 'index.html')),
                                   js_api=api, width=1240, height=860, min_size=(780, 640),
                                   background_color='#f2f3f6' if api._preferences.get('theme') == 'light' else '#0d1016', vibrancy=False)
    api._window = window
    def closing():
        if api.snapshot()['phase'] in ('connecting', 'downloading', 'processing', 'cancelling'):
            labels = {'th': ('กำลังดาวน์โหลด', 'ปิดแอปและหยุดงานนี้หรือไม่?'),
                      'en': ('Download in progress', 'Close the app and stop this download?'),
                      'ja': ('ダウンロード中', 'アプリを閉じてダウンロードを停止しますか？'),
                      'zh-CN': ('正在下载', '关闭应用并停止此次下载？')}
            confirmed = window.create_confirmation_dialog(*labels.get(api._preferences.get('language'), labels['th']))
            if confirmed:
                api.cancel_download()
            return confirmed
    window.events.closing += closing
    tested = None
    smoke_closed = None
    if '--self-test' in sys.argv:
        print('Native startup check: validating bundled engines and fonts.', flush=True)
        subprocess.run([ffmpeg_path(), '-version'], check=True, capture_output=True, timeout=10)
        if getattr(sys, 'frozen', False):
            from font_assets import check_font_assets
            check_font_assets()
            gallery = resource_path('bin', 'gallery-dl.exe' if sys.platform == 'win32' else 'gallery-dl')
            result = subprocess.run([str(gallery), '--config-ignore', '--list-modules'], check=True,
                                    capture_output=True, timeout=45,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if not result.stdout.strip():
                raise RuntimeError('The packaged image engine did not report any extractors.')
        tested = threading.Event()
        smoke_closed = threading.Event()
        smoke_stage = {'value': 'waiting for the WebView loaded event'}
        def smoke_test():
            try:
                smoke_stage['value'] = 'waiting for the UI, brand assets and Python bridge'
                print('Native startup check: WebView loaded.', flush=True)
                deadline = time.monotonic() + 15
                requested = False
                while time.monotonic() < deadline:
                    ready = window.evaluate_js('Boolean(window.studioReady && document.querySelector("#download") && window.pywebview?.api?.snapshot && document.querySelector(".brand img") && Array.from(document.querySelectorAll(".brand img")).every(img => img.complete && img.naturalWidth > 0))')
                    if ready and not requested:
                        window.evaluate_js('window.__studioSmoke = false; window.pywebview.api.snapshot().then(async s => {await document.fonts.ready; window.__studioSmoke = Boolean(s && s.preferences && Array.isArray(s.history) && Array.from(document.fonts).some(f => f.family.includes("Studio-") && f.status === "loaded"));}).catch(() => {});')
                        requested = True
                    if requested and window.evaluate_js('window.__studioSmoke === true'):
                        tested.set()
                        print('Native startup check: UI, bridge and font rendering passed.', flush=True)
                        break
                    time.sleep(.1)
                if not tested.is_set():
                    details = window.evaluate_js('JSON.stringify({document:document.readyState,ui:Boolean(window.studioReady),bridge:Boolean(window.pywebview?.api?.snapshot),images:Array.from(document.querySelectorAll(".brand img")).map(img => ({loaded:img.complete,width:img.naturalWidth})),fonts:document.fonts.status})')
                    print('Native startup check did not become ready: ' + str(details), flush=True)
            except Exception as exc:
                print('Native startup check failed: ' + repr(exc), flush=True)
                raise
            finally:
                window.destroy()
        def timeout():
            if not smoke_closed.wait(45):
                print('Native startup check timed out: ' + smoke_stage['value'], flush=True)
                os._exit(1)
        window.events.loaded += smoke_test
        threading.Thread(target=timeout, daemon=True).start()
    try:
        icon_name = ('app-icon.ico' if sys.platform == 'win32' else
                     'app-icon.icns' if sys.platform == 'darwin' else 'app-icon-1024.png')
        webview.start(gui='edgechromium' if sys.platform == 'win32' else None,
                      icon=str(resource_path('assets', 'branding', icon_name)))
    finally:
        api._cancel.set()
        api._updates.cancel.set()
        if smoke_closed is not None:
            smoke_closed.set()
    if tested is not None:
        if not tested.is_set():
            raise RuntimeError('The native UI or Python bridge did not become ready.')
        if '--smoke-result' in sys.argv:
            proof = Path(sys.argv[sys.argv.index('--smoke-result') + 1])
            result = dict(ok=True, executable=str(Path(sys.executable).resolve()))
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes
                get_console = ctypes.windll.kernel32.GetConsoleWindow
                get_console.restype = wintypes.HWND
                result['console_attached'] = bool(get_console())
            proof.write_text(json.dumps(result), encoding='utf-8')
    elif api._uninstall_plan:
        handoff = os.environ.get('NUVEL_UPDATE_HANDOFF')
        if sys.platform == 'win32' and handoff:
            Path(handoff).write_text(json.dumps(dict(action='uninstall', plan=str(api._uninstall_plan))), encoding='utf-8')
        else:
            from app_uninstall import launch_helper
            launch_helper(api._uninstall_plan)
    elif api._updates.snapshot().get('phase') == 'installing' and api._updates.plan:
        # Windows' supervisor starts the helper outside its child Job Object.
        # macOS has no supervisor and can launch a detached helper directly.
        handoff = os.environ.get('NUVEL_UPDATE_HANDOFF')
        if sys.platform == 'win32' and handoff:
            Path(handoff).write_text(json.dumps(dict(plan=str(api._updates.plan))), encoding='utf-8')
        else:
            from update_installer import launch_helper
            launch_helper(api._updates.plan)


if __name__ == '__main__':
    main()
