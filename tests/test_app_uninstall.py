"""Exercise uninstall validation and preservation using disposable app fixtures."""
import json
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path
import plistlib
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import app_uninstall as removal
from app_version import DISPLAY_NAME
from update_installer import write_marker


class UninstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nuvel uninstall ไทย & ' ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.target = self.root / 'nuvel-windows'
        self.target.mkdir()
        (self.target / (DISPLAY_NAME + '.exe')).write_bytes(b'app fixture')
        (self.target / '_internal').mkdir()
        (self.target / '_internal/runtime.dll').write_bytes(b'runtime fixture')
        write_marker(self.target, 'windows-x64')
        self.preferences = self.root / 'user-data/preferences.json'
        self.preferences.parent.mkdir()
        self.preference_patch = patch('ui_preferences.preferences_path', return_value=self.preferences)
        self.preference_patch.start()
        self.addCleanup(self.preference_patch.stop)
        self.downloads = self.root / 'Downloads'
        self.downloads.mkdir()
        self.media = self.downloads / 'keep.mp4'
        self.media.write_bytes(b'original media')
        (self.root / 'source.py').write_text('source remains')
        (self.root / 'dist').mkdir()
        (self.root / 'dist/backup').write_bytes(b'old build')

    def stage(self, **kwargs):
        plan = removal.stage_uninstall(self.target, 'windows-x64', **kwargs)
        self.addCleanup(lambda: shutil.rmtree(plan.parent) if plan.parent.exists() else None)
        return plan

    def test_plan_stages_an_independent_helper_and_preserves_original_app(self):
        plan = self.stage()
        data = removal.read_plan(plan)
        self.assertFalse(data['remove_settings'])
        self.assertTrue((plan.parent / self.target.name / (DISPLAY_NAME + '.exe')).is_file())
        self.assertTrue(self.target.is_dir())
        self.assertEqual(self.media.read_bytes(), b'original media')

    def test_unknown_folders_files_and_app_identity_are_rejected(self):
        with self.assertRaises(ValueError):
            removal.validate_target(self.root, 'windows-x64')
        extra = self.target / 'keep.png'
        extra.write_bytes(b'personal image')
        with self.assertRaisesRegex(ValueError, 'extra files'):
            self.stage()
        self.assertEqual(extra.read_bytes(), b'personal image')
        extra.unlink()
        marker = self.target / '.studio-build.json'
        data = json.loads(marker.read_text())
        data['product'] = 'Another App'
        marker.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.stage()

    def test_source_checkout_and_links_are_not_uninstall_targets(self):
        (self.target / '.git').mkdir()
        with self.assertRaises(ValueError):
            self.stage()
        (self.target / '.git').rmdir()
        link = self.root / DISPLAY_NAME
        try:
            link.symlink_to(self.target, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation not permitted')
        with self.assertRaises(ValueError):
            removal.validate_target(link, 'windows-x64')

    def test_current_and_saved_download_folders_inside_app_are_protected(self):
        media = self.target / '_internal/my downloads'
        media.mkdir()
        (media / 'keep.mp4').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'download folder is inside'):
            self.stage(download_folders=[media])
        self.preferences.write_text(json.dumps(dict(folder=str(media))))
        with self.assertRaisesRegex(ValueError, 'download folder is inside'):
            self.stage()
        self.assertEqual((media / 'keep.mp4').read_bytes(), b'keep')

    def test_inventory_protects_extra_nested_files_even_after_output_folder_changes(self):
        artwork = self.target / '_internal/icon.png'
        artwork.write_bytes(b'bundled artwork')
        removal.write_inventory(self.target, 'windows-x64')
        self.assertEqual(removal.validate_target(self.target, 'windows-x64'), self.target)
        photo = self.target / '_internal/ui/old downloads/photo.jpg'
        photo.parent.mkdir(parents=True)
        photo.write_bytes(b'personal photo')
        self.preferences.write_text(json.dumps(dict(folder=str(self.downloads))))
        with self.assertRaisesRegex(ValueError, 'extra files'):
            self.stage()
        self.assertEqual(photo.read_bytes(), b'personal photo')

    def test_old_builds_with_uninventoried_nested_media_are_not_removed(self):
        old_media = self.target / '_internal/clip.mp4'
        old_media.write_bytes(b'personal video')
        with self.assertRaisesRegex(ValueError, 'Media files'):
            self.stage()
        self.assertEqual(old_media.read_bytes(), b'personal video')

    def test_changed_marker_and_malformed_plan_are_not_applied(self):
        plan = self.stage()
        marker = self.target / '.studio-build.json'
        marker.write_text(marker.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'changed after'):
            removal.read_plan(plan)
        other = self.root / 'plan.json'
        other.write_bytes(plan.read_bytes())
        with self.assertRaisesRegex(ValueError, 'plan location'):
            removal.read_plan(other)

    def test_uninstall_preserves_media_source_backups_and_unrelated_shortcut(self):
        shortcut = self.root / (DISPLAY_NAME + '.lnk')
        shortcut.write_bytes(b'unrelated shortcut')
        self.preferences.write_text(json.dumps(dict(folder=str(self.downloads))))
        plan = self.stage()
        trash = self.root / 'trash'
        trash.mkdir()
        def recycle(path):
            path.rename(trash / path.name)
        with patch.object(removal, '_running_app', return_value=False), \
             patch.object(removal, '_shortcut_target', return_value=self.root / 'other.exe'), \
             patch.object(removal, '_trash', side_effect=recycle), \
             patch.object(removal, '_remove_preferences') as preferences:
            self.assertEqual(removal.uninstall(plan), [])
        preferences.assert_not_called()
        self.assertFalse(self.target.exists())
        self.assertTrue((trash / self.target.name / (DISPLAY_NAME + '.exe')).is_file())
        self.assertTrue(shortcut.is_file())
        self.assertTrue(self.preferences.is_file())
        self.assertEqual(self.media.read_bytes(), b'original media')
        self.assertTrue((self.root / 'source.py').is_file())
        self.assertEqual((self.root / 'dist/backup').read_bytes(), b'old build')

    def test_matching_shortcut_and_selected_settings_are_removed_after_app(self):
        plan = self.stage(remove_settings=True)
        shortcut = self.root / (DISPLAY_NAME + '.lnk')
        shortcut.write_bytes(b'app shortcut')
        with patch.object(removal, '_running_app', return_value=False), \
             patch.object(removal, '_shortcut_target', return_value=self.target / (DISPLAY_NAME + '.exe')), \
             patch.object(removal, '_trash') as trash, \
             patch.object(removal, '_remove_preferences', return_value=[]) as preferences:
            self.assertEqual(removal.uninstall(plan), [])
        self.assertEqual([call.args[0] for call in trash.call_args_list], [self.target, shortcut])
        preferences.assert_called_once()

    def test_running_app_or_failed_recycling_keeps_settings_and_shortcut(self):
        plan = self.stage(remove_settings=True)
        with patch.object(removal, '_running_app', return_value=True), patch.object(removal, '_trash') as trash:
            with self.assertRaisesRegex(RuntimeError, 'still running'):
                removal.uninstall(plan)
            trash.assert_not_called()
        with patch.object(removal, '_running_app', return_value=False), \
             patch.object(removal, '_shortcut_target', return_value=None), \
             patch.object(removal, '_trash', side_effect=OSError('locked')), \
             patch.object(removal, '_remove_preferences') as preferences:
            with self.assertRaisesRegex(OSError, 'locked'):
                removal.uninstall(plan)
            preferences.assert_not_called()
        self.assertTrue(self.target.is_dir())

    def test_preferences_cleanup_only_touches_known_files_and_one_credential(self):
        logs = self.root / 'logs'
        logs.mkdir()
        (logs / 'studio-20261024.log').write_text('app log')
        (logs / 'keep.mp4').write_bytes(b'media')
        self.preferences.write_text('{}')
        with patch('desktop_launcher.logs_directory', return_value=logs), \
             patch('update_credentials.credential') as credential, patch.object(removal, '_trash') as trash:
            self.assertEqual(removal._remove_preferences(), [])
        self.assertEqual({call.args[0] for call in trash.call_args_list},
                         {self.preferences, logs / 'studio-20261024.log'})
        credential.assert_called_once_with(delete=True)
        self.assertEqual((logs / 'keep.mp4').read_bytes(), b'media')

    def test_mac_bundle_and_pre_2_identity_are_recognized(self):
        app = self.root / (DISPLAY_NAME + '.app')
        (app / 'Contents/MacOS').mkdir(parents=True)
        (app / 'Contents/Resources').mkdir()
        (app / 'Contents/MacOS' / DISPLAY_NAME).write_bytes(b'mac fixture')
        info = dict(CFBundleIdentifier='local.nuvelstudio.app', CFBundleExecutable=DISPLAY_NAME,
                    CFBundleName=DISPLAY_NAME, CFBundleVersion='1.1.4', CFBundleShortVersionString='1.1.4')
        info_path = app / 'Contents/Info.plist'
        info_path.write_bytes(plistlib.dumps(info))
        write_marker(app, 'macos-arm64')
        self.assertEqual(removal.validate_target(app, 'macos-arm64'), app)
        info['CFBundleIdentifier'] = 'local.ytdlstudio.app'
        info_path.write_bytes(plistlib.dumps(info))
        (app / 'Contents/Resources/studio-build.json').write_text(json.dumps(dict(
            product='YTDL Studio', platform='macos-arm64', version='1.1.4')))
        self.assertEqual(removal.validate_target(app, 'macos-arm64'), app)

    def test_cancelled_confirmation_does_not_stage_or_remove_anything(self):
        with patch.object(removal, 'find_target', return_value=self.target), \
             patch.object(removal, 'platform_key', return_value='windows-x64'), \
             patch.object(removal, '_confirm', return_value=False), \
             patch.object(removal, 'stage_uninstall') as stage:
            self.assertEqual(removal.main([]), 0)
            stage.assert_not_called()
        self.assertTrue(self.target.is_dir())

    def test_check_mode_only_validates_and_writes_its_receipt(self):
        receipt = self.root / 'check.json'
        with patch.object(removal, 'find_target', return_value=self.target), \
             patch.object(removal, 'platform_key', return_value='windows-x64'), \
             patch.object(removal, '_confirm') as confirm, patch.object(removal, 'stage_uninstall') as stage, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(removal.main(['--check', '--check-result', str(receipt)]), 0)
        confirm.assert_not_called()
        stage.assert_not_called()
        self.assertEqual(json.loads(receipt.read_text()), dict(ok=True, target=str(self.target)))
        self.assertTrue(self.target.is_dir())

    def test_helper_waits_for_parent_before_uninstalling_and_cleans_its_stage(self):
        plan = self.stage()
        events = []
        with patch('update_installer.wait_for_parent', side_effect=lambda _: events.append('parent exited')), \
             patch.object(removal, 'uninstall', side_effect=lambda _: events.append('uninstall') or []), \
             patch.object(removal, '_message'), patch.object(removal.time, 'sleep'), \
             patch.object(removal, 'cleanup_helper') as cleanup:
            self.assertEqual(removal.finish_uninstall(plan, '123'), 0)
        self.assertEqual(events, ['parent exited', 'uninstall'])
        cleanup.assert_called_once_with(plan.parent)

    def test_cleanup_refuses_source_or_non_temporary_folder(self):
        with self.assertRaisesRegex(ValueError, 'temporary uninstall folder'):
            removal.cleanup_helper(self.root)
        self.assertTrue((self.root / 'source.py').is_file())

    @unittest.skipUnless(sys.platform in ('win32', 'darwin') and
                         not (sys.platform == 'win32' and os.environ.get('CI')),
                         'Native Trash requires macOS or an interactive Windows session')
    def test_native_trash_moves_only_the_disposable_app_fixture(self):
        self.assertEqual(self.target.resolve().parent, self.root)
        removal._trash(self.target)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.media.read_bytes(), b'original media')
        self.assertTrue((self.root / 'source.py').is_file())


