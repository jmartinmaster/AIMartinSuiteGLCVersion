# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
try:
    from PyQt6.QtGui import QColor, QPalette

    PYQT6_THEME_SUPPORT = True
except ImportError:
    QColor = None
    QPalette = None
    PYQT6_THEME_SUPPORT = False

__module_name__ = "Theme Manager"
__version__ = "1.2.0"

DEFAULT_THEME = "martin_modern_light"

READABLE_THEMES = {
    "martin_modern_light": "Martin Modern Light - industrial",
    "cyber_industrial_dark": "Cyber-Industrial Dark - neon steel",
    "flatly": "Flatly - balanced light",
    "cosmo": "Cosmo - crisp light",
    "lumen": "Lumen - soft light",
    "journal": "Journal - paper light",
    "litera": "Litera - text-forward light",
    "darkly": "Darkly - balanced dark",
    "superhero": "Superhero - high-contrast dark",
}

def get_theme_names():
    return list(READABLE_THEMES.keys())


def get_theme_labels():
    return [READABLE_THEMES[name] for name in get_theme_names()]


def get_theme_label(theme_name):
    return READABLE_THEMES.get(normalize_theme(theme_name), READABLE_THEMES[DEFAULT_THEME])


def normalize_theme(theme_name):
    if theme_name in READABLE_THEMES:
        return theme_name
    for key, label in READABLE_THEMES.items():
        if theme_name == label:
            return key
    return DEFAULT_THEME


def _resolve_theme_token_profile(theme_name):
    normalized = normalize_theme(theme_name)
    if normalized in {"cyber_industrial_dark", "darkly", "superhero"}:
        return "cyber_industrial_dark"
    return "martin_modern_light"


def _build_theme_tokens(theme_name):
    normalized = _resolve_theme_token_profile(theme_name)
    if normalized == "martin_modern_light":
        return {
            "app_bg": "#edf1f4",
            "sidebar_bg": "#162229",
            "sidebar_fg": "#f2f6f8",
            "sidebar_muted_fg": "#adc0c9",
            "sidebar_border": "#273740",
            "sidebar_button_bg": "#213038",
            "sidebar_button_hover": "#2c404a",
            "sidebar_button_active_bg": "#d7e7ef",
            "sidebar_button_active_fg": "#10222b",
            "content_bg": "#edf1f4",
            "surface_bg": "#ffffff",
            "surface_fg": "#152129",
            "muted_fg": "#637782",
            "border_color": "#c6d2d8",
            "accent": "#0f7c8f",
            "accent_soft": "#d6eef2",
            "canvas_bg": "#e8eef1",
            "banner_bg": "#f4f8fa",
            "banner_fg": "#38515c",
            "banner_border": "#c8d5db",
            "nav_font": ("Segoe UI", 10),
            "title_font": ("Segoe UI", 16, "bold"),
            "heading_font": ("Segoe UI", 11, "bold"),
            "layout_block_canvas_bg": "#e8eef1",
            "layout_card_shell_bg": "#f6f9fb",
            "layout_preview_grid_bg": "#eef2f5",
            "layout_preview_cell_bg": "#ffffff",
            "layout_preview_selected_bg": "#d6eef2",
            "layout_preview_muted_fg": "#6c7f89",
            "layout_preview_empty_fg": "#78909c",
            "layout_preview_text_fg": "#152129",
            "layout_preview_readonly_fg": "#0f7c8f",
            "layout_preview_border": "#8b98a5",
            "layout_preview_selected_border": "#0f7c8f",
            "layout_tooltip_bg": "#ffffff",
            "layout_tooltip_fg": "#152129",
            "layout_tooltip_border": "#c6d2d8",
        }

    if normalized == "cyber_industrial_dark":
        return {
            "app_bg": "#081016",
            "sidebar_bg": "#0d171d",
            "sidebar_fg": "#d9f7ff",
            "sidebar_muted_fg": "#78a4b0",
            "sidebar_border": "#1f3b47",
            "sidebar_button_bg": "#102029",
            "sidebar_button_hover": "#16313d",
            "sidebar_button_active_bg": "#22d1ee",
            "sidebar_button_active_fg": "#041015",
            "content_bg": "#0a131a",
            "surface_bg": "#101b22",
            "surface_fg": "#e7f8fb",
            "muted_fg": "#88a9b4",
            "border_color": "#23414d",
            "accent": "#22d1ee",
            "accent_soft": "#123845",
            "canvas_bg": "#081219",
            "banner_bg": "#0d171d",
            "banner_fg": "#9bc8d3",
            "banner_border": "#1f3b47",
            "nav_font": ("Segoe UI", 10),
            "title_font": ("Segoe UI Semibold", 16),
            "heading_font": ("Segoe UI Semibold", 11),
            "layout_block_canvas_bg": "#09131a",
            "layout_card_shell_bg": "#0c1820",
            "layout_preview_grid_bg": "#081219",
            "layout_preview_cell_bg": "#12212a",
            "layout_preview_selected_bg": "#153240",
            "layout_preview_muted_fg": "#88a5af",
            "layout_preview_empty_fg": "#5f7a84",
            "layout_preview_text_fg": "#e7f8fb",
            "layout_preview_readonly_fg": "#58e5ff",
            "layout_preview_border": "#2a505d",
            "layout_preview_selected_border": "#22d1ee",
            "layout_tooltip_bg": "#0d171d",
            "layout_tooltip_fg": "#e7f8fb",
            "layout_tooltip_border": "#2a505d",
        }


