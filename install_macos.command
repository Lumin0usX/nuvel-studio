#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/macos_common.sh"
choose_python
if [[ ! -d .venv-macos ]]; then
    "$BASE_PYTHON" -m venv .venv-macos
fi
[[ -x "$VENV_PYTHON" ]] || fail "The .venv-macos folder is incomplete. Rename it and run this installer again."
"$VENV_PYTHON" -c 'import platform,sys; assert platform.machine() == "arm64" and sys.version_info >= (3,12), "This environment must use native ARM64 Python 3.12+"'
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install --upgrade -r requirements.txt
require_environment
"$VENV_PYTHON" "$PROJECT_DIR/create_macos_launcher.py"
chmod +x start_macos.command build_macos.command install_macos.command update_macos.command
printf '\nInstallation complete. Open YTDL Studio Launcher.app (no Terminal).\n'
