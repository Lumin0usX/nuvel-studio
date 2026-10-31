import base64
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import image_download as images
from glass_app import StudioAPI

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6nT8AAAAASUVORK5CYII=')


class Response(io.BytesIO):
    def __init__(self, data=PNG, length=None):
        super().__init__(data)
        self.headers = {} if length is None else {'Content-Length': str(length)}


class DirectImageTests(unittest.TestCase):
    def test_extensionless_image_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'photo.png').write_bytes(b'keep this')
            updates = []
            with patch.object(images, 'urlopen', return_value=Response(length=len(PNG))):
                result = images.download_direct('https://example.org/photo', folder, threading.Event(), lambda **x: updates.append(x))
            self.assertEqual(result['title'], 'photo (1).png')
            self.assertEqual((Path(folder) / result['title']).read_bytes(), PNG)
            self.assertEqual((Path(folder) / 'photo.png').read_bytes(), b'keep this')
            self.assertTrue(updates[-1]['progress_known'])
            self.assertFalse(list(Path(folder).glob('*.part')))

    def test_html_disguised_as_jpeg_is_not_saved(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(images, 'urlopen', return_value=Response(b'<html>Login</html>')):
            with self.assertRaises(RuntimeError):
                images.download_images('https://example.org/photo.jpg', folder, threading.Event(), Mock())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_truncated_transfer_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(images, 'urlopen', return_value=Response(length=len(PNG) + 100)):
            with self.assertRaises(RuntimeError):
                images.download_direct('https://example.org/photo.png', folder, threading.Event(), Mock())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_cancel_mid_transfer_removes_partial_file(self):
        cancel = threading.Event()
        with tempfile.TemporaryDirectory() as folder, patch.object(images, 'urlopen', return_value=Response(PNG * 3000)):
            with self.assertRaises(RuntimeError):
                images.download_direct('https://example.org/photo.png', folder, cancel, lambda **_: cancel.set())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_unknown_length_does_not_claim_known_progress(self):
        updates = []
        with tempfile.TemporaryDirectory() as folder, patch.object(images, 'urlopen', return_value=Response()):
            images.download_direct('https://example.org/CON.jpg', folder, threading.Event(), lambda **x: updates.append(x))
            self.assertTrue((Path(folder) / 'image.png').is_file())
            self.assertFalse(updates[-1]['progress_known'])

    def test_direct_images_work_without_gallery_engine(self):
        with patch.object(images, 'download_direct', return_value={'count': 1}) as direct, patch.object(images, 'download_gallery') as gallery:
            images.download_images('https://cdn.example.org/x.png?token=abc', '.', threading.Event(), Mock())
            direct.assert_called_once()
            gallery.assert_not_called()

    def test_catalog_image_posts_go_straight_to_gallery_without_html_probe(self):
        hosts = ('www.artstation.com', 'www.behance.net', 'www.pexels.com', '500px.com',
                 'wallhaven.cc', 'ibb.co', 'imgbb.com', 'lensdump.com', 'commons.wikimedia.org',
                 'weibo.com', 'm.weibo.cn', 'bsky.app')
        for host in hosts:
            with self.subTest(host=host), patch.object(images, 'download_direct') as direct, \
                 patch.object(images, 'download_gallery', return_value={'count': 1}) as gallery:
                result = images.download_images('https://' + host + '/post/123', '.', threading.Event(), Mock())
                self.assertEqual(result['count'], 1)
                direct.assert_not_called()
                gallery.assert_called_once()

    def test_actual_image_links_on_gallery_hosts_still_use_direct_downloader(self):
        with patch.object(images, 'download_direct', return_value={'count': 1}) as direct, \
             patch.object(images, 'download_gallery') as gallery:
            images.download_images('https://www.pexels.com/photo.jpg', '.', threading.Event(), Mock())
            direct.assert_called_once()
            gallery.assert_not_called()

    def test_lookalike_host_is_not_treated_as_a_known_gallery(self):
        with patch.object(images, 'download_direct', return_value={'count': 1}) as direct, \
             patch.object(images, 'download_gallery') as gallery:
            images.download_images('https://artstation.com.example.org/photo', '.', threading.Event(), Mock())
            direct.assert_called_once()
            gallery.assert_not_called()

    def test_gallery_cookies_are_explicit_and_config_is_ignored(self):
        args = images.gallery_args(['gallery-dl'], 'https://example.org/post', '.', 'none', '')
        self.assertIn('--config-ignore', args)
        self.assertIn('--Print', args)
        self.assertNotIn('--print', args)  # lowercase print would disable downloads
        self.assertNotIn('--cookies', args)
        self.assertNotIn('--cookies-from-browser', args)
        self.assertEqual(args[-2:], ['--', 'https://example.org/post'])
        file_args = images.gallery_args(['gallery-dl'], 'https://example.org/post', '.', 'file', 'cookies.txt')
        self.assertEqual(file_args[file_args.index('--cookies') + 1], 'cookies.txt')


class GalleryProcessTests(unittest.TestCase):
    def _fake(self, folder, body):
        script = Path(folder) / 'fake_gallery.py'
        script.write_text('import sys,time\nfrom pathlib import Path\nfolder=Path(sys.argv[sys.argv.index("-D")+1])\n' + body, encoding='utf-8')
        return [sys.executable, str(script)]

    def test_gallery_counts_images_and_rejects_outside_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'for name in ["a.jpg","b.png"]:\n p=folder/name\n p.write_bytes(b"test")\n print("STUDIO_IMAGE_SAVED:"+str(p),flush=True)\nprint("STUDIO_IMAGE_SAVED:"+__file__,flush=True)\n')
            with patch.object(images, 'gallery_command', return_value=command):
                result = images.download_gallery('https://instagram.com/p/example', folder, threading.Event(), Mock())
            self.assertEqual(result['count'], 2)
            self.assertEqual(Path(result['folder']), Path(folder))
            self.assertEqual((Path(folder) / 'a.jpg').read_bytes(), b'test')
            self.assertEqual((Path(folder) / 'b.png').read_bytes(), b'test')
            self.assertFalse([p for p in Path(folder).iterdir() if p.is_dir()])

    def test_gallery_flattens_nested_paths_and_preserves_namesakes_across_jobs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'photo.jpg').write_bytes(b'keep existing')
            command = self._fake(folder, 'p=folder/"extractor"/"album"/"photo.jpg"\np.parent.mkdir(parents=True)\np.write_bytes(b"new image")\nprint("STUDIO_IMAGE_SAVED:"+str(p),flush=True)\n')
            with patch.object(images, 'gallery_command', return_value=command):
                for _ in range(2):
                    result = images.download_gallery('https://example.org/post', folder, threading.Event(), Mock())
                    self.assertEqual(result['folder'], folder)
            self.assertEqual((root / 'photo.jpg').read_bytes(), b'keep existing')
            for name in ('photo (1).jpg', 'photo (2).jpg'):
                self.assertEqual((root / name).read_bytes(), b'new image')
            self.assertFalse([p for p in root.iterdir() if p.is_dir()])

    def test_gallery_zero_images_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'print("No image results",flush=True)\n')
            with patch.object(images, 'gallery_command', return_value=command), self.assertRaises(RuntimeError):
                images.download_gallery('https://example.org/post', folder, threading.Event(), Mock())
            self.assertFalse([p for p in Path(folder).iterdir() if p.is_dir()])

    def test_gallery_failure_after_partial_download_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'p=folder/"a.jpg"\np.write_bytes(b"test")\nprint("STUDIO_IMAGE_SAVED:"+str(p),flush=True)\nsys.exit(4)\n')
            with patch.object(images, 'gallery_command', return_value=command), self.assertRaises(RuntimeError):
                images.download_gallery('https://example.org/post', folder, threading.Event(), Mock())
            self.assertEqual((Path(folder) / 'a.jpg').read_bytes(), b'test')
            self.assertFalse([p for p in Path(folder).iterdir() if p.is_dir()])

    def test_cancel_keeps_finished_images_in_destination_and_removes_work_folder(self):
        cancel = threading.Event()
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'for name in ["a.jpg","b.png"]:\n (folder/name).write_bytes(b"finished")\n'
                                 'for name in ["a.jpg","b.png"]:\n print("STUDIO_IMAGE_SAVED:"+str(folder/name),flush=True)\ntime.sleep(30)\n')
            def update(**values):
                if values.get('image_count') == 1:
                    cancel.set()
            with patch.object(images, 'gallery_command', return_value=command), self.assertRaises(RuntimeError):
                images.download_gallery('https://example.org/post', folder, cancel, update)
            self.assertEqual((Path(folder) / 'a.jpg').read_bytes(), b'finished')
            self.assertEqual((Path(folder) / 'b.png').read_bytes(), b'finished')
            self.assertFalse([p for p in Path(folder).iterdir() if p.is_dir()])

    def test_cancel_terminates_silent_child(self):
        cancel = threading.Event()
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'time.sleep(30)\n')
            with patch.object(images, 'gallery_command', return_value=command):
                with self.assertRaises(RuntimeError):
                    images.download_gallery('https://example.org/post', folder, cancel, lambda **_: cancel.set())

    def test_resize_failure_preserves_original_directly_in_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'p=folder/"a.jpg"\np.write_bytes(b"original")\nprint("STUDIO_IMAGE_SAVED:"+str(p),flush=True)\n')
            with patch.object(images, 'gallery_command', return_value=command), \
                    patch.object(images, 'resize_image', side_effect=RuntimeError('resize failed')), \
                    self.assertRaisesRegex(RuntimeError, 'resize failed'):
                images.download_gallery('https://example.org/post', folder, threading.Event(), Mock(), quality='640')
            self.assertEqual((Path(folder) / 'a.jpg').read_bytes(), b'original')
            self.assertFalse([p for p in Path(folder).iterdir() if p.is_dir()])

    def test_failed_destination_copy_keeps_staged_original_for_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            command = self._fake(folder, 'p=folder/"a.jpg"\np.write_bytes(b"original")\nprint("STUDIO_IMAGE_SAVED:"+str(p),flush=True)\n')
            with patch.object(images, 'gallery_command', return_value=command), \
                    patch.object(images, 'save_named_file', side_effect=OSError('disk full')), \
                    self.assertRaisesRegex(OSError, 'disk full'):
                images.download_gallery('https://example.org/post', folder, threading.Event(), Mock())
            staged, = Path(folder).glob('.studio-images-*')
            self.assertEqual((staged / 'a.jpg').read_bytes(), b'original')


