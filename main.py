#!/usr/bin/env python3
"""Slipcase - Entry point."""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from PyQt6.QtWidgets import QApplication

from core.config import Config
from ui.themes import THEMES, DEFAULT_THEME, set_active_theme, generate_stylesheet
from ui.main_window import MainWindow

# Limit decompression to prevent memory exhaustion from malicious images
Image.MAX_IMAGE_PIXELS = 178_956_970


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Slipcase")
    app.setOrganizationName("Slipcase")

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
