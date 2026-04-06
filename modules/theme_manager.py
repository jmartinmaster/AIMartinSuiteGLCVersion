# The Martin Suite (GLC Edition)
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

import ttkbootstrap as tb

__module_name__ = "Theme Manager"
__version__ = "1.1.0"

DEFAULT_THEME = "martin_modern_light"
DEFAULT_BASE_THEME = "flatly"

THEME_PRESETS = {
    "martin_modern_light": "flatly",
}

# Curated for readable contrast and generally consistent widget styling.
READABLE_THEMES = {
    "martin_modern_light": "Martin Modern Light - industrial",
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


def resolve_base_theme(theme_name):
    normalized = normalize_theme(theme_name)
    return THEME_PRESETS.get(normalized, normalized if normalized in READABLE_THEMES else DEFAULT_BASE_THEME)


def _build_theme_tokens(theme_name, colors):
    normalized = normalize_theme(theme_name)
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
        }

    is_dark = normalized in {"darkly", "superhero"}
    sidebar_bg = colors.dark if not is_dark else colors.secondary
    sidebar_fg = colors.light if not is_dark else colors.selectfg
    surface_bg = colors.bg if not is_dark else colors.inputbg
    surface_fg = colors.fg if not is_dark else colors.inputfg
    muted_fg = colors.secondary if not is_dark else colors.light
    border_color = colors.border if hasattr(colors, "border") else colors.secondary
    return {
        "app_bg": surface_bg,
        "sidebar_bg": sidebar_bg,
        "sidebar_fg": sidebar_fg,
        "sidebar_muted_fg": muted_fg,
        "sidebar_border": border_color,
        "sidebar_button_bg": sidebar_bg,
        "sidebar_button_hover": colors.primary,
        "sidebar_button_active_bg": colors.light if not is_dark else colors.primary,
        "sidebar_button_active_fg": colors.dark if not is_dark else colors.selectfg,
        "content_bg": surface_bg,
        "surface_bg": surface_bg,
        "surface_fg": surface_fg,
        "muted_fg": muted_fg,
        "border_color": border_color,
        "accent": colors.primary,
        "accent_soft": colors.info if hasattr(colors, "info") else colors.primary,
        "canvas_bg": surface_bg,
        "banner_bg": surface_bg,
        "banner_fg": muted_fg,
        "banner_border": border_color,
        "nav_font": ("Segoe UI", 10),
        "title_font": ("Segoe UI", 16, "bold"),
        "heading_font": ("Segoe UI", 11, "bold"),
    }


def get_theme_tokens(theme_name=None, root=None):
    if root is not None:
        cached_tokens = getattr(root, "_martin_theme_tokens", None)
        active_theme = getattr(root, "_martin_theme_name", None)
        if theme_name is None and cached_tokens and active_theme:
            return cached_tokens
        if theme_name is None and active_theme:
            theme_name = active_theme

    style = tb.Style.get_instance()
    if style is None:
        style = tb.Style()
    resolved_theme = theme_name or style.theme.name
    return _build_theme_tokens(resolved_theme, style.colors)


def apply_readability_overrides(root, theme_name=None):
    style = tb.Style.get_instance()
    if style is None:
        return

    resolved_theme = normalize_theme(theme_name or getattr(root, "_martin_theme_name", None) or style.theme.name)
    tokens = _build_theme_tokens(resolved_theme, style.colors)
    root._martin_theme_name = resolved_theme
    root._martin_theme_tokens = tokens

    root.configure(bg=tokens["app_bg"])
    root.option_add("*Font", tokens["nav_font"])
    root.option_add("*TCombobox*Listbox.font", tokens["nav_font"])

    style.configure("Martin.App.TFrame", background=tokens["content_bg"])
    style.configure("Martin.Sidebar.TFrame", background=tokens["sidebar_bg"])
    style.configure("Martin.Sidebar.TLabel", background=tokens["sidebar_bg"], foreground=tokens["sidebar_fg"])
    style.configure("Martin.SidebarTitle.TLabel", background=tokens["sidebar_bg"], foreground=tokens["sidebar_fg"], font=tokens["title_font"])
    style.configure("Martin.Content.TFrame", background=tokens["content_bg"])
    style.configure("Martin.Surface.TFrame", background=tokens["surface_bg"])
    style.configure("Martin.PageTitle.TLabel", background=tokens["content_bg"], foreground=tokens["surface_fg"], font=tokens["title_font"])
    style.configure("Martin.Subtitle.TLabel", background=tokens["content_bg"], foreground=tokens["muted_fg"])
    style.configure("Martin.Card.TLabelframe", background=tokens["surface_bg"], foreground=tokens["surface_fg"], bordercolor=tokens["border_color"])
    style.configure("Martin.Card.TLabelframe.Label", background=tokens["surface_bg"], foreground=tokens["surface_fg"], font=tokens["heading_font"])
    style.configure("Martin.Recovery.TLabelframe", background=tokens["surface_bg"], foreground=tokens["surface_fg"], bordercolor=tokens["border_color"])
    style.configure("Martin.Recovery.TLabelframe.Label", background=tokens["surface_bg"], foreground=tokens["surface_fg"], font=tokens["heading_font"])
    style.configure("Martin.Section.TLabel", background=tokens["surface_bg"], foreground=tokens["surface_fg"])
    style.configure("Martin.Muted.TLabel", background=tokens["surface_bg"], foreground=tokens["muted_fg"])
    style.configure("Martin.Status.TFrame", background=tokens["banner_bg"], bordercolor=tokens["banner_border"])
    style.configure("Martin.Status.TLabel", background=tokens["banner_bg"], foreground=tokens["banner_fg"])
    style.configure(
        "Martin.Nav.TButton",
        background=tokens["sidebar_button_bg"],
        foreground=tokens["sidebar_fg"],
        bordercolor=tokens["sidebar_border"],
        focuscolor=tokens["sidebar_button_hover"],
        relief="flat",
        anchor="w",
        padding=(12, 10),
        font=tokens["nav_font"],
    )
    style.map(
        "Martin.Nav.TButton",
        background=[("active", tokens["sidebar_button_hover"]), ("pressed", tokens["sidebar_button_hover"])],
        foreground=[("active", tokens["sidebar_fg"]), ("pressed", tokens["sidebar_fg"])],
    )
    style.configure(
        "Martin.NavActive.TButton",
        background=tokens["sidebar_button_active_bg"],
        foreground=tokens["sidebar_button_active_fg"],
        bordercolor=tokens["accent"],
        focuscolor=tokens["accent"],
        relief="flat",
        anchor="w",
        padding=(12, 10),
        font=tokens["nav_font"],
    )
    style.map(
        "Martin.NavActive.TButton",
        background=[("active", tokens["sidebar_button_active_bg"]), ("pressed", tokens["sidebar_button_active_bg"])],
        foreground=[("active", tokens["sidebar_button_active_fg"]), ("pressed", tokens["sidebar_button_active_fg"])],
    )

    style.configure("Treeview", rowheight=28)
    style.configure("TNotebook.Tab", padding=(10, 6))
    style.configure("TEntry", padding=6)
    style.configure("TCombobox", padding=4)
    style.map(
        "TNotebook.Tab",
        foreground=[("selected", tokens["surface_fg"]), ("!selected", tokens["muted_fg"])],
    )