# NÜVEL Studio — 03 Fluid

Source: the user-provided `NUVEL-Studio-Brand-Kit-v1/03-Fluid` folder, version 1.
Use **NÜVEL Studio** in visible copy, retaining the umlaut. Artwork is outlined
and has no font dependency. Project licensing remains proprietary.

- `ui/brand/nuvel-*-black.svg` and `*-white.svg`: original primary, small and
  wordmark vectors. Black is for Light; white is for Dark. The sidebar uses the
  small lockup at its recommended minimum canvas width of 160 px.
- `ui/brand/favicon.svg`: original extracted Ü tile, used in compact navigation
  and browser tabs. Original favicon ICO/PNG and Apple touch assets accompany it.
- `ui/brand/nuvel-small-white.png`: original 160 px PNG for the legacy Tk header.
- `assets/branding/app-icon-1024.png`: rendered directly from the original
  favicon SVG at 1024 × 1024. No stretching, recoloring or generated artwork.
- `app-icon.ico`: Windows 16/32/48/64/128/256 px representations.
- `app-icon.icns`: macOS representations through 1024 px.

Native icons are checked into source and passed explicitly to PyInstaller in
both native builders. Builders check that brand files and icon resolutions are
present. The authenticated browser fallback serves only the explicit brand
asset allowlist in `branding.py`.

Re-export ICO and ICNS from the checked-in PNG master with the existing Pillow
dependency; no additional build dependency is required:

```bash
python build_brand_icons.py
python branding.py
```

For a future vector revision, first render `ui/brand/favicon.svg` to the 1024 px
master. For example, with Sharp available as a development tool:

```javascript
await sharp('ui/brand/favicon.svg', {density: 288})
  .resize(1024, 1024).png().toFile('assets/branding/app-icon-1024.png');
```

The repository URL, OS preferences/keychain namespaces, bundle ID, update marker
product and release archive names retain their existing identifiers so older installations can still receive updates.
Windows builds produce **NÜVEL Studio.exe** and **NÜVEL Studio.lnk**. The old
executable remains a regular compatibility copy, and existing old-name shortcuts
are backed up and redirected to the new primary executable. Both executable names
must pass native startup acceptance before publication; no symlink permission
is required on Windows. The app folder remains `app-windows` and release ZIP
layout retains its `YTDL Studio` root.

macOS builds now produce **NÜVEL Studio.app** with a **NÜVEL Studio** executable.
After native acceptance, the previous project app is backed up and the old
`YTDL Studio.app` path becomes a link to the new app. Old released updaters still
receive a ZIP rooted at `YTDL Studio.app` and a compatibility executable symlink
inside `Contents/MacOS`; the primary executable and process name use NÜVEL.
macOS `CFBundleName`/`CFBundleDisplayName`,
Windows ProductName/FileDescription, native window/dialog titles, UI labels and
release titles use the NÜVEL display name. Source and packaged Windows shortcuts
use the new icon. Source pywebview launches also receive the native icon explicitly.
The native startup test requires the sidebar brand images to load successfully.
A new native build must pass every existing self-test before
replacing the installed app; changing source assets does not modify an old app.
