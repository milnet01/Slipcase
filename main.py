#!/usr/bin/env python3
"""Slipcase - Entry point."""

import multiprocessing
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

from PIL import Image
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from api.base import MAX_IMAGE_PIXELS
from core.config import Config
from ui.themes import THEMES, DEFAULT_THEME, set_active_theme, generate_stylesheet
from ui.main_window import MainWindow
from ui.single_instance import SingleInstance

# Limit decompression to prevent memory exhaustion from malicious images.
# The value lives in api/base.py, which also applies it at import so the
# download path is protected without depending on this module having run.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _smoke(app: QApplication, report_path: str | None) -> int:
    """Check the parts a packaged build can lose, and say so in one line.

    A bundle missing its resources, a Qt plugin, or the worker-process hook
    still starts without an error, so the packaging scripts run this against
    every build (SLIP-0018). The line goes to stdout and, when a path is
    given, to that file: a Windows build has no console to print to.
    Uses a temporary settings file, never the user's.
    """
    import tempfile
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context

    from core.case_types import CASE_TYPES
    from core.spine_generator import CASE_COLORS_ERROR
    from core.version import __version__
    from ui.workers import _render_single_image

    try:
        if CASE_COLORS_ERROR:
            raise RuntimeError(CASE_COLORS_ERROR)
        if app.windowIcon().isNull():
            raise RuntimeError("the application icons are missing")

        with tempfile.TemporaryDirectory() as scratch:
            # The batch path: a worker process that imports the renderer and
            # writes a PNG. In a frozen build without freeze_support() the
            # worker re-runs the application instead and this never returns.
            cover = os.path.join(scratch, "cover.jpg")
            Image.new("RGB", (300, 420), (40, 90, 160)).save(cover)
            case_type = next(iter(CASE_TYPES.values()))
            with ProcessPoolExecutor(1, mp_context=get_context("spawn")) as pool:
                job = (cover, scratch, case_type, {"output_width": 256}, 6)
                name = pool.submit(_render_single_image, job).result(timeout=120)
            with Image.open(os.path.join(scratch, f"{name}.png")) as rendered:
                rendered.load()
                if rendered.getbbox() is None:
                    raise RuntimeError("the batch render came out empty")

            # The window: every dialog import and the platform plugin.
            window = MainWindow(Config(os.path.join(scratch, "config.json")))
            window.show()
            app.processEvents()
            window.close()
            app.processEvents()
        line, code = f"slipcase smoke OK {__version__}", 0
    except Exception as e:
        line, code = f"slipcase smoke FAIL {type(e).__name__}: {e}", 1

    print(line, flush=True)
    if report_path:
        Path(report_path).write_text(line + "\n", encoding="utf-8")
    return code


def main():
    smoke = next((a for a in sys.argv[1:]
                  if a == "--smoke" or a.startswith("--smoke=")), None)

    app = QApplication(sys.argv)
    app.setApplicationName("Slipcase")
    app.setOrganizationName("Slipcase")

    # Both are needed, for different display servers. On X11 the title-bar
    # icon comes from _NET_WM_ICON, which Qt writes only from setWindowIcon;
    # on Wayland the icon is matched by app_id, which Qt takes from
    # desktopFileName. Without them the app shows a generic icon on either
    # (SLIP-0048). The name is slipcase.desktop, without the suffix.
    app.setDesktopFileName("slipcase")
    icon = QIcon()
    resources = Path(__file__).resolve().parent / "resources"
    for size in (48, 64, 128, 256):
        icon_file = resources / f"icon_{size}.png"
        if icon_file.exists():
            icon.addFile(str(icon_file))
    if not icon.isNull():
        app.setWindowIcon(icon)

    # Before the single-instance check and Config(): a self-check must not
    # talk to a running copy or touch the user's settings.
    if smoke is not None:
        sys.exit(_smoke(app, smoke.partition("=")[2] or None))

    # One copy at a time: two copies each held their own settings and the
    # last to save overwrote the other's (SLIP-0049). A second launch brings
    # the running window forward and exits. This runs before Config() so the
    # second copy never loads, and so never saves, the settings file.
    instance = SingleInstance()
    window_holder: list[MainWindow] = []

    def bring_forward() -> None:
        if window_holder:
            w = window_holder[0]
            if w.isMinimized():
                w.showNormal()
            else:
                w.show()
            w.raise_()
            w.activateWindow()

    if not instance.acquire(on_activate=bring_forward):
        if not instance.activate_running():
            QMessageBox.information(
                None, "Slipcase",
                "Slipcase is already running, but did not respond. "
                "Close it, then open Slipcase again.",
            )
        sys.exit(0)

    config = Config()

    # Apply saved theme (or default)
    theme_name = config.get("ui", "theme", default=DEFAULT_THEME)
    if theme_name not in THEMES:
        theme_name = DEFAULT_THEME
    theme = set_active_theme(theme_name)
    app.setStyleSheet(generate_stylesheet(theme))

    window = MainWindow(config)
    window_holder.append(window)
    window.show()

    code = app.exec()
    instance.release()
    sys.exit(code)


if __name__ == "__main__":
    # In a packaged build a worker process starts by running this file
    # again. freeze_support() is what turns that run into the worker; without
    # it every batch render opens another copy of the application.
    multiprocessing.freeze_support()
    main()
