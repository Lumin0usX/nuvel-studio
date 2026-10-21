# YTDL Studio

A desktop video, audio and image downloader with the Obsidian Futuristic interface,
powered by yt-dlp. Original project materials are proprietary.

## Features

- Download video as MP4; save native audio or choose an MP3 bitrate.
- Download original raster images directly (JPEG, PNG, WebP, GIF, AVIF, HEIC,
  TIFF, BMP, JXL, ICO), including image endpoints without file extensions.
- Download images from posts/albums through the separately invoked gallery-dl
  CLI. Image mode filters out videos and preserves original image formats.
- Desktop sidebar with Overview, Downloads, searchable History, and Settings.
  Contextual quality controls, real metadata previews where available, a transfer
  dock across pages, and Ctrl/Cmd + Enter to start from Overview.
- Dark design tokens, keyboard focus states, responsive auto-collapse, reduced
  motion and compact list preferences. No frontend framework or UI dependencies.
- Searchable platform indicators for 50 services, sorted with supported sources
  first. Video, audio and image capabilities are reported separately.
- New sources in the catalog: Bluesky, SoundCloud, Bandcamp, Mixcloud,
  Audiomack, Flickr, Imgur, Tumblr, Pixiv, DeviantArt, Unsplash, VK, RuTube,
  Rumble, Streamable, Internet Archive, Niconico, Douyin, and Snapchat Spotlight.
  Pixiv, DeviantArt and Unsplash use image mode. Music services use audio mode.
- Expanded catalog: LinkedIn, Telegram, Weibo, Xiaohongshu / RED, Kick, Odysee,
  PeerTube, TED, 9GAG, Medal.tv, Apple Podcasts, Audius, ArtStation, Behance,
  Pexels, 500px, Wallhaven, ImgBB, Lensdump, and Wikimedia Commons.
  Telegram uses public post embeds; PeerTube support depends on the instance.
  Apple Podcasts requires episode links, and Audius uses audio mode.
  ArtStation, Behance, Pexels, 500px, Wallhaven, ImgBB and Lensdump are image
  sources in this catalog. RED is listed for video/audio, not photo albums.
- Support for other sources available through the installed yt-dlp extractors.
- Progress, transfer speed, estimated time remaining, cancellation, and the
  last eight successful downloads from the current session.
- Optional browser cookies or a Netscape-format cookie file for authenticated content.

Platform indicators report installed extractor support, not successful live
tests of every service or URL. This project does not bypass DRM.
The installed engines currently report 34 video, 40 audio and 25 image sources
across the 50 entries; counts change with engine availability/version.

## Desktop interface

The HTML/CSS/JavaScript interface runs in the existing pywebview shell (or its
authenticated localhost fallback). Native window controls remain unchanged.
Metadata reads use yt-dlp without starting a download; unavailable previews do
not block downloading. Image-post metadata is read only during the actual job.

Settings use an atomic, per-user JSON file under `YTDLStudio/preferences.json`:
Local AppData on Windows, Application Support on macOS, or XDG config on Linux.
Destination, appearance and language preferences persist; cookies and cookie-file
paths remain in memory. Inter and Noto Sans Thai are preferred when installed,
with native system font fallbacks; the UI makes no external font requests.

Choose **Settings → General → Language** for English, Thai, Japanese, or
Simplified Chinese. The interface switches immediately and remembers the choice
across app launches. All translation assets are bundled for offline use, including
quality options, status messages, help and accessibility labels. Media titles,
filenames, platform names and raw third-party diagnostics stay in their original
form. Switching languages preserves quality selections and settings drafts.

Downloads supports the existing single-job workflow, cancellation, retry in the
current UI session, and opening folders. There is no pause/resume or queue.
History retains the latest eight successful jobs in memory; removing a record
does not delete a file. Opening individual files is not offered because the
backend does not reliably return a final file path for every mode and job.

