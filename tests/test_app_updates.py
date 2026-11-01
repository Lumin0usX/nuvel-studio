# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Release transport, real archive/rollback operations, and native-bridge guards."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request
import zipfile

import app_updates
from app_version import VERSION, REPOSITORY, version_tuple
from glass_app import StudioAPI
import release_client as releases
import release_tools
import update_installer as installer
import update_credentials


class ReleaseTransportTests(unittest.TestCase):
    def setUp(self):
        self.client = releases.ReleaseClient('github_pat_test_secret')
        self.client.opener = Mock()

    def test_stable_version_order_is_numeric_and_rejects_prerelease(self):
        self.assertGreater(version_tuple('v1.10.0'), version_tuple('1.9.9'))
        for tag in ('1.2', 'v1.2.3-beta', '../1.2.3', '01.2.3'):
            with self.assertRaises(ValueError):
                version_tuple(tag)

    def test_credentials_only_go_to_fixed_repository_api(self):
        path = '/repos/' + REPOSITORY + '/releases/latest'
        self.client.open(path)
        request = self.client.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.github.com' + path)
        self.assertEqual(request.get_header('Authorization'), 'Bearer github_pat_test_secret')
        for path in ('https://evil.test', '/repos/attacker/repo/releases/latest', '/repos/' + REPOSITORY + '/releases/../secrets'):
            with self.assertRaises(releases.UpdateError):
                self.client.open(path)

    def test_asset_redirect_strips_auth_and_rejects_untrusted_host(self):
        request = Request('https://api.github.com/repos/' + REPOSITORY + '/releases/assets/1',
                          headers={'Authorization': 'Bearer secret'})
        handler = releases.ReleaseRedirect()
        redirected = handler.redirect_request(request, None, 302, '', {},
                                                'https://release-assets.githubusercontent.com/file?signature=abc')
        self.assertIsNone(redirected.get_header('Authorization'))
        for url in ('http://github.com/file', 'https://github.com.evil.test/file', 'https://evil.test/file'):
            with self.assertRaises(releases.UpdateError):
                handler.redirect_request(request, None, 302, '', {}, url)

    def release_fixture(self):
        manifest = dict(schema=1, version='99.0.0', platforms={'windows-x64': dict(
            name=releases.ASSETS['windows-x64'], size=1234, sha256='a' * 64)})
        assets = [dict(name=releases.MANIFEST, id=1, state='uploaded', size=100),
                  dict(name=releases.ASSETS['windows-x64'], id=2, state='uploaded', size=1234)]
        release = dict(tag_name='v99.0.0', assets=assets, body='Real notes')
        return release, manifest

    def test_complete_release_requires_matching_version_size_and_platform_hash(self):
        release, manifest = self.release_fixture()
        with patch.object(self.client, 'json', return_value=manifest):
            resolved = self.client.resolve(release, 'windows-x64')
            self.assertEqual(resolved['version'], '99.0.0')
            self.assertNotIn('token', json.dumps(resolved))
            manifest['version'] = '98.0.0'
            with self.assertRaises(releases.UpdateError):
                self.client.resolve(release, 'windows-x64')
            manifest['version'] = '99.0.0'
            release['assets'][1]['size'] = 1
            with self.assertRaises(releases.UpdateError):
                self.client.resolve(release, 'windows-x64')

    def test_newest_stable_semantic_version_and_empty_repository(self):
        items = [dict(tag_name='v1.99.0', draft=True), dict(tag_name='v2.0.0-beta', prerelease=True),
                 dict(tag_name='v1.9.0'), dict(tag_name='v1.10.0')]
        with patch.object(self.client, 'json', return_value=items), patch.object(self.client, 'resolve') as resolve:
            self.client.latest('windows-x64')
            self.assertEqual(resolve.call_args.args[0]['tag_name'], 'v1.10.0')
        with patch.object(self.client, 'json', return_value=[]):
            with self.assertRaisesRegex(releases.UpdateError, 'no_release'):
                self.client.latest('windows-x64')

    def test_download_checks_bytes_hash_and_cancellation_without_leaving_partials(self):
        payload = b'real fixture zip bytes'
        release = dict(path='/repos/' + REPOSITORY + '/releases/assets/2', size=len(payload),
                       sha256=hashlib.sha256(payload).hexdigest())
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'update.zip'
            progress = []
            with patch.object(self.client, 'open', return_value=io.BytesIO(payload)):
                self.client.download(release, destination, progress.append, threading.Event())
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(progress[-1], 100)
            destination.unlink()
            for bad in (payload[:-1], payload + b'extra', b'x' * len(payload)):
                with patch.object(self.client, 'open', return_value=io.BytesIO(bad)):
                    with self.assertRaises(releases.UpdateError):
                        self.client.download(release, destination, progress.append, threading.Event())
                self.assertFalse(destination.exists())
            cancel = threading.Event(); cancel.set()
            with patch.object(self.client, 'open', return_value=io.BytesIO(payload)):
                with self.assertRaisesRegex(releases.UpdateError, 'cancelled'):
                    self.client.download(release, destination, progress.append, cancel)
            self.assertFalse(destination.exists())


