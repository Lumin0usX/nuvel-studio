# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

import unittest
import json
import re
from pathlib import Path
from unittest.mock import patch

from download_engine import PLATFORMS, PLATFORM_DOMAINS, AUDIO_ONLY, IMAGE_MODULES, platform_modes, platform_support


class PlatformRegistryTests(unittest.TestCase):
    def test_names_and_domains_cover_registry_without_platform_artwork(self):
        root = Path(__file__).resolve().parents[1]
        slugs = [row[2] for row in PLATFORMS]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(set(slugs), set(PLATFORM_DOMAINS))
        for slug in slugs:
            with self.subTest(slug=slug):
                self.assertTrue(PLATFORM_DOMAINS[slug])
        self.assertTrue(all(row[0] for row in PLATFORMS))
        self.assertFalse(list((root / 'assets/platforms').glob('*.png')))

    def test_photo_only_sources_do_not_promise_video(self):
        _, states = platform_support()
        for name, key, *_ in PLATFORMS:
            if key is not None:
                continue
            self.assertEqual(states[name], 'unsupported')

    def test_mode_capabilities_are_independent(self):
        engine = dict(available=True, modules=['pixiv', 'flickr', 'bluesky'])
        self.assertEqual(platform_modes('pixiv', 'unsupported', engine),
                         dict(video_status='unsupported', audio_status='unsupported', image_status='supported'))
        for slug in AUDIO_ONLY:
            statuses = platform_modes(slug, 'supported', engine)
            self.assertEqual(statuses['video_status'], 'unsupported')
            self.assertEqual(statuses['audio_status'], 'supported')
        self.assertEqual(platform_modes('bluesky', 'broken', engine)['video_status'], 'broken')
        self.assertEqual(platform_modes('youtube', 'supported', engine)['image_status'], 'unsupported')

    def test_missing_gallery_and_unknown_modules(self):
        self.assertEqual(platform_modes('pixiv', 'unsupported', dict(available=False, modules=[]))['image_status'], 'missing')
        self.assertEqual(platform_modes('archive', 'supported', dict(available=True, modules=['ao3']))['image_status'], 'unsupported')

    def test_gallery_aliases_match_real_module_names(self):
        engine = dict(available=True, modules=['500px', 'wikimedia', 'weibo'])
        for slug in ('fivehundredpx', 'wikimediacommons', 'weibo'):
            self.assertEqual(platform_modes(slug, 'supported', engine)['image_status'], 'supported')
        self.assertEqual(platform_modes('fivehundredpx', 'unsupported',
            dict(available=True, modules=['fivehundredpx']))['image_status'], 'unsupported')
        self.assertTrue(set(IMAGE_MODULES).issubset(PLATFORM_DOMAINS))

    def test_missing_gallery_does_not_suggest_it_adds_images_to_audio_sites(self):
        engine = dict(available=False, modules=[])
        for slug in AUDIO_ONLY | {'youtube', 'telegram', 'rednote'}:
            self.assertEqual(platform_modes(slug, 'supported', engine)['image_status'], 'unsupported')
        self.assertEqual(platform_modes('artstation', 'unsupported', engine)['image_status'], 'missing')

    def test_preview_seed_and_native_catalog_include_all_fifty_sources(self):
        from glass_app import StudioAPI
        root = Path(__file__).resolve().parents[1]
        html = (root / 'ui' / 'index.html').read_text(encoding='utf-8')
        seed = json.loads(re.search(r'<script id="platform-seed" type="application/json">(.*?)</script>', html, re.S)[1])
        self.assertEqual(len(PLATFORMS), 50)
        self.assertEqual([item['slug'] for item in seed], [row[2] for row in PLATFORMS])
        self.assertTrue(all(item['status'] == 'unknown' for item in seed))
        for row, item in zip(PLATFORMS, seed):
            self.assertEqual(item['domains'], list(PLATFORM_DOMAINS[row[2]]))
            self.assertNotIn('supported', [item['video_status'], item['audio_status'], item['image_status']])
        with patch.object(StudioAPI, '_scan'):
            api = StudioAPI()
        with patch('glass_app.image_support', return_value=dict(available=True, modules=list(IMAGE_MODULES.values()))):
            api._scan()
        catalog = api.snapshot()['platforms']
        self.assertEqual(len(catalog), 50)
        for item in catalog:
            self.assertNotIn('icon', item)
            self.assertTrue(item['name'])
            if item['slug'] in AUDIO_ONLY:
                self.assertEqual(item['video_status'], 'unsupported')


if __name__ == '__main__':
    unittest.main()
