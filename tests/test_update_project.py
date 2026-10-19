"""Use local Git repositories to verify updates without contacting GitHub."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from update_project import UpdateError, main, update_source


@unittest.skipUnless(shutil.which('git'), 'Git is required for updater integration tests')
class SourceUpdateTests(unittest.TestCase):
    def git(self, path, *args):
        return subprocess.run(['git', '-C', str(path), *args], check=True,
                              capture_output=True, text=True, timeout=15).stdout.strip()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ytdl-update-test-')
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.origin = root / 'origin.git'
        self.author = root / 'author'
        self.clone = root / 'YTDL Studio'
        self.git(root, 'init', '--bare', str(self.origin))
        self.git(root, 'init', '--initial-branch=main', str(self.author))
        self.identity(self.author)
        (self.author / 'program.txt').write_text('version one', encoding='utf-8')
        (self.author / '.gitignore').write_text('Downloads/\n.venv-macos/\n', encoding='utf-8')
        self.git(self.author, 'add', '.')
        self.git(self.author, 'commit', '-m', 'Initial')
        self.git(self.author, 'remote', 'add', 'origin', str(self.origin))
        self.git(self.author, 'push', 'origin', 'main')
        self.git(root, 'clone', '--branch', 'main', str(self.origin), str(self.clone))
        self.identity(self.clone)
        self.allowed = {str(self.origin).removesuffix('.git').lower()}
        self.before = self.git(self.clone, 'rev-parse', 'HEAD')

    def identity(self, path):
        self.git(path, 'config', 'user.name', 'Updater Test')
        self.git(path, 'config', 'user.email', 'updater@example.invalid')
        self.git(path, 'config', 'core.autocrlf', 'false')

    def publish(self):
        (self.author / 'program.txt').write_text('version two', encoding='utf-8')
        self.git(self.author, 'add', '.')
        self.git(self.author, 'commit', '-m', 'Update')
        self.git(self.author, 'push', 'origin', 'main')

    def update(self):
        with redirect_stdout(io.StringIO()):
            return update_source(self.clone, self.allowed)

    def unchanged(self):
        self.assertEqual(self.git(self.clone, 'rev-parse', 'HEAD'), self.before)

    def test_clean_clone_fast_forwards_and_preserves_ignored_downloads(self):
        self.publish()
        downloads = self.clone / 'Downloads'
        downloads.mkdir()
        media = downloads / 'keep.mp4'
        media.write_bytes(b'user media')
        self.assertTrue(self.update())
        self.assertEqual(self.git(self.clone, 'rev-parse', 'HEAD'), self.git(self.author, 'rev-parse', 'HEAD'))
        self.assertEqual((self.clone / 'program.txt').read_text(encoding='utf-8'), 'version two')
        self.assertEqual(media.read_bytes(), b'user media')
        self.assertEqual(self.git(self.clone, 'status', '--porcelain'), '')
        self.assertFalse(self.update())

    def test_already_current_does_not_change_commit(self):
        self.assertFalse(self.update())
        self.unchanged()

    def test_ignored_download_cannot_be_overwritten_by_a_new_tracked_file(self):
        for directory in (self.author, self.clone):
            (directory / 'Downloads').mkdir()
        original = self.clone / 'Downloads' / 'keep.mp4'
        original.write_bytes(b'user media')
        incoming = self.author / 'Downloads' / 'keep.mp4'
        incoming.write_bytes(b'different media')
        self.git(self.author, 'add', '-f', 'Downloads/keep.mp4')
        self.git(self.author, 'commit', '-m', 'Track conflicting file')
        self.git(self.author, 'push', 'origin', 'main')
        with self.assertRaises(UpdateError):
            self.update()
        self.assertEqual(original.read_bytes(), b'user media')
        self.unchanged()

    def test_local_edits_and_untracked_files_are_never_discarded(self):
        self.publish()
        edited = self.clone / 'program.txt'
        edited.write_text('my edits', encoding='utf-8')
        with self.assertRaisesRegex(UpdateError, 'Local changes'):
            self.update()
        self.assertEqual(edited.read_text(encoding='utf-8'), 'my edits')
        self.unchanged()
        self.git(self.clone, 'restore', 'program.txt')
        untracked = self.clone / 'my-notes.txt'
        untracked.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(UpdateError, 'untracked'):
            self.update()
        self.assertEqual(untracked.read_text(encoding='utf-8'), 'keep')
        self.unchanged()

    def test_local_commits_and_diverged_history_are_not_reset_or_merged(self):
        local = self.clone / 'my-work.txt'
        local.write_text('my work', encoding='utf-8')
        self.git(self.clone, 'add', '.')
        self.git(self.clone, 'commit', '-m', 'Local work')
        self.before = self.git(self.clone, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(UpdateError, 'history has diverged'):
            self.update()
        self.unchanged()
        self.publish()
        with self.assertRaisesRegex(UpdateError, 'history has diverged'):
            self.update()
        self.unchanged()
        self.assertEqual(local.read_text(encoding='utf-8'), 'my work')

    def test_wrong_branch_detached_head_and_wrong_origin_are_rejected(self):
        self.git(self.clone, 'switch', '-c', 'work')
        with self.assertRaisesRegex(UpdateError, 'main branch'):
            self.update()
        self.git(self.clone, 'checkout', '--detach')
        with self.assertRaisesRegex(UpdateError, 'main branch'):
            self.update()
        self.git(self.clone, 'switch', 'main')
        with self.assertRaisesRegex(UpdateError, 'Origin is not'):
            update_source(self.clone)
        self.unchanged()

    def test_fetch_failure_leaves_checkout_untouched(self):
        missing = self.origin.parent / 'missing.git'
        self.git(self.clone, 'remote', 'set-url', 'origin', str(missing))
        with self.assertRaisesRegex(UpdateError, 'Could not fetch updates'):
            with redirect_stdout(io.StringIO()):
                update_source(self.clone, {str(missing).removesuffix('.git').lower()})
        self.unchanged()
        self.assertEqual((self.clone / 'program.txt').read_text(encoding='utf-8'), 'version one')

    def test_non_clone_and_nested_folder_are_rejected(self):
        with self.assertRaisesRegex(UpdateError, 'not an accessible Git clone'):
            update_source(self.origin.parent, self.allowed)
        nested = self.clone / 'nested'
        nested.mkdir()
        with self.assertRaisesRegex(UpdateError, 'root of'):
            update_source(nested, self.allowed)

    def test_unfinished_git_operation_is_rejected(self):
        marker = self.clone / '.git' / 'rebase-merge'
        marker.mkdir()
        with self.assertRaisesRegex(UpdateError, 'unfinished'):
            self.update()
        self.unchanged()


class UpdateWorkflowTests(unittest.TestCase):
    def run_main(self, args, update_error=None, command_error=None):
        output = io.StringIO()
        with patch('update_project.sys', SimpleNamespace(platform='darwin', stderr=output)), \
             patch('update_project.update_source', side_effect=update_error) as update, \
             patch('update_project.subprocess.run', side_effect=command_error) as run, \
             redirect_stdout(output):
            result = main(args)
        return result, update, run, output.getvalue()

    def test_normal_update_installs_without_building(self):
        result, update, run, output = self.run_main([])
        self.assertEqual(result, 0)
        update.assert_called_once()
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.args[0][-1].endswith('install_macos.command'))
        self.assertIn('Update complete', output)

    def test_build_option_installs_builds_and_opens_dist(self):
        result, _, run, output = self.run_main(['--build'])
        self.assertEqual(result, 0)
        self.assertEqual(run.call_count, 3)
        self.assertTrue(run.call_args_list[1].args[0][-1].endswith('build_macos.command'))
        self.assertEqual(run.call_args_list[2].args[0][0], '/usr/bin/open')
        self.assertIn('Update and build complete', output)

    def test_git_failure_never_starts_install_or_build(self):
        result, _, run, output = self.run_main(['--build'], update_error=UpdateError('offline'))
        self.assertEqual(result, 1)
        run.assert_not_called()
        self.assertIn('Update stopped', output)
        self.assertNotIn('Update complete', output)

    def test_install_failure_does_not_build_or_claim_success(self):
        result, _, run, output = self.run_main(['--build'],
            command_error=subprocess.CalledProcessError(1, ['/bin/bash', 'install_macos.command']))
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn('installation/build failed', output)
        self.assertNotIn('Update and build complete', output)


if __name__ == '__main__':
    unittest.main()
