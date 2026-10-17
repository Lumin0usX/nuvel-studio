import tempfile
import unittest
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


if __name__=='__main__':
    unittest.main()