def _qt_stylesheet_font_family(font_value):
    if isinstance(font_value, tuple) and font_value:
        return str(font_value[0])
    return str(font_value)


def _qt_stylesheet_font_size(font_value, default_size=10):
    if isinstance(font_value, tuple) and len(font_value) >= 2:
        try:
            return int(font_value[1])
        except (TypeError, ValueError):
            return default_size
    return default_size


def _qt_stylesheet_font_weight(font_value):
    if isinstance(font_value, tuple) and any(str(part).lower() == "bold" for part in font_value[2:]):
        return 700
    return 400


def _hex_to_rgba(color_value, alpha):
    color_text = str(color_value).strip()
    if not color_text.startswith("#") or len(color_text) != 7:
        return color_text
    try:
        red = int(color_text[1:3], 16)
        green = int(color_text[3:5], 16)
        blue = int(color_text[5:7], 16)
    except ValueError:
        return color_text
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _require_qt_theme_support():
    if not PYQT6_THEME_SUPPORT:
        raise RuntimeError("PyQt6 is not installed in the active Python environment.")


def get_qt_palette(theme_name=None, root=None, theme_tokens=None):
    _require_qt_theme_support()
    tokens = dict(theme_tokens or get_theme_tokens(theme_name=theme_name, root=root))

    palette = QPalette()
    disabled_fg = QColor(tokens["muted_fg"])
    active_fg = QColor(tokens["surface_fg"])
    active_bg = QColor(tokens["surface_bg"])
    accent = QColor(tokens["accent"])

    active_colors = {
        QPalette.ColorRole.Window: QColor(tokens["app_bg"]),
        QPalette.ColorRole.WindowText: active_fg,
        QPalette.ColorRole.Base: active_bg,
        QPalette.ColorRole.AlternateBase: QColor(tokens["accent_soft"]),
        QPalette.ColorRole.ToolTipBase: QColor(tokens["layout_tooltip_bg"]),
        QPalette.ColorRole.ToolTipText: QColor(tokens["layout_tooltip_fg"]),
        QPalette.ColorRole.Text: active_fg,
        QPalette.ColorRole.Button: active_bg,
        QPalette.ColorRole.ButtonText: active_fg,
        QPalette.ColorRole.BrightText: QColor(tokens["sidebar_fg"]),
        QPalette.ColorRole.Highlight: accent,
        QPalette.ColorRole.HighlightedText: QColor(tokens["sidebar_button_active_fg"]),
        QPalette.ColorRole.Link: accent,
        QPalette.ColorRole.LinkVisited: QColor(tokens["layout_preview_readonly_fg"]),
        QPalette.ColorRole.PlaceholderText: disabled_fg,
    }
    for role, color in active_colors.items():
        palette.setColor(QPalette.ColorGroup.Active, role, color)
        palette.setColor(QPalette.ColorGroup.Inactive, role, color)

    disabled_colors = {
        QPalette.ColorRole.Window: QColor(tokens["content_bg"]),
        QPalette.ColorRole.WindowText: disabled_fg,
        QPalette.ColorRole.Base: QColor(tokens["content_bg"]),
        QPalette.ColorRole.AlternateBase: QColor(tokens["accent_soft"]),
        QPalette.ColorRole.ToolTipBase: QColor(tokens["layout_tooltip_bg"]),
        QPalette.ColorRole.ToolTipText: disabled_fg,
        QPalette.ColorRole.Text: disabled_fg,
        QPalette.ColorRole.Button: QColor(tokens["content_bg"]),
        QPalette.ColorRole.ButtonText: disabled_fg,
        QPalette.ColorRole.BrightText: QColor(tokens["sidebar_muted_fg"]),
        QPalette.ColorRole.Highlight: QColor(tokens["accent_soft"]),
        QPalette.ColorRole.HighlightedText: disabled_fg,
        QPalette.ColorRole.Link: QColor(tokens["layout_preview_readonly_fg"]),
        QPalette.ColorRole.LinkVisited: QColor(tokens["layout_preview_readonly_fg"]),
        QPalette.ColorRole.PlaceholderText: disabled_fg,
    }
    for role, color in disabled_colors.items():
        palette.setColor(QPalette.ColorGroup.Disabled, role, color)

    return palette


