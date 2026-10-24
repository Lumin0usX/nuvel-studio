"""Normalize macOS video downloads for QuickTime using the bundled FFmpeg.

Do not rely on the extension or extractor codec hints: an MP4 may contain
VP9/AV1, and the standard converter skips files already named .mp4.
"""
import os
from pathlib import Path
import re
import tempfile

from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor


class QuickTimeMP4PP(FFmpegPostProcessor):
    def __init__(self, downloader=None, check_cancel=None):
        super().__init__(downloader)
        self.check_cancel = check_cancel or (lambda: None)

    def run(self, info):
        self.check_cancel()
        source = Path(info['filepath'])
        # imageio-ffmpeg supplies FFmpeg, not ffprobe. Inspect the actual first
        # video/audio streams with that same binary; unknown formats re-encode.
        probe = self.run_ffmpeg(str(source), None, [], expected_retcodes=(1,))
        video = re.search(r'Stream[^\n]*Video: ([^\n]+)', probe)
        audio = re.search(r'Stream[^\n]*Audio: ([^\n]+)', probe)
        copy_video = bool(video and re.match(r'h264\b', video[1])
                          and re.search(r'\byuv420p(?:\(|,|\s|$)', video[1]))
        copy_audio = bool(audio and re.match(r'aac \(LC\)', audio[1]))
        self.check_cancel()
        options = ['-map', '0:v:0', '-map', '0:a:0?', '-sn', '-dn']
        if copy_video:
            options += ['-c:v', 'copy']
        else:
            # Keep source resolution/fps. Pad odd dimensions by at most one
            # pixel because 8-bit 4:2:0 H.264 requires even dimensions.
            options += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                        '-pix_fmt', 'yuv420p', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2']
        options += ['-tag:v', 'avc1']
        options += ['-c:a', 'copy'] if copy_audio else ['-c:a', 'aac', '-b:a', '192k']
        options += ['-movflags', '+faststart', '-f', 'mp4']
        destination = source.with_suffix('.mp4')
        # Never encode over the input. Only replace it after successful encoding
        # and a cancellation check; failure keeps the downloaded source intact.
        with tempfile.NamedTemporaryFile(prefix='nuvel-quicktime-', suffix='.mp4',
                                         dir=source.parent, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            self.to_screen('Preparing QuickTime-compatible MP4 (H.264 / AAC)')
            self.run_ffmpeg(str(source), str(temporary), options)
            self.check_cancel()
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        info.update(filepath=str(destination), ext='mp4', vcodec='h264')
        if audio:
            info['acodec'] = 'aac'
        return ([] if source == destination else [str(source)]), info
