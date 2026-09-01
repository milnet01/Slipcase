"""Theme definitions and stylesheet generation for the application."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A complete colour theme for the application."""
    name: str
    # Backgrounds (darkest to lightest)
    bg_darkest: str    # Main window background
    bg_dark: str       # Input fields, menus, secondary panels
    bg_mid: str        # Buttons, interactive elements
    bg_light: str      # Hover states
    bg_pressed: str    # Pressed/active states
    bg_preview: str    # Preview area background
    # Borders
    border: str        # Standard border
    border_accent: str # Highlighted border (e.g., spine preview)
    # Text
    text_primary: str  # Main text
    text_secondary: str  # Labels, secondary
    text_dim: str      # Disabled, hints
    # Accent
    accent: str        # Primary accent (selection, progress, handles)
    accent_dark: str   # Status bar, darker variant
    accent_hover: str  # Accent hover
    accent_text: str   # Text on accent background


# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

THEMES: dict[str, Theme] = {}


def _register(theme: Theme) -> Theme:
    THEMES[theme.name] = theme
    return theme


_register(Theme(
    name="Midnight Blue",
    bg_darkest="#0d1117",
    bg_dark="#161b22",
    bg_mid="#21262d",
    bg_light="#30363d",
    bg_pressed="#0d1117",
    bg_preview="#0d1117",
    border="#30363d",
    border_accent="#1f6feb",
    text_primary="#e6edf3",
    text_secondary="#b1bac4",
    text_dim="#6e7681",
    accent="#58a6ff",
    accent_dark="#1158c7",
    accent_hover="#79c0ff",
    accent_text="#ffffff",
))

_register(Theme(
    name="Emerald",
    bg_darkest="#0a1210",
    bg_dark="#111d19",
    bg_mid="#1a2922",
    bg_light="#24362d",
    bg_pressed="#0a1210",
    bg_preview="#0a1210",
    border="#2a3f35",
    border_accent="#2ea043",
    text_primary="#e0f0e8",
    text_secondary="#a8c8b8",
    text_dim="#5e7e6e",
    accent="#3fb950",
    accent_dark="#1a7f37",
    accent_hover="#56d364",
    accent_text="#ffffff",
))

_register(Theme(
    name="Crimson",
    bg_darkest="#140a0a",
    bg_dark="#1e1214",
    bg_mid="#2a1a1d",
    bg_light="#3a2428",
    bg_pressed="#140a0a",
    bg_preview="#140a0a",
    border="#3f2a2e",
    border_accent="#da3633",
    text_primary="#f0e0e0",
    text_secondary="#c8a8a8",
    text_dim="#7e5e5e",
    accent="#f85149",
    accent_dark="#b62324",
    accent_hover="#ff7b72",
    accent_text="#ffffff",
))

_register(Theme(
    name="Amethyst",
    bg_darkest="#100a18",
    bg_dark="#181220",
    bg_mid="#221a2e",
    bg_light="#302440",
    bg_pressed="#100a18",
    bg_preview="#100a18",
    border="#362a48",
    border_accent="#8b5cf6",
    text_primary="#e8e0f4",
    text_secondary="#b8a8d0",
    text_dim="#6e5e88",
    accent="#a78bfa",
    accent_dark="#6d28d9",
    accent_hover="#c4b5fd",
    accent_text="#ffffff",
))

_register(Theme(
    name="Nord",
    bg_darkest="#2e3440",
    bg_dark="#3b4252",
    bg_mid="#434c5e",
    bg_light="#4c566a",
    bg_pressed="#2e3440",
    bg_preview="#2e3440",
    border="#4c566a",
    border_accent="#81a1c1",
    text_primary="#eceff4",
    text_secondary="#d8dee9",
    text_dim="#7b88a1",
    accent="#88c0d0",
    accent_dark="#5e81ac",
    accent_hover="#8fbcbb",
    accent_text="#2e3440",
))

_register(Theme(
    name="Monokai",
    bg_darkest="#1a1a1a",
    bg_dark="#272822",
    bg_mid="#3e3d32",
    bg_light="#49483e",
    bg_pressed="#1a1a1a",
    bg_preview="#1a1a1a",
    border="#49483e",
    border_accent="#f92672",
    text_primary="#f8f8f2",
    text_secondary="#cfcfc2",
    text_dim="#75715e",
    accent="#a6e22e",
    accent_dark="#629812",
    accent_hover="#c8f76e",
    accent_text="#1a1a1a",
))

_register(Theme(
    name="Sunset",
    bg_darkest="#1a0f0a",
    bg_dark="#241812",
    bg_mid="#30211a",
    bg_light="#3e2c22",
    bg_pressed="#1a0f0a",
    bg_preview="#1a0f0a",
    border="#4a3628",
    border_accent="#e07030",
    text_primary="#f4e8e0",
    text_secondary="#d0b8a4",
    text_dim="#887060",
    accent="#f0903a",
    accent_dark="#c06020",
    accent_hover="#ffa856",
    accent_text="#ffffff",
))

DEFAULT_THEME = "Midnight Blue"

# Module-level active theme (set by apply_theme)
_active_theme: Theme = THEMES[DEFAULT_THEME]


def get_active_theme() -> Theme:
    """Return the currently active theme."""
    return _active_theme


def set_active_theme(name: str) -> Theme:
    """Set the active theme by name. Returns the theme."""
    global _active_theme
    _active_theme = THEMES.get(name, THEMES[DEFAULT_THEME])
    return _active_theme


