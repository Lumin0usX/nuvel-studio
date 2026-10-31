# Third-party notices

The proprietary license in `LICENSE` covers only the original materials
owned by this project's copyright holder. It does not replace or restrict
licenses granted by third parties for their own materials.

## Dependencies

Runtime and build dependencies include Python, yt-dlp and its optional
dependencies, imageio-ffmpeg, FFmpeg, pywebview and its platform dependencies,
and PyInstaller. Their licenses and notices are maintained by the respective
upstream projects and in the installed packages.

- Python: https://www.python.org/psf/license/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- imageio-ffmpeg: https://github.com/imageio/imageio-ffmpeg
- FFmpeg: https://ffmpeg.org/legal.html
- pywebview: https://github.com/r0x0r/pywebview
- PyInstaller: https://github.com/pyinstaller/pyinstaller
- gallery-dl (audited 1.32.17: GPL version 2): https://github.com/mikf/gallery-dl
- Pillow: https://github.com/python-pillow/Pillow

Image-post extraction invokes gallery-dl as a separate command-line process.
The source installer installs it into the Python environment. The Windows and
macOS builders exclude gallery-dl from the GUI interpreter and package it as a
separate command-line executable under `bin`. It is launched only as a child
process. Its corresponding Python source, GPL-2.0 license and build description
are included under `third-party/gallery-dl` in the bundled resources. Its code
and license remain separate from the original proprietary application code.

Before distributing a packaged application, review the exact dependency
versions and FFmpeg build that are included, preserve their required notices,
and satisfy any applicable source-distribution requirements. A private
repository and this project's proprietary license do not remove those
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
proprietary license. Their internal font names, outlines and glyph sets are
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

The current source and new builds use plain platform names, without the former
platform artwork. Historical Git commits and previously built/released packages
can still contain that artwork; they have not been rewritten or withdrawn.
`build_platform_icons.py` is retained as a legacy command name for regenerating
the text-only offline catalog. The separate NÜVEL identity remains unchanged;
its supplied brand-kit provenance still requires the owner's confirmation.
