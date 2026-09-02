#!/usr/bin/env python3
"""Slipcase - Entry point."""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

from PIL import Image
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from api.base import MAX_IMAGE_PIXELS
from core.config import Config
from ui.themes import THEMES, DEFAULT_THEME, set_active_theme, generate_stylesheet
from ui.main_window import MainWindow

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

    config = Config()

    # Apply saved theme (or default)
    theme_name = config.get("ui", "theme", default=DEFAULT_THEME)
    if theme_name not in THEMES:
        theme_name = DEFAULT_THEME
    theme = set_active_theme(theme_name)
    app.setStyleSheet(generate_stylesheet(theme))

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
