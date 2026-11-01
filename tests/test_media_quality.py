# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

import hashlib
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image
import yt_dlp

from glass_app import StudioAPI
from image_quality import resize_image
from media_quality import media_options, validate_quality


class QualitySelectionTests(unittest.TestCase):
    def _select_video(self, cap, heights):
        formats = [dict(format_id=str(height), url=f'https://example.org/{height}.mp4',
                        ext='mp4', height=height, width=height * 16 // 9, vcodec='h264', acodec='aac',
                        tbr=height * 3) for height in heights]
        with yt_dlp.YoutubeDL(dict(media_options('video', cap), quiet=True, no_warnings=True)) as ydl:
            return ydl.process_video_result(dict(id='test', title='Test', extractor='generic', formats=formats), download=False)['height']

    def test_highest_source_resolution_is_default(self):
        self.assertEqual(self._select_video('best', [360, 1080, 2160]), 2160)

    def test_video_cap_selects_best_available_below_ceiling(self):
        self.assertEqual(self._select_video('1080', [360, 720, 1440, 2160]), 720)

    def test_video_cap_does_not_silently_exceed_selection(self):
        with self.assertRaises(yt_dlp.utils.ExtractorError):
            self._select_video('480', [1080, 2160])

    def test_native_audio_is_default_and_mp3_bitrate_is_explicit(self):
        original = media_options('audio')['postprocessors'][0]
        self.assertEqual(original['preferredcodec'], 'best')
        mp3 = media_options('audio', '320')['postprocessors'][0]
        self.assertEqual((mp3['preferredcodec'], mp3['preferredquality']), ('mp3', '320'))

    def test_invalid_or_cross_mode_value_is_rejected(self):
        for mode, value in [('video', '320'), ('image', '1080'), ('audio', '2160'), ('video', '1080]/best')]:
            with self.assertRaises(ValueError):
                validate_quality(mode, value)

    def test_api_passes_quality_to_worker_and_blocks_invalid_quality(self):
        with patch.object(StudioAPI, '_scan'):
            api = StudioAPI()
        with tempfile.TemporaryDirectory() as folder, patch('glass_app.threading.Thread') as thread:
            bad = api.start_download(dict(url='https://example.org/video', folder=folder, mode='video', quality='320'))
            self.assertIn('error', bad)
            thread.assert_not_called()
            good = api.start_download(dict(url='https://example.org/video', folder=folder, mode='video', quality='1080'))
            self.assertEqual(good, dict(ok=True))
            self.assertEqual(thread.call_args.kwargs['args'][-1], '1080')


class ImageQualityTests(unittest.TestCase):
    def test_quality_is_applied_to_the_actual_downloaded_file(self):
        from image_download import download_images
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'downloaded.png'
            Image.new('RGB', (1600, 900), 'navy').save(path)
            result = dict(count=1, title=path.name, folder=folder)
            with patch('image_download.download_direct', return_value=result):
                download_images('https://example.org/photo.png', folder, threading.Event(), lambda **_: None, quality='640')
            with Image.open(path) as resized:
                self.assertEqual(resized.size, (640, 360))

    def test_original_quality_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'original.png'
            Image.new('RGB', (1600, 900), 'navy').save(path)
            before = hashlib.sha256(path.read_bytes()).digest()
            self.assertFalse(resize_image(path, 'best', threading.Event()))
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), before)

    def test_image_cap_preserves_aspect_ratio_and_transparency(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'large.png'
            Image.new('RGBA', (1600, 900), (20, 30, 40, 128)).save(path)
            self.assertTrue(resize_image(path, '640', threading.Event()))
            with Image.open(path) as result:
                self.assertEqual(result.size, (640, 360))
                self.assertEqual(result.mode, 'RGBA')
                self.assertEqual(result.getpixel((1, 1))[3], 128)

    def test_small_source_is_not_upscaled_or_reencoded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'small.jpg'
            Image.new('RGB', (320, 180), 'blue').save(path)
            before = path.read_bytes()
            self.assertFalse(resize_image(path, '2048', threading.Event()))
            self.assertEqual(path.read_bytes(), before)

    def test_portrait_image_is_capped_by_long_edge(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'portrait.jpg'
            Image.new('RGB', (900, 1600), 'blue').save(path)
            resize_image(path, '640', threading.Event())
            with Image.open(path) as result:
                self.assertEqual(result.size, (360, 640))

    def test_animation_keeps_frames_timing_and_loop(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'animation.gif'
            frames = [Image.new('RGB', (1000, 800), color) for color in ('red', 'blue')]
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=[100, 200], loop=2)
            resize_image(path, '640', threading.Event())
            with Image.open(path) as result:
                self.assertEqual(result.size, (640, 512))
                self.assertEqual(result.n_frames, 2)
                self.assertEqual(result.info['loop'], 2)
                self.assertEqual(result.info['duration'], 100)
                result.seek(1)
                self.assertEqual(result.info['duration'], 200)

    def test_cancel_preserves_original_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'large.png'
            Image.new('RGB', (1600, 900), 'red').save(path)
            before = path.read_bytes()
            cancel = threading.Event()
            cancel.set()
            with self.assertRaises(RuntimeError):
                resize_image(path, '640', cancel)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_webp_and_apng_remain_animated(self):
        for extension in ('webp', 'png'):
            with self.subTest(extension=extension), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / ('animated.' + extension)
                frames = [Image.new('RGBA', (1000, 800), color) for color in ('red', 'blue')]
                frames[0].save(path, save_all=True, append_images=frames[1:], duration=[100, 200], loop=2)
                resize_image(path, '640', threading.Event())
                with Image.open(path) as result:
                    self.assertEqual(result.size, (640, 512))
                    self.assertEqual(result.n_frames, 2)
                    self.assertEqual(result.info['loop'], 2)

    def test_exif_orientation_is_applied_before_resizing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rotated.jpg'
            exif = Image.Exif()
            exif[274] = 6
            Image.new('RGB', (1600, 900), 'blue').save(path, exif=exif)
            resize_image(path, '640', threading.Event())
            with Image.open(path) as result:
                self.assertEqual(result.size, (360, 640))
                self.assertNotEqual(result.getexif().get(274), 6)


if __name__ == '__main__':
    unittest.main()
