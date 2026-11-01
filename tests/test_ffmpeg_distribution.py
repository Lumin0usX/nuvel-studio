# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dependency_audit import digest
from ffmpeg_distribution import selected_bundle, validate_bundle
from mp4_compatibility import h264_encoder_options
from media_quality import media_options


CONFIG = '--disable-gpl --disable-nonfree --disable-version3 --disable-autodetect --enable-libmp3lame'


class FFmpegDistributionTests(unittest.TestCase):
    def bundle(self, root, target='macos-arm64'):
        filename = 'ffmpeg.exe' if target == 'windows-x64' else 'ffmpeg'
        (root / filename).write_bytes(b'not a real executable; probe is mocked')
        source = root / 'source'; source.mkdir()
        roles = dict(ffmpeg_source='source/ffmpeg.tar.xz', ffmpeg_license='source/COPYING.LGPLv2.1',
                     build_script='source/build.sh', build_log='source/build.log',
                     library_inventory='source/libraries.json')
        for name in [*roles.values(), 'source/lame.tar.gz', 'source/LAME-COPYING']:
            (root / name).write_text('test material')
        (source / 'libraries.json').write_text(json.dumps([
            dict(name='libmp3lame', license='LGPL-2.0-or-later', source='source/lame.tar.gz',
                 license_file='source/LAME-COPYING'),
            dict(name='OS SDK', license='system SDK terms', system=True)]))
        manifest = dict(schema=1, target=target, binary=filename, materials=roles,
                        files={p.relative_to(root).as_posix(): digest(p) for p in root.rglob('*') if p.is_file()})
        (root / 'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def evidence(self, config=CONFIG, license='GNU Lesser General Public License version 2.1 or later'):
        return dict(configuration=config, gpl_enabled='--enable-gpl' in config,
                    nonfree_enabled='--enable-nonfree' in config, version3_enabled='--enable-version3' in config,
                    outputs=dict(license=dict(stdout=license, stderr='')))

    def test_both_platforms_accept_source_bearing_lgpl_evidence(self):
        for target in ('macos-arm64', 'windows-x64'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); manifest = self.bundle(root, target)
                with patch('ffmpeg_distribution.ffmpeg_evidence', return_value=self.evidence()):
                    binary, source, _ = validate_bundle(root, target)
                self.assertEqual(binary.name, manifest['binary'])
                self.assertEqual(source, root / 'source')

    def test_gpl_nonfree_missing_config_or_non_lgpl_license_is_rejected(self):
        bad = [self.evidence(CONFIG + ' --enable-gpl'), self.evidence(CONFIG + ' --enable-nonfree'),
               self.evidence(CONFIG + ' --enable-version3'), self.evidence(CONFIG + ' --enable-libx264'),
               self.evidence(CONFIG.replace('--disable-autodetect', '')),
               self.evidence(license='GNU General Public License version 2 or later')]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.bundle(root)
            for evidence in bad:
                with self.subTest(evidence=evidence), patch('ffmpeg_distribution.ffmpeg_evidence', return_value=evidence):
                    with self.assertRaises(RuntimeError):
                        validate_bundle(root, 'macos-arm64')

    def test_tampering_missing_source_and_wrong_target_stop_before_binary_execution(self):
        for fault in ('tamper', 'source', 'target', 'unlisted', 'traversal'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); manifest = self.bundle(root)
                if fault == 'tamper':
                    (root / 'ffmpeg').write_bytes(b'changed')
                elif fault == 'source':
                    (root / 'source/ffmpeg.tar.xz').unlink()
                elif fault == 'unlisted':
                    (root / 'source/unreviewed.txt').write_text('not manifested')
                elif fault == 'traversal':
                    manifest['files']['../outside'] = '0' * 64
                    (root / 'manifest.json').write_text(json.dumps(manifest))
                with patch('ffmpeg_distribution.ffmpeg_evidence') as probe, self.assertRaises(RuntimeError):
                    validate_bundle(root, 'windows-x64' if fault == 'target' else 'macos-arm64')
                probe.assert_not_called()

    def test_undeclared_linked_library_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.bundle(root)
            with patch('ffmpeg_distribution.ffmpeg_evidence', return_value=self.evidence(CONFIG + ' --enable-libopus')):
                with self.assertRaisesRegex(RuntimeError, 'source inventory'):
                    validate_bundle(root, 'macos-arm64')

    def test_unconfigured_builder_never_falls_back_to_imageio_gpl(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(RuntimeError, 'NUVEL_FFMPEG_BUNDLE'):
            selected_bundle('macos-arm64')

    def test_frozen_or_explicit_lgpl_engine_uses_system_encoder_without_x264(self):
        with patch.dict('os.environ', {}, clear=True), patch('mp4_compatibility.sys.frozen', True, create=True):
            options = h264_encoder_options()
            self.assertIn('h264_videotoolbox', options)
            self.assertNotIn('libx264', options)
        with patch.dict('os.environ', {'NUVEL_FFMPEG_BUNDLE': '/test-only'}):
            self.assertIn('h264_videotoolbox', h264_encoder_options())

    def test_windows_lgpl_converter_overrides_implicit_encoder_and_keeps_best_selection(self):
        with patch('media_quality.sys.platform', 'win32'), patch.dict('os.environ', {'NUVEL_FFMPEG_BUNDLE': '/test-only'}):
            options = media_options('video')
        self.assertEqual(options['format'], 'bestvideo*+bestaudio/best')
        args = options['postprocessor_args']['VideoConvertor+ffmpeg_o']
        self.assertIn('h264_mf', args)
        self.assertNotIn('libx264', args)
        self.assertEqual(options['merge_output_format'], 'mp4')
