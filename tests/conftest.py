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