def fixture_bundle(path, version=VERSION):
    path.mkdir(parents=True)
    installer.executable_in(path, 'windows-x64').write_bytes(b'GUI executable fixture')
    installer.write_marker(path, 'windows-x64')
    marker = json.loads((path / installer.MARKER).read_text())
    marker['version'] = version
    (path / installer.MARKER).write_text(json.dumps(marker))
    (path / 'content.txt').write_text(version)
    return path


class InstallTransactions(unittest.TestCase):
    def test_windows_executable_must_be_a_file_with_the_product_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = fixture_bundle(Path(temporary) / 'app')
            primary = installer.executable_in(bundle, 'windows-x64')
            primary.rename(bundle / 'another-product.exe')
            primary.mkdir()
            with self.assertRaisesRegex(releases.UpdateError, 'invalid_package'):
                installer.check_bundle(bundle, 'windows-x64')

    def test_mac_symlinks_cannot_escape_or_receive_files_through_case_aliases(self):
        for target, child in (('../../../../outside', None), ('Versions', 'alias/file'), ('Versions', 'Alias/file')):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                link = zipfile.ZipInfo('NÜVEL Studio.app/Contents/Alias')
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                with zipfile.ZipFile(root / 'bad.zip', 'w') as package:
                    package.writestr(link, target)
                    if child:
                        package.writestr('NÜVEL Studio.app/Contents/' + child, b'not allowed through link')
                with self.assertRaises(releases.UpdateError), patch.object(installer.subprocess, 'run') as run:
                    installer.unpack(root / 'bad.zip', root / 'new', 'macos-arm64')
                run.assert_not_called()

    @unittest.skipIf(os.name == 'nt', 'Native macOS/Linux symlinks required')
    def test_framework_symlinks_inside_mac_bundle_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            framework = 'NÜVEL Studio.app/Contents/Frameworks/Python.framework/'
            with zipfile.ZipFile(root / 'mac.zip', 'w') as package:
                package.writestr(framework + 'Versions/3.12/Python', b'framework binary')
                for name, target in (('Versions/Current', '3.12'), ('Python', 'Versions/Current/Python')):
                    info = zipfile.ZipInfo(framework + name)
                    info.create_system = 3
                    info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    package.writestr(info, target)
            bundle = installer.unpack(root / 'mac.zip', root / 'new', 'macos-arm64')
            link = bundle / 'Contents/Frameworks/Python.framework/Python'
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.read_bytes(), b'framework binary')

    def test_extraction_rejects_traversal_absolute_paths_and_unexpected_root(self):
        for name in ('../outside', '/outside', 'NÜVEL Studio/../../outside',
                     'NÜVEL Studio/C:/outside', 'another-app/file', 'NÜVEL Studio\\outside'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with zipfile.ZipFile(root / 'bad.zip', 'w') as package:
                    info = zipfile.ZipInfo('placeholder')
                    info.filename = name
                    package.writestr(info, b'bad')
                with self.assertRaises(releases.UpdateError):
                    installer.unpack(root / 'bad.zip', root / 'new', 'windows-x64')
                self.assertFalse((root / 'outside').exists())

    def test_windows_archives_cannot_contain_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            info = zipfile.ZipInfo('NÜVEL Studio/link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(root / 'bad.zip', 'w') as package:
                package.writestr(info, '../outside')
            with self.assertRaises(releases.UpdateError):
                installer.unpack(root / 'bad.zip', root / 'new', 'windows-x64')

    def plan_fixture(self, root):
        target = fixture_bundle(root / 'installed app')
        stage = root / '.nuvel-update-test'
        stage.mkdir()
        candidate = fixture_bundle(stage / 'new/NÜVEL Studio', '99.0.0')
        plan = stage / 'plan.json'
        plan.write_text(json.dumps(dict(schema=1, target=str(target), candidate=str(candidate),
                                       platform='windows-x64', version='99.0.0')))
        return target, stage, candidate, plan

    def test_success_swaps_app_keeps_previous_and_does_not_touch_downloads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target, stage, candidate, plan = self.plan_fixture(root)
            media = root / 'my-video.mp4'; media.write_bytes(b'keep media')
            preferences = root / 'preferences.json'; preferences.write_text('keep settings')
            with patch.object(installer, 'verify_native') as verify, patch.object(installer, 'restart') as restart:
                installer.replace_bundle(plan)
            self.assertEqual((target / 'content.txt').read_text(), '99.0.0')
            self.assertEqual((stage / 'previous/content.txt').read_text(), VERSION)
            self.assertEqual(media.read_bytes(), b'keep media')
            self.assertEqual(preferences.read_text(), 'keep settings')
            verify.assert_called_once_with(target, 'windows-x64')
            restart.assert_called_once_with(target, 'windows-x64')

    def test_bad_native_startup_rolls_back_and_reopens_previous(self):
        with tempfile.TemporaryDirectory() as temporary:
            target, stage, candidate, plan = self.plan_fixture(Path(temporary).resolve())
            with patch.object(installer, 'verify_native', side_effect=RuntimeError('bad native UI')), \
                    patch.object(installer, 'restart') as restart:
                with self.assertRaisesRegex(RuntimeError, 'bad native UI'):
                    installer.replace_bundle(plan)
            self.assertEqual((target / 'content.txt').read_text(), VERSION)
            self.assertTrue(candidate.is_dir())
            restart.assert_called_once_with(target, 'windows-x64')

    def test_plan_cannot_replace_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            target, stage, candidate, plan = self.plan_fixture(Path(temporary).resolve())
            (target / installer.MARKER).unlink()
            with self.assertRaises(releases.UpdateError):
                installer.replace_bundle(plan)
            self.assertEqual((target / 'content.txt').read_text(), VERSION)

    def test_a_stale_plan_cannot_downgrade_a_newer_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            target, stage, candidate, plan = self.plan_fixture(Path(temporary).resolve())
            marker = json.loads((target / installer.MARKER).read_text())
            marker['version'] = '100.0.0'
            (target / installer.MARKER).write_text(json.dumps(marker))
            with self.assertRaises(releases.UpdateError):
                installer.replace_bundle(plan)
            self.assertTrue(target.is_dir())

    def test_cleanup_only_removes_completed_recognized_old_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target, active, candidate, plan = self.plan_fixture(root)
            old = root / '.nuvel-update-old'
            fixture_bundle(old / 'previous')
            fixture_bundle(old / 'helper' / target.name)
            (old / 'result.json').write_text(json.dumps(dict(ok=True, version='1.0.0')))
            (old / 'plan.json').write_text(json.dumps(dict(target=str(target), platform='windows-x64')))
            unrelated = root / '.nuvel-update-personal'; unrelated.mkdir()
            (unrelated / 'keep.txt').write_text('keep')
            installer.cleanup_completed(target, active, 'windows-x64')
            self.assertFalse(old.exists())
            self.assertTrue(active.exists())
            self.assertEqual((unrelated / 'keep.txt').read_text(), 'keep')

    def test_complete_package_is_staged_and_verified_before_old_app_changes(self):
        from windows_distribution import archive_bundle
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            current = fixture_bundle(root / 'my installed app')
            built = fixture_bundle(root / 'built/NÜVEL Studio', '99.0.0')
            stage = root / '.nuvel-update-test'; stage.mkdir()
            archive_bundle(built, stage / 'package.zip')
            with patch.object(installer, 'verify_native') as verify:
                plan = installer.stage_update(current, stage / 'package.zip', stage, 'windows-x64', '99.0.0')
            installer.read_plan(plan)
            self.assertEqual((current / 'content.txt').read_text(), VERSION)
            self.assertTrue((stage / 'helper' / current.name / 'content.txt').is_file())
            verify.assert_called_once()


class UpdateServiceTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows Credential Manager required')
    def test_windows_secure_store_round_trip_uses_only_a_disposable_credential(self):
        import uuid
        with patch.object(update_credentials, 'SERVICE', 'NuvelStudio.Test.' + uuid.uuid4().hex):
            try:
                try:
                    update_credentials.windows_token('github_pat_disposable_test')
                except OSError as exc:
                    if exc.errno in (5, 1312):
                        self.skipTest('This Windows session does not allow Credential Manager: ' + str(exc.errno))
                    raise
                self.assertEqual(update_credentials.windows_token(), 'github_pat_disposable_test')
            finally:
                update_credentials.windows_token(delete=True)
            self.assertEqual(update_credentials.windows_token(), '')

    def test_native_install_is_blocked_during_media_transfer(self):
        with patch.object(StudioAPI, '_scan'):
            api = StudioAPI()
        api._window = Mock()
        api._update(phase='processing')
        result = api.install_app_update()
        self.assertEqual(result['error'], 'download_active')
        api._window.destroy.assert_not_called()

    def test_installer_only_closes_window_when_an_update_is_ready(self):
        with patch.object(StudioAPI, '_scan'):
            api = StudioAPI()
        api._window = Mock()
        self.assertIn('error', api.install_app_update())
        api._window.destroy.assert_not_called()
        api._updates.plan = Path('prepared-plan')
        api._updates.set(phase='ready')
        self.assertTrue(api.install_app_update()['ok'])
        api._window.destroy.assert_called_once()
        self.assertEqual(api.start_download({})['error'], 'update_busy')

    def test_secret_never_appears_in_snapshot_or_preferences(self):
        service = app_updates.AppUpdates()
        with patch.object(app_updates, 'credential') as store:
            self.assertTrue(service.connect('github_pat_sensitive')['ok'])
            store.assert_called_once_with('github_pat_sensitive')
        self.assertNotIn('github_pat_sensitive', json.dumps(service.snapshot()))

    def test_failed_credentials_never_leak_exception_text(self):
        with patch.object(app_updates, 'credential', side_effect=OSError('sensitive token value')):
            service = app_updates.AppUpdates()
            self.assertEqual(service.connect('secret'), dict(ok=True, session_only=True))
            self.assertNotIn('secret', json.dumps(service.snapshot()))

    def test_offline_and_no_release_are_actionable_and_do_not_change_installed_app(self):
        for code in ('network_error', 'no_release', 'access_required'):
            service = app_updates.AppUpdates(); service.token = 'secret'
            service.set(platform='windows-x64')
            with patch.object(app_updates.ReleaseClient, 'latest', side_effect=releases.UpdateError(code)):
                service._run(service._check)
            self.assertEqual(service.snapshot()['error'], code)
            self.assertIsNone(service.plan)

    def test_ready_update_cannot_be_overwritten_by_another_request(self):
        service = app_updates.AppUpdates(); service.set(phase='ready')
        self.assertEqual(service.check()['error'], 'update_busy')

    def test_mac_keychain_secret_is_passed_on_stdin_not_command_line(self):
        with patch.object(update_credentials.subprocess, 'run', return_value=Mock(returncode=0)) as run:
            update_credentials.mac_token('github_pat_sensitive')
        self.assertNotIn('github_pat_sensitive', repr(run.call_args.args))
        self.assertIn('github_pat_sensitive', run.call_args.kwargs['input'])

    def test_manifest_requires_both_platform_packages_and_hashes_actual_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / releases.ASSETS['windows-x64']).write_bytes(b'windows')
            with self.assertRaises(FileNotFoundError):
                release_tools.manifest(folder)
            self.assertFalse((folder / releases.MANIFEST).exists())
            (folder / releases.ASSETS['macos-arm64']).write_bytes(b'mac')
            release_tools.manifest(folder)
            data = json.loads((folder / releases.MANIFEST).read_text())
            self.assertEqual(data['version'], VERSION)
            self.assertEqual(data['platforms']['macos-arm64']['sha256'], hashlib.sha256(b'mac').hexdigest())


if __name__ == '__main__':
    unittest.main()
