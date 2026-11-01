# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Quality preferences. Explicit values are ceilings; 'best' selects the best source."""
import os
import sys

QUALITY_CHOICES = {
    'video': ('best', '4320', '2160', '1440', '1080', '720', '480', '360'),
    'audio': ('best', '320', '256', '192', '128', '96'),
    'image': ('best', '4096', '2560', '2048', '1920', '1280', '1024', '640'),
}


def lgpl_encoder_options(target):
    if target == 'macos-arm64':
        return ['-c:v', 'h264_videotoolbox', '-allow_sw', '1', '-q:v', '75']
    if target == 'windows-x64':
        return ['-c:v', 'h264_mf', '-rate_control', 'quality', '-quality', '90']
    raise ValueError('Unsupported native encoder target')


def validate_quality(mode, quality):
    quality = str(quality)
    if quality not in QUALITY_CHOICES.get(mode, ()):
        raise ValueError('ค่าคุณภาพไม่ถูกต้องสำหรับโหมดนี้')
    return quality


def quality_label(mode, quality):
    if quality == 'best':
        return 'สูงสุดจากต้นทาง' if mode == 'video' else 'ต้นฉบับจากต้นทาง'
    if mode == 'video':
        return f'ไม่เกิน {quality}p'
    if mode == 'audio':
        return f'MP3 {quality} kbps'
    return f'ด้านยาวไม่เกิน {quality}px'


def media_options(mode, quality='best'):
    quality = validate_quality(mode, quality)
    if mode == 'audio':
        # Native audio avoids an unnecessary lossy encode for the default.
        processor = dict(key='FFmpegExtractAudio', preferredcodec='best' if quality == 'best' else 'mp3',
                         preferredquality='0' if quality == 'best' else quality)
        return dict(format='bestaudio/best', postprocessors=[processor])
    if mode == 'video':
        limit = '' if quality == 'best' else f'[height<={quality}]'
        if sys.platform == 'darwin':
            # Keep all source codecs/resolutions available. MKV is only an
            # intermediate; QuickTimeMP4PP always produces the final MP4.
            return dict(format=f'bestvideo*{limit}+bestaudio/best{limit}',
                        merge_output_format='mkv', postprocessors=[])
        options = dict(format=f'bestvideo*{limit}+bestaudio/best{limit}', merge_output_format='mp4',
                       postprocessors=[dict(key='FFmpegVideoConvertor', preferedformat='mp4')])
        if sys.platform == 'win32' and (getattr(sys, 'frozen', False) or os.environ.get('NUVEL_FFMPEG_BUNDLE')):
            # MP4's implicit default encoder can require GPL x264. Name the
            # system Media Foundation encoder explicitly for LGPL packages.
            options['postprocessor_args'] = {'VideoConvertor+ffmpeg_o': lgpl_encoder_options('windows-x64')
                                            + ['-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k']}
        return options
    raise ValueError('โหมดนี้ไม่ใช่วิดีโอหรือเสียง')


def add_video_postprocessor(ydl, mode, check_cancel=None):
    if mode == 'video' and sys.platform == 'darwin':
        from mp4_compatibility import QuickTimeMP4PP
        ydl.add_post_processor(QuickTimeMP4PP(ydl, check_cancel), when='post_process')
