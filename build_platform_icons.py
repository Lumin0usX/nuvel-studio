"""Legacy command name: refresh the text-only offline platform catalog, not logos."""
import json
from pathlib import Path
import re
from download_engine import PLATFORMS, PLATFORM_DOMAINS, AUDIO_ONLY, IMAGE_MODULES


def main():
    catalog = [dict(name=label, slug=slug, color=color, status='unknown', domains=PLATFORM_DOMAINS[slug],
                    video_status='unsupported' if not key or slug in AUDIO_ONLY else 'unknown',
                    audio_status='unknown' if key else 'unsupported',
                    image_status='unknown' if slug in IMAGE_MODULES else 'unsupported')
               for label, key, slug, color in PLATFORMS]
    page = Path(__file__).resolve().parent / 'ui/index.html'
    html, count = re.subn(r'(<script id="platform-seed" type="application/json">).*?(</script>)',
                         lambda match: match[1] + json.dumps(catalog, ensure_ascii=False) + match[2],
                         page.read_text(encoding='utf-8'), flags=re.S)
    if count != 1:
        raise RuntimeError('Expected one offline platform catalog.')
    page.write_text(html, encoding='utf-8')
    print(f'Refreshed {len(catalog)} source names; no platform artwork generated.')


if __name__ == '__main__':
    main()
