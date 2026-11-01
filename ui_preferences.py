# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Small, atomic store for non-secret UI preferences across desktop launches."""
import json
import os
from pathlib import Path
import sys
import tempfile
from font_assets import validate_fonts


def preferences_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return root / 'NuvelStudio' / 'preferences.json'


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
    theme = values.get('theme', 'dark')
    if theme not in ('dark', 'light', 'system'):
        raise ValueError('Invalid theme preference.')
    visual_style = values.get('visualStyle', 'obsidian')
    if visual_style not in ('obsidian', 'glass'):
        raise ValueError('Invalid interface style preference.')
    glass_opacity = values.get('glassOpacity', 72)
    if type(glass_opacity) is not int or not 0 <= glass_opacity <= 100:
        raise ValueError('Invalid glass opacity preference.')
    return dict(folder=str(folder.resolve()), sidebar=values['sidebar'],
                density=values['density'], reducedMotion=values['reducedMotion'], language=language, theme=theme, visualStyle=visual_style,
                fonts=validate_fonts(values.get('fonts')), glassOpacity=glass_opacity)


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
