import unittest
from pathlib import Path

from download_engine import PLATFORMS, PLATFORM_DOMAINS, AUDIO_ONLY, platform_modes, platform_support


class PlatformRegistryTests(unittest.TestCase):
    def test_assets_and_domains_cover_registry(self):
        root = Path(__file__).resolve().parents[1]
        slugs = [row[2] for row in PLATFORMS]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(set(slugs), set(PLATFORM_DOMAINS))
        for slug in slugs:
            with self.subTest(slug=slug):
                self.assertTrue((root / 'assets' / 'platforms' / (slug + '.png')).is_file())
                self.assertTrue(PLATFORM_DOMAINS[slug])

    def test_photo_only_sources_do_not_promise_video(self):
        _, states = platform_support()
        for name in ('Pixiv', 'DeviantArt', 'Unsplash'):
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


if __name__ == '__main__':
    unittest.main()
