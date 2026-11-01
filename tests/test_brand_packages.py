# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Unicode product roots must survive macOS ZIPs and reject ambiguous names."""
import json
from pathlib import Path
import plistlib
import stat
import tempfile
import unicodedata
import unittest
from unittest.mock import patch
import zipfile

from app_version import DISPLAY_NAME, VERSION
import release_client
import release_tools
import update_installer as installer


class BrandedPackageTests(unittest.TestCase):
    def make_mac_archive(self, archive):
        root = unicodedata.normalize('NFD', DISPLAY_NAME + '.app')
        executable = unicodedata.normalize('NFD', DISPLAY_NAME)
        marker = dict(product=DISPLAY_NAME, platform='macos-arm64', version=VERSION)
        with zipfile.ZipFile(archive, 'w') as package:
            package.writestr(root + '/Contents/Info.plist', plistlib.dumps(dict(
                CFBundleIdentifier=installer.APP_ID, CFBundleExecutable=executable)))
            package.writestr(root + '/Contents/Resources/studio-build.json', json.dumps(marker))
            package.writestr(root + '/Contents/MacOS/' + executable, b'native fixture')

    def test_decomposed_mac_root_round_trips_and_is_collected_for_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            folder = project / 'dist/build'; folder.mkdir(parents=True)
            archive = folder / release_client.ASSETS['macos-arm64']
            self.make_mac_archive(archive)
            candidate = installer.unpack(archive, project / 'unpacked', 'macos-arm64')
            self.assertEqual(candidate.name, DISPLAY_NAME + '.app')
            installer.check_bundle(candidate, 'macos-arm64', VERSION)
            self.assertTrue(installer.executable_in(candidate, 'macos-arm64').is_file())
            release_tools.collect(project, 'macos-arm64', project / 'release')
            self.assertEqual((project / 'release' / archive.name).read_bytes(), archive.read_bytes())

    def test_canonically_equivalent_archive_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = DISPLAY_NAME + '.app/Contents/Resources/file'
            with zipfile.ZipFile(root / 'bad.zip', 'w') as package:
                package.writestr(name, b'one')
                package.writestr(unicodedata.normalize('NFD', name), b'two')
            with patch.object(installer.subprocess, 'run') as run:
                with self.assertRaises(release_client.UpdateError):
                    installer.unpack(root / 'bad.zip', root / 'new', 'macos-arm64')
            run.assert_not_called()

    def test_normalized_alias_cannot_bypass_symlink_parent_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix = DISPLAY_NAME + '.app/Contents/'
            alias = zipfile.ZipInfo(prefix + 'A\u0301lias')
            alias.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(root / 'bad.zip', 'w') as package:
                package.writestr(alias, 'Versions')
                package.writestr(prefix + '\u00c1lias/file', b'payload')
            with patch.object(installer.subprocess, 'run') as run:
                with self.assertRaises(release_client.UpdateError):
                    installer.unpack(root / 'bad.zip', root / 'new', 'macos-arm64')
            run.assert_not_called()

    def test_foreign_marker_does_not_become_valid_from_the_executable_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            installer.executable_in(bundle, 'windows-x64').write_bytes(b'foreign executable')
            installer.marker_path(bundle, 'windows-x64').write_text(json.dumps(dict(
                product='Another Studio', platform='windows-x64', version=VERSION)))
            with self.assertRaises(release_client.UpdateError):
                installer.check_bundle(bundle, 'windows-x64')
