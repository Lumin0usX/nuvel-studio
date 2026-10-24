# NÜVEL Studio build verification

## Identity boundary: 2.0.0 (unreleased)

The source now uses NÜVEL Studio throughout its owned application identity.
The repository target is `Lumin0usX/nuvel-studio`; the GitHub rename has not
completed because this session's network connection was denied. Do not claim
that a release exists at the new repository address until it is verified.

| Component | Identity |
| --- | --- |
| Source entry point | `nuvel_studio.py` |
| Python application class | `NuvelStudio` |
| User preferences and logs | `NuvelStudio` |
| Credential service | `NuvelStudio.GitHubReleases` |
| Browser preferences | `nuvel-obsidian-preferences-v1` |
| macOS bundle ID | `local.nuvelstudio.app` |
| Package marker product | `NÜVEL Studio` |
| Windows ZIP/root | `NUVEL-Studio-Windows-x64.zip` / `NÜVEL Studio` |
| macOS ZIP/root | `NUVEL-Studio-macOS-arm64.zip` / `NÜVEL Studio.app` |

Compatibility executable copies, app aliases, old-name roots and old product
IDs have been removed. Older packaged versions need a one-time installation of
the new package and fresh private-repository access in the new credential
namespace. Native verification and rollback remain mandatory. Downloaded media
is not renamed or deleted. Historical Git commits, third-party dependencies and
previous generated artifacts are not rewritten or represented as new releases.

## Shared status-polling optimization

Snapshots acknowledge an optional engine-catalog revision. An unchanged catalog
is not resent with every progress update. Progress, preferences, history and app
update status remain live; callers of `snapshot()` receive the complete object.
Completing a scan or reconnecting refreshes the catalog on Windows and macOS.

A local measurement with 50 actual platform entries gave 97,585 bytes for the
full response and 777 bytes for the acknowledged response. One 100-call JSON
serialization run took 36.7 ms versus 1.4 ms. This is a serialization
microbenchmark, not total application CPU use. Actual authenticated HTTP requests
also verified the compact response with live download progress and a brand SVG.

## Earlier shell startup diagnostics

Before the complete identity replacement, both baseline and optimized Windows
artifact-only builds produced GUI executables but failed the mandatory startup
gate. Neither generated a verified release ZIP or replaced the installed app.
Logs remain under `dist/windows-review-build.log` and
`dist/windows-optimized-build.log`. Diagnostics reported a timeout waiting for
the WebView loaded event. A separate inline-HTML pywebview/EdgeChromium probe,
without the app frontend, API or engines, also timed out after 25 seconds.
The precise WebView/runtime/session cause has not been established.

The fully renamed source requires fresh native acceptance. Existing artifacts
predate the new identity and must not be relabeled or distributed as 2.0.0.
macOS startup, signing and archive acceptance require an Apple Silicon Mac or
the native release CI job. Older native release evidence does not validate
this packaging boundary. No new release or tag has been published.

## Full identity verification on this Windows host

The project directory is now `C:\Users\karn2\Desktop\NÜVEL Studio`. New local
Windows builds install under `nuvel-windows`, keeping the previous generated
installation separate. The local Git origin points to the new repository name;
the online rename remains blocked by this session's denied GitHub connection.
Non-secret preferences were copied into the new namespace without overwriting an
existing preference file. Private-release access must be configured again.

The renamed source passed 184 Python results (180 passed, 4 platform/environment
skips) and all seven JavaScript suites. Unicode package tests cover decomposed
macOS app roots, canonical duplicate rejection, symlink aliases and release-marker
collection. The current owned source files contain zero old project identifiers.
Compatibility-only tests were removed along with those retired package contracts;
GUI proof, foreign-product rejection, extraction safety and rollback remain tested.

The 2.0.0 artifact build at `dist/windows-20261024-061522-559607` produced one
branded GUI executable with the new product/version marker, but again failed the
mandatory native startup gate. See `dist/nuvel-identity-build.log`. No verified
archive was created and the previous installed binary was not replaced.

Windows denied edits to the pre-existing shortcuts, including archiving the
previous-name shortcut. Those existing shortcut files were left in place. A new
`Launch NÜVEL Studio.lnk` source launcher was created with the relocated paths.
Old generated builds, third-party source and Git history were preserved rather
than relabeled as newly built artifacts. Native macOS verification remains open.

## Windows desktop acceptance completed — 2026-10-24

