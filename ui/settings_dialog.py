"""Settings dialog for API keys and application preferences."""

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QMessageBox, QTabWidget, QVBoxLayout, QWidget,
)

from core.config import Config
from core.update_installer import detect_update_mode
from ui.themes import themed_dim_text_style


class SettingsDialog(QDialog):
    """Dialog for configuring API keys and preferences."""

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(self.tr("Settings"))
        self.setMinimumWidth(450)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_screenscraper_tab(), "ScreenScraper")
        tabs.addTab(self._build_thegamesdb_tab(), "TheGamesDB")
        tabs.addTab(self._build_libretro_tab(), "libretro")
        tabs.addTab(self._build_export_tab(), self.tr("Export"))
        tabs.addTab(self._build_updates_tab(), self.tr("Updates"))
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_screenscraper_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox(self.tr("ScreenScraper Credentials"))
        form = QFormLayout()

        self.ss_devid = QLineEdit()
        self.ss_devid.setEchoMode(QLineEdit.EchoMode.Password)
        self.ss_devpassword = QLineEdit()
        self.ss_devpassword.setEchoMode(QLineEdit.EchoMode.Password)
        self.ss_username = QLineEdit()
        self.ss_password = QLineEdit()
        self.ss_password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow(self.tr("Dev ID:"), self.ss_devid)
        form.addRow(self.tr("Dev Password:"), self.ss_devpassword)
        form.addRow(self.tr("Username:"), self.ss_username)
        form.addRow(self.tr("Password:"), self.ss_password)

        group.setLayout(form)
        layout.addWidget(group)

        info = QLabel(
            self.tr(
                "Register at screenscraper.fr for credentials.\n"
                "Dev credentials require a developer account."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _build_thegamesdb_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox(self.tr("TheGamesDB Credentials"))
        form = QFormLayout()

        self.tgdb_api_key = QLineEdit()
        # An API key is a secret: STANDARDS.md § 10 lists api_key in the very
        # pattern used to scrub it from error messages.
        self.tgdb_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(self.tr("API Key:"), self.tgdb_api_key)

        group.setLayout(form)
        layout.addWidget(group)

        info = QLabel(
            self.tr("Get a free API key at thegamesdb.net/register")
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _build_libretro_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.libretro_enabled = QCheckBox(self.tr("Search libretro thumbnails"))
        layout.addWidget(self.libretro_enabled)

        info = QLabel(
            self.tr(
                "libretro needs no account, so it is searched whenever the platform "
                "has libretro thumbnails. Untick to stop searches contacting it."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _build_export_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.box_file_enabled = QCheckBox(self.tr("Save a box file with each export"))
        layout.addWidget(self.box_file_enabled)

        info = QLabel(
            self.tr(
                "Beside each exported or batch-rendered PNG, also save the box's "
                "size, colours and face pictures (.box.json and three PNGs), so "
                "RetroDB can show the box in 3D."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _build_updates_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.update_check = QCheckBox(
            self.tr("Check for new versions when Slipcase starts"))
        # A source run, or a frozen build outside an AppImage, has nothing
        # to update (SLIP-0031 § 4.3).
        if detect_update_mode() is None:
            self.update_check.setEnabled(False)
            self.update_check.setToolTip(
                self.tr("Only the downloaded app can check for updates."))
        layout.addWidget(self.update_check)

        info = QLabel(
            self.tr(
                "Slipcase asks GitHub once per start whether a newer release is "
                "out. On Linux and Windows it can then download it, check its "
                "signature and install it; on a Mac it opens the download page."
            )
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _load_values(self) -> None:
        """Load saved values into fields."""
        self.ss_devid.setText(self.config.get("api", "screenscraper", "devid", default=""))
        self.ss_devpassword.setText(
            self.config.get("api", "screenscraper", "devpassword", default="")
        )
        self.ss_username.setText(self.config.get("api", "screenscraper", "username", default=""))
        self.ss_password.setText(self.config.get("api", "screenscraper", "password", default=""))
        self.tgdb_api_key.setText(self.config.get("api", "thegamesdb", "api_key", default=""))
        self.libretro_enabled.setChecked(
            bool(self.config.get("api", "libretro", "enabled", default=True))
        )
        self.box_file_enabled.setChecked(
            bool(self.config.get("export", "box_file", default=True))
        )
        # On means exactly True (SLIP-0031 INV-1).
        self.update_check.setChecked(self.config.get("updates", "check") is True)

    def _save_and_accept(self) -> None:
        """Save values to config and close."""
        # .strip() throughout: a pasted key with a trailing newline otherwise
        # saves cleanly and then fails auth with an opaque upstream message.
        self.config.set("api", "screenscraper", "devid", self.ss_devid.text().strip())
        self.config.set(
            "api", "screenscraper", "devpassword", self.ss_devpassword.text().strip()
        )
        self.config.set("api", "screenscraper", "username", self.ss_username.text().strip())
        self.config.set("api", "screenscraper", "password", self.ss_password.text().strip())
        self.config.set("api", "thegamesdb", "api_key", self.tgdb_api_key.text().strip())
        self.config.set("api", "libretro", "enabled", self.libretro_enabled.isChecked())
        self.config.set("export", "box_file", self.box_file_enabled.isChecked())
        if self.update_check.isEnabled():
            self.config.set("updates", "check", self.update_check.isChecked())
        try:
            self.config.save()
        except OSError as e:
            QMessageBox.warning(
                self, self.tr("Settings Not Saved"),
                self.tr("Your settings could not be written to disk:\n{0}").format(e),
            )
            return
        self.accept()
