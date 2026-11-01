#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright © 2026 Lumin0usX

set -euo pipefail
source "$(dirname "$0")/macos_common.sh"
require_environment
exec "$VENV_PYTHON" "$PROJECT_DIR/nuvel_studio.py"
