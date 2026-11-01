# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Keep bundled offline fonts usable and prevent broken or cross-language settings."""
import unittest

from font_assets import check_font_assets, font_catalog, validate_fonts


class FontAssetsTests(unittest.TestCase):
    def test_bundled_fonts_have_original_bytes_weights_licenses_and_language_glyphs(self):
        check_font_assets()

    def test_defaults_and_language_specific_choices(self):
        defaults = validate_fonts()
        self.assertEqual(defaults, dict(en='inter', th='notosansthai', ja='notosansjp', **{'zh-CN': 'notosanssc'}))
        for language, group in font_catalog()['languages'].items():
            for font in group['fonts']:
                selections = validate_fonts({language: font['id']})
                self.assertEqual(selections[language], font['id'])
                for other in defaults.keys() - {language}:
                    self.assertEqual(selections[other], defaults[other])

    def test_invalid_or_cross_language_font_is_rejected(self):
        for values in ([], 'inter', {'fr': 'inter'}, {'en': 'prompt'}, {'th': 'inter'},
                       {'ja': 'notosanssc'}, {'zh-CN': 'notosansjp'}, {'en': []}, {'en': None}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                validate_fonts(values)


if __name__ == '__main__':
    unittest.main()
