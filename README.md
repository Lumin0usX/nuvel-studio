# NÜVEL Studio

A desktop video, audio and image downloader with the Obsidian Futuristic interface,
powered by yt-dlp. Original project materials are proprietary.

The app uses the **NÜVEL Studio — 03 Fluid** identity, with the supplied outlined
black/white logos and extracted Ü app icon. The sidebar follows the app theme
and shows the Ü icon when collapsed. See [brand assets](assets/branding/README.md).
The 2.0 identity uses NÜVEL throughout: `nuvel_studio.py`, `NuvelStudio` user data
and credentials, `local.nuvelstudio.app`, `nuvel-obsidian-preferences-v1`, and
`NUVEL-Studio-*.zip` releases. Windows builds produce **NÜVEL Studio.exe** and
**NÜVEL Studio.lnk**; macOS builds produce **NÜVEL Studio.app** with a
**NÜVEL Studio** executable. Both platforms use the supplied ICO/ICNS icons.

**2.0 is an unreleased packaging boundary.** Older packaged versions require a
one-time installation of the new package; their updater cannot consume the new
archive names, roots or product IDs. Configure private-repository access again
for the new credential namespace. Existing downloads are unaffected. The new
repository address below requires the GitHub repository rename to be completed.

Source-folder updates on macOS can migrate the already-branded 1.1.2–1.x app
automatically: the builder checks its historical bundle ID, build marker,
matching versions, name and executable before accepting it. The old app is
backed up only after the new app passes its native startup test. Historical
identifiers are retained only as read-only migration checks; new packages use
the 2.0 identity. This does not change the older packaged in-app updater.

## Uninstall

