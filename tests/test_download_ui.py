"""Exercise job transitions without needing a desktop or network."""
import queue
import unittest
from unittest.mock import Mock, patch
from legacy_tk import YTDLStudio


class JobTransitions(unittest.TestCase):
    def setUp(self):
        self.app = YTDLStudio.__new__(YTDLStudio)
        self.app.events = queue.Queue()
        for attr in ('root', 'bar', 'percent_text', 'status', 'progress_text', 'status_label',
                     'download_btn', 'cookie_combo', 'mode', 'video_btn', 'audio_btn', 'mode_hint'):
            setattr(self.app, attr, Mock())
        self.app.mode.get.return_value = 'video'
        self.app.edit_controls = [Mock(), Mock()]
        self.app.busy = True
        self.app.active_output_dir = '/selected/folder'

    def test_processing_does_not_report_complete(self):
        self.app.events.put(('processing', 'Preparing file'))
        self.app._poll_events()
        self.assertTrue(self.app.busy)
        self.app.bar.start.assert_called_once()
        self.app.percent_text.set.assert_called_with('…')

    def test_finished_restores_controls_without_modal(self):
        with patch('legacy_tk.messagebox.showinfo') as modal:
            self.app.events.put(('done',))
            self.app._poll_events()
            modal.assert_not_called()
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.last_output_dir, '/selected/folder')
        self.app.bar.stop.assert_called_once()
        for control in self.app.edit_controls:
            control.configure.assert_called_with(state='normal')

    def test_error_stops_animation_and_allows_retry(self):
        with patch('legacy_tk.messagebox.showerror'):
            self.app.events.put(('error', 'offline'))
            self.app._poll_events()
        self.assertFalse(self.app.busy)
        self.app.bar.stop.assert_called_once()
        self.app.bar.configure.assert_called_with(mode='determinate', value=0)


if __name__ == '__main__':
    unittest.main()
