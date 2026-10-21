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
- gallery-dl (GPL-2.0): https://github.com/mikf/gallery-dl
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

The bundled small platform graphics are stylized identification marks
rendered by `build_platform_icons.py`, not official brand asset downloads.
No ownership of the underlying brands or trademarks is claimed.
