"""Settings dialog for API keys and application preferences."""

from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QTabWidget, QVBoxLayout, QWidget,
)

from core.config import Config
from ui.themes import themed_dim_text_style


class SettingsDialog(QDialog):
    """Dialog for configuring API keys and preferences."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_screenscraper_tab(), "ScreenScraper")
        tabs.addTab(self._build_thegamesdb_tab(), "TheGamesDB")
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

        group = QGroupBox("ScreenScraper Credentials")
        form = QFormLayout()

        self.ss_devid = QLineEdit()
        self.ss_devpassword = QLineEdit()
        self.ss_devpassword.setEchoMode(QLineEdit.EchoMode.Password)
        self.ss_username = QLineEdit()
        self.ss_password = QLineEdit()
        self.ss_password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Dev ID:", self.ss_devid)
        form.addRow("Dev Password:", self.ss_devpassword)
        form.addRow("Username:", self.ss_username)
        form.addRow("Password:", self.ss_password)

        group.setLayout(form)
        layout.addWidget(group)

        info = QLabel(
            "Register at screenscraper.fr for credentials.\n"
            "Dev credentials require a developer account."
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _build_thegamesdb_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("TheGamesDB Credentials")
        form = QFormLayout()

        self.tgdb_api_key = QLineEdit()
        form.addRow("API Key:", self.tgdb_api_key)

        group.setLayout(form)
        layout.addWidget(group)

        info = QLabel(
            "Get a free API key at thegamesdb.net/register"
        )
        info.setWordWrap(True)
        info.setStyleSheet(themed_dim_text_style())
        layout.addWidget(info)
        layout.addStretch()

        return widget

    def _load_values(self) -> None:
        """Load saved values into fields."""
        self.ss_devid.setText(self.config.get("api", "screenscraper", "devid", default=""))
        self.ss_devpassword.setText(self.config.get("api", "screenscraper", "devpassword", default=""))
        self.ss_username.setText(self.config.get("api", "screenscraper", "username", default=""))
        self.ss_password.setText(self.config.get("api", "screenscraper", "password", default=""))
        self.tgdb_api_key.setText(self.config.get("api", "thegamesdb", "api_key", default=""))

    def _save_and_accept(self) -> None:
        """Save values to config and close."""
        self.config.set("api", "screenscraper", "devid", self.ss_devid.text())
        self.config.set("api", "screenscraper", "devpassword", self.ss_devpassword.text())
        self.config.set("api", "screenscraper", "username", self.ss_username.text())
        self.config.set("api", "screenscraper", "password", self.ss_password.text())
        self.config.set("api", "thegamesdb", "api_key", self.tgdb_api_key.text())
        self.config.save()
        self.accept()
