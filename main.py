#!/usr/bin/env python3
"""Slipcase - Entry point."""

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


def main():
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
    main()
