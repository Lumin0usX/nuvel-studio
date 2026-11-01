# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Publication is tested on disk; actual packaged-UI acceptance is mandatory in the builder."""
import json
from pathlib import Path
import struct
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import windows_distribution as distribution


def gui_executable(path, subsystem=2):
    data = bytearray(160)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\x00\x00'
    struct.pack_into('<H', data, 156, subsystem)
    path.write_bytes(data)


class WindowsPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="NUVEL ไทย & ' Windows ")
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        self.built = self.project / 'dist/build-one/NÜVEL Studio'
        self.built.mkdir(parents=True)
        gui_executable(self.built / distribution.EXECUTABLE)
        (self.built / 'version.txt').write_text('new', encoding='utf-8')
        resources = self.built / '_internal/ui'
        resources.mkdir(parents=True)
        (resources / 'index.html').write_text('native UI', encoding='utf-8')
        self.current = self.project / distribution.FOLDER
        self.current.mkdir()
        (self.current / distribution.MARKER).write_text(json.dumps({'product': 'NÜVEL Studio', 'platform': 'windows'}))
        (self.current / 'version.txt').write_text('old', encoding='utf-8')
        self.shortcut = self.project / distribution.SHORTCUT
        self.shortcut.write_bytes(b'old shortcut')

    def publish(self, verify=None, shortcut_error=None):
        def accept(candidate, **kwargs):
            if verify:
                verify(candidate)
        def shortcut(project, target=None, shortcut=None):
            if shortcut_error:
                raise shortcut_error
            self.assertEqual(target, self.current / distribution.EXECUTABLE)
            shortcut.write_bytes(b'new shortcut')
        with patch.object(distribution, 'verify_app', side_effect=accept), \
                patch.object(distribution, 'create_launcher', side_effect=shortcut):
            return distribution.publish_build(self.project, self.built)

    def old_app_is_intact(self):
        self.assertEqual((self.current / 'version.txt').read_text(), 'old')
        self.assertEqual(self.shortcut.read_bytes(), b'old shortcut')

    def test_publish_replaces_app_and_shortcut_after_verifying_the_relocated_copy(self):
        def verify(candidate):
            self.old_app_is_intact()
            self.assertNotEqual(candidate, self.built)
            self.assertTrue((candidate / '_internal/ui/index.html').is_file())
        result = self.publish(verify=verify)
        self.assertEqual(result, self.current / distribution.EXECUTABLE)
        self.assertEqual((self.current / 'version.txt').read_text(), 'new')
        self.assertEqual(self.shortcut.read_bytes(), b'new shortcut')
        backups = list(self.built.parent.glob('previous-*-nuvel-windows'))
        self.assertEqual((backups[0] / 'version.txt').read_text(), 'old')
        with zipfile.ZipFile(self.built.parent / 'NUVEL-Studio-Windows-x64.zip') as archive:
            self.assertIn('NÜVEL Studio/_internal/ui/index.html', archive.namelist())
            self.assertIn('NÜVEL Studio/' + distribution.EXECUTABLE, archive.namelist())
            self.assertEqual([name for name in archive.namelist() if name.endswith('.exe')],
                             ['NÜVEL Studio/' + distribution.EXECUTABLE])


    def test_startup_failure_does_not_change_the_previous_app_or_shortcut(self):
        def fail(_):
            raise RuntimeError('startup failed')
        with self.assertRaisesRegex(RuntimeError, 'startup failed'):
            self.publish(verify=fail)
        self.old_app_is_intact()

    def test_shortcut_creation_failure_does_not_replace_the_previous_app(self):
        with self.assertRaisesRegex(OSError, 'shortcut failed'):
            self.publish(shortcut_error=OSError('shortcut failed'))
        self.old_app_is_intact()

    def test_late_failure_rolls_back_both_app_and_shortcut(self):
        with patch.object(distribution.os, 'replace', side_effect=OSError('archive publication failed')):
            with self.assertRaises(OSError):
                self.publish()
        self.old_app_is_intact()
        self.assertEqual(list(self.project.glob('.studio-publish-*')), [])

    def test_locked_running_application_is_kept(self):
        rename = Path.rename
        def locked(path, target):
            if path == self.current:
                raise PermissionError('application is still running')
            return rename(path, target)
        with patch.object(Path, 'rename', new=locked), self.assertRaises(PermissionError):
            self.publish()
        self.old_app_is_intact()

    def test_unrelated_folder_is_never_overwritten(self):
        (self.current / distribution.MARKER).unlink()
        with self.assertRaisesRegex(RuntimeError, 'unrecognized folder'):
            self.publish()
        self.old_app_is_intact()

    def test_console_executable_cannot_pass_gui_check(self):
        gui_executable(self.built / distribution.EXECUTABLE, subsystem=3)
        with self.assertRaisesRegex(RuntimeError, 'console-free'):
            distribution.check_gui_executable(self.built / distribution.EXECUTABLE)


class WindowsAcceptanceTests(unittest.TestCase):
    def run_acceptance(self, proof=None, exit_code=0):
        temporary = tempfile.TemporaryDirectory(prefix='NUVEL exe proof ')
        self.addCleanup(temporary.cleanup)
        folder = Path(temporary.name)
        executable = folder / distribution.EXECUTABLE
        gui_executable(executable)
        process = Mock(pid=1234)
        process.poll.return_value = exit_code
        def spawn(command, **kwargs):
            def finish(timeout=None):
                if proof is not None:
                    data = dict(ok=True, executable=str(executable), console_attached=False)
                    data.update(proof)
                    Path(command[-1]).write_text(json.dumps(data), encoding='utf-8')
                return exit_code
            process.wait.side_effect = finish
            return process
        with patch.object(distribution, 'WindowsJob') as job, \
                patch.object(distribution.subprocess, 'Popen', side_effect=spawn):
            try:
                distribution.verify_app(folder)
            finally:
                job.return_value.close.assert_called_once()

    def test_exit_zero_without_native_ui_proof_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, 'did not confirm'):
            self.run_acceptance()

    def test_native_console_attached_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'invalid startup'):
            self.run_acceptance({'console_attached': True})

    def test_wrong_application_proof_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'invalid startup'):
            self.run_acceptance({'executable': 'somewhere-else.exe'})

    def test_native_gui_proof_passes(self):
        self.run_acceptance({})


    def test_local_build_uses_its_separate_managed_image_cli(self):
        import image_download
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary).resolve()
            engine = project / '.venv-windows-build/Scripts/gallery-dl.exe'
            engine.parent.mkdir(parents=True)
            engine.write_bytes(b'external CLI fixture')
            with patch.object(image_download.sys, 'frozen', True, create=True), \
                    patch.object(image_download.sys, 'platform', 'win32'), \
                    patch.object(image_download.sys, 'executable', str(project / 'nuvel-windows/NÜVEL Studio.exe')):
                self.assertEqual(image_download.gallery_command(), [str(engine)])


if __name__ == '__main__':
    unittest.main()
