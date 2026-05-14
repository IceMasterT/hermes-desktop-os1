#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/4] Python syntax check"
python3 -m py_compile "$ROOT_DIR/linux-ui/os1_ubuntu_ui.py"

echo "[2/4] Shell script syntax checks"
bash -n "$ROOT_DIR/scripts/run-ubuntu-ui.sh"
bash -n "$ROOT_DIR/scripts/build-ubuntu-packages.sh"
bash -n "$ROOT_DIR/scripts/smoke-ubuntu-package.sh"

echo "[3/4] Build Ubuntu package artifacts"
"$ROOT_DIR/scripts/build-ubuntu-packages.sh"

echo "[4/4] Smoke-test built package"
"$ROOT_DIR/scripts/smoke-ubuntu-package.sh"

echo "Ubuntu UI verification passed."
