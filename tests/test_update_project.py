"""Use local Git repositories to verify updates without contacting GitHub."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from update_project import UpdateError, main, update_source
from update_bootstrap import main as bootstrap_main


@unittest.skipUnless(shutil.which('git'), 'Git is required for updater integration tests')
class SourceUpdateTests(unittest.TestCase):
    def git(self, path, *args):
        return subprocess.run(['git', '-C', str(path), *args], check=True,
                              capture_output=True, text=True, encoding='utf-8', timeout=15).stdout.strip()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='nuvel-update-test-')
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.origin = root / 'origin.git'
        self.author = root / 'author'
        self.clone = root / 'NÜVEL Studio ไทย'
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

    def test_current_and_previous_repository_urls_fetch_without_rewriting_origin(self):
        self.publish()
        urls = [f'{prefix}{name}.git' for name in ('nuvel-studio', 'ytdl-studio')
                for prefix in ('https://github.com/Lumin0usX/',
                               'git@github.com:Lumin0usX/',
                               'ssh://git@github.com/Lumin0usX/')]
        urls.append('https://github.com/Lumin0usX/YTDL-STUDIO.GIT/')
        for index, url in enumerate(urls):
            with self.subTest(url=url):
                # Redirect transport to the local fixture so these use the real
                # allowlist and Git fetch/merge without any GitHub/network access.
                self.git(self.clone, 'config', '--add', f'url.{self.origin.as_posix()}.insteadOf', url)
                self.git(self.clone, 'remote', 'set-url', 'origin', url)
                with redirect_stdout(io.StringIO()):
                    changed = update_source(self.clone)
                self.assertEqual(changed, index == 0)
                self.assertEqual(self.git(self.clone, 'rev-parse', 'HEAD'),
                                 self.git(self.author, 'rev-parse', 'HEAD'))
                self.assertEqual(self.git(self.clone, 'config', '--get', 'remote.origin.url'), url)

    def test_similar_repository_urls_are_rejected_without_fetch(self):
        for url in ('https://github.com/another-user/ytdl-studio.git',
                    'https://github.com/Lumin0usX/ytdl-studio-fork.git',
                    'https://github.com.evil.invalid/Lumin0usX/ytdl-studio.git',
                    'https://github.com/Lumin0usX/ytdl-studio.git?other=1',
                    'git@github.com:another-user/nuvel-studio.git'):
            with self.subTest(url=url):
                self.git(self.clone, 'remote', 'set-url', 'origin', url)
                with self.assertRaisesRegex(UpdateError, 'Origin is not'):
                    update_source(self.clone)
                self.assertFalse((self.clone / '.git/FETCH_HEAD').exists())
                self.unchanged()

    def test_failed_origin_recovers_using_only_the_other_project_name(self):
        self.publish()
        for name in ('nuvel-studio', 'ytdl-studio'):
            for prefix in ('https://github.com/lumin0usx/', 'git@github.com:lumin0usx/',
                           'ssh://git@github.com/lumin0usx/'):
                url = prefix + name + '.git'
                other = prefix + ('nuvel-studio' if name == 'ytdl-studio' else 'ytdl-studio') + '.git'
                with self.subTest(url=url):
                    self.git(self.clone, 'config', '--add',
                             f'url.{(self.origin.parent / "missing.git").as_posix()}.insteadOf', url)
                    self.git(self.clone, 'config', '--add', f'url.{self.origin.as_posix()}.insteadOf', other)
                    self.git(self.clone, 'remote', 'set-url', 'origin', url)
                    output = io.StringIO()
                    with redirect_stdout(output):
                        update_source(self.clone)
                    self.assertIn('Trying the alternate project URL', output.getvalue())
                    self.assertEqual(self.git(self.clone, 'rev-parse', 'HEAD'),
                                     self.git(self.author, 'rev-parse', 'HEAD'))
                    self.assertEqual(self.git(self.clone, 'config', '--get', 'remote.origin.url'), url)
                    self.git(self.clone, 'config', '--remove-section',
                             f'url.{(self.origin.parent / "missing.git").as_posix()}')
                    self.git(self.clone, 'config', '--remove-section', f'url.{self.origin.as_posix()}')

    def test_failure_of_both_urls_cannot_install_a_stale_fetch_head(self):
        self.publish()
        self.git(self.clone, 'fetch', 'origin', 'main')
        self.assertNotEqual(self.git(self.clone, 'rev-parse', 'FETCH_HEAD'), self.before)
        missing = (self.origin.parent / 'missing.git').as_posix()
        for name in ('nuvel-studio', 'ytdl-studio'):
            self.git(self.clone, 'config', '--add', f'url.{missing}.insteadOf',
                     f'https://github.com/lumin0usx/{name}.git')
        self.git(self.clone, 'remote', 'set-url', 'origin', 'https://github.com/lumin0usx/nuvel-studio.git')
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(UpdateError, 'either project URL'):
            update_source(self.clone)
        self.unchanged()

    def test_fallback_cannot_replace_checkout_with_unrelated_history(self):
        unrelated = self.origin.parent / 'unrelated'
        self.git(self.origin.parent, 'init', '--initial-branch=main', str(unrelated))
        self.identity(unrelated)
        (unrelated / 'other.txt').write_text('another history', encoding='utf-8')
        self.git(unrelated, 'add', '.')
        self.git(unrelated, 'commit', '-m', 'Unrelated root')
        primary = 'https://github.com/lumin0usx/nuvel-studio.git'
        alternate = 'https://github.com/lumin0usx/ytdl-studio.git'
        self.git(self.clone, 'remote', 'set-url', 'origin', primary)
        self.git(self.clone, 'config', '--add',
                 f'url.{(self.origin.parent / "missing.git").as_posix()}.insteadOf', primary)
        self.git(self.clone, 'config', '--add', f'url.{unrelated.as_posix()}.insteadOf', alternate)
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(UpdateError, 'history has diverged'):
            update_source(self.clone)
        self.unchanged()
        self.assertFalse((self.clone / 'other.txt').exists())

    def test_bootstrap_replaces_a_broken_orchestrator_before_running_it(self):
        updater = self.author / 'update_project.py'
        updater.write_text('raise SyntaxError("old updater is broken")\n', encoding='utf-8')
        self.git(self.author, 'add', '.')
        self.git(self.author, 'commit', '-m', 'Old updater')
        self.git(self.author, 'push', 'origin', 'main')
        self.update()
        updater.write_text('import sys\nfrom pathlib import Path\n'
                           'assert sys.argv[1:] == ["--build-current"]\n'
                           'Path("recovery-result").write_text("updated updater ran")\n', encoding='utf-8')
        self.publish()
        with patch('update_bootstrap.__file__', str(self.clone / 'update_bootstrap.py')), \
             patch('update_bootstrap.update_source', side_effect=lambda project: update_source(project, self.allowed)), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap_main([]), 0)
        self.assertEqual((self.clone / 'recovery-result').read_text(), 'updated updater ran')

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
    def run_main(self, args, update_error=None, command_error=None, platform='darwin'):
        output = io.StringIO()
        with patch('update_project.sys', SimpleNamespace(platform=platform, stderr=output, executable='chosen-python')), \
             patch('update_project.update_source', side_effect=update_error) as update, \
             patch('update_project.subprocess.run', side_effect=command_error) as run, \
             redirect_stdout(output):
            result = main(args)
        return result, update, run, output.getvalue()

    def test_normal_mac_update_builds_and_publishes_the_app(self):
        result, update, run, output = self.run_main([])
        self.assertEqual(result, 0)
        update.assert_called_once()
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.args[0][-1].endswith('build_macos.command'))
        self.assertIn('Update complete', output)
        self.assertIn('Open NÜVEL Studio.app in the project folder', output)

    def test_bootstrapped_build_does_not_fetch_a_second_time(self):
        result, update, run, output = self.run_main(['--build-current'])
        self.assertEqual(result, 0)
        update.assert_not_called()
        self.assertEqual(run.call_count, 1)
        self.assertIn('Update complete', output)

    def test_old_build_flag_keeps_the_same_single_mac_update_flow(self):
        result, _, run, output = self.run_main(['--build'])
        self.assertEqual(result, 0)
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.args[0][-1].endswith('build_macos.command'))
        self.assertIn('Update complete', output)

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

    def test_windows_uses_selected_python_to_build_and_verify_the_app(self):
        result, update, run, output = self.run_main([], platform='win32')
        self.assertEqual(result, 0)
        update.assert_called_once()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], 'chosen-python')
        self.assertTrue(run.call_args.args[0][1].endswith('build_windows.py'))
        self.assertIn('Open NÜVEL Studio shortcut', output)

    def test_windows_build_failure_does_not_claim_success(self):
        result, _, run, output = self.run_main([], platform='win32',
            command_error=subprocess.CalledProcessError(1, ['chosen-python', 'build_windows.py']))
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn('Update complete', output)

    def test_windows_git_failure_never_installs(self):
        result, _, run, output = self.run_main([], platform='win32', update_error=UpdateError('offline'))
        self.assertEqual(result, 1)
        run.assert_not_called()
        self.assertIn('offline', output)

    def test_check_mode_does_not_fetch_or_install(self):
        with patch('update_project.shutil.which', return_value='git'):
            result, update, run, output = self.run_main(['--check'], platform='win32')
        self.assertEqual(result, 0)
        update.assert_not_called()
        self.assertEqual([call.args[0] for call in run.call_args_list],
                         [['git', '--version'], ['chosen-python', '-m', 'pip', '--version']])
        self.assertIn('No updates were applied', output)

    def test_windows_accepts_legacy_build_flag_using_the_same_workflow(self):
        result, update, run, output = self.run_main(['--build'], platform='win32')
        self.assertEqual(result, 0)
        update.assert_called_once()
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.args[0][1].endswith('build_windows.py'))
        self.assertIn('Update complete', output)


@unittest.skipUnless(sys.platform == 'win32', 'Windows batch launcher tests')
class WindowsBatchUpdateTests(unittest.TestCase):
    def run_batch(self, updater, *args):
        with tempfile.TemporaryDirectory(prefix='nuvel-batch-test-') as temporary:
            folder = Path(temporary, 'NÜVEL Studio ไทย')
            folder.mkdir()
            shutil.copyfile(Path(__file__).resolve().parents[1] / 'update.bat', folder / 'update.bat')
            (folder / 'update_bootstrap.py').write_text(updater, encoding='utf-8')
            # Only the copied stub runs: these tests never fetch or install.
            return subprocess.run(['cmd.exe', '/d', '/c', 'update.bat', *args], cwd=folder,
                                  input='\n\n', text=True, encoding='utf-8', errors='replace',
                                  capture_output=True, timeout=15)

    def test_check_flag_is_forwarded_in_a_folder_with_spaces_and_thai(self):
        result = self.run_batch("import sys\nassert sys.argv[1:] == ['--check']\nprint('CHECK_OK')\n", '--check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('CHECK_OK', result.stdout)
        self.assertNotIn('Press any key', result.stdout)

    def test_failure_returns_nonzero_and_keeps_error_visible(self):
        result = self.run_batch("print('SIMULATED_UPDATE_ERROR')\nraise SystemExit(1)\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('SIMULATED_UPDATE_ERROR', result.stdout)
        self.assertIn('Update failed', result.stdout)

    def test_check_failure_returns_nonzero_without_prompting(self):
        result = self.run_batch("print('SIMULATED_CHECK_ERROR')\nraise SystemExit(1)\n", '--check')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('SIMULATED_CHECK_ERROR', result.stdout)
        self.assertNotIn('Press any key', result.stdout)

    def test_replacing_running_batch_does_not_execute_new_contents(self):
        updater = ("from pathlib import Path\n"
                   "Path(__file__).with_name('update.bat').write_bytes("
                   "b'@echo off\\r\\necho SHOULD_NOT_RUN\\r\\nexit /b 9\\r\\n')\n"
                   "print('UPDATE_OK')\n")
        result = self.run_batch(updater)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('UPDATE_OK', result.stdout)
        self.assertNotIn('SHOULD_NOT_RUN', result.stdout)
        self.assertNotIn('not recognized', result.stderr)


if __name__ == '__main__':
    unittest.main()
