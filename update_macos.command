#!/bin/bash
# Parse the whole function before Git replaces this file during the update.
main() {
    set -euo pipefail
    trap 'result=$?; printf "\nPress Return to close this window..."; read -r _ || true; exit "$result"' EXIT
    source "$(dirname "$0")/macos_common.sh"
    printf '\nYTDL Studio - Update\n\n'
    printf 'Close YTDL Studio before continuing, including any running downloads.\n'
    printf 'This updater uses your existing GitHub access to the private repository.\n\n'
    printf '1. Update (I launch start_macos.command)\n'
    printf '2. Update and build a new YTDL Studio.app\n\n'
    local choice
    read -r -p 'Choose 1 or 2, then press Return [1]: ' choice
    choose_python
    case "${choice:-1}" in
        1) "$BASE_PYTHON" -u "$PROJECT_DIR/update_project.py" ;;
        2) "$BASE_PYTHON" -u "$PROJECT_DIR/update_project.py" --build ;;
        *) printf '\nInvalid choice. No update was started.\n'; return 1 ;;
    esac
}
main "$@"
