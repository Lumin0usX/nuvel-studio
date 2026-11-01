#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

main() {
    set -euo pipefail
    source "$(dirname "$0")/macos_common.sh"
    if [[ -x "$VENV_PYTHON" ]]; then
        "$VENV_PYTHON" "$PROJECT_DIR/app_uninstall.py" "$@"
    else
        choose_python
        "$BASE_PYTHON" "$PROJECT_DIR/app_uninstall.py" "$@"
    fi
}
main "$@"
