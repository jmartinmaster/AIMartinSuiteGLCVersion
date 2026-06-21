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
__version__ = "1.4.5"

DEFAULT_THEME = "martin_modern_light"

READABLE_THEMES = {
    "martin_modern_light": "Martin Modern Light - industrial",
    "cyber_industrial_dark": "Cyber-Industrial Dark - neon steel",
    "journal": "Journal - paper light",
    "superhero": "Superhero - high-contrast dark",
}

LEGACY_THEME_ALIASES = {
    "flatly": "journal",
    "cosmo": "journal",
    "lumen": "journal",
    "litera": "journal",
    "darkly": "superhero",
}

LEGACY_THEME_LABEL_ALIASES = {
    "Flatly - balanced light": "journal",
    "Cosmo - crisp light": "journal",
    "Lumen - soft light": "journal",
    "Litera - text-forward light": "journal",
    "Darkly - balanced dark": "superhero",
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
    legacy_theme = LEGACY_THEME_ALIASES.get(theme_name)
    if legacy_theme:
        return legacy_theme
    for key, label in READABLE_THEMES.items():
        if theme_name == label:
            return key
    legacy_label_theme = LEGACY_THEME_LABEL_ALIASES.get(theme_name)
    if legacy_label_theme:
        return legacy_label_theme
    return DEFAULT_THEME


def _resolve_theme_token_profile(theme_name):
    normalized = normalize_theme(theme_name)
    if normalized == "cyber_industrial_dark":
        return "cyber_industrial_dark"
    if normalized == "journal":
        return "journal"
    if normalized == "superhero":
        return "superhero"
    return "martin_modern_light"


def _build_theme_tokens(theme_name):
    normalized = _resolve_theme_token_profile(theme_name)
    if normalized == "martin_modern_light":
        return {
            "app_bg": "#e7edf1",
            "sidebar_bg": "#0f1c23",
            "sidebar_fg": "#eff8fb",
            "sidebar_muted_fg": "#9fb6c0",
            "sidebar_border": "#223743",
            "sidebar_button_bg": "#172831",
            "sidebar_button_hover": "#21404c",
            "sidebar_button_active_bg": "#d9ecf3",
            "sidebar_button_active_fg": "#0d1c24",
            "content_bg": "#edf3f6",
            "surface_bg": "#fbfdfe",
            "surface_fg": "#142129",
            "muted_fg": "#5d7480",
            "border_color": "#b7c8d0",
            "accent": "#157f94",
            "accent_soft": "#d8eef4",
            "canvas_bg": "#e3ecf0",
            "banner_bg": "#eef5f7",
            "banner_fg": "#36505b",
            "banner_border": "#bfd1d8",
            "nav_font": ("Segoe UI", 10),
            "title_font": ("Segoe UI", 16, "bold"),
            "heading_font": ("Segoe UI", 11, "bold"),
            "layout_block_canvas_bg": "#e3ecf0",
            "layout_card_shell_bg": "#f4f9fb",
            "layout_preview_grid_bg": "#e9f0f4",
            "layout_preview_cell_bg": "#fcfeff",
            "layout_preview_selected_bg": "#cde8f0",
            "layout_preview_muted_fg": "#687d87",
            "layout_preview_empty_fg": "#728994",
            "layout_preview_text_fg": "#142129",
            "layout_preview_readonly_fg": "#157f94",
            "layout_preview_border": "#8198a3",
            "layout_preview_selected_border": "#157f94",
            "layout_tooltip_bg": "#ffffff",
            "layout_tooltip_fg": "#142129",
            "layout_tooltip_border": "#b7c8d0",
        }

    if normalized == "cyber_industrial_dark":
        return {
            "app_bg": "#02060a",
            "sidebar_bg": "#040b10",
            "sidebar_fg": "#e1fcff",
            "sidebar_muted_fg": "#7cbcc7",
            "sidebar_border": "#0f6072",
            "sidebar_button_bg": "#071118",
            "sidebar_button_hover": "#0b2530",
            "sidebar_button_active_bg": "#31f4ff",
            "sidebar_button_active_fg": "#021115",
            "content_bg": "#03090f",
            "surface_bg": "#07131a",
            "surface_fg": "#ebfdff",
            "muted_fg": "#84adb8",
            "border_color": "#166175",
            "accent": "#31f4ff",
            "accent_soft": "#094352",
            "canvas_bg": "#020b12",
            "banner_bg": "#051019",
            "banner_fg": "#9be4ee",
            "banner_border": "#0d5a6b",
            "nav_font": ("Segoe UI", 10),
            "title_font": ("Bahnschrift SemiBold", 16),
            "heading_font": ("Bahnschrift SemiBold", 11),
            "layout_block_canvas_bg": "#030b12",
            "layout_card_shell_bg": "#07131a",
            "layout_preview_grid_bg": "#020e16",
            "layout_preview_cell_bg": "#0d1d26",
            "layout_preview_selected_bg": "#0f4d60",
            "layout_preview_muted_fg": "#86afb9",
            "layout_preview_empty_fg": "#5e7c86",
            "layout_preview_text_fg": "#ebfdff",
            "layout_preview_readonly_fg": "#73fbff",
            "layout_preview_border": "#19708a",
            "layout_preview_selected_border": "#31f4ff",
            "layout_tooltip_bg": "#06111a",
            "layout_tooltip_fg": "#ebfdff",
            "layout_tooltip_border": "#19708a",
        }

    if normalized == "journal":
        return {
            "app_bg": "#efe4cf",
            "sidebar_bg": "#5a4738",
            "sidebar_fg": "#f7efe2",
            "sidebar_muted_fg": "#dbc9b0",
            "sidebar_border": "#826b57",
            "sidebar_button_bg": "#6a5341",
            "sidebar_button_hover": "#7b614d",
            "sidebar_button_active_bg": "#efe0c7",
            "sidebar_button_active_fg": "#37271d",
            "content_bg": "#f4ead8",
            "surface_bg": "#fbf4e8",
            "surface_fg": "#35271d",
            "muted_fg": "#7b6555",
            "border_color": "#baa489",
            "accent": "#8f5e37",
            "accent_soft": "#eadbc2",
            "canvas_bg": "#ebe0ca",
            "banner_bg": "#efe2ca",
            "banner_fg": "#5e493a",
            "banner_border": "#c6b094",
            "nav_font": ("Cambria", 9),
            "title_font": ("Georgia", 15, "bold"),
            "heading_font": ("Cambria", 10, "bold"),
            "layout_block_canvas_bg": "#ebdfc8",
            "layout_card_shell_bg": "#f7efdf",
            "layout_preview_grid_bg": "#f0e5d2",
            "layout_preview_cell_bg": "#fcf6ea",
            "layout_preview_selected_bg": "#e4cfb0",
            "layout_preview_muted_fg": "#786350",
            "layout_preview_empty_fg": "#927c67",
            "layout_preview_text_fg": "#35271d",
            "layout_preview_readonly_fg": "#8f5e37",
            "layout_preview_border": "#aa9278",
            "layout_preview_selected_border": "#8f5e37",
            "layout_tooltip_bg": "#f8efdf",
            "layout_tooltip_fg": "#35271d",
            "layout_tooltip_border": "#baa489",
        }

    if normalized == "superhero":
        return {
            "app_bg": "#11161c",
            "sidebar_bg": "#151d24",
            "sidebar_fg": "#e8f1f5",
            "sidebar_muted_fg": "#98acb6",
            "sidebar_border": "#273742",
            "sidebar_button_bg": "#1a242d",
            "sidebar_button_hover": "#23313c",
            "sidebar_button_active_bg": "#4fb3c9",
            "sidebar_button_active_fg": "#071216",
            "content_bg": "#12191f",
            "surface_bg": "#182128",
            "surface_fg": "#e8f0f4",
            "muted_fg": "#8ca1ab",
            "border_color": "#304450",
            "accent": "#4fb3c9",
            "accent_soft": "#203843",
            "canvas_bg": "#10171d",
            "banner_bg": "#151d24",
            "banner_fg": "#a4b8c0",
            "banner_border": "#2a3a46",
            "nav_font": ("Segoe UI", 10),
            "title_font": ("Segoe UI", 16, "semibold"),
            "heading_font": ("Segoe UI", 11, "semibold"),
            "layout_block_canvas_bg": "#11181f",
            "layout_card_shell_bg": "#171f26",
            "layout_preview_grid_bg": "#0e161c",
            "layout_preview_cell_bg": "#1b2630",
            "layout_preview_selected_bg": "#244654",
            "layout_preview_muted_fg": "#8ea2ac",
            "layout_preview_empty_fg": "#6d828c",
            "layout_preview_text_fg": "#e8f0f4",
            "layout_preview_readonly_fg": "#7dd2e5",
            "layout_preview_border": "#38515d",
            "layout_preview_selected_border": "#4fb3c9",
            "layout_tooltip_bg": "#151d24",
            "layout_tooltip_fg": "#e8f0f4",
            "layout_tooltip_border": "#38515d",
        }

    return _build_theme_tokens(DEFAULT_THEME)


def _qt_stylesheet_font_family(font_value):
    if isinstance(font_value, (tuple, list)) and font_value:
        return str(font_value[0])
    return str(font_value)


def _qt_stylesheet_font_size(font_value, default_size=10):
    if isinstance(font_value, (tuple, list)) and len(font_value) >= 2:
        try:
            return int(font_value[1])
        except (TypeError, ValueError):
            return default_size
    return default_size


def _qt_stylesheet_font_weight(font_value):
    weight_parts = []
    if isinstance(font_value, (tuple, list)):
        if font_value:
            weight_parts.append(str(font_value[0]).lower())
        weight_parts.extend(str(part).lower() for part in font_value[2:])
    else:
        weight_parts.append(str(font_value).lower())

    if any("semibold" in part or "demibold" in part for part in weight_parts):
        return 600
    if any("bold" in part for part in weight_parts):
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
    sidebar_title_font_size = max(heading_font_size + 2, 13)
    sidebar_title_font_weight = max(heading_font_weight, 600)
    accent_outline = _hex_to_rgba(tokens["accent"], 84)
    accent_soft_overlay = _hex_to_rgba(tokens["accent"], 24)

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
            "    border-radius: 10px;",
            "}",
            "QGroupBox {",
            f"    font-family: \"{heading_font_family}\";",
            f"    font-size: {heading_font_size}pt;",
            f"    font-weight: {heading_font_weight};",
            "    margin-top: 14px;",
            "    padding-top: 12px;",
            "    border-radius: 10px;",
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
                f"    font-family: \"{heading_font_family}\";",
                f"    font-size: {sidebar_title_font_size}pt;",
                f"    font-weight: {sidebar_title_font_weight};",
                f"    color: {tokens['sidebar_fg']};",
                f"    background-color: {tokens['sidebar_button_bg']};",
                f"    border: 1px solid {tokens['sidebar_border']};",
                "    border-radius: 8px;",
                "    padding: 6px 8px;",
                "}",
                "QLabel#sidebarSubtitleLabel {",
                f"    font-family: \"{nav_font_family}\";",
                f"    font-size: {nav_font_size}pt;",
                "    font-weight: 600;",
                f"    color: {tokens['sidebar_fg']};",
                f"    background-color: {tokens['sidebar_button_bg']};",
                f"    border: 1px solid {tokens['sidebar_border']};",
                "    border-radius: 7px;",
                "    padding: 3px 8px;",
                "    margin-left: 4px;",
                "    margin-right: 4px;",
                "}",
            "QMenuBar {",
            f"    background-color: {tokens['sidebar_bg']};",
            f"    color: {tokens['sidebar_fg']};",
            f"    border-bottom: 1px solid {tokens['sidebar_border']};",
            "}",
            "QMenuBar::item {",
            "    background: transparent;",
            f"    color: {tokens['sidebar_fg']};",
            "    padding: 6px 10px;",
            "    border-radius: 6px;",
            "}",
            "QMenuBar::item:selected {",
            f"    background-color: {tokens['sidebar_button_hover']};",
            "}",
            "QMenu::item:selected {",
            f"    background-color: {tokens['accent_soft']};",
            f"    color: {tokens['surface_fg']};",
            "}",
            "QPushButton, QToolButton {",
            f"    background-color: {tokens['surface_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    border-radius: 8px;",
            "    padding: 8px 14px;",
            "}",
            "QPushButton:hover, QToolButton:hover {",
            f"    border-color: {tokens['accent']};",
            f"    background-color: {tokens['accent_soft']};",
            "}",
            "QPushButton:pressed, QToolButton:pressed {",
            f"    background-color: {tokens['accent']};",
            f"    color: {tokens['sidebar_button_active_fg']};",
            "}",
            "QPushButton:disabled, QToolButton:disabled {",
            f"    background-color: {tokens['content_bg']};",
            f"    color: {tokens['muted_fg']};",
            f"    border-color: {tokens['border_color']};",
            "}",
            "QToolButton::menu-button {",
            f"    border-left: 1px solid {tokens['border_color']};",
            "    width: 16px;",
            "    border-top-right-radius: 8px;",
            "    border-bottom-right-radius: 8px;",
            "}",
            "QToolButton::menu-button:hover {",
            f"    background-color: {tokens['accent']};",
            "}",
            "QPushButton#navButton {",
            f"    background-color: {tokens['sidebar_button_bg']};",
            f"    color: {tokens['sidebar_fg']};",
            f"    border: 1px solid {tokens['sidebar_border']};",
            "    border-radius: 10px;",
            "    text-align: left;",
            f"    font-family: \"{nav_font_family}\";",
            f"    font-size: {nav_font_size}pt;",
            "    padding: 10px 12px;",
            "}",
            "QPushButton#navButton:hover {",
            f"    background-color: {tokens['sidebar_button_hover']};",
            f"    border-color: {tokens['accent']};",
            "}",
            "QPushButton#navButton[active=\"true\"] {",
            f"    background-color: {tokens['sidebar_button_active_bg']};",
            f"    color: {tokens['sidebar_button_active_fg']};",
            f"    border-color: {tokens['accent']};",
            "    padding-left: 14px;",
            "}",
                "QPushButton#sidebarToggleButton {",
                f"    background-color: {tokens['sidebar_button_bg']};",
                f"    color: {tokens['sidebar_fg']};",
                f"    border: 1px solid {tokens['sidebar_border']};",
                "    border-radius: 8px;",
                "    padding: 4px 6px;",
                "}",
                "QPushButton#sidebarToggleButton:hover {",
                f"    background-color: {tokens['sidebar_button_hover']};",
                f"    border-color: {tokens['accent']};",
                "}",
            "QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QListWidget, QTreeWidget, QTreeView, QTableWidget, QTableView {",
            f"    background-color: {tokens['surface_bg']};",
            f"    color: {tokens['surface_fg']};",
            f"    border: 1px solid {tokens['border_color']};",
            "    border-radius: 8px;",
            "    selection-background-color: %s;" % tokens["accent"],
            "    selection-color: %s;" % tokens["sidebar_button_active_fg"],
            "}",
            "QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QTextBrowser:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus, QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus {",
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
            "    border-top-left-radius: 8px;",
            "    border-top-right-radius: 8px;",
            "    padding: 8px 12px;",
            "    margin-right: 4px;",
            "}",
            "QTabBar::tab:hover {",
            f"    background-color: {tokens['accent_soft']};",
            f"    color: {tokens['surface_fg']};",
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
            "QStatusBar::item {",
            "    border: none;",
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
            "    border-radius: 8px;",
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