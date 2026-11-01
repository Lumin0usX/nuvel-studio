# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

"""Offline NÜVEL Studio artwork, shared by native builders and the browser fallback."""
from platform_runtime import resource_path


UI_BRAND_ASSETS = {
    **{f'nuvel-{variant}-{color}.svg': 'image/svg+xml'
       for variant in ('primary', 'small', 'wordmark') for color in ('black', 'white')},
    'favicon.svg': 'image/svg+xml',
    'favicon.ico': 'image/x-icon',
    **{name: 'image/png' for name in (
        'favicon-16.png', 'favicon-32.png', 'favicon-48.png', 'apple-touch-icon.png',
        'icon-192.png', 'icon-512.png', 'nuvel-small-white.png')},
}


def check_brand_assets():
    """Reject a package with missing artwork or incomplete native app icons."""
    from PIL import Image
    for name in UI_BRAND_ASSETS:
        if not resource_path('ui', 'brand', name).is_file():
            raise ValueError('Missing brand asset: ' + name)
    root = resource_path('assets', 'branding')
    with Image.open(root / 'app-icon-1024.png') as image:
        if image.size != (1024, 1024):
            raise ValueError('The native icon master must be 1024 × 1024.')
        image.verify()
    with Image.open(root / 'app-icon.ico') as image:
        if not {(size, size) for size in (16, 32, 48, 64, 128, 256)} <= image.ico.sizes():
            raise ValueError('The Windows icon is missing required resolutions.')
    with Image.open(root / 'app-icon.icns') as image:
        if (512, 512, 2) not in image.info['sizes']:
            raise ValueError('The macOS icon is missing its 1024 px representation.')


if __name__ == '__main__':
    check_brand_assets()
    print('NÜVEL Studio Fluid artwork, favicon and native app icons verified.')
