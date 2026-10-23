# Native build investigation — 2026-10-23

Latest status: **Release 1.1.4 is published**, with verified native Windows x64
and macOS ARM64 packages plus the update manifest. See the final release result
below. The earlier investigation entries describe failures before this release.

## Source and environment

- Read `README.md` and `README-macOS.md`; no applicable `AGENTS.md` was found.
- Started from clean `main` at `9133cb5966d25ab6473fb64ef076d8b9237e2725`
  (`Refine download workspace and add adjustable glass opacity`).
- Local `origin/main` also points to that commit. `git fetch origin` failed with
  `Could not resolve host: github.com`; the current remote tip is unverified.
- macOS 27.0.1, native ARM64, Homebrew Python 3.15.0.
- Created `.venv-macos-handoff-20261023` from the local Python interpreter.
  Installed packages from this Mac's cached wheels; did not copy another
  environment or any Windows build. The original `.venv-macos` is untouched.
  Setuptools 79.0.1 came from the wheel bundled with Homebrew Python's test data.
- Key versions: PyInstaller 6.22.3, pywebview 6.2.1, PyObjC 12.2.2,
  yt-dlp 2026.8.19, gallery-dl 1.32.17, imageio-ffmpeg 0.6.0, Pillow 13.0.0.
  Full package versions: `dist/handoff-20261023/requirements-build.txt`.

## Confirmed fixes

- `build_gallery_tool.py`: retain the isolated engine's exit code and stderr
  when its acceptance check fails. Previously only a generic error was shown.
  Zero exit without extractor output and nonzero exit with output still fail.
- `macos_distribution.py`: expose LaunchServices stderr and exit code when
  `open` fails, while still rejecting the build and preserving the existing app.
- `tests/test_macos_distribution.py` and `tests/test_windows_distribution.py`:
  resolve temporary fixture paths consistently with production code. Five tests
  previously failed on `/var/...` versus `/private/var/...`, the same location
  through macOS's symlink. Existing rollback assertions remain active.
- Added regression coverage in `tests/test_build_gallery_tool.py` and the macOS
  distribution tests. UI, runtime download behavior, license, and packaging
  acceptance requirements were not changed.