class UninstallAPITests(unittest.TestCase):
    def setUp(self):
        from glass_app import StudioAPI
        with patch.object(StudioAPI, '_scan'):
            self.api = StudioAPI()
        self.api._window = Mock()

    def test_busy_download_update_and_browser_mode_cannot_uninstall(self):
        self.api._state['phase'] = 'downloading'
        self.assertEqual(self.api.uninstall_app()['error'], 'download_active')
        self.api._state['phase'] = 'idle'
        self.api._updates.set(phase='installing')
        self.assertEqual(self.api.uninstall_app()['error'], 'update_busy')
        self.api._window = None
        self.assertEqual(self.api.uninstall_app()['error'], 'native_required')

    def test_staging_failure_keeps_window_open_and_can_be_retried(self):
        with patch.object(removal, 'stage_uninstall', side_effect=OSError('not writable')):
            self.assertEqual(self.api.uninstall_app()['error'], 'not writable')
        self.api._window.destroy.assert_not_called()
        self.assertIsNone(self.api._uninstall_plan)

    def test_confirmed_request_closes_only_after_staging_and_rejects_duplicate(self):
        plan = Path('fixture-plan.json')
        with patch.object(removal, 'stage_uninstall', return_value=plan) as stage:
            self.assertEqual(self.api.uninstall_app(True), dict(ok=True))
            self.assertEqual(self.api.uninstall_app(True)['error'], 'update_busy')
        self.assertEqual(stage.call_args.args[2], True)
        self.assertEqual(stage.call_args.args[3], [self.api._state['folder']])
        self.api._window.destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
