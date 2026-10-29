"""The update offer and its progress (SLIP-0031 § 4.8).

Shown with show(), never run modally, so a render's progress keeps moving
and the main window can still close. Later stores nothing, so the next
start offers again; Skip this version stores the version at once.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)

from api import releases
from core.update_installer import Installer
from core.updater import UpdateOffer
from core.version import __version__
from ui.workers import UpdateDownloadWorker

if TYPE_CHECKING:
    from ui.main_window import MainWindow

# The page a Mac user is sent to. Built from the tag, which passed the
# version grammar, never from the reply's html_url.
RELEASE_PAGE = "https://github.com/milnet01/Slipcase/releases/tag/"


class UpdateDialog(QDialog):
    """Offers one release: install it, open its page, skip it, or not now.

    `installer` is None in notify-only mode, which offers Open release page
    in place of Update now.
    """

    def __init__(self, window: MainWindow, offer: UpdateOffer,
                 installer: Installer | None, *, download=releases.download) -> None:
        super().__init__(window)
        self._window = window
        self._offer = offer
        self._installer = installer
        self._download = download
        self._worker: UpdateDownloadWorker | None = None
        # Set once the dialog is dismissed; a download finishing later is
        # deleted rather than installed (INV-13).
        self._closed = False
        self.setWindowTitle(self.tr("Update available"))
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.message_label = QLabel(
            self.tr("Slipcase {0} is available. You have {1}.").format(
                self._offer.version, __version__))
        self.message_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.message_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.later_button = QPushButton(self.tr("Later"))
        self.later_button.clicked.connect(self.close)
        self.skip_button = QPushButton(self.tr("Skip this version"))
        self.skip_button.clicked.connect(self._skip)
        buttons.addWidget(self.later_button)
        buttons.addWidget(self.skip_button)

        self.update_button: QPushButton | None = None
        self.release_page_button: QPushButton | None = None
        if self._installer is not None:
            self.update_button = QPushButton(self.tr("Update now"))
            self.update_button.clicked.connect(self._update_now)
            self.update_button.setDefault(True)
            buttons.addWidget(self.update_button)
        else:
            self.release_page_button = QPushButton(self.tr("Open release page"))
            self.release_page_button.clicked.connect(self._open_release_page)
            self.release_page_button.setDefault(True)
            buttons.addWidget(self.release_page_button)
        layout.addLayout(buttons)

    def done(self, result: int) -> None:
        """Every way the dialog is dismissed -- a button, Esc, the title bar."""
        self._closed = True
        if self._worker is not None:
            try:
                self._worker.requestInterruption()
            except RuntimeError:
                pass  # C++ object already deleted by deleteLater
        super().done(result)

    def _skip(self) -> None:
        self._window.config.set("updates", "skipped_version", self._offer.version)
        self._window._save_config()
        self.close()

    def _open_release_page(self) -> None:
        QDesktopServices.openUrl(QUrl(RELEASE_PAGE + self._offer.tag))
        self.close()

    def _show_busy(self) -> None:
        self.status_label.setText(self.tr("Finish or stop the current render first."))

    def _update_now(self) -> None:
        if self._worker is not None:
            return
        if self._window._busy_worker() is not None:
            self._show_busy()
            return
        worker = UpdateDownloadWorker(self._offer, self._installer, download=self._download)
        worker.progress.connect(self._on_progress)
        worker.ready.connect(self._on_ready)
        worker.error.connect(self._on_error)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        self.update_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        self.status_label.setText(self.tr("Downloading..."))
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self._window.start_update_download(worker)

    def _on_progress(self, received: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(received)

    def _on_ready(self, path: str) -> None:
        new_file = Path(path)
        if self._closed or self._window._busy_worker() is not None:
            new_file.unlink(missing_ok=True)
            if not self._closed:
                self._reset_buttons()
                self._show_busy()
            return
        try:
            self._installer.apply(new_file, self._window.shutdown_for_update)
        except Exception as e:
            # UpdateError, or anything else: an exception escaping a Qt slot
            # ends the process.
            new_file.unlink(missing_ok=True)
            self._reset_buttons()
            QMessageBox.warning(self, self.tr("Update not installed"), str(e))

    def _on_error(self, message: str) -> None:
        if self._closed:
            return
        self._reset_buttons()
        QMessageBox.warning(self, self.tr("Update not installed"), message)

    def _reset_buttons(self) -> None:
        self._worker = None
        self.progress_bar.hide()
        self.status_label.setText("")
        if self.update_button is not None:
            self.update_button.setEnabled(True)
        self.skip_button.setEnabled(True)
