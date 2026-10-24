#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/macos_common.sh"
require_environment
exec "$VENV_PYTHON" "$PROJECT_DIR/nuvel_studio.py"
