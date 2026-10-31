import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import platform_runtime as runtime


class PlatformTests(unittest.TestCase):
    def test_mac_open_uses_argument_list(self):
        with patch.object(runtime.sys, 'platform', 'darwin'), patch.object(runtime.subprocess, 'run') as run:
            runtime.open_directory('folder with spaces')
            self.assertEqual(run.call_args.args[0], ['open', str(Path('folder with spaces').resolve())])
            self.assertNotIn('shell', run.call_args.kwargs)

    def test_windows_open_unchanged(self):
        with patch.object(runtime.sys, 'platform', 'win32'), patch.object(runtime.os, 'startfile', create=True) as start:
            runtime.open_directory('.')
            start.assert_called_once_with(str(Path('.').resolve()))

    def test_trackpad_small_delta_is_not_lost(self):
        with patch.object(runtime.sys, 'platform', 'darwin'):
            self.assertEqual(runtime.scroll_units(1), -1)
            self.assertEqual(runtime.scroll_units(-2), 2)
            self.assertEqual(runtime.scroll_units(0), 0)
        with patch.object(runtime.sys, 'platform', 'win32'):
            self.assertEqual(runtime.scroll_units(120), -1)

    def test_resources_do_not_depend_on_working_directory(self):
        self.assertTrue(runtime.resource_path('assets', 'branding', 'app-icon.ico').is_file())

    def test_bundled_ffmpeg_preferred(self):
        with patch.object(runtime.sys, 'platform', 'darwin'), patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(runtime.ffmpeg_path(), str(runtime.resource_path('bin', 'ffmpeg')))

    def test_platform_specific_install_help(self):
        with patch.object(runtime.sys, 'platform', 'darwin'):
            self.assertEqual(runtime.install_instructions(), 'install_macos.command')
            with patch.object(runtime.sys, 'frozen', True, create=True):
                self.assertIn('build_macos.command', runtime.install_instructions())


if __name__ == '__main__':
    unittest.main()
