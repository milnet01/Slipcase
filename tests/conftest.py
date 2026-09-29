"""Top-level pytest configuration."""

from __future__ import annotations

# Force Qt's offscreen QPA platform before any pytest-qt fixture imports
# QApplication. Slipcase pulls in PyQt/PySide via requirements.txt
# for its image-pipeline GUI; without this guard, any test that touches
# QImage/QPainter (or imports a module that creates a QApplication
# at import time) would briefly composite a real top-level window
# onto whatever desktop is hosting the runner. `setdefault` lets a CI
# override (e.g. QT_QPA_PLATFORM=minimal) still win.
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# pytest-qt picks the first Qt binding it finds, and PySide6 wins on a
# machine that has both. Its Qt then loads ahead of PyQt6's bundled one, and
# PyQt6.QtNetwork fails on a missing private symbol. Slipcase is PyQt6.
os.environ.setdefault("PYTEST_QT_API", "pyqt6")
