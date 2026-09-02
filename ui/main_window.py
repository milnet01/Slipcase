"""Main application window for Slipcase."""

import re
from functools import partial
from pathlib import Path

from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QPixmap, QImage
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QSlider, QSpinBox, QSplitter, QStatusBar,
    QStackedWidget, QVBoxLayout, QWidget, QProgressBar,
)

from core.case_types import CASE_TYPES, ALL_PLATFORMS, PLATFORM_CASE_MAP
from core.config import Config
from core.image_utils import is_full_cover, split_full_cover
from core.png_utils import save_optimized_png
from core.renderer import BoxRenderer
from core.version import __version__
from ui.animation_dialog import AnimationDialog
from ui.preview_widget import BusyOverlay, PreviewWidget, pil_to_qpixmap
from ui.settings_dialog import SettingsDialog
from ui.search_dialog import SearchDialog
from ui.themes import (
    THEMES, generate_stylesheet, get_active_theme, set_active_theme,
    themed_generate_btn_style, themed_preview_style,
    themed_secondary_text_style, themed_split_thumb_style, themed_thumbnail_style,
)
from ui.workers import RenderWorker, BatchWorker, AnimationWorker


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle("Slipcase")
        self.setMinimumSize(900, 650)

        self._front_image: Image.Image | None = None
        self._front_image_path: str | None = None
        self._back_image: Image.Image | None = None
        self._spine_color: tuple[int, int, int] | None = None
        self._case_color: tuple[int, int, int] | None = None
        self._render_worker: RenderWorker | None = None
        self._batch_worker: BatchWorker | None = None
        self._anim_worker: AnimationWorker | None = None

        self._build_menu()
        self._build_ui()
        self._build_statusbar()
        self._restore_state()
        self._rebuild_recent_menu()

    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open Front Cover...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._load_front)
        file_menu.addAction(open_action)

        open_back_action = QAction("Open &Back Cover...", self)
        open_back_action.setShortcut("Ctrl+Shift+O")
        open_back_action.triggered.connect(self._load_back)
        file_menu.addAction(open_back_action)

        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent &Files")

        file_menu.addSeparator()

        export_action = QAction("&Export PNG...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_png)
        file_menu.addAction(export_action)

        anim_action = QAction("Export &Animation...", self)
        anim_action.setShortcut("Ctrl+Shift+A")
        anim_action.triggered.connect(self._export_animation)
        file_menu.addAction(anim_action)

        file_menu.addSeparator()
        batch_action = QAction("&Batch Process...", self)
        batch_action.setShortcut("Ctrl+B")
        batch_action.triggered.connect(self._batch_process)
        file_menu.addAction(batch_action)

        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        tools_menu = menubar.addMenu("&Tools")

        generate_action = QAction("&Generate", self)
        generate_action.setShortcut("Ctrl+G")
        generate_action.triggered.connect(self._generate)
        tools_menu.addAction(generate_action)

        # F5 as alternative generate shortcut
        generate_f5 = QAction("Generate (F5)", self)
        generate_f5.setShortcut(QKeySequence(Qt.Key.Key_F5))
        generate_f5.triggered.connect(self._generate)
        self.addAction(generate_f5)

        search_action = QAction("Search &Online...", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self._search_online)
        tools_menu.addAction(search_action)

        copy_action = QAction("&Copy to Clipboard", self)
        copy_action.setShortcut("Ctrl+Shift+C")
        copy_action.triggered.connect(self._copy_to_clipboard)
        tools_menu.addAction(copy_action)

        compare_action = QAction("Toggle &Comparison", self)
        compare_action.setShortcut("Ctrl+D")
        compare_action.triggered.connect(self._toggle_compare)
        tools_menu.addAction(compare_action)

        tools_menu.addSeparator()

        # Theme submenu
        self.theme_menu = tools_menu.addMenu("&Theme")
        self._theme_actions: dict[str, QAction] = {}
        for name in THEMES:
            action = QAction(name, self)
            action.setCheckable(True)
            action.triggered.connect(partial(self._change_theme, name))
            self.theme_menu.addAction(action)
            self._theme_actions[name] = action
        self._update_theme_checks()

        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top toolbar row
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Platform:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(ALL_PLATFORMS)
        self.platform_combo.currentTextChanged.connect(self._on_platform_changed)
        toolbar.addWidget(self.platform_combo)

        toolbar.addWidget(QLabel("Case Type:"))
        self.case_combo = QComboBox()
        self.case_combo.addItems(CASE_TYPES.keys())
        toolbar.addWidget(self.case_combo)

        search_btn = QPushButton("Search Online...")
        search_btn.clicked.connect(self._search_online)
        toolbar.addWidget(search_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Main content: left panel + preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([280, 600])
        main_layout.addWidget(splitter)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

    def _build_left_panel(self) -> QWidget:
        """Build the left control panel."""
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Front cover
        front_group = QGroupBox("Front Cover")
        front_layout = QVBoxLayout()
        front_btn_row = QHBoxLayout()
        load_front_btn = QPushButton("Load Image")
        load_front_btn.clicked.connect(self._load_front)
        front_btn_row.addWidget(load_front_btn)
        clear_front_btn = QPushButton("Clear")
        clear_front_btn.clicked.connect(self._clear_front)
        front_btn_row.addWidget(clear_front_btn)
        front_layout.addLayout(front_btn_row)
        self.front_thumb = QLabel("No image loaded")
        self.front_thumb.setFixedSize(180, 220)
        self.front_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.front_thumb.setStyleSheet(themed_thumbnail_style())
        front_layout.addWidget(self.front_thumb)
        front_group.setLayout(front_layout)
        left_layout.addWidget(front_group)

        # Back cover
        back_group = QGroupBox("Back Cover (optional)")
        back_layout = QVBoxLayout()
        back_btn_row = QHBoxLayout()
        load_back_btn = QPushButton("Load Image")
        load_back_btn.clicked.connect(self._load_back)
        back_btn_row.addWidget(load_back_btn)
        clear_back_btn = QPushButton("Clear")
        clear_back_btn.clicked.connect(self._clear_back)
        back_btn_row.addWidget(clear_back_btn)
        back_layout.addLayout(back_btn_row)
        self.back_thumb = QLabel("No image")
        self.back_thumb.setFixedSize(180, 120)
        self.back_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.back_thumb.setStyleSheet(themed_thumbnail_style())
        back_layout.addWidget(self.back_thumb)
        back_group.setLayout(back_layout)
        left_layout.addWidget(back_group)

        # Spine
        spine_group = QGroupBox("Spine")
        spine_layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Game title for spine text")
        title_row.addWidget(self.title_input)
        spine_layout.addLayout(title_row)

        serial_row = QHBoxLayout()
        serial_row.addWidget(QLabel("Serial:"))
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("e.g. SLUS-20946")
        serial_row.addWidget(self.serial_input)
        spine_layout.addLayout(serial_row)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self.color_btn = QPushButton("Auto")
        self.color_btn.setFixedWidth(80)
        self.color_btn.setToolTip("Uses platform template color by default")
        self.color_btn.clicked.connect(self._pick_spine_color)
        color_row.addWidget(self.color_btn)
        color_row.addStretch()
        spine_layout.addLayout(color_row)

        spine_group.setLayout(spine_layout)
        left_layout.addWidget(spine_group)

        # Case color
        case_color_row = QHBoxLayout()
        case_color_row.addWidget(QLabel("Case Color:"))
        self.case_color_btn = QPushButton("Auto")
        self.case_color_btn.setFixedWidth(80)
        self.case_color_btn.setToolTip(
            "Case plastic color for top/bottom faces.\n"
            "Auto extracts color from cover edges."
        )
        self.case_color_btn.clicked.connect(self._pick_case_color)
        case_color_row.addWidget(self.case_color_btn)
        case_color_row.addStretch()
        left_layout.addLayout(case_color_row)

        # Spine boundary adjustment (hidden until full cover detected)
        self._build_spine_adjustment(left_layout)

        # Generate / Export buttons
        action_row = QHBoxLayout()
        # Kept on self so _apply_themed_styles can restyle it: as a local it
        # was unreachable and kept the previous theme's colours after a switch.
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setStyleSheet(themed_generate_btn_style())
        self.generate_btn.clicked.connect(self._generate)
        action_row.addWidget(self.generate_btn)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_png)
        action_row.addWidget(export_btn)
        left_layout.addLayout(action_row)

        batch_btn = QPushButton("Batch...")
        batch_btn.clicked.connect(self._batch_process)
        left_layout.addWidget(batch_btn)

        left_layout.addStretch()
        return left

    def _build_spine_adjustment(self, parent_layout: QVBoxLayout) -> None:
        """Build the spine boundary adjustment panel."""
        self.spine_adjust_group = QGroupBox("Spine Boundary Adjustment")
        adj_layout = QVBoxLayout()

        self.spine_status_label = QLabel("No full cover loaded")
        adj_layout.addWidget(self.spine_status_label)

        # Left boundary slider (start of spine)
        left_row = QHBoxLayout()
        left_row.addWidget(QLabel("Left:"))
        self.spine_left_slider = QSlider(Qt.Orientation.Horizontal)
        self.spine_left_slider.setRange(-80, 80)
        self.spine_left_slider.setValue(0)
        self.spine_left_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.spine_left_slider.setTickInterval(10)
        self.spine_left_slider.setToolTip(
            "Adjust the left edge of the spine.\n"
            "Positive (+) moves it right (wider spine, narrower back).\n"
            "Negative (-) moves it left (narrower spine, wider back)."
        )
        left_row.addWidget(self.spine_left_slider)
        self.spine_left_label = QLabel("0 px")
        self.spine_left_label.setFixedWidth(50)
        left_row.addWidget(self.spine_left_label)
        adj_layout.addLayout(left_row)

        # Right boundary slider (end of spine)
        right_row = QHBoxLayout()
        right_row.addWidget(QLabel("Right:"))
        self.spine_right_slider = QSlider(Qt.Orientation.Horizontal)
        self.spine_right_slider.setRange(-80, 80)
        self.spine_right_slider.setValue(0)
        self.spine_right_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.spine_right_slider.setTickInterval(10)
        self.spine_right_slider.setToolTip(
            "Adjust the right edge of the spine.\n"
            "Positive (+) moves it right (narrower spine, wider front).\n"
            "Negative (-) moves it left (wider spine, narrower front)."
        )
        right_row.addWidget(self.spine_right_slider)
        self.spine_right_label = QLabel("0 px")
        self.spine_right_label.setFixedWidth(50)
        right_row.addWidget(self.spine_right_label)
        adj_layout.addLayout(right_row)

        # Reset button
        reset_row = QHBoxLayout()
        reset_btn = QPushButton("Reset to Auto")
        reset_btn.setFixedWidth(100)
        reset_btn.clicked.connect(self._reset_spine_offset)
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        adj_layout.addLayout(reset_row)

        # Split preview: 3 thumbnails side by side
        preview_row = QHBoxLayout()
        self.split_back_thumb = QLabel("Back")
        self.split_back_thumb.setFixedSize(70, 90)
        self.split_back_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.split_back_thumb.setStyleSheet(themed_split_thumb_style())
        preview_row.addWidget(self.split_back_thumb)

        self.split_spine_thumb = QLabel("Spine")
        self.split_spine_thumb.setFixedSize(20, 90)
        self.split_spine_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.split_spine_thumb.setStyleSheet(themed_split_thumb_style(is_spine=True))
        preview_row.addWidget(self.split_spine_thumb)

        self.split_front_thumb = QLabel("Front")
        self.split_front_thumb.setFixedSize(70, 90)
        self.split_front_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.split_front_thumb.setStyleSheet(themed_split_thumb_style())
        preview_row.addWidget(self.split_front_thumb)

        preview_row.addStretch()
        adj_layout.addLayout(preview_row)

        self.spine_adjust_group.setLayout(adj_layout)
        self.spine_adjust_group.hide()
        parent_layout.addWidget(self.spine_adjust_group)

        # Connect sliders
        self.spine_left_slider.valueChanged.connect(self._on_spine_left_changed)
        self.spine_right_slider.valueChanged.connect(self._on_spine_right_changed)

    def _build_right_panel(self) -> QWidget:
        """Build the right preview and controls panel."""
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget: page 0 = single preview, page 1 = comparison
        self.preview_stack = QStackedWidget()

        # Page 0: single preview
        self.preview = PreviewWidget()
        self.preview_stack.addWidget(self.preview)

        # Page 1: side-by-side comparison
        compare_widget = QWidget()
        compare_layout = QVBoxLayout(compare_widget)
        compare_layout.setContentsMargins(0, 0, 0, 0)

        compare_labels = QHBoxLayout()
        self.compare_orig_label = QLabel("Original")
        self.compare_orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compare_orig_label.setStyleSheet(themed_secondary_text_style())
        compare_labels.addWidget(self.compare_orig_label)
        self.compare_render_label = QLabel("3D Render")
        self.compare_render_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.compare_render_label.setStyleSheet(themed_secondary_text_style())
        compare_labels.addWidget(self.compare_render_label)
        compare_layout.addLayout(compare_labels)

        compare_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.compare_original = PreviewWidget()
        self.compare_render = PreviewWidget()
        compare_splitter.addWidget(self.compare_original)
        compare_splitter.addWidget(self.compare_render)
        compare_splitter.setSizes([300, 300])
        compare_layout.addWidget(compare_splitter, 1)

        self.preview_stack.addWidget(compare_widget)

        # Busy overlay (covers the preview stack)
        self._busy_overlay = BusyOverlay(self.preview_stack)

        right_layout.addWidget(self.preview_stack, 1)

        # Compare toggle
        compare_row = QHBoxLayout()
        self.compare_check = QCheckBox("Compare")
        self.compare_check.setToolTip("Show original cover alongside 3D render (Ctrl+D)")
        self.compare_check.toggled.connect(self._on_compare_toggled)
        compare_row.addWidget(self.compare_check)
        compare_row.addStretch()
        right_layout.addLayout(compare_row)

        # Controls below preview
        controls = QVBoxLayout()

        angle_row = QHBoxLayout()
        angle_row.addWidget(QLabel("Angle:"))
        self.angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.angle_slider.setRange(5, 60)
        self.angle_slider.setValue(30)
        self.angle_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.angle_slider.setTickInterval(5)
        angle_row.addWidget(self.angle_slider)
        self.angle_label = QLabel("30\u00b0")
        self.angle_label.setFixedWidth(40)
        self.angle_slider.valueChanged.connect(
            lambda v: self.angle_label.setText(f"{v}\u00b0")
        )
        angle_row.addWidget(self.angle_label)
        controls.addLayout(angle_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Output Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(128, 8192)
        self.width_spin.setValue(512)
        self.width_spin.setSuffix(" px")
        size_row.addWidget(self.width_spin)
        size_row.addStretch()
        controls.addLayout(size_row)

        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("Background:"))
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Transparent", "White", "Black"])
        bg_row.addWidget(self.bg_combo)
        bg_row.addStretch()
        controls.addLayout(bg_row)

        checks_row = QHBoxLayout()
        self.reflection_check = QCheckBox("Reflection")
        self.reflection_check.setChecked(True)
        checks_row.addWidget(self.reflection_check)
        self.shadow_check = QCheckBox("Shadow")
        self.shadow_check.setChecked(True)
        checks_row.addWidget(self.shadow_check)
        self.texture_check = QCheckBox("Case Texture")
        self.texture_check.setChecked(True)
        self.texture_check.setToolTip("Subtle embossed case details (ridges, indents)")
        checks_row.addWidget(self.texture_check)
        checks_row.addStretch()
        controls.addLayout(checks_row)

        self.auto_filename_check = QCheckBox("Auto Filename")
        self.auto_filename_check.setToolTip(
            "Auto-generate export filename from the source image's folder name"
        )
        controls.addWidget(self.auto_filename_check)

        export_row = QHBoxLayout()
        export_png_btn = QPushButton("Export PNG")
        export_png_btn.clicked.connect(self._export_png)
        export_row.addWidget(export_png_btn)
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        export_row.addWidget(copy_btn)
        self.export_split_btn = QPushButton("Export Split Covers")
        self.export_split_btn.setToolTip(
            "Export back, spine and front as separate PNG files"
        )
        self.export_split_btn.clicked.connect(self._export_split_covers)
        self.export_split_btn.setEnabled(False)
        export_row.addWidget(self.export_split_btn)
        controls.addLayout(export_row)

        right_layout.addLayout(controls)
        return right

    def _build_statusbar(self) -> None:
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def _cfg(self, section: str, key: str, default, kind):
        """Read a config value, falling back to `default` on a bad type.

        A hand-edited config could otherwise put a string or null straight
        into a Qt setter and raise inside __init__ -- before show(), so the
        app would not start and the only route back was deleting the file.
        """
        try:
            value = self.config.get(section, key, default=default)
            return kind(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def _restore_state(self) -> None:
        """Restore saved UI state from config."""
        platform = self.config.get("ui", "last_platform", default="PS2")
        idx = self.platform_combo.findText(platform)
        if idx >= 0:
            self.platform_combo.setCurrentIndex(idx)

        case_type = self.config.get("ui", "last_case_type", default="DVD Case")
        idx = self.case_combo.findText(case_type)
        if idx >= 0:
            self.case_combo.setCurrentIndex(idx)

        self.angle_slider.setValue(self._cfg("rendering", "angle", 30, int))
        self.width_spin.setValue(self._cfg("rendering", "output_width", 512, int))
        self.reflection_check.setChecked(self._cfg("rendering", "reflection", True, bool))
        self.shadow_check.setChecked(self._cfg("rendering", "shadow", True, bool))
        self.texture_check.setChecked(self._cfg("rendering", "texture", True, bool))
        self.auto_filename_check.setChecked(self._cfg("ui", "auto_filename", False, bool))

        bg = self._cfg("rendering", "background", "transparent", str)
        bg_idx = self.bg_combo.findText(bg.capitalize())
        if bg_idx >= 0:
            self.bg_combo.setCurrentIndex(bg_idx)

        # Restore window position and size
        geo = self.config.get("ui", "window_geometry")
        if (
            isinstance(geo, list) and len(geo) == 4
            and all(isinstance(v, int) for v in geo)
            and geo[2] > 0 and geo[3] > 0
        ):
            self.setGeometry(geo[0], geo[1], geo[2], geo[3])

    def _save_config(self) -> None:
        """Persist config, reporting a write failure instead of aborting.

        Config.save() raises OSError on a full disk, a read-only home, or a
        config that failed to load. An unhandled exception in a Qt slot is
        fatal, so every call site goes through here.
        """
        try:
            self.config.save()
        except OSError as e:
            self.status.showMessage(f"Could not save settings: {e}")

    def _save_state(self) -> None:
        """Save current UI state to config."""
        self.config.set("ui", "last_platform", self.platform_combo.currentText())
        self.config.set("ui", "last_case_type", self.case_combo.currentText())
        self.config.set("rendering", "angle", self.angle_slider.value())
        self.config.set("rendering", "output_width", self.width_spin.value())
        self.config.set("rendering", "reflection", self.reflection_check.isChecked())
        self.config.set("rendering", "shadow", self.shadow_check.isChecked())
        self.config.set("rendering", "texture", self.texture_check.isChecked())
        self.config.set("rendering", "background", self.bg_combo.currentText().lower())
        self.config.set("ui", "auto_filename", self.auto_filename_check.isChecked())
        geo = self.geometry()
        self.config.set("ui", "window_geometry", [geo.x(), geo.y(), geo.width(), geo.height()])
        self._save_config()

    def _reject_if_busy(self) -> bool:
        """Refuse to start a second worker while one is running.

        Without this, a second Ctrl+G rebinds the worker attribute: the older
        render can land last and overwrite the newer one, and the rebind drops
        the last Python reference to a live QThread.
        """
        if self._busy_worker() is not None:
            self.status.showMessage("Already working — wait for the current job to finish")
            return True
        return False

    def _busy_worker(self):
        """Return a running worker, or None. Tolerates a deleted C++ object."""
        for attr in ("_render_worker", "_batch_worker", "_anim_worker"):
            worker = getattr(self, attr, None)
            if worker is None:
                continue
            try:
                if worker.isRunning():
                    return worker
            except RuntimeError:
                pass  # C++ object already deleted by deleteLater
        return None

    def closeEvent(self, event) -> None:
        self._save_state()
        # Ask every running worker to stop and wait for it.
        #
        # quit() is NOT usable here: all three workers override run() without
        # calling exec(), so they have no event loop for quit() to reach and
        # wait() would simply time out. requestInterruption() sets a flag the
        # run() loops check.
        #
        # The reference is deliberately NOT cleared while a thread is still
        # running: dropping the last Python reference to a parentless live
        # QThread destroys the C++ object mid-run, which aborts the process.
        for attr in ("_render_worker", "_batch_worker", "_anim_worker"):
            worker = getattr(self, attr, None)
            if worker is None:
                continue
            try:
                if worker.isRunning():
                    worker.requestInterruption()
                    worker.quit()  # harmless, and correct for any future
                    if not worker.wait(5000):
                        continue  # still running: keep the reference alive
                setattr(self, attr, None)
            except RuntimeError:
                setattr(self, attr, None)  # already deleted by deleteLater
        # Release image references
        self._front_image = None
        self._front_image_path = None
        self._back_image = None
        self.preview.clear_image()
        self.compare_original.clear_image()
        self.compare_render.clear_image()
        super().closeEvent(event)

    # --- Platform / Case ---

    def _on_platform_changed(self, platform: str) -> None:
        """Update case type when platform changes."""
        case_name = PLATFORM_CASE_MAP.get(platform)
        if case_name:
            idx = self.case_combo.findText(case_name)
            if idx >= 0:
                self.case_combo.setCurrentIndex(idx)

    # --- Image loading ---

    def _load_image_dialog(
        self, title: str = "Open Image"
    ) -> tuple[Image.Image | None, str | None]:
        last_dir = self.config.get("ui", "last_image_directory", default="")
        path, _ = QFileDialog.getOpenFileName(
            self, title, last_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff);;All Files (*)",
        )
        if path:
            self.config.set("ui", "last_image_directory", str(Path(path).parent))
            self._save_config()
            try:
                img = Image.open(path)
                img.load()  # Read into memory, release file handle
                return img, path
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load image:\n{e}")
        return None, None

    def _set_thumbnail(self, label: QLabel, image: Image.Image) -> None:
        pm = pil_to_qpixmap(image)
        scaled = pm.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)

    def _load_front(self) -> None:
        img, path = self._load_image_dialog("Open Cover Image")
        if img:
            self._front_image_path = path
            self._set_front_image(img)
            if path:
                self._add_to_recent(path)
                # Auto-populate title from parent folder name (preferred) or filename
                if not self.title_input.text().strip():
                    folder_name = Path(path).parent.name
                    file_stem = Path(path).stem
                    self.title_input.setText(folder_name if folder_name else file_stem)

    def _set_front_image(self, img: Image.Image) -> None:
        """Set the front cover image and update UI state."""
        self._front_image = img
        self._set_thumbnail(self.front_thumb, img)
        self.compare_original.set_image(img)
        case_name = self.case_combo.currentText()
        case_type = CASE_TYPES[case_name]
        if is_full_cover(img, case_type):
            self.status.showMessage(
                "Full cover detected (back + spine + front) — spine will be extracted"
            )
            max_offset = max(40, min(150, int(img.size[0] * 0.03)))
            self.spine_left_slider.setRange(-max_offset, max_offset)
            self.spine_left_slider.setValue(0)
            self.spine_right_slider.setRange(-max_offset, max_offset)
            self.spine_right_slider.setValue(0)
            self._show_spine_adjustment()
            self.export_split_btn.setEnabled(True)
        else:
            self.status.showMessage("Front cover loaded")
            self._hide_spine_adjustment()
            self.export_split_btn.setEnabled(False)

    def _clear_front(self) -> None:
        self._front_image = None
        self._front_image_path = None
        self.front_thumb.setPixmap(QPixmap())
        self.front_thumb.setText("No image loaded")
        self._hide_spine_adjustment()
        self.export_split_btn.setEnabled(False)

    def _load_back(self) -> None:
        img, _ = self._load_image_dialog("Open Back Cover")
        if img:
            self._back_image = img
            self._set_thumbnail(self.back_thumb, img)
            self.status.showMessage("Back cover loaded")

    def _clear_back(self) -> None:
        self._back_image = None
        self.back_thumb.setPixmap(QPixmap())
        self.back_thumb.setText("No image")

    def _pick_spine_color(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._spine_color = (color.red(), color.green(), color.blue())
            self.color_btn.setText("")
            self.color_btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #888;"
            )
        else:
            self._spine_color = None
            self.color_btn.setText("Auto")
            self.color_btn.setStyleSheet("")

    def _pick_case_color(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._case_color = (color.red(), color.green(), color.blue())
            self.case_color_btn.setText("")
            self.case_color_btn.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #888;"
            )
        else:
            self._case_color = None
            self.case_color_btn.setText("Auto")
            self.case_color_btn.setStyleSheet("")

    # --- Spine adjustment ---

    def _update_split_preview(self) -> None:
        """Update the three-panel split preview thumbnails."""
        if self._front_image is None:
            return
        case_name = self.case_combo.currentText()
        case_type = CASE_TYPES[case_name]
        if not is_full_cover(self._front_image, case_type):
            return

        left_off = self.spine_left_slider.value()
        right_off = self.spine_right_slider.value()
        try:
            back, spine, front = split_full_cover(
                self._front_image, case_type,
                left_offset=left_off, right_offset=right_off,
            )
            # Update thumbnails
            self._set_thumbnail(self.split_back_thumb, back)
            self._set_thumbnail(self.split_spine_thumb, spine)
            self._set_thumbnail(self.split_front_thumb, front)
        except Exception as e:
            self.status.showMessage(f"Spine split preview failed: {e}")

    def _on_spine_left_changed(self, value: int) -> None:
        self.spine_left_label.setText(f"{value:+d} px")
        self._update_split_preview()

    def _on_spine_right_changed(self, value: int) -> None:
        self.spine_right_label.setText(f"{value:+d} px")
        self._update_split_preview()

    def _reset_spine_offset(self) -> None:
        self.spine_left_slider.setValue(0)
        self.spine_right_slider.setValue(0)

    def _show_spine_adjustment(self) -> None:
        """Show the spine adjustment panel and populate the preview."""
        self.spine_status_label.setText("Full cover detected — adjust if needed")
        self.spine_adjust_group.show()
        self._update_split_preview()

    def _hide_spine_adjustment(self) -> None:
        """Hide the spine adjustment panel."""
        self.spine_adjust_group.hide()
        self.spine_left_slider.setValue(0)
        self.spine_right_slider.setValue(0)

    # --- Rendering ---

    def _supersample(self) -> int:
        """Supersample factor from config, clamped to a sane range.

        STANDARDS.md § 7 documents this key, so it has to be read somewhere;
        it was previously hardcoded at every call site.
        """
        try:
            return max(1, min(4, int(self.config.get("rendering", "supersample", default=2))))
        except (TypeError, ValueError):
            return 2

    def _compress_level(self) -> int:
        """PNG zlib level from config, clamped to 0-9."""
        try:
            return max(0, min(9, int(
                self.config.get("rendering", "compress_level", default=6)
            )))
        except (TypeError, ValueError):
            return 6

    def _get_renderer(self) -> BoxRenderer:
        case_name = self.case_combo.currentText()
        case_type = CASE_TYPES[case_name]
        return BoxRenderer(
            case_type=case_type,
            angle=self.angle_slider.value(),
            output_width=self.width_spin.value(),
            show_reflection=self.reflection_check.isChecked(),
            show_shadow=self.shadow_check.isChecked(),
            show_texture=self.texture_check.isChecked(),
            supersample=self._supersample(),
            background=self.bg_combo.currentText().lower(),
        )

    def _generate(self) -> None:
        if self._front_image is None:
            QMessageBox.information(self, "No Image", "Please load a front cover image first.")
            return
        if self._reject_if_busy():
            return

        self.status.showMessage("Rendering...")
        self._busy_overlay.resize(self.preview_stack.size())
        self._busy_overlay.show_busy()
        renderer = self._get_renderer()

        self._render_worker = RenderWorker(
            renderer=renderer,
            front=self._front_image,
            back=self._back_image,
            title=self.title_input.text() or "Game",
            serial=self.serial_input.text(),
            platform=self.platform_combo.currentText(),
            spine_color=self._spine_color,
            case_color=self._case_color,
            spine_left_offset=self.spine_left_slider.value(),
            spine_right_offset=self.spine_right_slider.value(),
        )
        self._render_worker.rendered.connect(self._on_rendered)
        self._render_worker.error.connect(self._on_render_error)
        self._render_worker.finished.connect(self._render_worker.deleteLater)
        self._render_worker.start()

    def _on_rendered(self, image: Image.Image) -> None:
        self._busy_overlay.hide_busy()
        self.preview.set_image(image)
        self.compare_render.set_image(image)
        self.status.showMessage(f"Rendered: {image.size[0]}x{image.size[1]}")

    def _on_render_error(self, msg: str) -> None:
        self._busy_overlay.hide_busy()
        self.status.showMessage(f"Render error: {msg}")
        QMessageBox.warning(self, "Render Error", msg)

    # --- Export ---

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Reduce a title to a single safe path component.

        The title can come from a cover-art API (see _on_search_images), so it
        is untrusted: a name containing '../..' would otherwise escape the
        directory the user chose, and a '/' would raise out of a Qt slot.
        """
        cleaned = re.sub(r"[^\w \-.()\[\]]", "_", name).strip(" .")
        return cleaned[:120] or "Untitled"

    def _export_png(self) -> None:
        image = self.preview.get_rendered_image()
        if image is None:
            QMessageBox.information(self, "No Render", "Generate a render first.")
            return

        # Prefer source file's directory, then last export dir, then last import dir
        if self._front_image_path:
            default_dir = str(Path(self._front_image_path).parent)
        else:
            default_dir = self.config.get(
                "ui", "last_export_directory",
                default=self.config.get("ui", "last_image_directory", default=""),
            )

        # Always suggest a filename — Auto Filename controls using folder name
        if self.auto_filename_check.isChecked() and self._front_image_path:
            name = Path(self._front_image_path).parent.name
        elif self.title_input.text().strip():
            name = self.title_input.text().strip()
        elif self._front_image_path:
            name = Path(self._front_image_path).stem
        else:
            name = "Untitled"
        suggested = str(Path(default_dir) / f"{self._safe_filename(name)} 3D Boxart.png")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PNG", suggested, "PNG Images (*.png)"
        )
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            try:
                save_optimized_png(image, path, compress_level=self._compress_level())
            except OSError as e:
                QMessageBox.warning(self, "Export Failed", f"Could not write the PNG:\n{e}")
                return
            self.config.set("ui", "last_export_directory", str(Path(path).parent))
            self._save_config()
            self.status.showMessage(f"Exported: {path}")

    def _export_split_covers(self) -> None:
        if self._front_image is None:
            return
        case_name = self.case_combo.currentText()
        case_type = CASE_TYPES[case_name]
        if not is_full_cover(self._front_image, case_type):
            QMessageBox.information(self, "Not a Full Cover",
                                    "The loaded image is not a full cover.")
            return

        if self._front_image_path:
            default_dir = str(Path(self._front_image_path).parent)
        else:
            default_dir = self.config.get(
                "ui", "last_export_directory",
                default=self.config.get("ui", "last_image_directory", default=""),
            )
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", default_dir)
        if not output_dir:
            return

        left_off = self.spine_left_slider.value()
        right_off = self.spine_right_slider.value()
        back, spine, front = split_full_cover(
            self._front_image, case_type,
            left_offset=left_off, right_offset=right_off,
        )

        if self.auto_filename_check.isChecked() and self._front_image_path:
            base = Path(self._front_image_path).parent.name
        elif self.title_input.text().strip():
            base = self.title_input.text().strip()
        elif self._front_image_path:
            base = Path(self._front_image_path).stem
        else:
            base = "cover"

        safe_base = self._safe_filename(base)
        try:
            for part, suffix in [
                (back, "Back Cover"), (spine, "Spine"), (front, "Front Cover"),
            ]:
                out_path = str(Path(output_dir) / f"{safe_base} {suffix}.png")
                save_optimized_png(part, out_path, compress_level=self._compress_level())
        except OSError as e:
            del back, spine, front
            QMessageBox.warning(self, "Export Failed", f"Could not write the covers:\n{e}")
            return
        del back, spine, front
        self.config.set("ui", "last_export_directory", output_dir)
        self._save_config()
        self.status.showMessage(f"Exported split covers to: {output_dir}")

    def _copy_to_clipboard(self) -> None:
        image = self.preview.get_rendered_image()
        if image is None:
            QMessageBox.information(self, "No Render", "Generate a render first.")
            return

        img = image.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888)
        # .copy() is required: QImage's raw-data constructor does not copy,
        # so the clipboard would be left pointing at `data`, a local bytes
        # object freed on return.
        QApplication.clipboard().setImage(qimg.copy())
        self.status.showMessage("Copied to clipboard")

    # --- Batch processing ---

    def _batch_process(self) -> None:
        if self._reject_if_busy():
            return
        last_dir = self.config.get("ui", "last_image_directory", default="")
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Cover Images", last_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if not files:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        renderer = self._get_renderer()
        self.progress_bar.show()
        self.progress_bar.setMaximum(len(files))
        self.progress_bar.setValue(0)

        # Collect failures rather than showing them: the status bar is
        # overwritten by the very next progress message, so a batch where
        # every file failed reported "Processed 0 images." with no cause.
        self._batch_errors: list[str] = []
        self._batch_total = len(files)

        self._batch_worker = BatchWorker(files, output_dir, renderer)
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.finished_signal.connect(self._on_batch_done)
        self._batch_worker.error.connect(self._on_batch_error)
        self._batch_worker.finished.connect(self._batch_worker.deleteLater)
        self._batch_worker.start()

    def _on_batch_progress(self, current: int, total: int, name: str) -> None:
        self.progress_bar.setValue(current)
        self.status.showMessage(f"Processing {current}/{total}: {name}")

    def _on_batch_error(self, msg: str) -> None:
        self._batch_errors.append(msg)

    def _on_batch_done(self, count: int) -> None:
        self.progress_bar.hide()
        errors = getattr(self, "_batch_errors", [])
        total = getattr(self, "_batch_total", count)
        if errors:
            self.status.showMessage(
                f"Batch complete: {count} of {total} rendered, {len(errors)} failed"
            )
            shown = "\n".join(errors[:10])
            if len(errors) > 10:
                shown += f"\n... and {len(errors) - 10} more"
            QMessageBox.warning(
                self, "Batch Finished With Errors",
                f"Processed {count} of {total} images.\n\n{len(errors)} failed:\n{shown}",
            )
        else:
            self.status.showMessage(f"Batch complete: {count} images rendered")
            QMessageBox.information(self, "Batch Complete", f"Processed {count} images.")

    # --- Online search ---

    def _search_online(self) -> None:
        platform = self.platform_combo.currentText()
        dialog = SearchDialog(self.config, platform=platform, parent=self)
        dialog.images_selected.connect(self._on_search_images)
        dialog.boxart3d_selected.connect(self._on_search_3d_boxart)
        dialog.exec()

    def _on_search_images(self, front, back, name: str) -> None:
        if front:
            self._front_image_path = None
            self._set_front_image(front)
        if back:
            self._back_image = back
            self._set_thumbnail(self.back_thumb, back)
        if name:
            self.title_input.setText(name)
        self.status.showMessage(f"Downloaded: {name}")

    def _on_search_3d_boxart(self, image, name: str) -> None:
        """Handle pre-rendered 3D boxart from ScreenScraper — show directly in preview."""
        self.preview.set_image(image)
        if name:
            self.title_input.setText(name)
        self.status.showMessage(f"3D boxart loaded: {name}")

    # --- Comparison view ---

    def _on_compare_toggled(self, checked: bool) -> None:
        self.preview_stack.setCurrentIndex(1 if checked else 0)

    def _toggle_compare(self) -> None:
        self.compare_check.setChecked(not self.compare_check.isChecked())

    # --- Animation export ---

    def _export_animation(self) -> None:
        if self._front_image is None:
            QMessageBox.information(self, "No Image", "Please load a front cover image first.")
            return
        if self._reject_if_busy():
            return

        dialog = AnimationDialog(current_width=self.width_spin.value(), parent=self)
        if dialog.exec() != AnimationDialog.DialogCode.Accepted:
            return
        params = dialog.get_params()

        fmt = params["fmt"]
        ext = ".gif" if fmt == "GIF" else ".png"
        last_dir = self.config.get("ui", "last_image_directory", default="")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Animation", last_dir,
            f"{fmt} Files (*{ext})",
        )
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext

        case_name = self.case_combo.currentText()
        case_type = CASE_TYPES[case_name]

        self.progress_bar.show()
        total = params["frame_count"]
        if params["bounce"] and total > 2:
            total = total * 2 - 2
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.status.showMessage("Rendering animation...")

        self._anim_worker = AnimationWorker(
            case_type=case_type,
            front_image=self._front_image,
            back_image=self._back_image,
            title=self.title_input.text() or "Game",
            serial=self.serial_input.text(),
            platform=self.platform_combo.currentText(),
            spine_color=self._spine_color,
            case_color=self._case_color,
            spine_left_offset=self.spine_left_slider.value(),
            spine_right_offset=self.spine_right_slider.value(),
            output_path=path,
            output_width=params["output_width"],
            start_angle=params["start_angle"],
            end_angle=params["end_angle"],
            frame_count=params["frame_count"],
            frame_delay=params["frame_delay"],
            bounce=params["bounce"],
            fmt=fmt,
            show_reflection=self.reflection_check.isChecked(),
            show_shadow=self.shadow_check.isChecked(),
            show_texture=self.texture_check.isChecked(),
            supersample=self._supersample(),
            background=self.bg_combo.currentText().lower(),
        )
        self._anim_worker.progress.connect(self._on_anim_progress)
        self._anim_worker.finished_signal.connect(self._on_anim_done)
        self._anim_worker.error.connect(self._on_anim_error)
        self._anim_worker.finished.connect(self._anim_worker.deleteLater)
        self._anim_worker.start()

    def _on_anim_progress(self, current: int, total: int) -> None:
        self.progress_bar.setValue(current)
        self.status.showMessage(f"Rendering frame {current}/{total}...")

    def _on_anim_done(self, path: str) -> None:
        self.progress_bar.hide()
        self.status.showMessage(f"Animation exported: {path}")
        QMessageBox.information(self, "Animation Exported", f"Saved to:\n{path}")

    def _on_anim_error(self, msg: str) -> None:
        self.progress_bar.hide()
        self.status.showMessage(f"Animation error: {msg}")
        QMessageBox.warning(self, "Animation Error", msg)

    # --- Recent files ---

    def _add_to_recent(self, path: str) -> None:
        """Add a file path to the recent files list."""
        recent = self.config.get("ui", "recent_files", default=[])
        if not isinstance(recent, list):
            recent = []
        # Remove if already present (move to top)
        path = str(Path(path).resolve())
        recent = [p for p in recent if p != path]
        recent.insert(0, path)
        recent = recent[:10]
        self.config.set("ui", "recent_files", recent)
        self._save_config()
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        """Rebuild the recent files submenu."""
        self.recent_menu.clear()
        recent = self.config.get("ui", "recent_files", default=[])
        if not isinstance(recent, list):
            recent = []

        if not recent:
            empty = self.recent_menu.addAction("(empty)")
            empty.setEnabled(False)
            return

        for i, path in enumerate(recent):
            name = Path(path).name
            action = self.recent_menu.addAction(f"&{i + 1}  {name}")
            action.setToolTip(path)
            action.triggered.connect(partial(self._open_recent, path))

        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self._clear_recent)

    def _open_recent(self, path: str) -> None:
        """Open a file from the recent files list."""
        p = Path(path)
        if not p.exists():
            QMessageBox.warning(self, "File Not Found", f"File no longer exists:\n{path}")
            recent = self.config.get("ui", "recent_files", default=[])
            if isinstance(recent, list):
                recent = [r for r in recent if r != path]
                self.config.set("ui", "recent_files", recent)
                self._save_config()
                self._rebuild_recent_menu()
            return

        try:
            img = Image.open(path)
            img.load()  # Read into memory, release file handle
            self._front_image_path = path
            self._set_front_image(img)
            self._add_to_recent(path)
            self.config.set("ui", "last_image_directory", str(p.parent))
            self._save_config()
            # Auto-populate title from parent folder name or filename
            if not self.title_input.text().strip():
                folder_name = p.parent.name
                self.title_input.setText(folder_name if folder_name else p.stem)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load image:\n{e}")

    def _clear_recent(self) -> None:
        """Clear the recent files list."""
        self.config.set("ui", "recent_files", [])
        self._save_config()
        self._rebuild_recent_menu()

    # --- Theme ---

    def _change_theme(self, name: str) -> None:
        """Switch the application theme."""
        theme = set_active_theme(name)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(generate_stylesheet(theme))
        # Re-apply inline themed styles
        self._apply_themed_styles()
        self.config.set("ui", "theme", name)
        self._save_config()
        self._update_theme_checks()

    def _update_theme_checks(self) -> None:
        """Update checkmarks on the theme menu."""
        current = get_active_theme().name
        for name, action in self._theme_actions.items():
            action.setChecked(name == current)

    def _apply_themed_styles(self) -> None:
        """Re-apply all inline themed styles after a theme change."""
        thumb_style = themed_thumbnail_style()
        self.front_thumb.setStyleSheet(thumb_style)
        self.back_thumb.setStyleSheet(thumb_style)
        self.split_back_thumb.setStyleSheet(themed_split_thumb_style())
        self.split_spine_thumb.setStyleSheet(themed_split_thumb_style(is_spine=True))
        self.split_front_thumb.setStyleSheet(themed_split_thumb_style())
        self.preview.setStyleSheet(themed_preview_style())
        self.compare_original.setStyleSheet(themed_preview_style())
        self.compare_render.setStyleSheet(themed_preview_style())
        self.generate_btn.setStyleSheet(themed_generate_btn_style())
        self.compare_orig_label.setStyleSheet(themed_secondary_text_style())
        self.compare_render_label.setStyleSheet(themed_secondary_text_style())

    # --- Dialogs ---

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, parent=self)
        dialog.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Slipcase",
            f"Slipcase v{__version__}\n\n"
            "Convert 2D game cover art into realistic 3D boxart renders.\n"
            "Compatible with RetroArch and LaunchBox.",
        )
