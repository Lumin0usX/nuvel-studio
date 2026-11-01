# Third-party notices

The GPL-3.0-only grant in `COPYRIGHT`, with the full text in `LICENSE`, covers
only original project work the owner has authority to license. It does not replace
or restrict licenses granted by third parties for their own materials.

Copyright © 2026 Lumin0usX. This notice is not distribution clearance for a whole
executable. Public Windows and macOS binary releases remain **BLOCKED**.

## Dependencies

Runtime and build dependencies include Python, yt-dlp and its optional
dependencies, imageio-ffmpeg, FFmpeg, pywebview and its platform dependencies,
and PyInstaller. Their licenses and notices are maintained by the respective
upstream projects and in the installed packages.

- Python: https://www.python.org/psf/license/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- mutagen (GPL-2.0-or-later; observed in an existing GUI PYZ): https://github.com/quodlibet/mutagen
- imageio-ffmpeg: https://github.com/imageio/imageio-ffmpeg
- FFmpeg: https://ffmpeg.org/legal.html
- pywebview: https://github.com/r0x0r/pywebview
- PyInstaller: https://github.com/pyinstaller/pyinstaller
- gallery-dl (environment 1.32.17; packaged CLI/source 1.32.19: GPL version 2): https://github.com/mikf/gallery-dl
- Pillow: https://github.com/python-pillow/Pillow

Image-post extraction invokes gallery-dl as a separate command-line process.
The source installer installs it into the Python environment. The Windows and
macOS builders exclude gallery-dl from the GUI interpreter and package it as a
separate command-line executable under `bin`. It is launched only as a child
process. Its corresponding Python source, GPL-2.0 license and build description
are included under `third-party/gallery-dl` in the bundled resources. Its code
and license remain distinct from the terms of original project application code.

**Distribution hold (2026-11-01):** the inspected frozen CLI combines GPLv2-only
gallery-dl with Apache-2.0 requests. No applicable exception or compatible release
has been verified. Separate execution from the GUI does not resolve the CLI's
internal licensing question. A GPL-3.0-only original-code grant also does not
provide a GPLv2-compatible grant for a copyrightable generated entry combined
with GPLv2-only code. Preserve this independent review/blocker and all upstream
notices; do not interpret the package layout as clearance for distribution.


Before distributing a packaged application, review the exact dependency
versions and FFmpeg build that are included, preserve their required notices,
and satisfy any applicable source-distribution requirements. Private hosting
and this project's GPL-3.0-only choice do not remove those
obligations. Generated applications and binaries are excluded from this
source repository by default.

The 2026-10-31 audit is **not a distribution clearance**. Both inspected macOS
FFmpeg files identify as GPL version 2 or later and enable GPL components;
the BSD license of the imageio-ffmpeg Python wrapper is not FFmpeg's license.
The current Windows executable has not been attested in this audit. Matching
FFmpeg/library source and build materials have not been supplied by this tree.
Gallery-dl's copied Python source does not by itself establish completeness for
its whole frozen executable, dependencies and bootloader. See `legal/AUDIT.md`.

New builders require an explicit source-bearing LGPL FFmpeg bundle through
`NUVEL_FFMPEG_BUNDLE`, exclude imageio-ffmpeg from the GUI package, and include
the supplied source/build materials under `third-party/ffmpeg`. This migration
is incomplete: no replacement LGPL binary or native package has passed acceptance
in this audit. Source development can still use the GPL imageio binary; old
packages are unaffected. See `legal/FFMPEG-LGPL.md`.

## Bundled fonts

UI font families are original, unmodified files from the Google Fonts repository:
Inter, Roboto, Open Sans, Montserrat, Lato, Noto Sans Thai, Sarabun, Kanit, Prompt,
IBM Plex Sans Thai, Noto Sans JP, Noto Serif JP, M PLUS 1p, Noto Sans SC,
Noto Serif SC, and ZCOOL XiaoWei.

Each font retains its SIL Open Font License and copyright notices under
`ui/fonts/*-OFL.txt`. Source links, file sizes, actual weight ranges and SHA-256
hashes are in `ui/fonts/catalog.json`. Font files are not covered by the app's
new GPL grant. Their internal font names, outlines and glyph sets are
unchanged; CSS aliases scope their use to this application.

Upstream: https://github.com/google/fonts

## Platform marks

YouTube, TikTok, Facebook, Instagram, X/Twitter, Reddit, Vimeo, Dailymotion,
Twitch, Bilibili, Pinterest, Bluesky, SoundCloud, Bandcamp, Mixcloud, Audiomack,
Flickr, Imgur, Tumblr, Pixiv, DeviantArt, Unsplash, VK, RuTube, Rumble,
Streamable, Internet Archive, Niconico, Douyin, Snapchat, LinkedIn, Telegram,
Weibo, Xiaohongshu / RED, Kick, Odysee, PeerTube, TED, 9GAG, Medal.tv,
Apple Podcasts, Audius, ArtStation, Behance, Pexels, 500px, Wallhaven,
ImgBB, Lensdump, and Wikimedia Commons names and marks identify their respective
platforms. They belong to their respective owners. Their inclusion does not
imply endorsement, sponsorship, or affiliation.

The current application uses plain platform names, without platform artwork.
The owner confirms the former platform artwork was sourced by Codex; that alone
is not an upstream license or third-party clearance. Local Strategy B history
remediation replaced the inventoried artwork with Feather-derived neutral assets
and replaced the historical SVG symbol definitions. This does not establish
removal from GitHub, caches, other clones or previously distributed packages.
`build_platform_icons.py` remains the legacy command name for the text catalog.

The owner confirms the supplied 03-Fluid kit is **AI-generated artwork created
using OpenAI ChatGPT Image Generation at the direction of the project owner.**
Brand artwork is excluded from the new software grant; existing artwork terms
remain unchanged. No automatic copyright protection, exclusivity or trademark
registration is asserted. See [BRAND-NOTICE.md](BRAND-NOTICE.md) and [COPYRIGHT](COPYRIGHT).

## Feather icons and remediation placeholders

The current inline SVG symbol sprite in `ui/index.html` uses adapted Feather
4.29.2 icons, Copyright (c) 2013-2023 Cole Bemis, under MIT. The selected original
SVGs, neutral PNG and generator paint adaptations, source archive URL, archive
hash and per-icon hashes are recorded in
[third_party/feather/PROVENANCE.md](third_party/feather/PROVENANCE.md).
Retain the complete [MIT license and copyright notice](third_party/feather/LICENSE)
with copies or substantial portions. This license does not relicense NÜVEL
branding or the original application template. No file-wide GPL header is applied
to the mixed HTML file. Font OFL texts and all other third-party license texts
remain unchanged.