def get_qt_stylesheet(theme_name=None, root=None, theme_tokens=None):
    tokens = dict(theme_tokens or get_theme_tokens(theme_name=theme_name, root=root))
    nav_font_family = _qt_stylesheet_font_family(tokens["nav_font"])
    nav_font_size = _qt_stylesheet_font_size(tokens["nav_font"])
    title_font_family = _qt_stylesheet_font_family(tokens["title_font"])
    title_font_size = _qt_stylesheet_font_size(tokens["title_font"], default_size=16)
    title_font_weight = _qt_stylesheet_font_weight(tokens["title_font"])
    heading_font_family = _qt_stylesheet_font_family(tokens["heading_font"])
    heading_font_size = _qt_stylesheet_font_size(tokens["heading_font"], default_size=11)
    heading_font_weight = _qt_stylesheet_font_weight(tokens["heading_font"])
    accent_outline = _hex_to_rgba(tokens["accent"], 64)
    accent_soft_overlay = _hex_to_rgba(tokens["accent"], 18)

    return "\n".join(
        [
            "QMainWindow, QWidget {",
            f"    background-color: {tokens['content_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    font-family: \"{nav_font_family}\";",
            f"    font-size: {nav_font_size}pt;",
            "}",
            "QWidget#sidebar, QFrame#sidebar {",
            f"    background-color: {tokens['sidebar_bg']};",
            f"    color: {tokens['sidebar_fg']};",
            f"    border-right: 1px solid {tokens['sidebar_border']};",
            "}",
            "QWidget#surfaceCard, QFrame#surfaceCard, QGroupBox, QMenu, QDialog {",
            f"    background-color: {tokens['surface_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "}",
            "QGroupBox {",
            f"    font-family: \"{heading_font_family}\";",
            f"    font-size: {heading_font_size}pt;",
            f"    font-weight: {heading_font_weight};",
            "    margin-top: 12px;",
            "    padding-top: 10px;",
            "    border-radius: 6px;",
            "}",
            "QGroupBox::title {",
            "    subcontrol-origin: margin;",
            "    left: 12px;",
            "    padding: 0 4px;",
            "}",
            "QLabel#pageTitle {",
            f"    font-family: \"{title_font_family}\";",
            f"    font-size: {title_font_size}pt;",
            f"    font-weight: {title_font_weight};",
            f"    color: {tokens['surface_fg']};",
            "}",
            "QLabel#mutedLabel, QLabel#subtitleLabel, QLabel#sectionHint {",
            f"    color: {tokens['muted_fg']};",
            "}",
                "QLabel#sidebarTitleLabel {",
                f"    font-family: \"{title_font_family}\";",
                f"    font-size: {title_font_size}pt;",
                f"    font-weight: {title_font_weight};",
                f"    color: {tokens['sidebar_fg']};",
                "}",
                "QLabel#sidebarSubtitleLabel {",
                f"    color: {tokens['sidebar_muted_fg']};",
                "}",
            "QPushButton {",
            f"    background-color: {tokens['surface_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    border-radius: 6px;",
            "    padding: 7px 12px;",
            "}",
            "QPushButton:hover {",
            f"    border-color: {tokens['accent']};",
            f"    background-color: {tokens['accent_soft']};",
            "}",
            "QPushButton:pressed {",
            f"    background-color: {tokens['accent']};",
            f"    color: {tokens['sidebar_button_active_fg']};",
            "}",
            "QPushButton:disabled {",
            f"    background-color: {tokens['content_bg']};",
            f"    color: {tokens['muted_fg']};",
            f"    border-color: {tokens['border_color']};",
            "}",
            "QPushButton#navButton {",
            f"    background-color: {tokens['sidebar_button_bg']};",
            f"    color: {tokens['sidebar_fg']};",
            f"    border: 1px solid {tokens['sidebar_border']};",
            "    text-align: left;",
            f"    font-family: \"{nav_font_family}\";",
            f"    font-size: {nav_font_size}pt;",
            "    padding: 10px 12px;",
            "}",
            "QPushButton#navButton:hover {",
            f"    background-color: {tokens['sidebar_button_hover']};",
            "}",
            "QPushButton#navButton[active=\"true\"] {",
            f"    background-color: {tokens['sidebar_button_active_bg']};",
            f"    color: {tokens['sidebar_button_active_fg']};",
            f"    border-color: {tokens['accent']};",
            "}",
                "QPushButton#sidebarToggleButton {",
                f"    background-color: {tokens['sidebar_button_bg']};",
                f"    color: {tokens['sidebar_fg']};",
                f"    border: 1px solid {tokens['sidebar_border']};",
                "    border-radius: 6px;",
                "    padding: 4px 6px;",
                "}",
                "QPushButton#sidebarToggleButton:hover {",
                f"    background-color: {tokens['sidebar_button_hover']};",
                f"    border-color: {tokens['accent']};",
                "}",
            "QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QListWidget, QTreeWidget, QTreeView, QTableWidget, QTableView {",
            f"    background-color: {tokens['surface_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    border-radius: 6px;",
            "    selection-background-color: %s;" % tokens["accent"],
            "    selection-color: %s;" % tokens["sidebar_button_active_fg"],
            "}",
            "QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus {",
            f"    border: 1px solid {tokens['accent']};",
            f"    background-color: {tokens['surface_bg']};",
            f"    selection-background-color: {tokens['accent']};",
            f"    selection-color: {tokens['sidebar_button_active_fg']};",
            f"    outline: 1px solid {accent_outline};",
            "}",
            "QHeaderView::section {",
            f"    background-color: {tokens['accent_soft']};",
            f"    color: {tokens['surface_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    padding: 6px 8px;",
            f"    font-family: \"{heading_font_family}\";",
            f"    font-size: {heading_font_size}pt;",
            f"    font-weight: {heading_font_weight};",
            "}",
            "QTabWidget::pane {",
            f"    border: 1px solid {tokens['border_color']};",
            f"    background-color: {tokens['surface_bg']};",
            "    top: -1px;",
            "}",
            "QTabBar::tab {",
            f"    background-color: {tokens['content_bg']};",
            f"    color: {tokens['muted_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    border-bottom: none;",
            "    border-top-left-radius: 6px;",
            "    border-top-right-radius: 6px;",
            "    padding: 8px 12px;",
            "    margin-right: 4px;",
            "}",
            "QTabBar::tab:selected {",
            f"    background-color: {tokens['surface_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    border-color: {tokens['accent']};",
            "}",
            "QStatusBar {",
            f"    background-color: {tokens['banner_bg']};",
            f"    color: {tokens['banner_fg']};",
            f"    border-top: 1px solid {tokens['banner_border']};",
            "}",
            "QToolTip {",
            f"    background-color: {tokens['layout_tooltip_bg']};",
            f"    color: {tokens['layout_tooltip_fg']};",
            f"    border: 1px solid {tokens['layout_tooltip_border']};",
            "    padding: 4px 6px;",
            "}",
            "QScrollBar:vertical, QScrollBar:horizontal {",
            f"    background-color: {tokens['content_bg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    border-radius: 6px;",
            "    margin: 0;",
            "}",
            "QScrollBar::handle:vertical, QScrollBar::handle:horizontal {",
            f"    background-color: {tokens['sidebar_button_hover']};",
            "    border-radius: 5px;",
            "    min-height: 24px;",
            "    min-width: 24px;",
            "}",
            "QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {",
            f"    background-color: {tokens['accent']};",
            "}",
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {",
            "    background: transparent;",
            "    border: none;",
            "}",
            "QSplitter::handle {",
            f"    background-color: {accent_soft_overlay};",
            "}",
        ]
    )


def get_theme_tokens(theme_name=None, root=None):
    if root is not None:
        cached_tokens = getattr(root, "_martin_theme_tokens", None)
        active_theme = getattr(root, "_martin_theme_name", None)
        if theme_name is None and cached_tokens and active_theme:
            return cached_tokens
        if theme_name is None and active_theme:
            theme_name = active_theme

    cached_tokens = getattr(root, "_martin_theme_tokens", None) if root is not None else None
    if cached_tokens and theme_name is None:
        return cached_tokens
    return _build_theme_tokens(theme_name or DEFAULT_THEME)


def apply_readability_overrides(root, theme_name=None):
    _ = root
    _ = theme_name
    raise RuntimeError("Tk readability overrides were removed from the live Phase 9 runtime.")

    style.configure("Treeview", rowheight=28)
    style.configure("TNotebook.Tab", padding=(10, 6))
    style.configure("TEntry", padding=6)
    style.configure("TCombobox", padding=4)
    style.map(
        "TNotebook.Tab",
        foreground=[("selected", tokens["surface_fg"]), ("!selected", tokens["muted_fg"])],
    )