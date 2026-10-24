#!/bin/bash
# Parse the whole function before Git replaces this file during the update.
main() {
    set -euo pipefail
    trap 'result=$?; printf "\nPress Return to close this window..."; read -r _ || true; exit "$result"' EXIT
    source "$(dirname "$0")/macos_common.sh"
    printf '\nNÜVEL Studio - Update\n\n'
    printf 'Close NÜVEL Studio before continuing, including any running downloads.\n'
    printf 'This updater uses your existing GitHub access to the private repository.\n\n'
    printf 'The updater builds and verifies the app before replacing the previous version.\n\n'
    choose_python
    "$BASE_PYTHON" -u "$PROJECT_DIR/update_project.py"
}
main "$@"