The current Windows installation at `nuvel-windows/NÜVEL Studio.exe` passed the
actual packaged `--self-test` when launched through Windows Shell on the user's
desktop. The fresh receipt in `dist/nuvel-desktop-final-proof.json` confirms the
exact installed executable and `console_attached: false`. Its real startup log
reports UI, Python bridge, fonts and engines passed, followed by owned-process
shutdown. A normal launch through the new primary shortcut also rendered the
connected workspace with all 50 platform entries. The application was left open.

The earlier shell-launched startup failure also occurred with a minimal inline
HTML probe, including a probe without the application-owned Job Object. The
same application works via desktop launch. This isolates the observed failure
to launch context; the precise inherited/runtime restriction is not established.
The normal build's native gate and process-ownership checks remain in force.
`validate_startup_proof` is shared by automated checks and desktop receipt
validation; missing/wrong receipts and attached consoles are still rejected.

Manual native-UI checks downloaded a real local H.264/AAC MP4, extracted native
AAC audio and downloaded an original PNG. The PNG matched its source byte for
byte; FFmpeg decoded the audio. Testing revealed that audio extraction could
reuse and remove an earlier MP4 through a shared output template. Audio now uses
an `[audio]` filename suffix. A real yt-dlp/FFmpeg regression downloads video,
native audio and MP3 from the same URL and verifies the video bytes remain intact.
The final native build includes this fix and passed the desktop self-test again.

Final Python regression: **186 results, 182 passed, 4 platform/environment skips**.
This includes a real Unicode/space/quote shortcut-argument round trip. Current
JavaScript suites remain seven. Native macOS execution is still pending.

The local verified ZIP is
`dist/windows-desktop-acceptance/NUVEL-Studio-Windows-x64.zip` (135,067,153 bytes),
SHA-256 `974911b1d980c538d5d404e7bd136796923b2f8bfa6468aba8d68e50bfea4ed6`.
The ZIP CRC check and single-GUI-executable layout passed. The executable hash,
receipt path and archive hash are recorded in
`dist/nuvel-desktop-acceptance-result.json`. This is a local artifact, not a
published GitHub release. The new build reused the builder-generated PyInstaller
spec and already-validated unchanged engine binaries, then required a fresh native
receipt from the relocated installation before archiving it.

Windows Shell moved the previous shortcuts into `dist/previous-shortcuts`,
preserving them as backups. The root now has exactly one shortcut,
`NÜVEL Studio.lnk`, pointing to the verified packaged executable. The temporary
source launcher was archived. Test downloads were removed from Downloads and the
local fixture server was stopped. GitHub repository rename remains blocked by
the lack of an authenticated browser session and denied CLI network access;
no commit, push, tag or release publication was performed.

## Offline uninstaller verification — 2026-10-24

Added Settings → Uninstall and the source-folder `uninstall.bat` /
`uninstall_macos.command` entry points. Removal defaults to keeping preferences;
it preserves downloaded media, source, build environments and backups. Only a
verified app bundle and a matching adjacent Windows shortcut are recycled.
Optional cleanup removes known preference/log files and this app's release
credential. New builds inventory their installed files to reject extra user
content before removal. Windows hands the request to its supervisor after the
owned GUI process tree closes, so its uninstaller survives Job Object cleanup.

The full Python suite passed **218 tests, with 5 skips** (223 total). A subsequent
native Trash regression was added and passed with the focused uninstaller suite
(19 passed, 1 symlink-permission skip); that regression also runs on macOS CI.
All seven JavaScript suites, Python compilation, shell syntax and diff checks
passed. `uninstall.bat --check` validated the existing local install without
changing it. Native Windows process lookup and Unicode shortcut inspection were
checked, and the native recycle API moved only disposable QA fixtures.

An isolated PyInstaller build completed at
`dist/uninstall-verification-20261024-114819/NÜVEL Studio` using the existing
builder-generated spec and unchanged engine binaries. Its GUI-subsystem check
passed. The real frozen `--uninstall --check --check-result` invocation exited 0;
`uninstall-readonly-proof.json` in that build directory identifies the exact
isolated bundle. Executable SHA-256:
`05ecfce7446dc456989062fd228f369359a4c078315db5d5056c9a1720035adb`.

The isolated native app was opened on the user's desktop. Settings and its
confirmation dialog rendered correctly; the settings-removal checkbox was
unchecked. Cancel returned to Settings with the app intact, and the review
window was closed normally. The user's installed app, media, preferences and
credentials were not uninstalled or reset. This is an isolated test build, not
a release archive or replacement of the current installation. Native macOS
uninstall/signing execution still requires a Mac; no GitHub publication was
performed for this change.
