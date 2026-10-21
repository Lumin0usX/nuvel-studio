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

    def test_old_settings_default_to_dark_and_theme_choices_persist(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False)
            Path(folder, 'prefs.json').write_text(json.dumps(values))
            self.assertEqual(load_preferences()['theme'], 'dark')
            for theme in ('light', 'system', 'dark'):
                save_preferences(dict(**values, theme=theme))
                self.assertEqual(load_preferences()['theme'], theme)
            with self.assertRaises(ValueError):
                save_preferences(dict(**values, theme='invalid'))
            self.assertEqual(load_preferences()['theme'], 'dark')

    def test_styles_and_animation_preferences_persist_without_changing_theme_or_fonts(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False)
            legacy = save_preferences(values)
            self.assertEqual(legacy['visualStyle'], 'obsidian')
            for style in ('glass', 'obsidian'):
                for reduced_motion in (True, False):
                    expected = dict(legacy, visualStyle=style, reducedMotion=reduced_motion)
                    self.assertEqual(save_preferences(expected), expected)
                    self.assertEqual(load_preferences(), expected)
            before = Path(folder, 'prefs.json').read_bytes()
            with self.assertRaises(ValueError):
                save_preferences(dict(values, visualStyle='unknown'))
            self.assertEqual(Path(folder, 'prefs.json').read_bytes(), before)

    def test_glass_opacity_migrates_and_persists_independently_of_style_and_theme(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False)
            path = Path(folder, 'prefs.json')
            path.write_text(json.dumps(values))
            self.assertEqual(load_preferences()['glassOpacity'], 72)
            defaults = load_preferences()
            for opacity in (0, 1, 35, 72, 99, 100):
                for style, theme in (('glass', 'dark'), ('glass', 'light'), ('obsidian', 'dark')):
                    saved = save_preferences(dict(values, visualStyle=style, theme=theme, glassOpacity=opacity))
                    self.assertEqual(load_preferences(), saved)
                    self.assertEqual(saved['glassOpacity'], opacity)
                    self.assertEqual(saved['fonts'], defaults['fonts'])
            before = path.read_bytes()
            for opacity in (None, True, '35', -1, 101, 3.5):
                with self.subTest(opacity=opacity), self.assertRaises(ValueError):
                    save_preferences(dict(values, glassOpacity=opacity))
                self.assertEqual(path.read_bytes(), before)

    def test_font_choices_remain_separate_across_language_changes(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False)
            fonts = {'en': 'lato', 'th': 'prompt', 'ja': 'mplus1p', 'zh-CN': 'zcoolxiaowei'}
            for language in fonts:
                clean = save_preferences(dict(**values, language=language, fonts=fonts))
                self.assertEqual(load_preferences()['fonts'], fonts)
                self.assertEqual(clean['theme'], 'dark')

    def test_legacy_preferences_receive_font_defaults_and_bad_fonts_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder, patch('ui_preferences.preferences_path', return_value=Path(folder, 'prefs.json')):
            values = dict(folder=folder, sidebar='auto', density='comfortable', reducedMotion=False)
            path = Path(folder, 'prefs.json')
            path.write_text(json.dumps(values))
            expected = dict(en='inter', th='notosansthai', ja='notosansjp', **{'zh-CN': 'notosanssc'})
            self.assertEqual(load_preferences()['fonts'], expected)
            for fonts in ({'en': 'kanit'}, {'th': 'missing-font'}, {'en': []}, 'invalid'):
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    save_preferences(dict(**values, fonts=fonts))
                self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
