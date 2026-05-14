#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist/linux"
APP_DIR="$DIST_DIR/os1-ubuntu-ui"
DEB_ROOT="$DIST_DIR/deb-root"
VERSION="${OS1_UBUNTU_UI_VERSION:-0.1.0}"
ARCH="${OS1_UBUNTU_UI_ARCH:-amd64}"
PKG_NAME="os1-ubuntu-ui"

mkdir -p "$DIST_DIR"
rm -rf "$APP_DIR" "$DEB_ROOT"

mkdir -p "$APP_DIR"
cp "$ROOT_DIR/linux-ui/os1_ubuntu_ui.py" "$APP_DIR/os1_ubuntu_ui.py"
cp "$ROOT_DIR/scripts/run-ubuntu-ui.sh" "$APP_DIR/run-ubuntu-ui.sh"
chmod +x "$APP_DIR/os1_ubuntu_ui.py" "$APP_DIR/run-ubuntu-ui.sh"

# Build .deb layout
mkdir -p \
  "$DEB_ROOT/DEBIAN" \
  "$DEB_ROOT/opt/$PKG_NAME" \
  "$DEB_ROOT/usr/bin" \
  "$DEB_ROOT/usr/share/applications" \
  "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps"

cp -R "$APP_DIR/." "$DEB_ROOT/opt/$PKG_NAME/"

cat > "$DEB_ROOT/usr/bin/os1-ubuntu-ui" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /opt/os1-ubuntu-ui/run-ubuntu-ui.sh
EOF
chmod +x "$DEB_ROOT/usr/bin/os1-ubuntu-ui"

cp "$ROOT_DIR/linux-ui/packaging/os1-ubuntu-ui.desktop" "$DEB_ROOT/usr/share/applications/os1-ubuntu-ui.desktop"
cp "$ROOT_DIR/assets/terminal.png" "$DEB_ROOT/usr/share/icons/hicolor/256x256/apps/os1-ubuntu-ui.png"

cat > "$DEB_ROOT/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: OS1 Team <noreply@example.com>
Depends: python3, python3-tk
Description: OS1 Ubuntu desktop UI
 Ubuntu desktop interface for OS1 workflows (connections, sessions,
 files, terminal, kanban, skills, cron) with local persistence.
EOF

DEB_PATH="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$DEB_ROOT" "$DEB_PATH" >/dev/null

# Optional AppImage build (requires appimagetool)
APPIMAGE_PATH="$DIST_DIR/${PKG_NAME}-${VERSION}-${ARCH}.AppImage"
if command -v appimagetool >/dev/null 2>&1; then
  APPIMAGE_ROOT="$DIST_DIR/AppDir"
  rm -rf "$APPIMAGE_ROOT"
  mkdir -p "$APPIMAGE_ROOT/usr/bin" "$APPIMAGE_ROOT/usr/share/applications" "$APPIMAGE_ROOT/usr/share/icons/hicolor/256x256/apps"

  cp -R "$APP_DIR/." "$APPIMAGE_ROOT/usr/bin/"
  cp "$ROOT_DIR/linux-ui/packaging/os1-ubuntu-ui.desktop" "$APPIMAGE_ROOT/os1-ubuntu-ui.desktop"
  cp "$ROOT_DIR/linux-ui/packaging/os1-ubuntu-ui.desktop" "$APPIMAGE_ROOT/usr/share/applications/os1-ubuntu-ui.desktop"
  cp "$ROOT_DIR/assets/terminal.png" "$APPIMAGE_ROOT/os1-ubuntu-ui.png"
  cp "$ROOT_DIR/assets/terminal.png" "$APPIMAGE_ROOT/usr/share/icons/hicolor/256x256/apps/os1-ubuntu-ui.png"

  cat > "$APPIMAGE_ROOT/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec "$APPDIR/usr/bin/run-ubuntu-ui.sh"
EOF
  chmod +x "$APPIMAGE_ROOT/AppRun" "$APPIMAGE_ROOT/usr/bin/run-ubuntu-ui.sh" "$APPIMAGE_ROOT/usr/bin/os1_ubuntu_ui.py"

  appimagetool "$APPIMAGE_ROOT" "$APPIMAGE_PATH" >/dev/null
  echo "Built AppImage: $APPIMAGE_PATH"
else
  echo "appimagetool not found; skipping AppImage build"
fi

echo "Built Debian package: $DEB_PATH"
