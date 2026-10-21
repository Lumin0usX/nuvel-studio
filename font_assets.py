"""Vendored UI fonts: one catalog, offline CSS, and native-build integrity checks."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct

from platform_runtime import resource_path


@lru_cache(maxsize=1)
def font_catalog():
    return json.loads(resource_path('ui', 'fonts', 'catalog.json').read_text(encoding='utf-8'))


def validate_fonts(values=None):
    languages = font_catalog()['languages']
    values = {} if values is None else values
    if not isinstance(values, dict) or set(values) - set(languages):
        raise ValueError('Invalid font preference.')
    result = {}
    for language, group in languages.items():
        selected = values.get(language, group['default'])
        if not isinstance(selected, str) or selected not in {font['id'] for font in group['fonts']}:
            raise ValueError('Invalid font preference.')
        result[language] = selected
    return result


def font_tables(data):
    if data[:4] not in (b'\x00\x01\x00\x00', b'OTTO'):
        raise ValueError('Not an OpenType/TrueType font.')
    count = struct.unpack_from('>H', data, 4)[0]
    tables = {}
    for index in range(count):
        tag, _, offset, length = struct.unpack_from('>4sIII', data, 12 + 16 * index)
        if offset + length > len(data):
            raise ValueError('Truncated font table.')
        tables[tag] = data[offset:offset + length]
    return tables


def font_weight(data):
    tables = font_tables(data)
    if b'fvar' in tables:
        table = tables[b'fvar']
        offset, _, count, size = struct.unpack_from('>HHHH', table, 4)
        for index in range(count):
            axis = offset + index * size
            if table[axis:axis + 4] == b'wght':
                low = round(struct.unpack_from('>i', table, axis + 4)[0] / 65536)
                high = round(struct.unpack_from('>i', table, axis + 12)[0] / 65536)
                return f'{low} {high}'
    return str(struct.unpack_from('>H', tables[b'OS/2'], 4)[0])


def has_glyph(tables, codepoint):
    cmap = tables[b'cmap']
    count = struct.unpack_from('>H', cmap, 2)[0]
    for index in range(count):
        platform, encoding, offset = struct.unpack_from('>HHI', cmap, 4 + index * 8)
        if platform != 0 and not (platform == 3 and encoding in (1, 10)):
            continue
        table = cmap[offset:]
        fmt = struct.unpack_from('>H', table)[0]
        if fmt == 12:
            groups = struct.unpack_from('>I', table, 12)[0]
            for group in range(groups):
                first, last, glyph = struct.unpack_from('>III', table, 16 + group * 12)
                if first <= codepoint <= last:
                    return glyph + codepoint - first != 0
        elif fmt == 4 and codepoint <= 0xFFFF:
            segments = struct.unpack_from('>H', table, 6)[0] // 2
            for segment in range(segments):
                last = struct.unpack_from('>H', table, 14 + segment * 2)[0]
                first = struct.unpack_from('>H', table, 16 + segments * 2 + segment * 2)[0]
                if not first <= codepoint <= last:
                    continue
                delta = struct.unpack_from('>h', table, 16 + segments * 4 + segment * 2)[0]
                position = 16 + segments * 6 + segment * 2
                distance = struct.unpack_from('>H', table, position)[0]
                if not distance:
                    return (codepoint + delta) % 65536 != 0
                glyph = struct.unpack_from('>H', table, position + distance + (codepoint - first) * 2)[0]
                return glyph != 0 and (glyph + delta) % 65536 != 0
    return False


def frontend_catalog():
    return {language: dict(default=group['default'], sample=group['sample'],
                           fonts=[dict(id=font['id'], name=font['name']) for font in group['fonts']])
            for language, group in font_catalog()['languages'].items()}


def generated_assets():
    css = ['/* Vendored original font files. Licenses and hashes: fonts/catalog.json. */']
    for group in font_catalog()['languages'].values():
        for font in group['fonts']:
            for face in font['files']:
                css.append('@font-face { font-family: "Studio-' + font['id'] + '"; src: url("fonts/' +
                           face['file'] + '") format("truetype"); font-style: normal; font-weight: ' +
                           face['weight'] + '; font-display: swap; }')
    script = '// Generated from fonts/catalog.json; keep font_assets.py --check passing.\n'
    script += 'window.StudioFontCatalog = ' + json.dumps(frontend_catalog(), ensure_ascii=False, indent=2) + ';\n'
    return '\n'.join(css) + '\n', script


def check_font_assets():
    root = resource_path('ui', 'fonts')
    catalog = font_catalog()
    if catalog['schema'] != 1:
        raise ValueError('Unsupported font catalog.')
    for language, expected_count in (('en', 5), ('th', 5), ('ja', 3), ('zh-CN', 3)):
        group = catalog['languages'][language]
        if len(group['fonts']) != expected_count:
            raise ValueError('Incomplete font catalog: ' + language)
        for font in group['fonts']:
            license_text = (root / font['license']).read_text(encoding='utf-8')
            if 'SIL OPEN FONT LICENSE' not in license_text:
                raise ValueError('Missing font license: ' + font['id'])
            for face in font['files']:
                data = (root / face['file']).read_bytes()
                if len(data) != face['size'] or hashlib.sha256(data).hexdigest() != face['sha256']:
                    raise ValueError('Font checksum mismatch: ' + face['file'])
                if font_weight(data) != face['weight']:
                    raise ValueError('Incorrect font weight metadata: ' + face['file'])
                tables = font_tables(data)
                if any(not has_glyph(tables, ord(char)) for char in group['sample'] if not char.isspace()):
                    raise ValueError('Font is missing characters for ' + language + ': ' + face['file'])
    validate_fonts()
    css, script = generated_assets()
    if resource_path('ui', 'fonts.css').read_text(encoding='utf-8') != css or \
            resource_path('ui', 'font-catalog.js').read_text(encoding='utf-8') != script:
        raise ValueError('Generated font CSS/catalog is out of date.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.generate:
        css, script = generated_assets()
        resource_path('ui', 'fonts.css').write_text(css, encoding='utf-8')
        resource_path('ui', 'font-catalog.js').write_text(script, encoding='utf-8')
    check_font_assets()
    print('Offline font assets verified: 16 families, original files, weights, glyphs, licenses and checksums.')
