"""Literal output names shared by the media and image downloaders."""
from pathlib import Path
import re
import unicodedata


INVALID_NAME = 'Use a file name without folders or these characters: < > : " / \\ | ? *'
LONG_NAME = 'The file name is too long. Choose a shorter name.'
MEDIA_EXTENSIONS = frozenset(('mp4', 'mkv', 'webm', 'mov', 'avi', 'm4v', 'flv', 'ts',
                              'mp3', 'm4a', 'aac', 'opus', 'ogg', 'wav', 'flac', 'aiff',
                              'jpg', 'jpeg', 'png', 'webp', 'gif', 'avif', 'heic', 'heif',
                              'tif', 'tiff', 'bmp', 'jxl', 'ico'))


def validate_output_name(value=''):
    if not isinstance(value, str):
        raise ValueError(INVALID_NAME)
    name = unicodedata.normalize('NFC', value.strip())
    if not name:
        return ''
    if re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', name) or name in ('.', '..') or name.endswith('.'):
        raise ValueError(INVALID_NAME)
    # The engine selects the real extension from the format, never from this field.
    while Path(name).suffix.lower().lstrip('.') in MEDIA_EXTENSIONS:
        name = name[:-len(Path(name).suffix)].rstrip()
    if not name or name.endswith('.') or re.fullmatch(r'(?i)(con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])', name.split('.')[0].rstrip()):
        raise ValueError(INVALID_NAME)
    if len(name.encode('utf-8')) > 160:
        raise ValueError(LONG_NAME)
    return name


def save_named_file(source, folder, stem, check_cancel=lambda: None):
    """Publish a completed file with exclusive creation, preserving any namesakes."""
    source, folder = Path(source), Path(folder)
    for number in range(10000):
        check_cancel()
        suffix = (f' ({number})' if number else '') + source.suffix
        # Source-generated names can already fill the filesystem's component
        # limit. Leave room for the collision suffix without splitting Unicode.
        prefix = stem.encode('utf-8')[:255 - len(suffix.encode('utf-8'))].decode('utf-8', errors='ignore')
        name = prefix + suffix
        target = folder / name
        try:
            destination = target.open('xb')
        except FileExistsError:
            continue
        try:
            with destination, source.open('rb') as stream:
                while block := stream.read(1024 * 1024):
                    check_cancel()
                    destination.write(block)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target
    raise RuntimeError('Too many files with this name. Choose another file name.')
