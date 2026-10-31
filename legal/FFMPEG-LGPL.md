# FFmpeg distribution decision — 2026-10-31

The owner delegated the choice to reduce distribution risk. Future macOS ARM64
and Windows x64 packages require a separately built **LGPL** FFmpeg CLI with
matching source and build materials. This reduces the GPL-component compliance
burden for the proprietary product; it is not a legal clearance, a codec patent
license, or permission to download third-party media.

**Migration is incomplete. No replacement LGPL executable has been built or
accepted on either OS in this audit.** Installed apps and old release assets
have not been replaced or withdrawn. Both inspected macOS binaries remain
GPL-2.0-or-later. No current Windows binary was available for reinspection.

## Evidence bundle and packaging gate

Both builders call `ffmpeg_distribution.selected_bundle` and stop if evidence
is absent, mismatched or identifies GPL/nonfree components. There is no builder
fallback to imageio-ffmpeg. Both exclude that package from PyInstaller, so its
additional GPL executable is not swept into the GUI. Native startup, bridge,
font and engine checks remain mandatory.
Before freezing either GUI, builders also require real local test-media
generation, AAC/MP4 conversion, MP3 encoding and output decoding with that exact
executable. Mac exercises VideoToolbox; Windows exercises Media Foundation.
Failure stops packaging; no media from
third-party platforms is downloaded by this check.

Prepare a directory outside tracked source, such as `dist/ffmpeg-lgpl/`:

```text
ffmpeg                 # ffmpeg.exe on Windows; native target architecture
manifest.json
source/
  ffmpeg-source.tar.xz # exact source, including changes
  COPYING.LGPLv2.1
  build.sh            # actual commands, including dependency builds
  build.log           # actual configure/compiler/linker output
  libraries.json
  ...                 # linked libraries' sources, patches and notices
```

Create `manifest.json` **after** the real build: schema `1`, target
`macos-arm64` or `windows-x64`, `binary` (`ffmpeg` or `ffmpeg.exe`), a `files`
mapping of every other file's relative POSIX path to its SHA-256, and a
`materials` mapping with roles `ffmpeg_source`, `ffmpeg_license`, `build_script`,
`build_log`, `library_inventory`. All material paths start with `source/`.
Every file must be hashed; escaping paths, symlinks and unlisted files stop packaging.

`libraries.json` lists **all** linked libraries, with `name` and `license`.
Non-system libraries also need `source` and `license_file` paths listed in the
manifest. Use configure names such as `libmp3lame`. Identify OS SDK/runtime
components explicitly with `system: true`; do not label redistributed DLLs or
static libraries as system to omit their source. Include patches, dependency
build scripts and copyright notices as hashed files. Exclude credentials.

Configure explicitly with `--disable-gpl --disable-nonfree --disable-version3
--disable-autodetect`. Do not enable x264/x265/fdk-aac or other GPL, incompatible
or unreviewed components. Disabling autodetection prevents accidental linkage
to libraries from the builder's machine; explicitly account for required
allowed libraries and system facilities.

MP3 export needs an appropriate encoder, such as an audited LGPL libmp3lame
with matching source/build instructions. Check AAC, stream-copy/remux, decoders,
filters, HLS and TLS/network paths too. Do not remove supported formats to get
an LGPL label. Review current official releases/security fixes and verify
upstream source signatures. This audit has not downloaded replacement source,
invented checksums, or silently trusted a third-party binary.

```bash
python ffmpeg_distribution.py /absolute/path/to/bundle --target macos-arm64 --verify-media
export NUVEL_FFMPEG_BUNDLE=/absolute/path/to/bundle
python -m unittest discover -s tests
python build_macos.py
```

On Windows PowerShell set `$env:NUVEL_FFMPEG_BUNDLE = 'C:\path\to\bundle'`, use
target `windows-x64`, and run `python build_windows.py`. Rebuild on each native
OS. Provisioning reviewed LGPL bundles on release runners remains outstanding;
the current workflow will stop rather than package its old GPL fallback.

Builders include the supplied `source/` and `manifest.json` under
`third-party/ffmpeg`. The manifest's binary hash is the **input** hash; macOS
signing can change packaged bytes. Record final artifact hashes separately.
Hashes and `-L` cannot prove source correspondence, hidden linked code or all
redistribution rights. A reviewer must establish those facts from the real build.

## Codec migration and acceptance

Mac frozen apps and explicitly selected LGPL bundles use Apple's system
`h264_videotoolbox` with OS software fallback, preserve source resolution/fps,
pad odd dimensions, and produce H.264/AAC MP4. Already-compatible streams still
copy; encoding failure preserves the source. Source-only development without
a selected LGPL bundle retains imageio/libx264 behavior. Passing development
tests does not validate the new LGPL encoder.

A direct VideoToolbox probe failed to create a compression session with
OSStatus **-12908**, including at 320×240 with `-allow_sw 1`. This establishes
a failure in this launch context, not its root cause. Packaged apps cannot
fall back to GPL x264 to hide it. Real conversion/playback, best-source quality,
MP3/AAC, network paths and native startup must pass with each exact new LGPL
binary. Windows retains its remux/conversion pipeline but explicitly selects
the system `h264_mf` encoder for required conversion, avoiding MP4's implicit
encoder choice. Test Media Foundation on supported Windows machines, including
availability of OS media components. No native Windows result is claimed here.

References: [FFmpeg legal](https://ffmpeg.org/legal.html),
[official source/releases](https://ffmpeg.org/download.html),
[VideoToolbox implementation](https://github.com/FFmpeg/FFmpeg/blob/n7.1/libavcodec/videotoolboxenc.c),
[Media Foundation implementation](https://github.com/FFmpeg/FFmpeg/blob/n7.1/libavcodec/mfenc.c).
