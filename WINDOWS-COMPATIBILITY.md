# NÜVEL Studio Windows compatibility

Windows x64 uses the existing Python/pywebview EdgeChromium shell.
The source entry point is `nuvel_studio.py`; packaged launches use
`nuvel-windows/NÜVEL Studio.exe` and the `NÜVEL Studio.lnk` shortcut.
The release ZIP is `NUVEL-Studio-Windows-x64.zip`, rooted at `NÜVEL Studio`.
Only one branded executable is packaged. No symlink permission is needed.

Every build validates offline assets, FFmpeg and the isolated gallery-dl CLI.
It then checks the relocated GUI executable, native UI/Python bridge, loaded
fonts, brand images and absence of an attached console before creating a ZIP
or replacing the current app. Publication failures restore the app and shortcut.
Foreign product markers and unrelated application folders are rejected.

Version 2.0.0 establishes a new package/product identity. Earlier packaged apps
require one new installation; their updater cannot consume the new names and
product IDs. Set up private-repository access in the new credential namespace.
Source updates use `Lumin0usX/nuvel-studio` after the repository rename completes.

Tests cover Thai/Unicode paths, process ownership, GUI proof, malformed packages,
archive layout, authenticated release transport and transactional rollback.
The current installation passed real desktop native startup acceptance and
opened through the primary shortcut. Earlier shell-context WebView hangs are
recorded separately in [BUILD-VERIFICATION.md](BUILD-VERIFICATION.md); they also
affected a minimal probe without the app's own Job Object. The exact context
restriction remains unresolved. Unit tests and compilation alone are not native
acceptance; actual UI/bridge/font/engine and console receipts were validated.
