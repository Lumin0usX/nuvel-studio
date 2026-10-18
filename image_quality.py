"""Downscale downloaded images in place, preserving originals on failure."""
import os
from pathlib import Path
import tempfile

from media_quality import validate_quality


def resize_image(path, quality, cancel):
    quality = validate_quality('image', quality)
    if quality == 'best':
        return False  # Do not decode/re-encode the default original download.
    from PIL import Image, ImageOps, ImageSequence
    path = Path(path)
    cap = int(quality)
    temporary = None
    try:
        with Image.open(path) as source:
            if max(source.size) <= cap:
                return False
            fmt = source.format
            options = {}
            if source.info.get('icc_profile'):
                options['icc_profile'] = source.info['icc_profile']
            frames = []
            durations = []
            pixels = 0
            animated = getattr(source, 'is_animated', False)
            if getattr(source, 'n_frames', 1) > 1 and not animated:
                raise ValueError('ไฟล์ภาพหลายหน้าต้องเลือกคุณภาพต้นฉบับ')
            if animated and fmt not in ('GIF', 'WEBP', 'PNG'):
                raise ValueError('ภาพเคลื่อนไหวชนิดนี้ต้องเลือกคุณภาพต้นฉบับ')
            for frame in ImageSequence.Iterator(source):
                if cancel.is_set():
                    raise RuntimeError('หยุดการปรับขนาดภาพแล้ว')
                image = ImageOps.exif_transpose(frame.copy())
                image.thumbnail((cap, cap), Image.Resampling.LANCZOS)
                pixels += image.width * image.height
                if animated:
                    if len(frames) >= 200 or pixels > 64_000_000:
                        raise ValueError('ภาพเคลื่อนไหวใหญ่เกินไปสำหรับการย่อ เลือกคุณภาพต้นฉบับ')
                    image = image.convert('RGBA')
                frames.append(image)
                durations.append(frame.info.get('duration', 100))
            if fmt == 'JPEG':
                frames[0] = frames[0].convert('RGB')
                options.update(quality=95, subsampling=0)
            elif fmt == 'WEBP':
                options.update(quality=95)
            if animated:
                options.update(save_all=True, append_images=frames[1:])
                if 'loop' in source.info:
                    options['loop'] = source.info['loop']
                if fmt == 'PNG' and source.info.get('default_image'):
                    options.update(default_image=True, duration=durations[1:])
                else:
                    options['duration'] = durations
                if fmt == 'GIF':
                    options['disposal'] = 2
            # Metadata is intentionally not copied wholesale: EXIF orientation
            # has already been applied, and old pixel dimensions would be stale.
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.studio-resize-', suffix=path.suffix, delete=False) as output:
                temporary = Path(output.name)
            frames[0].save(temporary, format=fmt, **options)
        if cancel.is_set():
            raise RuntimeError('หยุดการปรับขนาดภาพแล้ว')
        os.replace(temporary, path)
        return True
    except Exception as exc:
        if cancel.is_set():
            raise
        raise RuntimeError(f'ปรับขนาดภาพ {path.name} ไม่สำเร็จ · ต้นฉบับยังอยู่ในโฟลเดอร์ '
                           f'ลองเลือกคุณภาพต้นฉบับ\n{exc}') from exc
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