def generate_stylesheet(theme: Theme) -> str:
    """Generate a complete QSS stylesheet from a theme."""
    t = theme
    return f"""
        QMainWindow, QDialog {{
            background-color: {t.bg_darkest};
            color: {t.text_primary};
        }}
        QWidget {{
            background-color: {t.bg_darkest};
            color: {t.text_primary};
        }}
        QGroupBox {{
            border: 1px solid {t.border};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
            color: {t.text_primary};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: {t.text_secondary};
        }}
        QPushButton {{
            background-color: {t.bg_mid};
            border: 1px solid {t.border};
            border-radius: 3px;
            padding: 5px 12px;
            color: {t.text_primary};
        }}
        QPushButton:hover {{
            background-color: {t.bg_light};
            border-color: {t.accent};
        }}
        QPushButton:pressed {{
            background-color: {t.bg_pressed};
            border-color: {t.accent};
        }}
        QPushButton:disabled {{
            color: {t.text_dim};
            background-color: {t.bg_dark};
            border-color: {t.border};
        }}
        QLineEdit, QSpinBox, QComboBox {{
            background-color: {t.bg_dark};
            border: 1px solid {t.border};
            border-radius: 3px;
            padding: 3px 6px;
            color: {t.text_primary};
            selection-background-color: {t.accent};
            selection-color: {t.accent_text};
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border-color: {t.accent};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {t.bg_dark};
            color: {t.text_primary};
            selection-background-color: {t.accent};
            selection-color: {t.accent_text};
            border: 1px solid {t.border};
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {t.bg_mid};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {t.accent};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {t.accent_hover};
        }}
        QSlider::sub-page:horizontal {{
            background: {t.accent_dark};
            border-radius: 3px;
        }}
        QCheckBox {{
            spacing: 6px;
            color: {t.text_primary};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {t.border};
            border-radius: 3px;
            background-color: {t.bg_dark};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t.accent};
            border-color: {t.accent};
        }}
        QCheckBox::indicator:hover {{
            border-color: {t.accent_hover};
        }}
        QMenuBar {{
            background-color: {t.bg_dark};
            color: {t.text_primary};
            border-bottom: 1px solid {t.border};
        }}
        QMenuBar::item:selected {{
            background-color: {t.bg_mid};
        }}
        QMenu {{
            background-color: {t.bg_dark};
            color: {t.text_primary};
            border: 1px solid {t.border};
        }}
        QMenu::item:disabled {{
            color: {t.text_dim};
        }}
        QMenu::item:selected {{
            background-color: {t.accent};
            color: {t.accent_text};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t.border};
            margin: 4px 8px;
        }}
        QStatusBar {{
            background-color: {t.accent_dark};
            color: {t.accent_text};
            border-top: 1px solid {t.border};
        }}
        QProgressBar {{
            border: 1px solid {t.border};
            border-radius: 3px;
            text-align: center;
            background-color: {t.bg_dark};
            color: {t.text_primary};
        }}
        QProgressBar::chunk {{
            background-color: {t.accent};
            border-radius: 2px;
        }}
        QSplitter::handle {{
            background-color: {t.border};
        }}
        QSplitter::handle:hover {{
            background-color: {t.accent};
        }}
        QListWidget {{
            background-color: {t.bg_dark};
            border: 1px solid {t.border};
            color: {t.text_primary};
        }}
        QListWidget::item:selected {{
            background-color: {t.accent};
            color: {t.accent_text};
        }}
        QListWidget::item:hover {{
            background-color: {t.bg_mid};
        }}
        QTabWidget::pane {{
            border: 1px solid {t.border};
            background-color: {t.bg_darkest};
        }}
        QTabBar::tab {{
            background-color: {t.bg_dark};
            border: 1px solid {t.border};
            padding: 6px 12px;
            color: {t.text_secondary};
            border-bottom: none;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }}
        QTabBar::tab:selected {{
            background-color: {t.bg_darkest};
            color: {t.text_primary};
            border-bottom: 2px solid {t.accent};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {t.bg_mid};
            color: {t.text_primary};
        }}
        QScrollBar:vertical {{
            background: {t.bg_darkest};
            width: 10px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {t.bg_light};
            min-height: 20px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {t.bg_darkest};
            height: 10px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background: {t.bg_light};
            min-width: 20px;
            border-radius: 4px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {t.accent};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QToolTip {{
            background-color: {t.bg_dark};
            color: {t.text_primary};
            border: 1px solid {t.accent};
            padding: 4px;
        }}
        QDialogButtonBox > QPushButton {{
            min-width: 70px;
        }}
    """


def themed_preview_style() -> str:
    """Return the stylesheet for preview widgets using the active theme."""
    t = _active_theme
    return f"QLabel {{ background-color: {t.bg_preview}; border: 1px solid {t.border}; }}"


def themed_thumbnail_style() -> str:
    """Return the stylesheet for thumbnail labels using the active theme."""
    t = _active_theme
    return f"border: 1px solid {t.border}; background: {t.bg_preview};"


def themed_dim_text_style() -> str:
    """Return the stylesheet for dim info labels using the active theme."""
    t = _active_theme
    return f"color: {t.text_dim};"


def themed_secondary_text_style() -> str:
    """Return the stylesheet for secondary text using the active theme."""
    t = _active_theme
    return f"font-weight: bold; color: {t.text_secondary};"


def themed_split_thumb_style(is_spine: bool = False) -> str:
    """Return the stylesheet for split preview thumbnails."""
    t = _active_theme
    border = t.border_accent if is_spine else t.border
    return (
        f"border: 1px solid {border}; background: {t.bg_preview}; "
        f"font-size: 9px; color: {t.text_dim};"
    )


def themed_generate_btn_style() -> str:
    """Return the stylesheet for the primary Generate button."""
    t = _active_theme
    return (
        f"font-weight: bold; background-color: {t.accent_dark}; "
        f"color: {t.accent_text}; border: 1px solid {t.accent};"
    )
