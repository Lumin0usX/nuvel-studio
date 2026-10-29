import base64
import io
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from glass_app import StudioAPI
import image_download as images
from output_names import validate_output_name, save_named_file


class OutputNameTests(unittest.TestCase):
    def test_blank_unicode_names_extensions_and_literal_templates(self):
        for raw, expected in [('', ''), ('  ', ''), (' ทริป 京都 2026.mp4 ', 'ทริป 京都 2026'),
                              ('100% %(title)s {id}.PNG', '100% %(title)s {id}'),
                              ('part.2026', 'part.2026'), ('NU\u0308VEL', 'NÜVEL'), ('Trip.mp4.png', 'Trip')]:
            with self.subTest(raw=raw):
                self.assertEqual(validate_output_name(raw), expected)
                self.assertEqual(validate_output_name(expected), expected)

    def test_paths_reserved_names_controls_and_long_names_are_rejected(self):
        for name in ('../clip', '/tmp/clip', 'C:\\clip', 'clip?', '.', '..', 'CON', 'nul.txt',
                     'LPT1', 'COM¹', 'clip.', 'a\nb', 'a\x00b', 'ก' * 54, 123, None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_output_name(name)

    def test_collision_and_failed_copy_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.mp3'; source.write_bytes(b'new audio')
            existing = root / 'Trip.mp3'; existing.write_bytes(b'old audio')
            target = save_named_file(source, root, 'Trip')
            self.assertEqual(target.name, 'Trip (1).mp3')
            self.assertEqual(target.read_bytes(), b'new audio')
            self.assertEqual(existing.read_bytes(), b'old audio')
            cancel = Mock(side_effect=[None, RuntimeError('cancelled')])
            with self.assertRaisesRegex(RuntimeError, 'cancelled'):
                save_named_file(source, root, 'Cancelled', cancel)
            self.assertFalse((root / 'Cancelled.mp3').exists())
            self.assertEqual(source.read_bytes(), b'new audio')


class NamedDownloadTests(unittest.TestCase):
    def setUp(self):
        with patch.object(StudioAPI, '_scan'):
            self.api = StudioAPI()

    def test_api_passes_optional_name_for_every_mode_and_rejects_invalid_names_before_start(self):
        with tempfile.TemporaryDirectory() as folder:
            for mode in ('video', 'audio', 'image'):
                self.api._update(phase='idle')
                with patch('glass_app.threading.Thread') as worker:
                    result = self.api.start_download(dict(url='https://example.org/clip', folder=folder,
                                                         mode=mode, output_name=' ชื่อใหม่.mp4 '))
                    self.assertEqual(result, {'ok': True})
                    self.assertEqual(worker.call_args.kwargs['kwargs']['output_name'], 'ชื่อใหม่')
            self.api._update(phase='idle')
            with patch('glass_app.threading.Thread') as worker:
                result = self.api.start_download(dict(url='https://example.org/clip', folder=folder, output_name='../bad'))
                self.assertIn('error', result)
                worker.assert_not_called()
                self.assertEqual(self.api.snapshot()['phase'], 'idle')

    def test_media_uses_literal_name_after_conversion_and_preserves_same_named_video(self):
        import yt_dlp
        original = yt_dlp.YoutubeDL
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / '100% %(title)s.mp4'; video.write_bytes(b'keep this video')
            def create_downloader(opts):
                # Exercise yt-dlp's real template parser, then emulate completed conversion.
                with original(dict(quiet=True)) as parser:
                    filename = parser.prepare_filename(dict(title='SOURCE', id='1', ext='mp3'), outtmpl=opts['outtmpl'])
                self.assertEqual(Path(filename).suffix, '.mp3')
                self.assertNotIn('100%', Path(filename).name)
                self.assertNotEqual(Path(filename).parent, Path(folder))
                Path(filename).write_bytes(b'converted audio')
                def download(_):
                    opts['post_hooks'][0](filename)
                    return 0
                engine = Mock(); engine.__enter__ = Mock(return_value=engine); engine.__exit__ = Mock(return_value=False)
                engine.download.side_effect = download
                return engine
            with patch('yt_dlp.YoutubeDL', side_effect=create_downloader), patch('glass_app.ffmpeg_path', return_value='ffmpeg'):
                for _ in range(2):
                    self.api._download('https://example.org/clip', folder, 'audio', 'none', '', '128', '100% %(title)s')
                    self.assertEqual(self.api.snapshot()['phase'], 'done')
            self.assertEqual(video.read_bytes(), b'keep this video')
            self.assertEqual((Path(folder) / '100% %(title)s.mp3').read_bytes(), b'converted audio')
            self.assertEqual((Path(folder) / '100% %(title)s (1).mp3').read_bytes(), b'converted audio')
            self.assertFalse(list(Path(folder).glob('.studio-download-*')))
            self.assertEqual(self.api.snapshot()['history'][0]['title'], '100% %(title)s (1).mp3')

    def test_multiple_video_results_use_distinct_intermediates_and_numbered_output_names(self):
        import yt_dlp
        original = yt_dlp.YoutubeDL
        def downloader(opts):
            def download(_):
                with original(dict(quiet=True)) as parser:
                    paths = []
                    for index in range(2):
                        filename = parser.prepare_filename(dict(title='Source', id=str(index), ext='mp4'), outtmpl=opts['outtmpl'])
                        paths.append(filename)
                        Path(filename).write_bytes(f'video {index}'.encode())
                        opts['post_hooks'][0](filename)
                    self.assertNotEqual(paths[0], paths[1])
                return 0
            engine = Mock(); engine.__enter__ = Mock(return_value=engine); engine.__exit__ = Mock(return_value=False)
            engine.download.side_effect = download
            return engine
        with tempfile.TemporaryDirectory() as folder, patch('yt_dlp.YoutubeDL', side_effect=downloader), \
                patch('glass_app.ffmpeg_path', return_value='ffmpeg'), patch('glass_app.add_video_postprocessor'):
            self.api._download('https://example.org/post', folder, 'video', 'none', '', 'best', 'Trip')
            self.assertEqual(self.api.snapshot()['phase'], 'done', self.api.snapshot()['error'])
            self.assertEqual((Path(folder) / 'Trip.mp4').read_bytes(), b'video 0')
            self.assertEqual((Path(folder) / 'Trip (1).mp4').read_bytes(), b'video 1')

    def test_direct_image_uses_custom_name_actual_extension_and_collision_suffix(self):
        data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6nT8AAAAASUVORK5CYII=')
        with tempfile.TemporaryDirectory() as folder:
            existing = Path(folder) / 'ทริป.png'; existing.write_bytes(b'keep')
            response = io.BytesIO(data); response.headers = {}
            with patch.object(images, 'urlopen', return_value=response):
                result = images.download_images('https://example.org/photo.jpg', folder, threading.Event(), Mock(), output_name='ทริป.jpg')
            self.assertEqual(result['title'], 'ทริป (1).png')
            self.assertEqual((Path(folder) / result['title']).read_bytes(), data)
            self.assertEqual(existing.read_bytes(), b'keep')

    def test_real_named_video_and_audio_conversion_preserve_previous_outputs(self):
        import yt_dlp
        from platform_runtime import ffmpeg_path
        original = yt_dlp.YoutubeDL
        # Permit only this test's controlled local fixture, without a network server.
        def downloader(opts):
            return original(dict(opts, enable_file_urls=True))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.mp4'
            output = root / 'output'; output.mkdir()
            subprocess.run([ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                            '-i', 'color=s=64x48:r=10', '-f', 'lavfi', '-i', 'sine=frequency=440',
                            '-t', '0.3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(source)],
                           check=True, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            with patch('yt_dlp.YoutubeDL', side_effect=downloader):
                for mode, quality, suffix in [('video', 'best', '.mp4'), ('audio', '128', '.mp3'), ('audio', 'best', '.m4a')]:
                    self.api._download(source.as_uri(), str(output), mode, 'none', '', quality, 'ทริป 100%')
                    state = self.api.snapshot()
                    self.assertEqual(state['phase'], 'done', state['error'])
                    self.assertEqual(state['history'][0]['title'], 'ทริป 100%' + suffix)
                    path = output / ('ทริป 100%' + suffix)
                    self.assertGreater(path.stat().st_size, 0)
                    if mode == 'video':
                        video_bytes = path.read_bytes()
                    else:
                        self.assertEqual((output / 'ทริป 100%.mp4').read_bytes(), video_bytes)
            self.assertFalse(list(output.glob('.studio-download-*')))

    def test_gallery_renames_images_in_download_order_and_preserves_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / 'gallery.py'
            script.write_text('import sys\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index("-D")+1])\n'
                              'for name in ["z.jpg", "a.png"]:\n f=p/name\n f.write_bytes(name.encode())\n'
                              ' print("STUDIO_IMAGE_SAVED:"+str(f),flush=True)\n', encoding='utf-8')
            import sys
            with patch.object(images, 'gallery_command', return_value=[sys.executable, str(script)]):
                result = images.download_images('https://instagram.com/p/example', folder, threading.Event(), Mock(), output_name='ทริป {id}')
            album = Path(result['folder'])
            self.assertEqual(result['count'], 2)
            self.assertEqual(result['title'], 'ทริป {id}')
            self.assertEqual((album / 'ทริป {id}-001.jpg').read_bytes(), b'z.jpg')
            self.assertEqual((album / 'ทริป {id}-002.png').read_bytes(), b'a.png')
            self.assertEqual(len(list(album.iterdir())), 2)