See [UI review and verification](DESIGN.md) for design decisions and QA limits.

Close Studio and double-click `update.bat` on Windows or `update_macos.command`
on macOS in the Git clone to fetch the latest `main` and update dependencies.
On macOS, choose option 2 to also build a new `.app`; replace the old app manually
after the successful build.
The private repository requires existing GitHub access. Local changes and
diverged history stop the update without discarding files. See
[macOS update instructions](README-macOS.md) for setup and limitations.

## Quality preferences

All three modes default to the highest quality the source exposes.

- Video: highest available, or a height ceiling from 360p through 8K/4320p.
  The downloader chooses the best format at or below the cap; if none exists,
  it reports an error instead of downloading above the cap. It does not upscale.
- Audio: the default keeps the best audio stream and native codec when possible
  (for example M4A or Opus). To export MP3, select 96/128/192/256/320 kbps.
  Re-encoding at a higher bitrate cannot improve a low-quality source.
- Images: the default preserves the exact downloaded bytes. Other choices
  limit the long edge to 640–4096 px after download, preserving aspect ratio
  and never enlarging smaller originals. Resizing needs Pillow. JPEG/WebP
  resizing re-encodes at quality 95; GIF/WebP/APNG animation is retained within
  processing limits. Unsupported codecs, very large animations or multipage
  documents require original quality; failures leave the downloaded original.

Selections are independent for each mode during the current app session.
History records the requested quality ceiling, not a claim that the source
actually had that resolution. Direct links cannot retrieve a larger image than
the linked file itself; there is no AI upscaling or invented source quality.

## Image download setup

