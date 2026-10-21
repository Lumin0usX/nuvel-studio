"""Verify publication/rollback on disk; the actual native UI test runs during each Mac build."""
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import macos_distribution as distribution


class MacDistributionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="YTDL ไทย & ' build ")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.built = self.project / 'dist/new-build' / distribution.APP_NAME
        self.current = self.project / distribution.APP_NAME
        self.make_app(self.built, 'new')
        self.make_app(self.current, 'old')

    def make_app(self, path, version):
        (path / 'Contents/MacOS').mkdir(parents=True)
        with (path / 'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleIdentifier': distribution.BUNDLE_ID,
                          'CFBundleExecutable': 'YTDL Studio'}, stream)
        (path / 'Contents/MacOS/YTDL Studio').write_text(version, encoding='utf-8')

    def version(self, path):
        return (path / 'Contents/MacOS/YTDL Studio').read_text(encoding='utf-8')

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
        self.assertTrue((self.built.parent / 'YTDL-Studio-macOS-arm64.zip').is_file())

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

    def test_build_outside_dist_is_not_published(self):
        with self.assertRaises(ValueError):
            distribution.publish_build(self.project, self.current)
        self.assertEqual(self.version(self.current), 'old')

    def test_previous_source_launcher_is_automatically_migrated(self):
        # Only this OS primitive may be unavailable on Windows without Developer Mode.
        probe = self.project / 'symlink-probe'
        try:
            probe.symlink_to(self.current, target_is_directory=True)
        except OSError:
            self.skipTest('Creating symlinks is not permitted on this Windows account')
        probe.unlink()
        legacy = self.project / distribution.LEGACY_NAME
        scripts = legacy / 'Contents/Resources/Scripts'
        scripts.mkdir(parents=True)
        (scripts / 'main.scpt').write_bytes(b'original source launcher')
        with (legacy / 'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleExecutable': 'applet'}, stream)
        self.publish()
        self.assertTrue(legacy.is_symlink())
        self.assertEqual(legacy.resolve(), self.current.resolve())
        backups = list(self.built.parent.glob('previous-*-' + distribution.LEGACY_NAME))
        self.assertEqual((backups[0] / 'Contents/Resources/Scripts/main.scpt').read_bytes(), b'original source launcher')

    def test_os_launch_success_without_native_proof_is_rejected(self):
        with patch.object(distribution.subprocess, 'run'):
            with self.assertRaisesRegex(RuntimeError, 'did not complete'):
                distribution.verify_app(self.built)

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
                'executable': str(self.built / 'Contents/MacOS/YTDL Studio')}), encoding='utf-8')
        with patch.object(distribution.subprocess, 'run', side_effect=launch):
            distribution.verify_app(self.built)


if __name__ == '__main__':
    unittest.main()
