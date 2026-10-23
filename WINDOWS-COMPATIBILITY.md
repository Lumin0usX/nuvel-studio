# Windows compatibility audit — 2026-10-23

**Status: source changes and platform-independent checks passed; a real Windows
x64 build/startup has not been run for this revision.** This audit ran on an
Apple Silicon Mac. No Windows executable or release was produced.

## Corrections made

The Windows builder still used `--name 'YTDL Studio'` after the macOS name fix.
It now produces **NÜVEL Studio.exe**, with **NÜVEL Studio.lnk** as the primary
project shortcut. Windows ProductName and FileDescription also use NÜVEL Studio.

- `build_windows.py` passes the ICO explicitly, packages UI/fonts/brand assets,
  and creates an identical regular `YTDL Studio.exe` compatibility copy. Both
  executable names must pass the real native startup test in local and CI builds.
- `windows_distribution.py` preserves `app-windows`, validates the GUI subsystem
  and native startup proof, and creates the new shortcut. An existing old shortcut
  is backed up and redirected to the new executable. App and both shortcuts roll
  back together on a locked file or a later publication failure.
- `create_windows_launcher.py` selects the new executable when present, accepts
  an older installed executable, and uses the new icon for source launches.
  It continues using Unicode `IShellLinkW`/`IPersistFile` APIs. No symlink or
  Developer Mode permission is required for the Windows rename.
- `update_installer.py` recognizes both executable layouts. It only falls back
  when the new executable is absent; an invalid new entry cannot be hidden by a
  valid old executable. ZIP asset names, the `YTDL Studio` archive root, marker
  product, repository, preferences and credential-store namespaces remain stable.
- Windows batch launchers retain CRLF and ASCII command text, and set
  `PYTHONIOENCODING=utf-8` so redirected Python output preserves the Ü character.
  `update_project.py` and Windows guides now name the new shortcut.

The shared UI remains HTML/CSS/JavaScript in pywebview. Dark/Light brand images,
collapsed sidebar icon, browser favicon and translated app labels use bundled
files. Windows pywebview receives an ICO and the Edge Chromium renderer; the
macOS-only ICNS, plist, `ditto` and app symlink operations stay in macOS paths.
The native startup test still requires loaded brand images, a backend bridge
round trip, a loaded bundled font, working engines and window shutdown. Windows
also rejects a console-attached process. None of these acceptance gates was
disabled or replaced with a mock in the production builder.

## Verification on this Mac

| Check | Result |
| --- | --- |
| Windows build/distribution tests | 27 results: 23 passed, 4 native Windows tests skipped |
| Shared updater tests | 26 results: 25 passed, 1 Windows credential-store test skipped |
| macOS distribution regression tests | All 17 passed |
| Full Python discovery | 185 results: 172 passed, 2 errors, 11 existing/native Windows skips |
| JavaScript | All 6 suites passed |
| Font/brand integrity | Passed: EN 5 / TH 5 / JP 3 / CN 3; SVG/favicon files and native icon resolutions present |
| Windows icon | ICO decoded; 16/32/48/64/128/256 px representations verified |
| Python compilation / diff whitespace | Passed |
| Batch files | CRLF, ASCII command content and UTF-8 Python output setting verified |
| Windows platform guard | Correctly refused to build on this Mac |

The new orchestration test mocks PyInstaller, WebView2, native process launch and
COM shortcut creation, then exercises real file copying, both executable entries,
version metadata text, shortcut publication and ZIP layout. Publication tests
exercise the real backup/rollback logic on disk, including a locked legacy
shortcut and failed acceptance of the compatibility executable. Native proof
tests simulate process results; they are not evidence of a working real `.exe`.

The two full-suite errors are unchanged: this Mac's Python lacks `_tkinter`, and
the real MP4 download test is denied a loopback socket bind. The 11 skipped tests
need Windows batch, process/console, shortcut or credential APIs. They were not
forced to pass or removed.

Logs are in `dist/windows-compatibility-check/`: `python-tests.log`,
`windows-tests.log`, `javascript-tests.log`, and `platform-guard.log`.

## Native Windows acceptance still required

Run `build_windows.bat --check`, then `build_windows.bat` on Windows x64. The
builder creates its own `.venv-windows-build`; do not copy the Mac environment,
`dist`, or an existing `app-windows` between operating systems. A successful build
must test both real GUI executables, fonts, bridge, FFmpeg and gallery-dl before
replacing the old app or shortcuts. WebView2 Runtime remains required.

The existing release workflow runs Python tests, all six JavaScript suites and
the native builder on its Windows runner. It has not been run for these current
uncommitted changes. No conclusion is drawn about the cause of the two startup
failures reported from the previous Windows machine.

At the time of this audit, no native Windows build, commit, push or release had
been made. Subsequent release preparation is recorded in BUILD-VERIFICATION.md.
Existing installed apps were not modified by the audit.

## Native CI follow-up

The Windows x64 job for tag **v1.1.3**, commit **5547f83**, subsequently passed on
GitHub's real Windows runner, including Python tests, all six JavaScript suites,
the real executable build, both native startup checks and ZIP artifact upload.
Evidence: [Windows job](https://github.com/Lumin0usX/ytdl-studio/actions/runs/39923546904/job/120314295254).
The release was withheld because the macOS framework-signature check failed;
the next version, 1.1.4, must pass both native jobs before publication.