Run the installer again after updating (`install.bat` on Windows, or
`bash install_macos.command` on macOS). It installs gallery-dl alongside the app.
Choose **ภาพ**, paste an image, post or album URL, and download. Direct image
links work without gallery-dl. Post/album support depends on the installed
[gallery-dl extractors](https://gdl-org.github.io/docs/supportedsites.html);
some sites require cookies from an account that can view the content.

Image mode shows separate source indicators; they inspect local extractor
modules and do not promise that every post will work. Other gallery-dl sources
outside the catalog can also be entered directly. The catalog includes Flickr,
Imgur, Tumblr, Pixiv, DeviantArt, Unsplash and Bluesky with their own logo tiles.
A profile URL can download multiple posts; use a post URL for a smaller job.

Direct files go into the selected folder without overwriting existing files.
Gallery jobs use a separate `Images-<timestamp>` subfolder. Progress shows
image counts when the total is unknown. Cancellation preserves completed
images; partial/failed jobs are not added to the success history. Direct
images have a 256 MB per-file limit. SVG and arbitrary HTML scraping are not
supported. Video thumbnails are not used as a substitute for image posts.

The packaged macOS `.app` does not bundle gallery-dl. Install the external CLI
with `brew install gallery-dl` or `pipx install gallery-dl`, then reopen the app.
Direct image links still work without that CLI.

Image transfers are covered by local automated tests (including a simulated
gallery subprocess). Live social-site downloads have not been verified here;
the development environment blocks package/network connections.

## Windows

Install 64-bit x64 Python 3.10+ and enable **Add Python to PATH**, then run:

```bat
build_windows.bat
```

Then double-click **YTDL Studio** (`YTDL Studio.lnk`) in the project folder.
The builder prepares an isolated environment, bundles the application and
creates a shortcut to **app-windows/YTDL Studio.exe**. The application includes
Python, the UI, video/audio engines and FFmpeg. Keep the complete app-windows
folder together; the exe depends on its bundled `_internal` directory.
The portable ZIP is kept in `dist/windows-<build timestamp>`.

Microsoft Edge WebView2 Runtime must be available on Windows.
The windowless launcher reports startup failures with a dialog and a log in
`%LOCALAPPDATA%\YTDLStudio\logs`. It requires the native bridge; it never leaves
an invisible browser server running. Closing the window ends its session and
stops owned download/conversion processes. Closing during a download asks for
confirmation and can leave partial files.

`start.bat` remains available for terminal diagnostics. When pywebview is not
installed, that diagnostic launcher serves the UI on an authenticated
loopback address and opens Edge/Chrome in app mode, or the default browser.
Keep the launcher terminal open in this fallback mode. Folder and cookie file
paths can be entered manually; native file dialogs require pywebview.

Validate the build Python without installing or opening the UI:

```bat
build_windows.bat --check
update.bat --check
```

To update, close Studio and double-click **update.bat** in the project folder.
It updates code, prepares dependencies and rebuilds the packaged application.
The relocated executable must complete a native UI/bridge/FFmpeg test and
confirm that it has no console before it replaces the app and shortcut.
Startup failure, a locked running app or publication failure preserves the
previous app. Open the **YTDL Studio** shortcut after success.
Git for Windows must be installed, and Git must have access to the private repo.
The first update requires `git pull --ff-only origin main` to receive update.bat.
Local changes or conflicting Git history stop the update without discarding files.
Locally built apps use gallery-dl from the managed build environment as a separate
process. The portable ZIP excludes that CLI, as on macOS; an independent CLI
installation is needed for image posts on a machine receiving only the ZIP.
Direct image URLs work without it. See [the Windows guide](README-Windows.md).

## macOS Apple Silicon

Use native ARM64 Python 3.12+ and run these commands from the project directory:

```bash
bash build_macos.command
```

The build prepares dependencies and produces **YTDL Studio.app** directly in
the project folder. Open this app for normal use without Terminal. It contains
the Python runtime, UI, video/audio engines and FFmpeg; you may copy it into
Applications. The distributable ZIP is also kept in `dist/<build timestamp>`.

Double-click **update_macos.command** to update and rebuild in one flow, with
no source/packaged mode choice. The app in the project folder is replaced only
after the new bundle passes a native startup test. Previous apps are preserved
in `dist`. If you made a separate copy in Applications, replace that copy with
the newly built app. The old AppleScript launcher is migrated automatically to
a link to the main app. No runtime repair commands are part of normal setup.

See [the macOS guide](README-macOS.md). The build is ad-hoc signed, not notarized
for public distribution. A macOS binary cannot be built by this project on Windows.

## Validation status

- Windows tests exercise a real shortcut launched from a Thai path and a hidden
  session that stops a remaining subprocess when its GUI exits.
- Windows packaging tests cover GUI subsystem validation, missing/wrong startup
  proof, console detection, locked apps and rollback of both app and shortcut.
  PyInstaller was unavailable from the package index in this development
  environment, so a real Windows executable has not been built or validated here.
- macOS publication tests cover startup failure, missing startup proof, rollback,
  preservation of previous apps and refusal to replace unrelated applications.
  Each actual Mac build tests the relocated app through LaunchServices and
  requires success proof from its native UI before publishing the app or ZIP.
  That native acceptance test cannot be run on this Windows development machine;
  the new packaging flow still requires verification on Apple Silicon.
- Python unit tests cover platform adapters, download transitions, validation,
  cancellation, and successful/failed jobs using mocks.
- Windows launcher checks and the authenticated local HTTP bridge were tested.
- JavaScript syntax and HTML element bindings were checked.
- Browser workflow was tested with real local image transfers, cancellation,
  retry, history, settings and responsive layouts. The targeted UI refinement was
  reviewed with actual browser screenshots; native Apple Silicon validation remains open.
  Live downloads were not verified across all platforms. No macOS binary is included.

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
| `ui/i18n.js` | Offline translations and live language switching |
| `download_engine.py` | Platform registry and error guidance |
| `platform_runtime.py` | Cross-platform resources, FFmpeg, and folder opening |
| `ui_preferences.py` | Validated, atomic per-user appearance/destination preferences |
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