## Results

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -v` | 170 results: 158 passed, 2 errors, 10 existing Windows-only skips; suite failed |
| JavaScript tests, all six `tests/*.cjs` | Passed using Node 24.21.0 bundled with ChatGPT |
| `python check_macos.py` | Passed: ARM64 Python/WebKit, 50 icons, UI assets, fonts, yt-dlp, curl-cffi, ARM64 FFmpeg execution |
| `python font_assets.py --check` | Passed: EN 5 / TH 5 / JP 3 / CN 3, original file hashes, glyphs, weights, licenses and generated assets |
| `python -m pip check` | Passed |
| Source gallery-dl `--config-ignore --list-modules` | Passed, 286 modules |
| Source yt-dlp `--version` | Passed, 2026.08.19 |
| macOS build, two attempts | Stopped at mandatory packaged gallery-dl CLI check, before packaging the main app |
| Native source `--self-test` | Failed with SIGABRT; no bridge/font-render proof |
| Existing app LaunchServices `--self-test` | Failed: `kLSNoExecutableErr` (-10827); no startup proof |
| Existing app signature and architecture | `codesign --verify --deep --strict` passed; ARM64 executable exists |
| Existing app preservation | File hashes and symlink targets match `dist/20261022-033923-980182/YTDL Studio.app` |

The two Python errors are:

1. `test_download_ui` cannot import `legacy_tk` because this Python lacks
   `_tkinter`. Its three legacy tests therefore were not collected individually.
2. The real MP4 HTTP download pipeline test cannot bind its loopback server:
   `PermissionError: [Errno 1] Operation not permitted`.

The packaged gallery-dl executable reports, before listing extractors:

```text
Failed to initialize sync semaphore!
semctl: Operation not permitted
LOADER: failed to destroy sync semaphore (errno 1)!
```

This identifies the denied operation in this execution session. It does not
establish a general application defect or the cause of the previous Windows
startup failures. No Windows failure logs or executable were found in this
checkout. The Mac source crash report places the abort at `_RegisterApplication`
while initializing `NSApplication`; the underlying reason remains unconfirmed.
Computer-use launch also timed out without producing a verified native window.
There is no successful screenshot or native frontend/backend bridge verification.
Font integrity passed; actual font rendering in a new bundle remains unverified.
Live external-site downloads and in-app update transport were not verified.

## Artifacts and next verification

- Final failed build output: `dist/20261023-083605-196346/`; only the staged
  FFmpeg and gallery engine build exist, with no main `.app` or release ZIP.
- Logs, test output and dependency versions: `dist/handoff-20261023/`.
  In particular: `build-final.log`, `python-tests-final.log`,
  `javascript-tests.log`, `gallery-final.log`, `existing-macos-launch-final.log`.
- Existing app: `YTDL Studio.app` in the project root; it is the previous build.
- No self-test was bypassed, weakened or disabled. No commit, push, tag,
  GitHub Release or replacement of the existing app was performed.

To continue, use a native desktop execution session that permits the engine's
semaphore initialization, loopback binding and LaunchServices startup, and a
Python installation with Tk support for the complete legacy test suite. Rerun
the full suite and build; do not infer success from packaging alone. With the
new environment, the build command is:

```bash
.venv-macos-handoff-20261023/bin/python build_macos.py
```

The existing builder will still require the isolated engine check and the
relocated app's native UI/bridge/FFmpeg/font check before replacing the old app
or creating the distributable ZIP. Git remote verification and Windows native
acceptance remain separate outstanding checks.

## Branding follow-up — NÜVEL Studio / 03 Fluid

The user selected the supplied `NUVEL-Studio-Brand-Kit-v1/03-Fluid` artwork and
approved changing the displayed app name to NÜVEL Studio. The original outlined
SVGs, favicon assets and 160 px legacy-header PNG are now bundled in `ui/brand`.
All six SVG logo variants and eight favicon files were compared byte-for-byte
with the supplied kit. The native 1024 px icon was rendered directly from its
favicon vector; ICO and ICNS exports are in `assets/branding`.

Changed visible branding in the sidebar, browser title, update UI/translations,
native window/error dialogs, legacy header, Windows shortcut description,
Windows version metadata, macOS display-name metadata, and release title.
Both builders now pass the new icon to PyInstaller; source pywebview launches
also receive the platform-specific icon explicitly. Browser-fallback brand
requests use an explicit asset allowlist. The native startup self-test now
requires the sidebar images to have loaded before proceeding to bridge proof.
Internal update/storage identifiers and existing package filenames are retained.

Branding validation:

- All six JavaScript suites passed after the UI and translation changes.
- Full Python run: 158 passed, the same 2 errors and 10 Windows-only skips.
  After the final native-icon/smoke-check changes, the desktop-launcher subset
  passed its 9 runnable tests, with 2 Windows-only skips.
- `branding.py`, `check_macos.py`, Python compilation and `git diff --check`
  passed. ICO representations 16/32/48/64/128/256 and ICNS through 1024 decoded.
- Referenced HTML brand files exist and are all included in the fallback allowlist.
- Real Safari static preview displayed the NÜVEL Studio title, the white Fluid
  sidebar lockup on Dark, and the extracted Ü icon during collapse. This is a
  frontend-only preview, not a native bridge or media-download test. The black
  logo is selected by the existing resolved Light theme attribute; live Light
  preview was not completed.
- The new Mac build attempt still failed at the mandatory isolated gallery-dl
  loader check with `semctl: Operation not permitted`. Output is under
  `dist/20261023-141633-930467/`; there is no new main app or release ZIP.
  Build/test logs are under `dist/nuvel-brand-check/`.

The previously installed app was not modified. No commit, push, tag or release
publication was performed for this branding change.

## Native macOS name correction

The user subsequently rebuilt successfully in Terminal. Inspection of that
installed app confirmed `CFBundleName` and `CFBundleDisplayName` were already
NÜVEL Studio, but `CFBundleExecutable` and the outer app filename were still
YTDL Studio. The builder's unchanged PyInstaller `--name` caused this mismatch.

- `build_macos.py` now uses the display name for PyInstaller, the `.app` filename
  and the primary executable. A `Contents/MacOS/YTDL Studio` symlink preserves
  compatibility with old released updater code before the new bundle is signed.
- `macos_distribution.py` publishes `NÜVEL Studio.app` after native verification,
  backs up both prior app names, and redirects existing old project launch paths
  through relative symlinks. Failure rolls back app and aliases together.
- Release ZIP asset/root names remain compatible with existing updaters. A real
  `ditto` archive/unpack test checks that the new executable and old alias survive.
- `update_installer.py` resolves the macOS executable from the bundle plist,
  accepting only the old or new approved name; Windows behavior is unchanged.
- The source updater success message and macOS build documentation now point to
  `NÜVEL Studio.app`.

The macOS distribution suite passed all 17 tests, including the new-name native
proof, legacy proof, migration, repeat publication, late rollback and real archive
compatibility tests. The updater suite passed its 24 runnable tests, with its one
existing Windows-only credential-store skip. The currently installed app was not
edited in place; a newly verified build is still required to apply this correction.

Full regression run after this correction: 176 results, 164 passed, the same
2 errors (`_tkinter` import and denied loopback bind), and 10 existing Windows-only
skips. The build attempt again stopped at the isolated engine's denied `semctl`
operation. Logs are in `dist/nuvel-name-check/`. File hashes and symlink targets
of the user's successfully rebuilt `YTDL Studio.app` still match its build output
under `dist/20261023-142635-770862/`; it was preserved while this fix was prepared.

## Windows follow-up

The latest Windows source audit, name/shortcut migration fixes, regression
results and remaining native acceptance requirements are recorded in
[WINDOWS-COMPATIBILITY.md](WINDOWS-COMPATIBILITY.md). The full suite now reports
172 passed, the same 2 errors and 11 native Windows skips across 185 results.
No native Windows build, commit, push or release publication was performed here.

## Release 1.1.2 preparation

The user requested pushing to the original repository so other devices can
update. `origin` is still `https://github.com/Lumin0usX/ytdl-studio.git` and the
working branch is `main`. The version is raised from 1.1.1 to **1.1.2** because
the packaged updater ignores releases whose version is not newer than its own.
The existing `v*.*.*` tag workflow must pass native Windows and macOS builds,
Python/JavaScript tests and startup acceptance before publishing the complete
release assets and manifest. Pushing `main` alone only updates source checkouts.

At preparation time, Git and GitHub CLI remote checks failed to reach GitHub
(`Could not resolve host: github.com` / `error connecting to api.github.com`).
The remote branch, tags and latest release could not yet be verified. Any push
must be non-forced; a release must not be represented as published until the
native workflow and GitHub publication actually complete.

## First remote CI and 1.1.3 correction

Commit `31a7b24` and tag `v1.1.2` were pushed successfully through GitHub Desktop.
The repository was confirmed private in GitHub's UI. Native run
`39922050689` failed before publication and no release assets were published.

- Windows failed the real shortcut test because TEMP used `RUNNER~1` while the
  launched process returned the equivalent long profile path. The fixture now
  resolves both paths, publishes its result atomically, and waits for its actual
  process to exit before the temporary folder is cleaned up. Console and path
  assertions remain mandatory.
- macOS passed Python and all JavaScript tests, then `codesign --deep --force`
  crashed during final signing. A local diagnostic copy reproduced an invalid
  resource seal: the composed-Ü main executable was recorded as nested code,
  so signing the main executable invalidated its own recorded hash. Renaming the
  real file through an intermediate filename into macOS's decomposed Unicode
  form, matching its plist and compatibility symlink, passed deep strict
  verification. The visible name remains NÜVEL Studio.
- Final signing now refreshes the outer bundle after PyInstaller's nested
  signatures and requires `codesign --verify --deep --strict`, following
  [Apple TN2206](https://developer.apple.com/library/archive/technotes/tn2206/).
  Native startup acceptance is still required afterwards. Startup proof uses
  filesystem identity to accept canonically equivalent macOS path spellings.

The failed 1.1.2 tag is retained. The corrected release version is **1.1.3**.
Local macOS distribution tests pass all 19 checks, including normalization and
rejection of an invalid signature. Native Windows behavior still requires the
next remote CI run; no failed check was bypassed.

## Native 1.1.3 result and 1.1.4 framework signing fix

Run `39923546904`, commit `5547f83`, passed the real Windows x64 job:
Python tests, all six JavaScript suites, both executable startup tests, archive
collection and artifact upload succeeded. The Windows short-path fixture fix
is verified on the native runner.

macOS passed tests and reached strict signature verification. That mandatory
gate correctly rejected Python.org's copied `Python.framework`: its retained
signature referenced resources absent from the frozen framework. Signing now
refreshes each framework container inside-out, then the outer app, then requires
recursive strict verification and the existing native startup check. A local
diagnostic copy reproduced a missing framework seal; the corrected signing flow
recreated it and passed recursive strict verification.

The next release version is **1.1.4**; failed tags remain unchanged. Publication
still requires successful native builds for both platforms at this same version.

## Final verified release — 1.1.4

- Repository remains **private**: `Lumin0usX/ytdl-studio`; license remains proprietary.
- Release commit: **6de289c**, tag **v1.1.4**.
- [Native CI run 39924319272](https://github.com/Lumin0usX/ytdl-studio/actions/runs/39924319272)
  completed successfully: both platform jobs and publication passed. Both jobs
  ran the Python and JavaScript suites and their real packaged startup checks.
- [NÜVEL Studio 1.1.4](https://github.com/Lumin0usX/ytdl-studio/releases/tag/v1.1.4)
  is published as **Latest**, with both ZIPs and `studio-update.json` present.
- The published manifest was downloaded from the private release and checked:
  schema 1, version 1.1.4, both platform entries, and SHA-256 values matching
  GitHub's displayed digests of the actual uploaded ZIP assets.

| Asset | Size in bytes | SHA-256 |
| --- | ---: | --- |
| YTDL-Studio-Windows-x64.zip | 147958093 | f284fa0b8234ea2032b7ec42db94ebc4022bee81debb56f3f16ea66639e8572e |
| YTDL-Studio-macOS-arm64.zip | 145440609 | f3a8e7fa27f7e884fbbb8ad92cd3501b8a54632ff30b37cb2be73c2b1eda7034 |
| studio-update.json | 422 | 36b8315a25bdfa125e128af713eccb4c646e4a3888fb95eb9e33df99158ff3a3 |

Commit and tag were pushed through the user's GitHub Desktop installation after
the terminal's Git/GitHub CLI network attempts failed. No force push or tag
rewrite was used. Source devices can use the existing folder updater; packaged
devices with the in-app updater can check for 1.1.4 using their private-repository
read access. Browser/Git sign-in is separate from the app's saved update token.
Live downloads across every external media service remain outside this release
verification; native startup, bridge, bundled font rendering and engines passed.
