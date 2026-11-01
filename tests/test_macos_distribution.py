# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Verify publication/rollback on disk; the actual native UI test runs during each Mac build."""
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
import unicodedata
from unittest.mock import patch

import macos_distribution as distribution
from app_version import DISPLAY_NAME
from update_installer import check_bundle, executable_in, unpack, write_marker


class MacDistributionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="NUVEL ไทย & ' build ")
        self.addCleanup(temporary.cleanup)
        # macOS exposes its temporary directory through the /var -> /private/var symlink.
        self.project = Path(temporary.name).resolve()
        self.built = self.project / 'dist/new-build' / distribution.APP_NAME
        self.current = self.project / distribution.APP_NAME
        self.make_app(self.built, 'new')
        self.make_app(self.current, 'old')

    def make_app(self, path, version, executable=DISPLAY_NAME):
        (path / 'Contents/MacOS').mkdir(parents=True)
        with (path / 'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleIdentifier': distribution.BUNDLE_ID,
                          'CFBundleExecutable': executable}, stream)
        (path / 'Contents/MacOS' / executable).write_text(version, encoding='utf-8')

    def version(self, path):
        folder = path / 'Contents/MacOS'
        return (folder / DISPLAY_NAME).read_text(encoding='utf-8')

    def require_symlinks(self):
        probe = self.project / 'symlink-probe'
        try:
            probe.symlink_to(self.current, target_is_directory=True)
        except OSError:
            self.skipTest('Creating symlinks is not permitted on this account')
        probe.unlink()

    def publish(self, verifier=None, archiver=None):
        def archive(app, destination):
            destination.write_bytes(b'tested archive')
        with patch.object(distribution, 'copy_bundle', side_effect=lambda source, target: shutil.copytree(source, target)), \
                patch.object(distribution, 'verify_app', side_effect=verifier) as verify, \
                patch.object(distribution, 'archive_bundle', side_effect=archiver or archive):
            result = distribution.publish_build(self.project, self.built)
        return result, verify

    def test_verified_app_is_published_at_a_stable_location_and_old_app_is_kept(self):
        def verify(candidate):
            self.assertNotEqual(candidate, self.built)
            self.assertEqual(self.version(candidate), 'new')
            self.assertEqual(self.version(self.current), 'old')
        result, verifier = self.publish(verifier=verify)
        self.assertEqual(result, self.current)
        self.assertEqual(self.version(self.current), 'new')
        verifier.assert_called_once()
        backups = list(self.built.parent.glob('previous-*-' + distribution.APP_NAME))
        self.assertEqual(len(backups), 1)
        self.assertEqual(self.version(backups[0]), 'old')
        self.assertEqual(self.version(self.built), 'new')
        self.assertTrue((self.built.parent / 'NUVEL-Studio-macOS-arm64.zip').is_file())

    def test_startup_failure_keeps_the_working_app(self):
        with self.assertRaisesRegex(RuntimeError, 'native startup failed'):
            self.publish(verifier=lambda _: (_ for _ in ()).throw(RuntimeError('native startup failed')))
        self.assertEqual(self.version(self.current), 'old')
        self.assertEqual(list(self.built.parent.glob('previous-*')), [])
        self.assertEqual(list(self.project.glob('.studio-publish-*')), [])

    def test_archive_failure_does_not_replace_the_working_app(self):
        with self.assertRaises(OSError):
            self.publish(archiver=lambda *_: (_ for _ in ()).throw(OSError('archive failed')))
        self.assertEqual(self.version(self.current), 'old')

    def test_late_publication_failure_restores_the_previous_app(self):
        with patch.object(distribution.os, 'replace', side_effect=OSError('fixture final publication failed')):
            with self.assertRaises(OSError):
                self.publish()
        self.assertEqual(self.version(self.current), 'old')
        self.assertEqual(list(self.project.glob('.studio-publish-*')), [])

    def test_unrelated_app_is_never_overwritten(self):
        with (self.current / 'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleIdentifier': 'someone.else.app'}, stream)
        with self.assertRaisesRegex(RuntimeError, 'unrelated application'):
            self.publish()
        self.assertEqual(self.version(self.current), 'old')

    def make_previous_identity(self, version='1.1.4'):
        info_path = self.current / 'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleIdentifier='local.ytdlstudio.app',
                    CFBundleName=DISPLAY_NAME, CFBundleDisplayName=DISPLAY_NAME,
                    CFBundleVersion=version, CFBundleShortVersionString=version)
        info_path.write_bytes(plistlib.dumps(info))
        marker = self.current / 'Contents/Resources/studio-build.json'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(dict(product='YTDL Studio', platform='macos-arm64',
                                         version=version)), encoding='utf-8')

    def test_rebranded_releases_and_decomposed_executable_are_recognized(self):
        folder = self.current / 'Contents/MacOS'
        executable_name = unicodedata.normalize('NFD', DISPLAY_NAME)
        intermediate = folder / 'renaming'
        (folder / DISPLAY_NAME).rename(intermediate)
        intermediate.rename(folder / executable_name)
        for version in ('1.1.2', '1.1.3', '1.1.4'):
            with self.subTest(version=version):
                self.make_previous_identity(version)
                info_path = self.current / 'Contents/Info.plist'
                info = plistlib.loads(info_path.read_bytes())
                info['CFBundleExecutable'] = executable_name
                info_path.write_bytes(plistlib.dumps(info))
                distribution._check_existing(self.current, self.project)

    def test_previous_identity_migrates_only_after_native_verification(self):
        self.make_previous_identity()
        original_info = (self.current / 'Contents/Info.plist').read_bytes()
        def verify(candidate):
            self.assertEqual(self.version(self.current), 'old')
            self.assertEqual(self.version(candidate), 'new')
        result, verifier = self.publish(verifier=verify)
        self.assertEqual(result, self.current)
        self.assertEqual(self.version(self.current), 'new')
        verifier.assert_called_once()
        backup, = self.built.parent.glob('previous-*-' + distribution.APP_NAME)
        self.assertEqual(self.version(backup), 'old')
        self.assertEqual((backup / 'Contents/Info.plist').read_bytes(), original_info)

    def test_previous_identity_is_preserved_on_startup_or_publication_failure(self):
        self.make_previous_identity()
        with self.assertRaisesRegex(RuntimeError, 'native startup failed'):
            self.publish(verifier=lambda _: (_ for _ in ()).throw(RuntimeError('native startup failed')))
        self.assertEqual(self.version(self.current), 'old')
        self.assertEqual(list(self.built.parent.glob('previous-*')), [])
        with patch.object(distribution.os, 'replace', side_effect=OSError('publication failed')):
            with self.assertRaisesRegex(OSError, 'publication failed'):
                self.publish()
        self.assertEqual(self.version(self.current), 'old')
        self.assertEqual(list(self.built.parent.glob('previous-*')), [])

    def test_previous_bundle_id_alone_does_not_allow_replacement(self):
        self.make_previous_identity()
        marker = self.current / 'Contents/Resources/studio-build.json'
        original = json.loads(marker.read_text(encoding='utf-8'))
        for change in (dict(product=DISPLAY_NAME), dict(platform='windows-x64'),
                       dict(version='2.0.0'), dict(version='1.1.3'), dict(version='invalid')):
            with self.subTest(change=change):
                marker.write_text(json.dumps(original | change), encoding='utf-8')
                with self.assertRaisesRegex(RuntimeError, 'unrelated application'):
                    self.publish()
                self.assertEqual(self.version(self.current), 'old')
        marker.unlink()
        with self.assertRaisesRegex(RuntimeError, 'unrelated application'):
            self.publish()

    def test_previous_identity_requires_our_name_and_existing_executable(self):
        self.make_previous_identity()
        info_path = self.current / 'Contents/Info.plist'
        original = plistlib.loads(info_path.read_bytes())
        for change in (dict(CFBundleIdentifier='someone.else.app'),
                       dict(CFBundleName='Another app'),
                       dict(CFBundleExecutable='../other'),
                       dict(CFBundleVersion='1.1.3')):
            with self.subTest(change=change):
                info_path.write_bytes(plistlib.dumps(original | change))
                with self.assertRaisesRegex(RuntimeError, 'unrelated application'):
                    self.publish()
        info_path.write_bytes(plistlib.dumps(original))
        (self.current / 'Contents/MacOS' / DISPLAY_NAME).unlink()
        with self.assertRaisesRegex(RuntimeError, 'unrelated application'):
            self.publish()

    def test_build_outside_dist_is_not_published(self):
        with self.assertRaises(ValueError):
            distribution.publish_build(self.project, self.current)
        self.assertEqual(self.version(self.current), 'old')


    @unittest.skipUnless(sys.platform == 'darwin', 'macOS ditto archive tools required')
    def test_archive_uses_the_product_name_and_round_trips_through_the_updater(self):
        (self.built / 'Contents/Resources').mkdir()
        write_marker(self.built, 'macos-arm64')
        archive = self.project / 'update.zip'
        distribution.archive_bundle(self.built, archive)
        with zipfile.ZipFile(archive) as package:
            self.assertIn('NÜVEL Studio.app/Contents/Info.plist', package.namelist())
        candidate = unpack(archive, self.project / 'unpacked', 'macos-arm64')
        check_bundle(candidate, 'macos-arm64')
        self.assertEqual(executable_in(candidate, 'macos-arm64').name, DISPLAY_NAME)
        self.assertEqual(list((candidate / 'Contents/MacOS').iterdir()),
                         [executable_in(candidate, 'macos-arm64')])

    def test_os_launch_success_without_native_proof_is_rejected(self):
        with patch.object(distribution.subprocess, 'run'):
            with self.assertRaisesRegex(RuntimeError, 'did not complete'):
                distribution.verify_app(self.built)

    def test_launch_failure_reports_the_os_diagnostic_and_preserves_the_app(self):
        failure = subprocess.CalledProcessError(1, ['open'], stderr=b'kLSNoExecutableErr')
        with patch.object(distribution.subprocess, 'run', side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, 'exit code 1.*kLSNoExecutableErr.*previous app was kept'):
                distribution.verify_app(self.built)
        self.assertEqual(self.version(self.current), 'old')

    def test_native_proof_must_come_from_the_app_being_built(self):
        def launch(command, **kwargs):
            self.assertEqual(command[:4], ['/usr/bin/open', '-n', '-W', str(self.built)])
            Path(command[-1]).write_text(json.dumps({'ok': True, 'executable': 'another-app'}), encoding='utf-8')
        with patch.object(distribution.subprocess, 'run', side_effect=launch):
            with self.assertRaisesRegex(RuntimeError, 'invalid startup result'):
                distribution.verify_app(self.built)

    def test_native_proof_is_accepted_after_launchservices_exits(self):
        def launch(command, **kwargs):
            Path(command[-1]).write_text(json.dumps({'ok': True,
                'executable': str(self.built / 'Contents/MacOS' / DISPLAY_NAME)}), encoding='utf-8')
        with patch.object(distribution.subprocess, 'run', side_effect=launch):
            distribution.verify_app(self.built)


    @unittest.skipUnless(sys.platform == 'darwin', 'macOS filename normalization required')
    def test_decomposed_executable_accepts_equivalent_native_proof(self):
        folder = self.built / 'Contents/MacOS'
        name = unicodedata.normalize('NFD', DISPLAY_NAME)
        temporary = folder / 'rename-temporary'
        (folder / DISPLAY_NAME).rename(temporary)
        temporary.rename(folder / name)
        info_path = self.built / 'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info['CFBundleExecutable'] = name
        info_path.write_bytes(plistlib.dumps(info))
        self.assertEqual(executable_in(self.built, 'macos-arm64').name, name)
        def launch(command, **kwargs):
            Path(command[-1]).write_text(json.dumps({'ok': True,
                'executable': str(folder / DISPLAY_NAME)}), encoding='utf-8')
        with patch.object(distribution.subprocess, 'run', side_effect=launch):
            distribution.verify_app(self.built)

    def test_failed_deep_signature_verification_is_not_accepted(self):
        failure = subprocess.CalledProcessError(1, ['codesign'], stderr=b'invalid sealed resource')
        with patch.object(distribution.subprocess, 'run', side_effect=[None, failure]) as run:
            with self.assertRaisesRegex(RuntimeError, 'invalid sealed resource'):
                distribution.sign_bundle(self.built)
        self.assertEqual(run.call_args.args[0][1:4], ['--verify', '--deep', '--strict'])

    def test_invalid_framework_seal_prevents_signing_the_outer_app(self):
        framework = self.built / 'Contents/Frameworks/Python.framework'
        framework.mkdir(parents=True)
        failure = subprocess.CalledProcessError(1, ['codesign'], stderr=b'invalid framework seal')
        with patch.object(distribution.subprocess, 'run', side_effect=failure) as run:
            with self.assertRaisesRegex(RuntimeError, 'invalid framework seal'):
                distribution.sign_bundle(self.built)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-1], str(framework))


if __name__ == '__main__':
    unittest.main()
