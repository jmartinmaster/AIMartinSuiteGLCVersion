# The Martin Suite (GLC Edition)
# Copyright (C) 2026 Jamie Martin
# Licensed under GNU GPLv3.

import ttkbootstrap as tb

DEFAULT_THEME = "flatly"

# Curated for readable contrast and generally consistent widget styling.
READABLE_THEMES = {
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


def normalize_theme(theme_name):
    if theme_name in READABLE_THEMES:
        return theme_name
    return DEFAULT_THEME


def apply_readability_overrides(root):
    style = tb.Style.get_instance()
    if style is None:
        return

    colors = style.colors
    theme_name = normalize_theme(style.theme.name)
    is_dark = theme_name in {"darkly", "superhero"}

    sidebar_bg = colors.dark if not is_dark else colors.secondary
    sidebar_fg = colors.light if not is_dark else colors.selectfg
    surface_bg = colors.bg if not is_dark else colors.inputbg
    surface_fg = colors.fg if not is_dark else colors.inputfg
    muted_fg = colors.secondary if not is_dark else colors.light
    border_color = colors.border if hasattr(colors, "border") else colors.secondary

    root.option_add("*Font", "TkDefaultFont 10")
    root.option_add("*TCombobox*Listbox.font", "TkDefaultFont 10")

    style.configure("Martin.Sidebar.TFrame", background=sidebar_bg)
    style.configure("Martin.Sidebar.TLabel", background=sidebar_bg, foreground=sidebar_fg)
    style.configure("Martin.Content.TFrame", background=surface_bg)
    style.configure("Martin.Card.TLabelframe", background=surface_bg, foreground=surface_fg, bordercolor=border_color)
    style.configure("Martin.Card.TLabelframe.Label", background=surface_bg, foreground=surface_fg)
    style.configure("Martin.Recovery.TLabelframe", background=surface_bg, foreground=surface_fg, bordercolor=border_color)
    style.configure("Martin.Recovery.TLabelframe.Label", background=surface_bg, foreground=surface_fg)
    style.configure("Martin.Section.TLabel", background=surface_bg, foreground=surface_fg)
    style.configure("Martin.Muted.TLabel", background=surface_bg, foreground=muted_fg)

    style.configure("Treeview", rowheight=28)
    style.configure("TNotebook.Tab", padding=(10, 6))
    style.configure("TEntry", padding=6)
    style.configure("TCombobox", padding=4)
    style.map(
        "TNotebook.Tab",
        foreground=[("selected", colors.fg), ("!selected", muted_fg)],
    )