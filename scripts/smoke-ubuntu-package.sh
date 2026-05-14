#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist/linux"

deb_file="$(ls -1 "$DIST_DIR"/os1-ubuntu-ui_*_amd64.deb 2>/dev/null | sort | tail -n 1 || true)"
if [[ -z "$deb_file" ]]; then
  echo "No .deb found in $DIST_DIR. Build first: ./scripts/build-ubuntu-packages.sh" >&2
  exit 1
fi

echo "Inspecting package: $deb_file"
dpkg-deb -I "$deb_file" >/dev/null

tmp_dir="$(mktemp -d)"
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT

dpkg-deb -x "$deb_file" "$tmp_dir"

test -f "$tmp_dir/usr/share/applications/os1-ubuntu-ui.desktop"
test -f "$tmp_dir/usr/bin/os1-ubuntu-ui"
test -x "$tmp_dir/usr/bin/os1-ubuntu-ui"
test -f "$tmp_dir/opt/os1-ubuntu-ui/os1_ubuntu_ui.py"
test -x "$tmp_dir/opt/os1-ubuntu-ui/run-ubuntu-ui.sh"
test -f "$tmp_dir/usr/share/icons/hicolor/256x256/apps/os1-ubuntu-ui.png"

desktop_exec="$(grep '^Exec=' "$tmp_dir/usr/share/applications/os1-ubuntu-ui.desktop" | cut -d= -f2-)"
if [[ "$desktop_exec" != "os1-ubuntu-ui" ]]; then
  echo "Desktop Exec mismatch: expected os1-ubuntu-ui, got: $desktop_exec" >&2
  exit 1
fi

python3 -m py_compile "$tmp_dir/opt/os1-ubuntu-ui/os1_ubuntu_ui.py"

echo "Ubuntu package smoke check passed."
