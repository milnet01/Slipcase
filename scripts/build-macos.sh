#!/usr/bin/env bash
# Build dist/Slipcase-macos-<arch>.dmg and run its self-check (SLIP-0020).
#
# .github/workflows/release.yml runs this script on a Mac runner for each
# processor type; the build is for the processor of the machine it runs on
# (arm64 for Apple silicon, x86_64 for Intel). Nobody has tried the result by
# hand on a real Mac: the self-check below is the whole of the evidence.
#
# The app is not signed with an Apple developer certificate (decided
# 2026-09-02), so macOS asks the user to confirm the first launch.
#
# Usage: ./scripts/build-macos.sh
#   PYTHON              interpreter to build with (default: python3)
#   SLIPCASE_BUILD_DIR  scratch folder (default: build/ in the repository)
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
BUILD_DIR="${SLIPCASE_BUILD_DIR:-build}"
ARCH="$(uname -m)"
NAME="Slipcase-macos-$ARCH.dmg"

mkdir -p "$BUILD_DIR" dist

printf '\n=== bundle ===\n'
"$PYTHON" -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/pip" install --quiet --disable-pip-version-check \
    -r requirements.lock -r requirements-build.txt
"$BUILD_DIR/venv/bin/pyinstaller" --noconfirm --log-level WARN \
    --distpath "$BUILD_DIR/dist" --workpath "$BUILD_DIR/work" \
    packaging/slipcase.spec

printf '\n=== disk image ===\n'
# The app beside a shortcut to Applications: the user drags one onto the other.
STAGE="$BUILD_DIR/dmg"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$BUILD_DIR/dist/Slipcase.app" "$STAGE/Slipcase.app"
ln -s /Applications "$STAGE/Applications"
rm -f "dist/$NAME"
hdiutil create -quiet -volname Slipcase -srcfolder "$STAGE" -ov -format UDZO "dist/$NAME"

printf '\n=== self-check ===\n'
# Run the copy inside the finished disk image, since that is what ships. A
# private settings folder and no window: the check must not touch the
# settings of whoever runs the build. The report file is the evidence.
SMOKE_DIR="$(mktemp -d)"
MOUNT="$SMOKE_DIR/volume"
mkdir "$MOUNT"
trap 'hdiutil detach -quiet "$MOUNT" 2>/dev/null || true; rm -rf "$SMOKE_DIR"' EXIT
hdiutil attach -quiet -nobrowse -readonly -mountpoint "$MOUNT" "dist/$NAME"
env QT_QPA_PLATFORM=offscreen XDG_CONFIG_HOME="$SMOKE_DIR/config" \
    "$MOUNT/Slipcase.app/Contents/MacOS/slipcase" "--smoke=$SMOKE_DIR/report.txt"
grep -q "^slipcase smoke OK " "$SMOKE_DIR/report.txt"

(cd dist && shasum -a 256 "$NAME" > "$NAME.sha256")
printf '\nbuilt dist/%s (%s)\n' "$NAME" "$(du -h "dist/$NAME" | cut -f1)"
