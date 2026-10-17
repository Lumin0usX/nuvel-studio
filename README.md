# YTDL Studio

A desktop video and audio downloader with a Liquid Glass-inspired interface,
powered by yt-dlp. Original project materials are proprietary.

## Features

- Download video as MP4 or audio as MP3.
- Local WebView interface with translucent cards and a responsive layout.
- Platform indicators for YouTube, TikTok, Facebook, Instagram, X, Reddit,
  Vimeo, Dailymotion, Twitch Clips, Bilibili, and Pinterest.
- Support for other sources available through the installed yt-dlp extractors.
- Progress, transfer speed, estimated time remaining, cancellation, and the
  last eight successful downloads from the current session.
- Optional browser cookies or a Netscape-format cookie file for authenticated content.

Platform indicators report installed extractor support, not successful live
tests of every service or URL. This project does not bypass DRM.

## Windows

Install Python 3.10+ and enable **Add Python to PATH**, then run:

```bat
install.bat
start.bat
```

The native interface requires pywebview and Microsoft Edge WebView2 Runtime.
When pywebview is not installed, the launcher serves the UI on an authenticated
loopback address and opens Edge/Chrome in app mode, or the default browser.
Keep the launcher terminal open in this fallback mode. Folder and cookie file
paths can be entered manually; native file dialogs require pywebview.

Validate launcher dependencies without opening the UI:

```bat
start.bat --check
install.bat --check
```

## macOS Apple Silicon

Use native ARM64 Python 3.12+ and run these commands from the project directory:

```bash
bash install_macos.command
bash start_macos.command
```

Build a local `.app` **on an Apple Silicon Mac**:

```bash
bash build_macos.command
```

See [the macOS guide](README-macOS.md). The build is ad-hoc signed, not notarized
for public distribution. A macOS binary cannot be built by this project on Windows.

## Validation status

- Python unit tests cover platform adapters, download transitions, validation,
  cancellation, and successful/failed jobs using mocks.
- Windows launcher checks and the authenticated local HTTP bridge were tested.
- JavaScript syntax and HTML element bindings were checked.
- The new interface has not completed visual or end-to-end validation on a real
  Windows desktop or Apple Silicon Mac. Live downloads have not been verified
  across all listed platforms. No finished macOS binary is included.

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

## Project layout

| Path | Purpose |
| --- | --- |
| `ytdl_studio.py` | Main launcher |
| `glass_app.py` | WebView shell, local API, download jobs |
| `ui/` | HTML, CSS, and JavaScript interface |
| `download_engine.py` | Platform registry and error guidance |
| `platform_runtime.py` | Cross-platform resources, FFmpeg, and folder opening |
| `assets/platforms/` | Bundled platform marks |
| `legacy_tk.py` | Previous interface, available with `--classic` |
| `tests/` | Automated tests |

`ui/index.html` can be opened for a static design preview. Downloads require the
launcher. Browser profiles, cookies, virtual environments, generated builds,
and downloaded media are excluded from version control.

## License

**Proprietary — All rights reserved.** Copyright © 2026 Lumin0usX.
Use, modification, and redistribution require prior written permission.
See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
