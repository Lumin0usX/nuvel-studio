import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glass_app import StudioAPI


class MetadataAndHistoryTests(unittest.TestCase):
    def setUp(self):
        with patch.object(StudioAPI, '_scan'):
            self.api = StudioAPI()

    def test_metadata_reads_without_downloading_or_changing_job(self):
        with patch('yt_dlp.YoutubeDL') as ydl:
            client = ydl.return_value.__enter__.return_value
            client.extract_info.return_value = dict(title='Actual source title', duration=61,
                thumbnail='https://example.com/image.jpg', extractor_key='Example',
                formats=[dict(height=720, ext='mp4'), dict(height=1080, ext='webm'), dict(height=720, ext='mp4')])
            result = self.api.analyze_url(dict(url='https://example.com/clip'))
            client.extract_info.assert_called_once_with('https://example.com/clip', download=False)
            client.download.assert_not_called()
            self.assertEqual(result['title'], 'Actual source title')
            self.assertEqual(result['resolutions'], [720, 1080])
            self.assertEqual(result['formats'], ['mp4', 'webm'])
            self.assertEqual(self.api.snapshot()['phase'], 'idle')
            self.assertNotIn('cookiesfrombrowser', ydl.call_args.args[0])

    def test_metadata_validation_and_image_mode(self):
        with patch('yt_dlp.YoutubeDL') as ydl:
            for url in ('javascript:alert(1)', 'file:///private/file', 'not-a-url'):
                self.assertIn('error', self.api.analyze_url(dict(url=url)))
            self.assertTrue(self.api.analyze_url(dict(url='https://example.com/post', mode='image'))['unavailable'])
            ydl.assert_not_called()

    def test_metadata_failure_does_not_turn_into_download_failure(self):
        with patch('yt_dlp.YoutubeDL', side_effect=RuntimeError('Unsupported URL')):
            self.assertIn('error', self.api.analyze_url(dict(url='https://example.com/clip')))
        self.assertEqual(self.api.snapshot()['phase'], 'idle')
        self.assertEqual(self.api.snapshot()['history'], [])

    def test_missing_metadata_and_playlist_are_not_invented(self):
        with patch('yt_dlp.YoutubeDL') as ydl:
            client = ydl.return_value.__enter__.return_value
            client.extract_info.return_value = dict(id='123')
            result = self.api.analyze_url(dict(url='https://example.com/clip'))
            self.assertEqual(result['title'], '')
            self.assertIsNone(result['duration'])
            self.assertEqual(result['formats'], [])
            client.extract_info.return_value = dict(_type='playlist', entries=[])
            self.assertTrue(self.api.analyze_url(dict(url='https://example.com/list'))['unavailable'])

    def test_removing_history_leaves_downloaded_file_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder, 'media.mp4')
            output.write_bytes(b'original downloaded content')
            self.api._update(history=[dict(id='keep', title='Other'), dict(id='remove', title='media.mp4', folder=folder)])
            self.assertTrue(self.api.remove_history('remove')['ok'])
            self.assertEqual([item['id'] for item in self.api.snapshot()['history']], ['keep'])
            self.assertEqual(output.read_bytes(), b'original downloaded content')
            self.assertIn('error', self.api.remove_history(None))


if __name__ == '__main__':
    unittest.main()
