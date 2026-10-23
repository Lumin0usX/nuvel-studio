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
        temporary = tempfile.TemporaryDirectory(prefix="YTDL ไทย & ' build ")
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
        return (folder / (DISPLAY_NAME if (folder / DISPLAY_NAME).exists() else 'YTDL Studio')).read_text(encoding='utf-8')

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
        legacy = self.project / distribution.LEGACY_NAME
        scripts = legacy / 'Contents/Resources/Scripts'
        scripts.mkdir(parents=True)
        (scripts / 'main.scpt').write_bytes(b'original source launcher')
        with (legacy / 'Contents/Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleExecutable': 'applet'}, stream)
        self.publish()
        self.assertFalse(legacy.exists() or legacy.is_symlink())
        backups = list(self.built.parent.glob('previous-*-' + distribution.LEGACY_NAME))
        self.assertEqual((backups[0] / 'Contents/Resources/Scripts/main.scpt').read_bytes(), b'original source launcher')

    def test_ytdl_app_migrates_to_nuvel_only_after_native_acceptance(self):
        shutil.rmtree(self.current)
        old = self.project / distribution.OLD_APP_NAME
        self.make_app(old, 'old', executable='YTDL Studio')
        def verify(candidate):
            self.assertFalse(self.current.exists())
            self.assertEqual(self.version(old), 'old')
            self.assertEqual(executable_in(candidate, 'macos-arm64').name, DISPLAY_NAME)
        result, _ = self.publish(verifier=verify)
        self.assertEqual(result.name, 'NÜVEL Studio.app')
        self.assertEqual(self.version(result), 'new')
        self.assertFalse(old.exists() or old.is_symlink())
        backup, = self.built.parent.glob('previous-*-' + distribution.OLD_APP_NAME)
        self.assertEqual(self.version(backup), 'old')

    def test_failed_native_migration_leaves_the_old_name_and_bundle_intact(self):
        shutil.rmtree(self.current)
        old = self.project / distribution.OLD_APP_NAME
        self.make_app(old, 'old', executable='YTDL Studio')
        with self.assertRaisesRegex(RuntimeError, 'native startup failed'):
            self.publish(verifier=lambda _: (_ for _ in ()).throw(RuntimeError('native startup failed')))
        self.assertFalse(self.current.exists())
        self.assertFalse(old.is_symlink())
        self.assertEqual(self.version(old), 'old')

    def test_late_migration_failure_restores_both_old_aliases(self):
        self.require_symlinks()
        shutil.rmtree(self.current)
        old = self.project / distribution.OLD_APP_NAME
        self.make_app(old, 'old', executable='YTDL Studio')
        legacy = self.project / distribution.LEGACY_NAME
        legacy.symlink_to(distribution.OLD_APP_NAME)
        with patch.object(distribution.os, 'replace', side_effect=OSError('archive publication failed')):
            with self.assertRaisesRegex(OSError, 'archive publication failed'):
                self.publish()
        self.assertFalse(self.current.exists())
        self.assertFalse(old.is_symlink())
        self.assertEqual(self.version(old), 'old')
        self.assertEqual(legacy.readlink(), Path(distribution.OLD_APP_NAME))
        self.assertEqual(legacy.resolve(), old)

    def test_another_build_removes_both_obsolete_launch_aliases(self):
        self.require_symlinks()
        old = self.project / distribution.OLD_APP_NAME
        legacy = self.project / distribution.LEGACY_NAME
        old.symlink_to(distribution.APP_NAME)
        legacy.symlink_to(distribution.APP_NAME)
        self.publish()
        self.assertEqual(self.version(self.current), 'new')
        for alias in (old, legacy):
            self.assertFalse(alias.exists() or alias.is_symlink())
            backup, = self.built.parent.glob('previous-*-' + alias.name)
            self.assertEqual(backup.readlink(), Path(distribution.APP_NAME))

    def test_late_publication_failure_restores_both_obsolete_launch_aliases(self):
        self.require_symlinks()
        aliases = [self.project / name for name in (distribution.OLD_APP_NAME, distribution.LEGACY_NAME)]
        for alias in aliases:
            alias.symlink_to(distribution.APP_NAME)
        with patch.object(distribution.os, 'replace', side_effect=OSError('archive publication failed')):
            with self.assertRaises(OSError):
                self.publish()
        self.assertEqual(self.version(self.current), 'old')
        for alias in aliases:
            self.assertEqual(alias.readlink(), Path(distribution.APP_NAME))
            self.assertEqual(alias.resolve(), self.current)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS ditto archive tools required')
    def test_renamed_app_archive_still_works_with_the_existing_updater_layout(self):
        (self.built / 'Contents/Resources').mkdir()
        write_marker(self.built, 'macos-arm64')
        alias = self.built / 'Contents/MacOS/YTDL Studio'
        alias.symlink_to(DISPLAY_NAME)
        archive = self.project / 'update.zip'
        distribution.archive_bundle(self.built, archive)
        with zipfile.ZipFile(archive) as package:
            self.assertIn('YTDL Studio.app/Contents/Info.plist', package.namelist())
        candidate = unpack(archive, self.project / 'unpacked', 'macos-arm64')
        check_bundle(candidate, 'macos-arm64')
        self.assertEqual(executable_in(candidate, 'macos-arm64').name, DISPLAY_NAME)
        self.assertEqual((candidate / 'Contents/MacOS/YTDL Studio').resolve(),
                         executable_in(candidate, 'macos-arm64'))

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

    def test_native_verification_also_accepts_the_previous_executable_name(self):
        old = self.project / 'dist/legacy' / distribution.OLD_APP_NAME
        self.make_app(old, 'old', executable='YTDL Studio')
        def launch(command, **kwargs):
            Path(command[-1]).write_text(json.dumps({'ok': True,
                'executable': str(old / 'Contents/MacOS/YTDL Studio')}), encoding='utf-8')
        with patch.object(distribution.subprocess, 'run', side_effect=launch):
            distribution.verify_app(old)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS filename normalization required')
    def test_decomposed_executable_accepts_equivalent_native_proof_and_legacy_alias(self):
        folder = self.built / 'Contents/MacOS'
        name = unicodedata.normalize('NFD', DISPLAY_NAME)
        temporary = folder / 'rename-temporary'
        (folder / DISPLAY_NAME).rename(temporary)
        temporary.rename(folder / name)
        alias = folder / 'YTDL Studio'
        alias.symlink_to(name)
        info_path = self.built / 'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info['CFBundleExecutable'] = name
        info_path.write_bytes(plistlib.dumps(info))
        self.assertEqual(executable_in(self.built, 'macos-arm64').name, name)
        self.assertEqual(alias.resolve(), executable_in(self.built, 'macos-arm64').resolve())
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
