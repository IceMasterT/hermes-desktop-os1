#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  echo "Usage: ./scripts/prepare-ubuntu-release.sh <version>" >&2
  echo "Example: ./scripts/prepare-ubuntu-release.sh 0.2.0" >&2
  exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must be semver-like: X.Y.Z" >&2
  exit 1
fi

echo "Running Ubuntu verification..."
"$ROOT_DIR/scripts/verify-ubuntu-ui.sh"

echo "Building release artifacts with version $VERSION..."
OS1_UBUNTU_UI_VERSION="$VERSION" "$ROOT_DIR/scripts/build-ubuntu-packages.sh"

echo
echo "Release prep complete."
echo "Next steps:"
echo "  git tag v$VERSION"
echo "  git push origin v$VERSION"
echo "This triggers .github/workflows/ubuntu-ui-release.yml"
