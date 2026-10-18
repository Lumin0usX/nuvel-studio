"""Small, atomic store for non-secret UI preferences across desktop launches."""
import json
import os
from pathlib import Path
import sys
import tempfile


def preferences_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return root / 'YTDLStudio' / 'preferences.json'


def validate_preferences(values):
    if not isinstance(values, dict):
        raise ValueError('ข้อมูลการตั้งค่าไม่ถูกต้อง')
    folder = Path(str(values.get('folder', '')).strip()).expanduser()
    if not values.get('folder') or not folder.is_dir():
        raise ValueError('เลือกโฟลเดอร์ปลายทางที่มีอยู่ก่อน')
    if values.get('sidebar') not in ('auto', 'expanded', 'collapsed'):
        raise ValueError('รูปแบบแถบเมนูไม่ถูกต้อง')
    if values.get('density') not in ('comfortable', 'compact') or not isinstance(values.get('reducedMotion'), bool):
        raise ValueError('การตั้งค่าหน้าตาไม่ถูกต้อง')
    language = values.get('language', 'th')
    if language not in ('en', 'th', 'ja', 'zh-CN'):
        raise ValueError('ภาษาไม่ถูกต้อง')
    return dict(folder=str(folder.resolve()), sidebar=values['sidebar'],
                density=values['density'], reducedMotion=values['reducedMotion'], language=language)


def load_preferences():
    try:
        path = preferences_path()
        if path.stat().st_size > 65536:
            return {}
        return validate_preferences(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError):
        return {}


def save_preferences(values):
    clean = validate_preferences(values)
    path = preferences_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.preferences-', suffix='.tmp', delete=False) as output:
            temporary = Path(output.name)
            json.dump(clean, output, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
    return clean
