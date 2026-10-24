import tempfile
import unittest
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import threading
from unittest.mock import patch, Mock
from glass_app import StudioAPI


class GlassAPITests(unittest.TestCase):
    def setUp(self):
        with patch.object(StudioAPI, '_scan'):
            self.api = StudioAPI()

    def test_invalid_link_never_starts_job(self):
        result = self.api.start_download({'url':'file:///private/file','folder':'.'})
        self.assertIn('error', result)
        self.assertEqual(self.api.snapshot()['phase'], 'idle')

    def test_busy_job_rejected(self):
        self.api._update(phase='processing')
        self.assertIn('error', self.api.start_download({'url':'https://example.com','folder':'.'}))

    def test_cancel_does_not_claim_job_finished(self):
        self.api._update(phase='processing')
        self.api.cancel_download()
        self.assertEqual(self.api.snapshot()['phase'],'cancelling')
        self.assertTrue(self.api._cancel.is_set())

    def test_worker_success_and_history(self):
        self.api._update(phase='connecting',title='Clip title')
        with tempfile.TemporaryDirectory() as folder, patch('yt_dlp.YoutubeDL') as ydl, patch('glass_app.ffmpeg_path',return_value='ffmpeg'):
            ydl.return_value.__enter__.return_value.download.return_value=0
            self.api._download('https://example.com/clip',folder,'audio','none','')
            state=self.api.snapshot()
            self.assertEqual(state['phase'],'done')
            self.assertEqual(state['history'][0]['folder'],folder)
            self.assertEqual(state['history'][0]['mode'],'audio')
            self.assertNotIn('cookiesfrombrowser',ydl.call_args.args[0])

    def test_real_audio_extraction_preserves_a_previously_downloaded_video(self):
        from platform_runtime import ffmpeg_path
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'; source.mkdir()
            output = root / 'output'; output.mkdir()
            subprocess.run([ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                            'color=s=64x48:r=10', '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '0.3',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(source / 'clip.mp4')],
                           check=True, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(source)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/clip.mp4'
                self.api._download(url, str(output), 'video', 'none', '')
                self.assertEqual(self.api.snapshot()['phase'], 'done')
                video, = output.glob('*.mp4')
                original = video.read_bytes()
                for quality, extension in [('best', 'm4a'), ('128', 'mp3')]:
                    self.api._download(url, str(output), 'audio', 'none', '', quality)
                    self.assertEqual(self.api.snapshot()['phase'], 'done')
                    self.assertTrue(video.is_file(), 'Audio extraction deleted the earlier video')
                    self.assertEqual(video.read_bytes(), original)
                    audio, = output.glob('*.' + extension)
                    self.assertGreater(audio.stat().st_size, 0)
            finally:
                server.shutdown()
                server.server_close()

    def test_error_does_not_add_success_history(self):
        with patch('yt_dlp.YoutubeDL',side_effect=RuntimeError('offline')), patch('glass_app.ffmpeg_path',return_value='ffmpeg'):
            self.api._download('https://example.com/clip','.','video','none','')
        self.assertEqual(self.api.snapshot()['phase'],'error')
        self.assertEqual(self.api.snapshot()['history'],[])

    def test_settings_validation(self):
        self.assertIn('error',self.api.start_download(None))
        self.assertIn('error',self.api.start_download({'url':'https://example.com','folder':'.','cookies':'unknown'}))

    def test_snapshot_does_not_expose_mutable_state(self):
        snapshot=self.api.snapshot()
        snapshot['history'].append({'title':'injected'})
        self.assertEqual(self.api.snapshot()['history'],[])

    def test_catalog_acknowledgment_omits_only_static_data_and_keeps_live_state(self):
        self.api._platforms = [dict(name='Source', icon='data:image/png;base64,fixture')]
        self.api._image_engine = dict(available=True, modules=['fixture'])
        initial = self.api.snapshot()
        revision = initial['catalog_revision']
        self.api._update(phase='downloading', percent=42, speed='2.0 MB/s')
        delta = self.api.snapshot(revision)
        self.assertEqual(delta['percent'], 42)
        self.assertEqual(delta['speed'], '2.0 MB/s')
        self.assertEqual(delta['catalog_revision'], revision)
        for key in ('preferences', 'app_update', 'history'):
            self.assertIn(key, delta)
        for key in ('platforms', 'version', 'image_engine'):
            self.assertNotIn(key, delta)
        delta['history'].append({'title': 'injected'})
        initial['platforms'][0]['name'] = 'injected'
        initial['image_engine']['modules'].append('injected')
        full = self.api.snapshot()
        self.assertEqual(full['history'], [])
        self.assertEqual(full['platforms'][0]['name'], 'Source')
        self.assertEqual(full['image_engine']['modules'], ['fixture'])
        self.assertIn('platforms', self.api.snapshot('previous-session'))

    def test_finishing_an_engine_scan_invalidates_the_acknowledged_catalog(self):
        from download_engine import PLATFORMS
        initial = self.api.snapshot()
        states = {name: 'supported' for name, *_ in PLATFORMS}
        with patch('glass_app.platform_support', return_value=('fixture-version', states)), \
                patch('glass_app.image_support', return_value=dict(available=False, modules=[])):
            self.api._scan()
        refreshed = self.api.snapshot(initial['catalog_revision'])
        self.assertNotEqual(refreshed['catalog_revision'], initial['catalog_revision'])
        self.assertEqual(len(refreshed['platforms']), len(PLATFORMS))
        self.assertEqual(refreshed['version'], 'fixture-version')
        self.assertNotIn('platforms', self.api.snapshot(refreshed['catalog_revision']))


if __name__=='__main__':
    unittest.main()