class ImageAPITests(unittest.TestCase):
    def setUp(self):
        with patch.object(StudioAPI, '_scan'):
            self.api = StudioAPI()

    def test_image_mode_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder, patch('glass_app.threading.Thread') as thread:
            self.assertEqual(self.api.start_download({'url': 'https://example.org/p.png', 'folder': folder, 'mode': 'image'}), {'ok': True})
            self.assertEqual(thread.call_args.kwargs['args'][2], 'image')

    def test_image_history_has_count_and_actual_folder(self):
        with patch('glass_app.download_images', return_value=dict(title='Album', count=3, folder='/saved/album')):
            self.api._download('https://example.org/post', '.', 'image', 'none', '')
        state = self.api.snapshot()
        self.assertEqual(state['phase'], 'done')
        self.assertEqual(state['history'][0]['count'], 3)
        self.assertEqual(state['history'][0]['folder'], '/saved/album')
        self.assertEqual(state['history'][0]['mode'], 'image')

    def test_image_failure_does_not_create_success_history(self):
        with patch('glass_app.download_images', side_effect=RuntimeError('No images')):
            self.api._download('https://example.org/post', '.', 'image', 'none', '')
        self.assertEqual(self.api.snapshot()['phase'], 'error')
        self.assertEqual(self.api.snapshot()['history'], [])


if __name__ == '__main__':
    unittest.main()
