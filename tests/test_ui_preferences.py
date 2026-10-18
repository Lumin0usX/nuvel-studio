import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ui_preferences import load_preferences, save_preferences


class PreferencesTests(unittest.TestCase):
    def test_round_trip_is_atomic_and_excludes_credentials(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', reducedMotion=True, density='compact',
                          cookies='chrome', cookie_path='secret.txt', token='secret')
            clean = save_preferences(values)
            self.assertEqual(load_preferences(), clean)
            self.assertNotIn('cookies', clean)
            self.assertNotIn('secret', Path(folder, 'prefs.json').read_text())
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_invalid_preferences_do_not_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            path = Path(folder, 'prefs.json')
            path.write_text('{"keep":true}')
            with self.assertRaises(ValueError):
                save_preferences(dict(folder=folder, sidebar='invalid', density='compact', reducedMotion=True))
            self.assertEqual(json.loads(path.read_text()), dict(keep=True))
            self.assertEqual(load_preferences(), {})

    def test_missing_or_corrupted_preferences_are_safe(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            self.assertEqual(load_preferences(), {})
            Path(folder, 'prefs.json').write_text('broken json')
            self.assertEqual(load_preferences(), {})

    def test_all_languages_survive_save_and_reload(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            for language in ('en', 'th', 'ja', 'zh-CN'):
                save_preferences(dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False, language=language))
                self.assertEqual(load_preferences()['language'], language)

    def test_old_settings_default_to_thai_and_unknown_languages_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False)
            self.assertEqual(save_preferences(values)['language'], 'th')
            with self.assertRaises(ValueError):
                save_preferences(dict(**values, language='unsupported'))
            self.assertEqual(load_preferences()['language'], 'th')


if __name__ == '__main__':
    unittest.main()
