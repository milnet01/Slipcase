"""Unified online cover art search dialog across all configured APIs."""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
    QProgressBar, QMessageBox, QGroupBox,
)
from PIL import Image

from core.config import Config
from api.screenscraper import ScreenScraperAPI, SCREENSCRAPER_SYSTEMS
from api.thegamesdb import TheGamesDBAPI, THEGAMESDB_PLATFORMS
from api.libretro import LibretroThumbnails, LIBRETRO_SYSTEMS
from ui.preview_widget import pil_to_qpixmap
from ui.themes import get_active_theme, themed_thumbnail_style


def _create_ss_client(config: Config) -> ScreenScraperAPI:
    """Create a ScreenScraper API client from config."""
    return ScreenScraperAPI(
        devid=config.get("api", "screenscraper", "devid", default=""),
        devpassword=config.get("api", "screenscraper", "devpassword", default=""),
        username=config.get("api", "screenscraper", "username", default=""),
        password=config.get("api", "screenscraper", "password", default=""),
    )


def _create_tgdb_client(config: Config) -> TheGamesDBAPI:
    """Create a TheGamesDB API client from config."""
    return TheGamesDBAPI(
        api_key=config.get("api", "thegamesdb", "api_key", default=""),
    )


class SearchWorker(QThread):
    """Background thread for API searches."""
    results_ready = pyqtSignal(list)  # list of (source, name, platform, result_obj)
    error = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, query: str, platform: str, config: Config):
        super().__init__()
        self.query = query
        self.platform = platform
        self.config = config

    def run(self):
        all_results = []

        # ScreenScraper
        ss = _create_ss_client(self.config)
        try:
            if ss.is_configured:
                sys_id = SCREENSCRAPER_SYSTEMS.get(self.platform)
                try:
                    results = ss.search_game(self.query, system_id=sys_id)
                    for r in results[:10]:
                        all_results.append(("ScreenScraper", r.name, r.platform, r))
                except Exception as e:
                    self.error.emit(f"ScreenScraper: {e}")
        finally:
            ss.close()

        # TheGamesDB
        tgdb = _create_tgdb_client(self.config)
        try:
            if tgdb.is_configured:
                plat_id = THEGAMESDB_PLATFORMS.get(self.platform)
                try:
                    results = tgdb.search_game(self.query, platform_id=plat_id)
                    for r in results[:10]:
                        all_results.append(("TheGamesDB", r.name, r.platform, r))
                except Exception as e:
                    self.error.emit(f"TheGamesDB: {e}")
        finally:
            tgdb.close()

        # libretro (try direct lookup)
        lr = LibretroThumbnails()
        try:
            lr_system = LIBRETRO_SYSTEMS.get(self.platform)
            if lr_system:
                try:
                    img = lr.download_boxart(lr_system, self.query)
                    if img:
                        all_results.append(("libretro", self.query, self.platform, img))
                except Exception:
                    pass
        finally:
            lr.close()

        self.results_ready.emit(all_results)
        self.finished_signal.emit()


class PreviewWorker(QThread):
    """Background thread for downloading a thumbnail preview of a selected result."""
    preview_ready = pyqtSignal(object, int)  # PIL Image, row index
    error = pyqtSignal(str)

    def __init__(self, source: str, result_obj, config: Config, row: int):
        super().__init__()
        self.source = source
        self.result_obj = result_obj
        self.config = config
        self.row = row

    def run(self):
        try:
            img = None
            if self.source == "ScreenScraper":
                ss = _create_ss_client(self.config)
                try:
                    img = ss.download_front(self.result_obj)
                finally:
                    ss.close()

            elif self.source == "TheGamesDB":
                tgdb = _create_tgdb_client(self.config)
                try:
                    img = tgdb.download_front(self.result_obj)
                finally:
                    tgdb.close()

            elif self.source == "libretro":
                img = self.result_obj

            if img:
                self.preview_ready.emit(img, self.row)
            else:
                self.error.emit("No preview available")
        except Exception as e:
            self.error.emit(str(e))


