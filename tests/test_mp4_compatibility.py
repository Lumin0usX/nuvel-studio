"""Exercise real codecs, including an incompatible codec already inside MP4."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import yt_dlp

from media_quality import add_video_postprocessor, media_options
from mp4_compatibility import QuickTimeMP4PP
from platform_runtime import ffmpeg_path


class MacVideoOptionsTests(unittest.TestCase):
    def test_mac_keeps_best_source_and_resolution_cap(self):
        with patch('media_quality.sys', SimpleNamespace(platform='darwin')):
            options = media_options('video', '2160')
            self.assertEqual(options['format'], 'bestvideo*[height<=2160]+bestaudio/best[height<=2160]')
            self.assertEqual(options['merge_output_format'], 'mkv')
            self.assertEqual(options['postprocessors'], [])
            self.assertEqual(media_options('video')['format'], 'bestvideo*+bestaudio/best')

    def test_processor_only_attached_to_mac_video(self):
        client, cancel = Mock(), Mock()
        with patch('mp4_compatibility.QuickTimeMP4PP') as processor:
            with patch('media_quality.sys', SimpleNamespace(platform='darwin')):
                add_video_postprocessor(client, 'audio', cancel)
                add_video_postprocessor(client, 'image', cancel)
                processor.assert_not_called()
                add_video_postprocessor(client, 'video', cancel)
                processor.assert_called_once_with(client, cancel)
                client.add_post_processor.assert_called_once_with(processor.return_value, when='post_process')
            with patch('media_quality.sys', SimpleNamespace(platform='win32')):
                self.assertEqual(media_options('video')['merge_output_format'], 'mp4')
                add_video_postprocessor(client, 'video')
                self.assertEqual(processor.call_count, 1)


class QuickTimeMP4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = ffmpeg_path()

    def command(self, *args):
        return subprocess.run([self.ffmpeg, '-hide_banner', '-nostdin', *args],
                              check=True, capture_output=True)

    def client(self):
        return yt_dlp.YoutubeDL(dict(ffmpeg_location=self.ffmpeg, quiet=True, no_warnings=True))

    def test_vp9_opus_already_in_mp4_is_actually_transcoded(self):
        with tempfile.TemporaryDirectory() as folder, self.client() as client:
            path = Path(folder, 'video with spaces.mp4')
            self.command('-f', 'lavfi', '-i', 'testsrc2=size=64x48:rate=10',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                         '-t', '0.5', '-c:v', 'libvpx-vp9', '-c:a', 'libopus', str(path))
            original = path.read_bytes()
            info = client.run_pp(QuickTimeMP4PP(client), dict(filepath=str(path), ext='mp4'))
            self.assertEqual(info['filepath'], str(path))
            self.assertNotEqual(path.read_bytes(), original)
            probe = subprocess.run([self.ffmpeg, '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
            self.assertIn('Video: h264', probe)
            self.assertIn('yuv420p', probe)
            self.assertIn('64x48', probe)
            self.assertIn('10 fps', probe)
            self.assertIn('Audio: aac (LC)', probe)
            self.command('-v', 'error', '-i', str(path), '-f', 'null', '-')
            content = path.read_bytes()
            self.assertLess(content.index(b'moov'), content.index(b'mdat'))
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_real_download_pipeline_runs_compatibility_before_reporting_finished(self):
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder, 'source.mp4')
            self.command('-f', 'lavfi', '-i', 'testsrc2=size=64x48:rate=10',
                         '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000',
                         '-t', '0.3', '-c:v', 'libvpx-vp9', '-c:a', 'libopus', str(source))
            output = Path(folder, 'download', 'clip.mp4')
            hooks = []
            with ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=folder)) as server:
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    with patch('media_quality.sys', SimpleNamespace(platform='darwin')):
                        options = dict(media_options('video'), ffmpeg_location=self.ffmpeg,
                                       outtmpl=str(output), quiet=True, no_warnings=True, noprogress=True,
                                       postprocessor_hooks=[lambda data: hooks.append((data['postprocessor'], data['status']))])
                        with yt_dlp.YoutubeDL(options) as client:
                            add_video_postprocessor(client, 'video')
                            client.process_ie_result(dict(id='clip', title='Clip',
                                url=f'http://127.0.0.1:{server.server_port}/source.mp4',
                                ext='mp4', vcodec='vp9', acodec='opus', extractor='generic'))
                finally:
                    server.shutdown()
                    worker.join(timeout=5)
            probe = subprocess.run([self.ffmpeg, '-hide_banner', '-i', str(output)], capture_output=True, text=True).stderr
            self.assertIn('Video: h264', probe)
            self.assertIn('Audio: aac (LC)', probe)
            self.assertIn(('QuickTimeMP4', 'finished'), hooks)
            self.assertTrue(source.exists())
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_high_bit_depth_mkv_becomes_eight_bit_mp4(self):
        with tempfile.TemporaryDirectory() as folder, self.client() as client:
            source = Path(folder, 'high-bit-depth.mkv')
            self.command('-f', 'lavfi', '-i', 'testsrc2=size=64x48:rate=10',
                         '-t', '0.3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p10le', str(source))
            info = client.run_pp(QuickTimeMP4PP(client), dict(filepath=str(source), ext='mkv'))
            output = source.with_suffix('.mp4')
            self.assertEqual(info['filepath'], str(output))
            self.assertEqual(info['ext'], 'mp4')
            self.assertFalse(source.exists())
            probe = subprocess.run([self.ffmpeg, '-hide_banner', '-i', str(output)], capture_output=True, text=True).stderr
            self.assertIn('Video: h264', probe)
            self.assertIn('yuv420p(', probe)
            self.assertNotIn('yuv420p10le', probe)
            self.assertNotIn('Audio:', probe)
            self.command('-v', 'error', '-i', str(output), '-f', 'null', '-')

    def test_compatible_streams_are_copied_without_lossy_reencoding(self):
        with tempfile.TemporaryDirectory() as folder, self.client() as client:
            source = Path(folder, 'compatible.mp4')
            source.write_bytes(b'original')
            processor = QuickTimeMP4PP(client)
            probe = ('Stream #0:0: Video: h264 (High) (avc1), yuv420p(tv, bt709), 1920x1080\n'
                     'Stream #0:1: Audio: aac (LC) (mp4a), 48000 Hz, stereo\n')
            def run(path, output, options, **kwargs):
                if output is None:
                    return probe
                self.assertIn(['-c:v', 'copy'], [options[i:i+2] for i in range(len(options)-1)])
                self.assertIn(['-c:a', 'copy'], [options[i:i+2] for i in range(len(options)-1)])
                self.assertNotIn('-vf', options)
                Path(output).write_bytes(b'remuxed')
            with patch.object(processor, 'run_ffmpeg', side_effect=run):
                processor.run(dict(filepath=str(source), ext='mp4'))
            self.assertEqual(source.read_bytes(), b'remuxed')

    def test_failure_or_cancellation_preserves_source_and_removes_partial_output(self):
        for cancel_after_encode in (False, True):
            with self.subTest(cancel=cancel_after_encode), tempfile.TemporaryDirectory() as folder, self.client() as client:
                source = Path(folder, 'original.mp4')
                source.write_bytes(b'original content')
                cancelled = False
                def check_cancel():
                    if cancelled:
                        raise RuntimeError('Download cancelled')
                processor = QuickTimeMP4PP(client, check_cancel)
                def run(path, output, options, **kwargs):
                    nonlocal cancelled
                    if output is None:
                        return 'Stream #0:0: Video: vp9, yuv420p, 64x48\n'
                    Path(output).write_bytes(b'partial output')
                    if cancel_after_encode:
                        cancelled = True
                    else:
                        raise RuntimeError('FFmpeg failed')
                with patch.object(processor, 'run_ffmpeg', side_effect=run), self.assertRaises(RuntimeError):
                    processor.run(dict(filepath=str(source), ext='mp4'))
                self.assertEqual(source.read_bytes(), b'original content')
                self.assertEqual(list(Path(folder).iterdir()), [source])


if __name__ == '__main__':
    unittest.main()
