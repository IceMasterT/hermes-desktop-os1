#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "error: python3 is required" >&2
    exit 1
fi

"$PYTHON_BIN" "$ROOT_DIR/linux-ui/os1_ubuntu_ui.py"
