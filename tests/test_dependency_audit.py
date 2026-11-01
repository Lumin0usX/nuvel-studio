# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from dependency_audit import ffmpeg_evidence


class FFmpegAuditTests(unittest.TestCase):
    def test_exact_binary_flags_and_license_are_reported_without_claiming_clearance(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'ffmpeg.exe'; binary.write_bytes(b'binary fixture')
            version = 'ffmpeg version fixture\nconfiguration: --enable-gpl --enable-version3 --enable-libx264\n'
            license_text = 'GNU General Public License version 3 or later'
            results = [subprocess.CompletedProcess([], 0, version, ''),
                       subprocess.CompletedProcess([], 0, license_text, '')]
            with patch('dependency_audit.subprocess.run', side_effect=results) as run:
                report = ffmpeg_evidence(binary)
            self.assertEqual(run.call_args_list[1].args[0], [str(binary), '-L'])
            self.assertTrue(report['gpl_enabled'])
            self.assertTrue(report['version3_enabled'])
            self.assertFalse(report['nonfree_enabled'])
            self.assertEqual(report['outputs']['license']['stdout'], license_text)
            self.assertEqual(len(report['sha256']), 64)
            self.assertIn('remain to be verified', report['status'])

    def test_failed_probe_does_not_fall_back_to_an_assumed_license(self):
        with patch('dependency_audit.subprocess.run', side_effect=subprocess.CalledProcessError(1, ['ffmpeg'])):
            with self.assertRaises(subprocess.CalledProcessError):
                ffmpeg_evidence('ffmpeg')
