#!/usr/bin/env bash
# Build dist/Slipcase-x86_64.AppImage and run its self-check (SLIP-0018).
#
# .github/workflows/release.yml runs this same script, so a build made here
# and the one attached to a release are made the same way. The release build
# runs on an older Ubuntu so the result starts on older systems; a build made
# on a newer machine is for testing only.
#
# Usage: ./scripts/build-appimage.sh
#   PYTHON              interpreter to build with (default: python3)
#   SLIPCASE_BUILD_DIR  scratch folder (default: build/ in the repository)
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
BUILD_DIR="${SLIPCASE_BUILD_DIR:-build}"
ARCH=x86_64
OUT="dist/Slipcase-$ARCH.AppImage"

# The packer and the launcher stub it embeds, pinned by checksum. The packer
# would otherwise download whichever launcher is newest at build time.
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-$ARCH.AppImage"
APPIMAGETOOL_SHA256=ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-$ARCH"
RUNTIME_SHA256=2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d

fetch() { # url sha256 destination
    if [[ ! -f "$3" ]] || ! echo "$2  $3" | sha256sum --check --status; then
        curl --fail --silent --show-error --location --output "$3" "$1"
        echo "$2  $3" | sha256sum --check --quiet
    fi
}

mkdir -p "$BUILD_DIR/tools" dist

printf '\n=== bundle ===\n'
"$PYTHON" -m venv "$BUILD_DIR/venv"
"$BUILD_DIR/venv/bin/pip" install --quiet --disable-pip-version-check \
    -r requirements.lock -r requirements-build.txt
"$BUILD_DIR/venv/bin/pyinstaller" --noconfirm --log-level WARN \
    --distpath "$BUILD_DIR/dist" --workpath "$BUILD_DIR/work" \
    packaging/slipcase.spec

printf '\n=== AppDir ===\n'
APPDIR="$BUILD_DIR/Slipcase.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a "$BUILD_DIR/dist/slipcase" "$APPDIR/usr/lib/slipcase"
install -m 755 packaging/linux/AppRun "$APPDIR/AppRun"
install -m 644 packaging/linux/slipcase.desktop "$APPDIR/slipcase.desktop"
install -m 644 packaging/linux/slipcase.desktop "$APPDIR/usr/share/applications/slipcase.desktop"
install -m 644 resources/icon_256.png "$APPDIR/slipcase.png"
install -m 644 resources/icon_256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/slipcase.png"
ln -s slipcase.png "$APPDIR/.DirIcon"

printf '\n=== AppImage ===\n'
fetch "$APPIMAGETOOL_URL" "$APPIMAGETOOL_SHA256" "$BUILD_DIR/tools/appimagetool"
fetch "$RUNTIME_URL" "$RUNTIME_SHA256" "$BUILD_DIR/tools/runtime"
chmod +x "$BUILD_DIR/tools/appimagetool"
rm -f "$OUT"
# Extract-and-run: the packer is itself an AppImage, and a CI runner has no
# FUSE to mount it with.
ARCH="$ARCH" APPIMAGE_EXTRACT_AND_RUN=1 "$BUILD_DIR/tools/appimagetool" \
    --no-appstream --runtime-file "$BUILD_DIR/tools/runtime" "$APPDIR" "$OUT"

printf '\n=== self-check ===\n'
# A private settings and runtime folder, and no display: the check must not
# touch the settings of whoever runs the build, or open a window on their
# desktop. The report file is the evidence, not the exit code alone.
SMOKE_DIR="$(mktemp -d)"
trap 'rm -rf "$SMOKE_DIR"' EXIT
env QT_QPA_PLATFORM=offscreen APPIMAGE_EXTRACT_AND_RUN=1 \
    XDG_CONFIG_HOME="$SMOKE_DIR" XDG_RUNTIME_DIR="$SMOKE_DIR" \
    "$OUT" "--smoke=$SMOKE_DIR/report.txt"
grep --quiet '^slipcase smoke OK ' "$SMOKE_DIR/report.txt"

(cd dist && sha256sum "Slipcase-$ARCH.AppImage" > "Slipcase-$ARCH.AppImage.sha256")
printf '\nbuilt %s (%s)\n' "$OUT" "$(du -h "$OUT" | cut -f1)"
