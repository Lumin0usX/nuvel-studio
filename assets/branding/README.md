# NÜVEL Studio — 03 Fluid

Source: the user-provided `NUVEL-Studio-Brand-Kit-v1/03-Fluid` folder, version 1.
Use **NÜVEL Studio** in visible copy, retaining the umlaut. Artwork is outlined
and has no font dependency. The project's covered original code is GPL-3.0-only;
this new software grant excludes the artwork and does not grant additional
trademark rights. Existing artwork permissions remain unchanged. The owner
confirms: **AI-generated artwork created using OpenAI ChatGPT Image Generation at the direction of the project owner.**
This does not establish automatic copyright, exclusivity or third-party rights
clearance. See [brand notice](../../BRAND-NOTICE.md) and
[copyright scope](../../COPYRIGHT). No registration is asserted.

Source-publication review: all 15 files under `ui/brand/` byte-match files in
the supplied kit, including the legacy 160 px PNG. The three native icon files
are documented conversions rather than byte-identical kit files. These matches
corroborate the supplied-kit origin; the generation provenance is owner-confirmed.
The kit's usage guide contains no separate artwork license. No new artwork grant
is introduced and none is inferred from GPL. The owner directs continued source
inclusion; required assets were not removed, regenerated or changed.

- `ui/brand/nuvel-*-black.svg` and `*-white.svg`: supplied primary, small and
  wordmark vectors. Black is for Light; white is for Dark. The sidebar uses the
  small lockup at its recommended minimum canvas width of 160 px.
- `ui/brand/favicon.svg`: supplied extracted Ü tile, used in compact navigation
  and browser tabs. Supplied favicon ICO/PNG and Apple touch assets accompany it.
- `ui/brand/nuvel-small-white.png`: supplied 160 px PNG for the legacy Tk header.
- `assets/branding/app-icon-1024.png`: rendered directly from the supplied
  favicon SVG at 1024 × 1024. This is a format/size conversion of the AI-generated
  brand artwork, without a further generation step, stretching or recoloring.
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

The application uses the NÜVEL identity for all owned filenames, bundle
metadata, preference and credential namespaces, archive names and updater roots.
Windows packages contain a single NÜVEL Studio.exe; macOS packages contain
NÜVEL Studio.app with one main executable, normalized for macOS signing.
Neither platform generates compatibility aliases or duplicate executable copies.
Native startup acceptance is mandatory before installation or publication.
The full identity boundary is documented in the root README.
