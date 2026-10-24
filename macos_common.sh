#!/bin/bash
# Shared setup; compatible with macOS /bin/bash 3.2.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PROJECT_DIR="$PWD"
VENV_PYTHON="$PROJECT_DIR/.venv-macos/bin/python"
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
if [[ "$(uname -s)" != Darwin ]]; then
    fail "Run this script on macOS Apple Silicon. Windows uses start.bat."
fi
choose_python() {
    local candidate
    for candidate in "${NUVEL_PYTHON:-}" \
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.15/bin/python3 \
        /opt/homebrew/bin/python3 python3; do
        [[ -n "$candidate" ]] || continue
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
            'import sys,platform; assert sys.version_info >= (3,12); assert platform.machine() == "arm64"' >/dev/null 2>&1; then
            BASE_PYTHON="$candidate"
            return
        fi
    done
    fail "Install Python 3.12+ universal2 from python.org, run Install Certificates.command, then retry from a native Terminal (not Rosetta)."
}
require_environment() {
    [[ -x "$VENV_PYTHON" ]] || fail "Run install_macos.command first."
    "$VENV_PYTHON" "$PROJECT_DIR/check_macos.py"
}
