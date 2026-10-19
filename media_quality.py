"""Quality preferences. Explicit values are ceilings; 'best' selects the best source."""
import sys

QUALITY_CHOICES = {
    'video': ('best', '4320', '2160', '1440', '1080', '720', '480', '360'),
    'audio': ('best', '320', '256', '192', '128', '96'),
    'image': ('best', '4096', '2560', '2048', '1920', '1280', '1024', '640'),
}


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
        return dict(format=f'bestvideo*{limit}+bestaudio/best{limit}', merge_output_format='mp4',
                    postprocessors=[dict(key='FFmpegVideoConvertor', preferedformat='mp4')])
    raise ValueError('โหมดนี้ไม่ใช่วิดีโอหรือเสียง')


def add_video_postprocessor(ydl, mode, check_cancel=None):
    if mode == 'video' and sys.platform == 'darwin':
        from mp4_compatibility import QuickTimeMP4PP
        ydl.add_post_processor(QuickTimeMP4PP(ydl, check_cancel), when='post_process')
