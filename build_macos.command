#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/macos_common.sh"
# One build entry point prepares the environment automatically.
/bin/bash "$PROJECT_DIR/install_macos.command"
require_environment
"$VENV_PYTHON" -m pip install 'pyinstaller>=6.16,<7'
"$VENV_PYTHON" "$PROJECT_DIR/build_macos.py"