Open **Settings → Uninstall → Uninstall app**. Confirm the removal; the app
closes before an independent helper moves its verified bundle to the system
[Trash](https://developer.apple.com/documentation/foundation/filemanager/trashitem(at:resultingitemurl:)) /
[Recycle Bin](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shfileoperationw).
It works offline and a packaged installation does not require a system Python.
Close other copies of the app first. Active downloads or updates block removal.

Downloaded media, the source checkout, build environments and old builds are
kept. **Also remove preferences, startup logs and saved GitHub release access**
is off by default; selecting it removes only this app's known preference/log
files and its own credential-store entry, not Git/GitHub CLI credentials.
Only a matching adjacent Windows shortcut is removed. Other copied shortcuts
and other app installations are kept.

Source installations also have **uninstall.bat** and **uninstall_macos.command**
for double-click removal of the project-local app. `uninstall.bat --check` or
`./uninstall_macos.command --check` validates the target without uninstalling.
The source scripts use the existing Python environment and do not install or
download anything. If the app folder contains downloads/extra files, move them
outside the app first. New builds include an installed-file inventory to catch
extra files even if the output-folder preference has since changed. Older
builds conservatively reject media found outside their UI/artwork directories.
This portable app does not register a Windows Apps & Features uninstall entry.

## Download the ready-to-use app

Open [Releases](https://github.com/Lumin0usX/nuvel-studio/releases) while signed in
to a GitHub account with access to this private repository. Download the ZIP
asset, not GitHub's automatically generated source-code archive.

- Windows x64: extract **NUVEL-Studio-Windows-x64.zip**, keep the entire
  **NÜVEL Studio** folder, and open **NÜVEL Studio.exe**. Windows 10/11 needs
  [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
  (normally already installed). Python, Git and a terminal are not needed.
- Mac Apple Silicon: extract **NUVEL-Studio-macOS-arm64.zip**, move
  **NÜVEL Studio.app** to a writable location such as your user's Applications
  folder, and open it. Python, Homebrew and a terminal are not needed.

Both packages include FFmpeg and an isolated gallery-dl CLI for image posts.
The legal audit selected LGPL FFmpeg for future packages. Builders now stop
until an explicit source-bearing LGPL bundle is supplied; migration and native
acceptance remain incomplete. Review the [audit](legal/AUDIT.md) and
[FFmpeg requirements](legal/FFMPEG-LGPL.md) before building or distributing.
Local builds are ad-hoc signed, not Apple-notarized or Windows Authenticode-signed;
OS trust prompts can appear on a first download. A release is published only
after both native build jobs and their startup checks succeed.

### Update from inside the app

Use **Settings → App updates → Check for updates**. For this private repository,
expand **Private repository access** and save a fine-grained GitHub token scoped
to **Lumin0usX/nuvel-studio**, with **Contents: read-only**. Windows Credential
Manager or macOS Keychain stores it; it is not written to preferences, release
files, localStorage or the source repository. Use **Remove saved access** to
delete the saved credential. Browser GitHub sign-in alone does not authenticate
the desktop updater.
If the OS credential store is unavailable, access is kept in memory for the
current session only and the app clearly says so; no plain-text fallback is used.

Choose **Download update**, then **Restart and install**. The app checks the
release version, SHA-256 and package layout, then tests the staged native app.
Installation is disabled during media downloads. Once requested, it replaces the
app at its existing path, tests it again, and restarts it. A failed startup restores the previous app.
Downloaded media and per-user preferences are not replaced. The previous bundle
is kept in the adjacent `.nuvel-update-*` directory. Updates require a writable
installation folder and sufficient space for the download, staged app and backup.
Network or access failures leave the existing app usable.

Source users must build **this version once** to enable packaged installation.
Source launches can check releases but cannot replace the running Python
environment in-app. Earlier package identities need the new one-time installation.
Until a release is published, the app reports that no packaged release is available.

### Publish a version (maintainer)

Set `VERSION` in `app_version.py`, commit, and push a matching tag, for example
`v2.0.0`. `.github/workflows/release.yml` builds Windows x64 and macOS ARM64 on
their native GitHub runners, runs tests and native startup checks, and uploads
both ZIPs plus `studio-update.json` to a draft release. Only the complete release
is published. Re-running is supported for drafts; published versions must not
be overwritten. This is separate from the Git-based source updater below.

```powershell
git add .
git commit -m "Complete NUVEL Studio identity and packaging"
git push origin main
git tag v2.0.0
git push origin v2.0.0
```

The workflow must be enabled in this private repository. No personal token or
signing credential is embedded in its artifacts. The workflow uses GitHub's
short-lived repository token only for publishing release assets.

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
tests of every service or URL. The app does not enable DRM-protected formats.
Technical support is not permission to download or reuse content. Follow the
source's terms and obtain any required rights. See [legal/distribution audit](legal/AUDIT.md).
The installed engines currently report 34 video, 40 audio and 25 image sources
across the 50 entries; counts change with engine availability/version.

## Desktop interface

The HTML/CSS/JavaScript interface runs in the existing pywebview shell (or its
authenticated localhost fallback). Native window controls remain unchanged.
Status polling acknowledges an engine-catalog revision, so unchanged platform
source names and extractor details are not resent with each progress update. A fresh
connection or completed engine scan sends the complete catalog again; clients
requesting `snapshot()` without an argument still receive the full response.
The overview keeps a bounded composer close to the sidebar, with compact media
choices and quality, output format, destination and download action grouped
together. Empty recent activity is a single line below the composer. A dedicated
activity column appears on wide windows only when real jobs or history exist;
smaller windows keep activity below the workflow. Source counts refer to support
in the currently selected media mode; fixed output formats are labels, not controls.
Supported sources initially show eight entries; **View all sources** expands the
directory, and search always covers the entire list, including hidden entries.
Metadata reads use yt-dlp without starting a download; unavailable previews do
not block downloading. Image-post metadata is read only during the actual job.

Settings use an atomic, per-user JSON file under `NuvelStudio/preferences.json`:
Local AppData on Windows, Application Support on macOS, or XDG config on Linux.
Destination, appearance, language and per-language font preferences persist;
cookies and cookie-file paths remain in memory. The UI fonts and their licenses
are bundled; the app makes no external font requests and does not install fonts
into the operating system.

Choose **Settings → General → Language** for English, Thai, Japanese, or
Simplified Chinese. The interface switches immediately and remembers the choice
across app launches. All translation assets are bundled for offline use, including
quality options, status messages, help and accessibility labels. Media titles,
filenames, platform names and raw third-party diagnostics stay in their original
form. Switching languages preserves quality selections and settings drafts.

Choose **Settings → Appearance → Theme** for Dark, Light, or Follow system.
Dark is the default, including for older preferences without a theme setting.
Theme changes apply immediately and persist on this device. Follow system tracks
OS appearance changes; explicit Dark or Light choices stay fixed. Light uses a
soft gray canvas with matching controls, dialogs and progress colors.

Choose **Settings → Appearance → Interface style** for **Obsidian (original)**
or **Liquid Glass**. Obsidian remains the default. Liquid Glass adds translucent
material, softly lit edges and glass selection surfaces to the existing workflow;
both styles support Dark, Light, Follow system and every bundled font. Materials
use an opaque fallback when backdrop filtering is unavailable and respect system
Reduce Transparency where supported. This is an in-app material, not OS desktop vibrancy.

In Liquid Glass, **Glass opacity** adjusts the material from **0% (clear)** to
**100% (solid)**, with a **72%** default and a Reset action. Dragging updates glass
surfaces immediately; releasing the slider or using the keyboard saves the value.
Text, icons and download actions do not fade. The same value works in Dark and
Light and is retained when switching styles or restarting. If system Reduce
Transparency is enabled or the renderer lacks backdrop filtering, surfaces remain
opaque and the slider explains why it is unavailable; the saved value is preserved.

**Animations** switches motion on or off immediately and saves the preference.
Enabled motion includes a moving selection surface in navigation and media modes,
brief page, preview, dialog and toast entrances, and gentle button/switch feedback.
There is no ambient animation or idle rendering loop. Turning motion off cancels
active entrance effects and removes CSS transitions/animations, including progress
sweeps; actual progress information continues updating. System **Reduce Motion**
always takes precedence, and the settings row explains when it is active. Older
saved Reduce Motion preferences continue to work. Style and motion settings persist
across app launches independently of language, theme and fonts.

Choose **Settings → Appearance → Interface font**. The list follows the selected
interface language and remembers a different choice for each language:

| Language | Bundled choices |
| --- | --- |
| English | Inter, Roboto, Open Sans, Montserrat, Lato |
| Thai | Noto Sans Thai, Sarabun, Kanit, Prompt, IBM Plex Sans Thai |
| Japanese | Noto Sans JP, Noto Serif JP, M PLUS 1p |
| Simplified Chinese | Noto Sans SC, Noto Serif SC, ZCOOL XiaoWei |

A sample is shown below the selector. Changes apply and save immediately after
the actual font loads. Other scripts in media titles retain language-appropriate
fallbacks. Default families are Inter, Noto Sans Thai, Noto Sans JP and Noto Sans SC.
The original font files from Google Fonts are included under `ui/fonts` with
OFL licenses, source links and SHA-256 hashes. Native builds validate the files,
weights and sample glyphs; startup checks also require a bundled font to render.

Downloads supports the existing single-job workflow, cancellation, retry in the
current UI session, and opening folders. There is no pause/resume or queue.
History retains the latest eight successful jobs in memory; removing a record
does not delete a file. Opening individual files is not offered because the
backend does not reliably return a final file path for every mode and job.

See [UI review and verification](DESIGN.md) for design decisions and QA limits.

For a source checkout, close Studio and double-click `update.bat` on Windows or
`update_macos.command` on macOS in the Git clone. Both fetch the latest `main`,
update dependencies, build and verify the native app, and replace the project's
app only after a successful check. There is no build/skip-build choice.
The private repository requires existing GitHub access. Local changes and
diverged history stop the update without discarding files. See
[macOS update instructions](README-macOS.md) for setup and limitations.
The source updater also accepts this project's original GitHub repository URL
as a migration alias for existing clones, without changing their remote or
accepting repositories owned by other accounts.

The double-click launchers use a small, independent `update_bootstrap.py`.
It fetches and fast-forwards the source before starting `update_project.py` in
a fresh Python process, so a broken older build orchestrator can be replaced
before it runs. If fetching origin fails, it tries the other known project URL
once using the same HTTPS/SSH transport and existing credentials. It does not
rewrite origin, reset local work, or run a standalone script from a remote URL.
Both fetches failing stops the update; a stale `FETCH_HEAD` is never installed.
Build failures are reported without automatic retries.

This recovery path requires these new launcher/bootstrap files to have reached
the machine first. It cannot repair a broken bootstrap, missing Git/Python,
offline access, or missing private-repository permissions. Existing packaged
apps continue to use the separate release-based in-app updater.

## Quality preferences

All three modes default to the highest quality the source exposes.

Before downloading, optionally enter a **File name** in the download form.
Leave it blank to retain the source naming. Extensions follow the actual output
format automatically; a supplied media extension is removed from the name first.
Albums use numbered names such as `Trip-001.jpg` and `Trip-002.png`. Existing files
are kept, with `(1)`, `(2)`, etc. added to new names when needed. Names apply to
the current download request and its retry, rather than being saved as settings.

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
Imgur, Tumblr, Pixiv, DeviantArt, Unsplash and Bluesky as plain source names.
A profile URL can download multiple posts; use a post URL for a smaller job.

Direct files and gallery images go straight into the selected destination,
without a per-job subfolder or overwriting existing files. Progress shows
image counts when the total is unknown. Cancellation preserves completed
images; partial/failed jobs are not added to the success history. Direct
images have a 256 MB per-file limit. SVG and arbitrary HTML scraping are not
supported. Video thumbnails are not used as a substitute for image posts.

Both packaged apps include gallery-dl as a separate CLI. No independent CLI
installation is needed for new builds. Direct images use the built-in downloader.

Image transfers are covered by local automated tests (including a simulated
gallery subprocess). Live social-site downloads have not been verified here;
the development environment blocks package/network connections.

## Windows

Install 64-bit x64 Python 3.10+ and enable **Add Python to PATH**, then run:

```bat
build_windows.bat
```

Then double-click **NÜVEL Studio** (`NÜVEL Studio.lnk`) in the project folder.
The builder prepares an isolated environment, bundles the application and
creates a shortcut to **nuvel-windows/NÜVEL Studio.exe**. The application includes
Python, the UI, video/audio engines and FFmpeg. Keep the complete nuvel-windows
folder together; the exe depends on its bundled `_internal` directory.
The portable ZIP is kept in `dist/windows-<build timestamp>`.

Microsoft Edge WebView2 Runtime must be available on Windows.
The windowless launcher reports startup failures with a dialog and a log in
`%LOCALAPPDATA%\NuvelStudio\logs`. It requires the native bridge; it never leaves
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
The relocated executable must complete native UI/bridge/font/engine tests and
confirm it has no console before replacing the app and shortcut.
Startup failure, a locked running app or publication failure preserves the
previous app. Open the **NÜVEL Studio** shortcut after success.
Git for Windows must be installed, and Git must have access to the private repo.
The first update requires `git pull --ff-only origin main` to receive update.bat.
Local changes or conflicting Git history stop the update without discarding files.
Both local builds and release ZIPs include the isolated image-post CLI.
See [the Windows guide](README-Windows.md).

## macOS Apple Silicon

Use native ARM64 Python 3.12+ and run these commands from the project directory:

```bash
bash build_macos.command
```

The build prepares dependencies and produces **NÜVEL Studio.app** directly in
the project folder. Open this app for normal use without Terminal. It contains
the Python runtime, UI, video/audio engines and FFmpeg; you may copy it into
Applications. The distributable ZIP is also kept in `dist/<build timestamp>`.

Double-click **update_macos.command** to update and rebuild in one flow, with
no source/packaged mode choice. The app in the project folder is replaced only
after the new bundle passes a native startup test. Previous apps are preserved
in `dist`. If you made a separate copy in Applications, replace that copy with
the newly built app. No runtime repair commands are part of normal setup.

See [the macOS guide](README-macOS.md). The build is ad-hoc signed, not notarized
for public distribution. A macOS binary cannot be built by this project on Windows.

## Validation status

The **2.0.0** identity changes are unreleased. Both native build jobs and startup
checks must pass before the new ZIPs and manifest can be published.
See [the verification record](BUILD-VERIFICATION.md) for current results.
The Windows build passed real desktop native acceptance and is installed locally
under `nuvel-windows`; macOS acceptance and GitHub publication remain pending.

Windows tests cover Unicode shortcuts, process ownership, GUI subsystem and
startup proof, locked installations and rollback. Shared tests cover download
transitions, settings, metadata, catalog polling, safe archive extraction and
release transport. macOS-specific signing, filename normalization and LaunchServices
checks require native macOS execution. Live downloads across every service have
not been verified. A successful source test run is not native build acceptance.

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

## Project layout

| Path | Purpose |
| --- | --- |
| `nuvel_studio.py` | Main launcher |
| `glass_app.py` | WebView shell, local API, download jobs |
| `ui/` | HTML, CSS, and JavaScript interface |
| `ui/i18n.js` | Offline translations and live language switching |
| `download_engine.py` | Platform registry and error guidance |
| `platform_runtime.py` | Cross-platform resources, FFmpeg, and folder opening |
| `ui_preferences.py` | Validated, atomic per-user appearance/destination preferences |
| `legal/` | Distribution audit, platform terms register and proposed freeware permission |
| `legacy_tk.py` | Previous interface, available with `--classic` |
| `tests/` | Automated tests |

`ui/index.html` can be opened for a static design preview. Downloads require the
launcher. Browser profiles, cookies, virtual environments, generated builds,
and downloaded media are excluded from version control.

## License

**Proprietary — All rights reserved.** Copyright © 2026 Lumin0usX.
Use, modification, and redistribution require prior written permission.
See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
