# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""A failed isolated CLI must stop packaging and report the actual loader error."""
import subprocess
import unittest
from unittest.mock import patch

from build_gallery_tool import verify_tool


class GalleryToolAcceptanceTests(unittest.TestCase):
    def test_loader_failure_exposes_stderr_instead_of_only_a_generic_error(self):
        result = subprocess.CompletedProcess([], 1, '', 'semctl: Operation not permitted\n')
        with patch('build_gallery_tool.subprocess.run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'exit code 1.*\nsemctl: Operation not permitted'):
                verify_tool('gallery-dl')

    def test_exit_zero_without_extractors_is_still_rejected(self):
        result = subprocess.CompletedProcess([], 0, ' \n', '')
        with patch('build_gallery_tool.subprocess.run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'No extractor output'):
                verify_tool('gallery-dl')

    def test_extractor_output_with_nonzero_exit_is_still_rejected(self):
        result = subprocess.CompletedProcess([], 2, 'instagram\n', '')
        with patch('build_gallery_tool.subprocess.run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'exit code 2.*\ninstagram'):
                verify_tool('gallery-dl')

    def test_success_requires_the_isolated_cli_to_return_extractors(self):
        result = subprocess.CompletedProcess([], 0, 'instagram\n', '')
        with patch('build_gallery_tool.subprocess.run', return_value=result) as run:
            verify_tool('gallery-dl')
        self.assertEqual(run.call_args.args[0], ['gallery-dl', '--config-ignore', '--list-modules'])
        self.assertEqual(run.call_args.kwargs['timeout'], 60)


if __name__ == '__main__':
    unittest.main()
