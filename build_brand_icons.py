"""Export native icons from the 1024 px rendering of the supplied Fluid favicon SVG."""
from PIL import Image
from platform_runtime import resource_path


def main():
    root = resource_path('assets', 'branding')
    with Image.open(root / 'app-icon-1024.png') as image:
        image.save(root / 'app-icon.ico', sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
        image.save(root / 'app-icon.icns')
    from branding import check_brand_assets
    check_brand_assets()
    print('Exported NÜVEL Studio icons for Windows and macOS.')


if __name__ == '__main__':
    main()