class DownloadWorker(QThread):
    """Background thread for downloading a selected cover image (front + back)."""
    image_ready = pyqtSignal(object, object)  # front_image, back_image (PIL Images or None)
    error = pyqtSignal(str)

    def __init__(self, source: str, result_obj, config: Config):
        super().__init__()
        self.source = source
        self.result_obj = result_obj
        self.config = config
        self.download_3d = False

    def run(self):
        front = None
        back = None

        try:
            if self.source == "ScreenScraper":
                ss = _create_ss_client(self.config)
                try:
                    if self.download_3d:
                        front = ss.download_box3d(self.result_obj)
                    else:
                        front = ss.download_front(self.result_obj)
                        back = ss.download_back(self.result_obj)
                finally:
                    ss.close()

            elif self.source == "TheGamesDB":
                tgdb = _create_tgdb_client(self.config)
                try:
                    front = tgdb.download_front(self.result_obj)
                    back = tgdb.download_back(self.result_obj)
                finally:
                    tgdb.close()

            elif self.source == "libretro":
                # result_obj is already the PIL Image
                front = self.result_obj

            self.image_ready.emit(front, back)
        except Exception as e:
            self.error.emit(str(e))


class SearchDialog(QDialog):
    """Search dialog for finding and downloading cover art from online APIs."""

    # Emitted when user selects cover images: (front_image, back_image, game_name)
    images_selected = pyqtSignal(object, object, str)  # noqa: N815
    # Emitted when user selects a pre-rendered 3D boxart: (image, game_name)
    boxart3d_selected = pyqtSignal(object, str)

    def __init__(self, config: Config, platform: str = "", parent=None):
        super().__init__(parent)
        self.config = config
        self.platform = platform
        self.setWindowTitle("Search Online Cover Art")
        self.setMinimumSize(600, 500)
        self._results: list = []
        self._preview_cache: dict[int, Image.Image] = {}
        self._worker: SearchWorker | None = None
        self._dl_worker: DownloadWorker | None = None
        self._preview_worker: PreviewWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter game name...")
        self.search_input.returnPressed.connect(self._do_search)
        search_row.addWidget(self.search_input)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self.search_btn)
        layout.addLayout(search_row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMaximum(0)
        self.progress.hide()
        layout.addWidget(self.progress)

        # Results list
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout()
        self.results_list = QListWidget()
        self.results_list.currentRowChanged.connect(self._on_result_selected)
        results_layout.addWidget(self.results_list)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Preview and actions
        bottom = QHBoxLayout()
        self.preview_label = QLabel("Select a result to preview")
        self.preview_label.setFixedSize(150, 200)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(themed_thumbnail_style())
        bottom.addWidget(self.preview_label)

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        bottom.addWidget(self.info_label, 1)

        btn_layout = QVBoxLayout()
        self.download_btn = QPushButton("Use This Cover")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self._download_selected)
        btn_layout.addWidget(self.download_btn)
        self.use3d_btn = QPushButton("Use 3D Boxart")
        self.use3d_btn.setEnabled(False)
        self.use3d_btn.setToolTip("Download pre-rendered 3D boxart from ScreenScraper")
        self.use3d_btn.clicked.connect(self._download_3d_boxart)
        btn_layout.addWidget(self.use3d_btn)
        btn_layout.addStretch()
        bottom.addLayout(btn_layout)

        layout.addLayout(bottom)

        self.status_label = QLabel("Enter a game name and click Search")
        layout.addWidget(self.status_label)

    def _do_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return

        self.results_list.clear()
        self._results.clear()
        self._preview_cache.clear()
        self.preview_label.setText("Select a result to preview")
        self.search_btn.setEnabled(False)
        self.progress.show()
        self.status_label.setText("Searching...")

        self._worker = SearchWorker(query, self.platform, self.config)
        self._worker.results_ready.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_search_done)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_results(self, results: list) -> None:
        self._results = results
        for source, name, platform, obj in results:
            item = QListWidgetItem(f"[{source}] {name} ({platform})")
            self.results_list.addItem(item)

        if not results:
            self.status_label.setText("No results found")
        else:
            self.status_label.setText(f"Found {len(results)} result(s)")

    def _on_error(self, msg: str) -> None:
        self.status_label.setText(f"Error: {msg}")

    def _on_search_done(self) -> None:
        self.search_btn.setEnabled(True)
        self.progress.hide()

    def _on_result_selected(self, row: int) -> None:
        valid = 0 <= row < len(self._results)
        self.download_btn.setEnabled(valid)
        self.use3d_btn.setEnabled(False)
        if not valid:
            return

        source, name, platform, obj = self._results[row]
        info = f"<b>{name}</b><br>Source: {source}<br>Platform: {platform}"

        # Check if 3D boxart is available
        has_3d = (source == "ScreenScraper"
                  and hasattr(obj, "box3d_url") and obj.box3d_url)
        if has_3d:
            info += f"<br><span style='color: {get_active_theme().accent};'>3D Boxart available</span>"
            self.use3d_btn.setEnabled(True)

        self.info_label.setText(info)

        # Check preview cache first
        if row in self._preview_cache:
            self._show_preview(self._preview_cache[row])
            return

        # For libretro results, the obj is already a PIL Image
        if source == "libretro" and isinstance(obj, Image.Image):
            self._preview_cache[row] = obj
            self._show_preview(obj)
            return

        # Fetch preview in background for ScreenScraper / TheGamesDB
        self.preview_label.setText("Loading...")
        self._preview_worker = PreviewWorker(source, obj, self.config, row)
        self._preview_worker.preview_ready.connect(self._on_preview_ready)
        self._preview_worker.error.connect(lambda msg: self.preview_label.setText("No preview"))
        self._preview_worker.finished.connect(self._preview_worker.deleteLater)
        self._preview_worker.start()

    def _on_preview_ready(self, image: Image.Image, row: int) -> None:
        self._preview_cache[row] = image
        if self.results_list.currentRow() == row:
            self._show_preview(image)

    def _show_preview(self, image: Image.Image) -> None:
        pm = pil_to_qpixmap(image)
        self.preview_label.setPixmap(
            pm.scaled(self.preview_label.size(),
                      Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation)
        )

    def _download_selected(self) -> None:
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self._results):
            return

        source, name, platform, obj = self._results[row]

        # For libretro results, emit directly
        if source == "libretro" and isinstance(obj, Image.Image):
            self.images_selected.emit(obj, None, name)
            self.accept()
            return

        self.download_btn.setEnabled(False)
        self.status_label.setText("Downloading...")
        self.progress.show()

        self._dl_worker = DownloadWorker(source, obj, self.config)
        self._dl_worker.image_ready.connect(lambda f, b: self._on_download(f, b, name))
        self._dl_worker.error.connect(self._on_error)
        self._dl_worker.finished.connect(self._dl_worker.deleteLater)
        self._dl_worker.start()

    def _on_download(self, front, back, name: str) -> None:
        self.progress.hide()
        self.download_btn.setEnabled(True)
        if front is None:
            self.status_label.setText("Failed to download cover image")
            return

        self.images_selected.emit(front, back, name)
        self.accept()

    def _download_3d_boxart(self) -> None:
        """Download pre-rendered 3D boxart from ScreenScraper."""
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self._results):
            return

        source, name, platform, obj = self._results[row]
        if not (hasattr(obj, "box3d_url") and obj.box3d_url):
            return

        self.use3d_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.status_label.setText("Downloading 3D boxart...")
        self.progress.show()

        self._dl_worker = DownloadWorker(source, obj, self.config)
        self._dl_worker.image_ready.connect(lambda f, b: self._on_3d_download(f, name))
        self._dl_worker.error.connect(self._on_error)
        self._dl_worker.finished.connect(self._dl_worker.deleteLater)
        # Override the worker to download box3d instead
        self._dl_worker.download_3d = True
        self._dl_worker.start()

    def _on_3d_download(self, image, name: str) -> None:
        self.progress.hide()
        self.download_btn.setEnabled(True)
        self.use3d_btn.setEnabled(True)
        if image is None:
            self.status_label.setText("Failed to download 3D boxart")
            return

        self.boxart3d_selected.emit(image, name)
        self.accept()

    def reject(self) -> None:
        self._cleanup()
        super().reject()

    def _cleanup(self) -> None:
        """Release cached images and results to free memory."""
        self._preview_cache.clear()
        self._results.clear()
