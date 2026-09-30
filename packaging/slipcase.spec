# PyInstaller recipe for the packaged builds of Slipcase (SLIP-0018, SLIP-0019,
# SLIP-0020).
#
# Bundles the interpreter, the dependencies and resources/.
#   Linux:   one folder, dist/slipcase/, which scripts/build-appimage.sh wraps
#            into an AppImage.
#   Windows: one file, dist/Slipcase-windows-x64.exe, built by
#            scripts/build-windows.ps1.
#   macOS:   Slipcase.app, which scripts/build-macos.sh puts in a disk image.
# Run it through those scripts rather than directly: they pin the tools and
# run the self-check on what comes out.
#
# resources/ is placed beside the bundled modules, which is where main.py and
# core/spine_generator.py already look for it (relative to their own file),
# so the application code needs no "am I packaged?" branch.

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 -- SPECPATH is injected by PyInstaller

a = Analysis(  # noqa: F821
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "resources"), "resources")],
)

if sys.platform.startswith("linux"):
    # Leave out Qt's GTK theme plugin. It drags the build machine's own GTK
    # libraries into the bundle, and those fail to load against another
    # distribution's system libraries. Without it Qt draws its own dialogs.
    #
    # By this point the plugin's own libraries are already in the list with
    # nothing to say who asked for them, so ask the linker: drop whatever the
    # plugin needs that nothing else in the bundle does.
    def _needs(path):
        listing = subprocess.run(["ldd", path], capture_output=True, text=True).stdout
        return {line.split()[0] for line in listing.splitlines() if "=>" in line}

    _kept = [b for b in a.binaries if "libqgtk3" not in b[0]]
    _plugin_needs = set().union(*(_needs(b[1]) for b in a.binaries if "libqgtk3" in b[0]))
    _others = [b for b in _kept if Path(b[0]).name not in _plugin_needs]
    _gtk_only = _plugin_needs - set().union(*(_needs(b[1]) for b in _others))
    a.binaries = [b for b in _kept if Path(b[0]).name not in _gtk_only]
    if any("libgtk" in b[0] for b in a.binaries):
        raise SystemExit("GTK is still being bundled; see the comment above")

    # Leave these to the system the AppImage runs on. They are the entries of
    # the AppImage project's excludelist (AppImageCommunity/pkg2appimage) that
    # the bundler picks up from the build machine. Shipping the build
    # machine's fontconfig is the one that shows: it cannot read a newer
    # system's font settings, so the window comes up in a fallback font.
    _SYSTEM_LIBS = {
        "libcom_err.so.2", "libexpat.so.1", "libfontconfig.so.1", "libfreetype.so.6",
        "libgcc_s.so.1", "libgpg-error.so.0", "libstdc++.so.6", "libuuid.so.1",
        "libX11.so.6", "libX11-xcb.so.1", "libz.so.1",
    }
    a.binaries = [b for b in a.binaries if b[0] not in _SYSTEM_LIBS]

pyz = PYZ(a.pure)  # noqa: F821

if sys.platform == "win32":
    # One portable file: it unpacks itself to a temporary folder on each
    # start. No console window; the icon is converted from the PNG by Pillow.
    EXE(  # noqa: F821
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="Slipcase-windows-x64",
        console=False,
        icon=str(ROOT / "resources" / "icon_256.png"),
    )
else:
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        exclude_binaries=True,
        name="slipcase",
        console=False,
    )
    folder = COLLECT(exe, a.binaries, a.datas, name="slipcase")  # noqa: F821
    if sys.platform == "darwin":
        version = re.search(
            r'__version__ = "([^"]+)"',
            (ROOT / "core" / "version.py").read_text(encoding="utf-8"),
        ).group(1)
        BUNDLE(  # noqa: F821
            folder,
            name="Slipcase.app",
            icon=str(ROOT / "resources" / "icon_256.png"),
            bundle_identifier="io.github.milnet01.slipcase",
            info_plist={
                "CFBundleShortVersionString": version,
                "NSHighResolutionCapable": True,
            },
        )
