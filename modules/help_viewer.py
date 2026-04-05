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

import os
import tkinter as tk
import tkinter.font as tkfont
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from modules.utils import local_or_resource_path

__module_name__ = "Help Viewer"
__version__ = "1.2.2"


class RoundedNavChip(tk.Canvas):
    def __init__(self, parent, text, command, width=None):
        self.command = command
        self.text = text
        self.radius = 16
        self.height = 36
        self.font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        text_width = self.font.measure(text)
        chip_width = width or max(120, text_width + 28)
        bg_color = self._resolve_canvas_background(parent)
        super().__init__(
            parent,
            width=chip_width,
            height=self.height,
            highlightthickness=0,
            bd=0,
            bg=bg_color,
            cursor="hand2",
        )
        self.palette = {
            "normal_fill": "#EAF1F8",
            "normal_outline": "#D5E2F0",
            "normal_text": "#24425C",
            "hover_fill": "#DDEAF7",
            "hover_outline": "#BFD4EA",
            "active_fill": "#2D6FA4",
            "active_outline": "#2D6FA4",
            "active_text": "#FFFFFF",
        }
        self.is_active = False
        self.is_hovered = False
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._render()

    def _resolve_canvas_background(self, parent):
        try:
            style_name = str(parent.cget("style") or "TFrame")
        except tk.TclError:
            style_name = "TFrame"

        try:
            background = parent.tk.call("ttk::style", "lookup", style_name, "-background")
            if background:
                return str(background)
        except tk.TclError:
            pass

        try:
            background = parent.tk.call("ttk::style", "lookup", "TFrame", "-background")
            if background:
                return str(background)
        except tk.TclError:
            pass

        return "#2F4154"

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, fill, outline):
        self.create_arc(x1, y1, x1 + radius * 2, y1 + radius * 2, start=90, extent=90, fill=fill, outline=outline)
        self.create_arc(x2 - radius * 2, y1, x2, y1 + radius * 2, start=0, extent=90, fill=fill, outline=outline)
        self.create_arc(x1, y2 - radius * 2, x1 + radius * 2, y2, start=180, extent=90, fill=fill, outline=outline)
        self.create_arc(x2 - radius * 2, y2 - radius * 2, x2, y2, start=270, extent=90, fill=fill, outline=outline)
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=outline)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=outline)

    def _current_colors(self):
        if self.is_active:
            return self.palette["active_fill"], self.palette["active_outline"], self.palette["active_text"]
        if self.is_hovered:
            return self.palette["hover_fill"], self.palette["hover_outline"], self.palette["normal_text"]
        return self.palette["normal_fill"], self.palette["normal_outline"], self.palette["normal_text"]

    def _render(self):
        self.delete("all")
        fill, outline, text_color = self._current_colors()
        self._draw_rounded_rect(1, 1, int(self["width"]) - 2, self.height - 2, self.radius, fill, outline)
        self.create_text(
            int(self["width"]) // 2,
            self.height // 2,
            text=self.text,
            font=self.font,
            fill=text_color,
        )

    def _on_click(self, _event=None):
        if callable(self.command):
            self.command()

    def _on_enter(self, _event=None):
        self.is_hovered = True
        self._render()

    def _on_leave(self, _event=None):
        self.is_hovered = False
        self._render()

    def set_active(self, is_active):
        self.is_active = bool(is_active)
        self._render()


class HelpViewer:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.palette = {
            "page_bg": "#223548",
            "hero_bg": "#D8E1EA",
            "hero_title": "#16324B",
            "hero_text": "#28465F",
            "hero_badge_bg": "#274C6B",
            "hero_badge_fg": "#F4F8FC",
            "hero_badge_muted_bg": "#B8C6D4",
            "hero_badge_muted_fg": "#35516A",
            "panel_bg": "#E7EDF3",
            "panel_inner": "#F8FBFE",
            "panel_title": "#17324A",
            "panel_meta": "#4B657C",
            "panel_badge_bg": "#2B6EA3",
            "panel_badge_fg": "#FFFFFF",
            "text_bg": "#1F3347",
            "text_fg": "#F3F7FB",
            "text_path": "#35516A",
            "scroll_trough": "#D0DAE4",
        }
        self.container = None
        self.hero_panel = None
        self.link_bar = None
        self.link_canvas = None
        self.link_window = None
        self.link_scrollbar = None
        self.doc_panel = None
        self.doc_surface = None
        self.doc_title_var = tb.StringVar(value="User Guide")
        self.doc_path_var = tb.StringVar(value="docs/help/user_guide.md")
        self.doc_meta_var = tb.StringVar(value="Bundled guide")
        self.doc_text_widget = None
        self.doc_link_buttons = {}
        self.active_doc_path = None
        self.doc_index = [
            ("User Guide", "docs/help/user_guide.md"),
            ("App Icons", "docs/help/app_icons.md"),
            ("Layout JSON", "docs/help/layout_config.md"),
            ("Settings JSON", "docs/help/settings_json.md"),
            ("Rates JSON", "docs/help/rates_json.md"),
            ("Draft JSON", "docs/help/draft_json.md"),
            ("License", "LICENSE.txt"),
        ]
        self.setup_ui()

    def setup_ui(self):
        self.container = tb.Frame(self.parent, padding=24)
        self.container.pack(fill=BOTH, expand=True)
        self.container.pack_propagate(False)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(2, weight=1)
        self.container.configure(bootstyle=DARK)

        self.hero_panel = tk.Frame(self.container, bg=self.palette["hero_bg"], padx=22, pady=22)
        self.hero_panel.grid(row=0, column=0, sticky=EW, pady=(0, 16))
        self.hero_panel.columnconfigure(0, weight=1)
        self.hero_panel.columnconfigure(1, weight=0)

        hero_copy = tk.Frame(self.hero_panel, bg=self.palette["hero_bg"])
        hero_copy.grid(row=0, column=0, sticky=EW)
        tk.Label(
            hero_copy,
            text="Help Center",
            font=("Segoe UI Semibold", 22),
            fg=self.palette["hero_title"],
            bg=self.palette["hero_bg"],
        ).pack(anchor=W)
        tk.Label(
            hero_copy,
            text="A cleaner reading space for workflow guides, editable JSON references, and bundled release notes.",
            font=("Segoe UI", 12),
            fg=self.palette["hero_text"],
            bg=self.palette["hero_bg"],
            wraplength=560,
            justify=LEFT,
        ).pack(anchor=W, pady=(6, 12))

        stats_row = tk.Frame(hero_copy, bg=self.palette["hero_bg"])
        stats_row.pack(anchor=W)
        tk.Label(
            stats_row,
            text=f"{len(self.doc_index)} bundled references",
            font=("Segoe UI Semibold", 10),
            fg=self.palette["hero_badge_fg"],
            bg=self.palette["hero_badge_bg"],
            padx=10,
            pady=4,
        ).pack(side=LEFT)
        tk.Label(
            stats_row,
            text="Single-page navigation",
            font=("Segoe UI Semibold", 10),
            fg=self.palette["hero_badge_muted_fg"],
            bg=self.palette["hero_badge_muted_bg"],
            padx=10,
            pady=4,
        ).pack(side=LEFT, padx=(12, 0))

        action_row = tk.Frame(self.hero_panel, bg=self.palette["hero_bg"])
        action_row.grid(row=0, column=1, sticky=NE, padx=(18, 0))
        tb.Button(
            action_row,
            text="Open Current File",
            bootstyle=PRIMARY,
            command=self.open_active_document
        ).pack(anchor=E)
        tb.Button(
            action_row,
            text="Open License File",
            bootstyle=SECONDARY,
            command=lambda: self.dispatcher.open_help_document("LICENSE.txt")
        ).pack(anchor=E, pady=(8, 0))

        nav_shell = tk.Frame(self.container, bg=self.palette["page_bg"], padx=4, pady=4)
        nav_shell.grid(row=1, column=0, sticky=EW)
        nav_shell.columnconfigure(0, weight=1)
        nav_shell.rowconfigure(0, weight=1)

        self.link_canvas = tk.Canvas(
            nav_shell,
            height=52,
            highlightthickness=0,
            bd=0,
            bg=self.palette["page_bg"],
            xscrollincrement=24,
        )
        self.link_canvas.grid(row=0, column=0, sticky=EW)

        self.link_scrollbar = tb.Scrollbar(nav_shell, orient=HORIZONTAL, command=self.link_canvas.xview)
        self.link_scrollbar.grid(row=1, column=0, sticky=EW, pady=(6, 0))
        self.link_scrollbar.configure(bootstyle=SECONDARY)
        self.link_canvas.configure(xscrollcommand=self.link_scrollbar.set)

        self.link_bar = tk.Frame(self.link_canvas, bg=self.palette["page_bg"])
        self.link_window = self.link_canvas.create_window((0, 0), window=self.link_bar, anchor="nw")
        self.link_bar.bind("<Configure>", self.on_link_bar_configure)
        self.link_canvas.bind("<Configure>", self.on_link_canvas_resize)
        self.link_canvas.bind("<Shift-MouseWheel>", self.on_link_bar_mousewheel)
        self.link_canvas.bind("<MouseWheel>", self.on_link_bar_mousewheel)

        for doc_name, doc_path in self.doc_index:
            button = RoundedNavChip(
                self.link_bar,
                text=doc_name,
                command=lambda name=doc_name, path=doc_path: self.show_document(name, path),
            )
            button.pack(side=LEFT, padx=(0, 10), pady=(0, 8))
            self.doc_link_buttons[doc_path] = button

        self.doc_panel = tk.Frame(self.container, bg=self.palette["panel_bg"], padx=20, pady=20)
        self.doc_panel.grid(row=2, column=0, sticky=NSEW)
        self.doc_panel.columnconfigure(0, weight=1)
        self.doc_panel.rowconfigure(1, weight=1)

        header_band = tk.Frame(self.doc_panel, bg=self.palette["panel_bg"])
        header_band.grid(row=0, column=0, sticky=EW, pady=(0, 14))
        header_band.columnconfigure(0, weight=1)

        tk.Label(
            header_band,
            textvariable=self.doc_title_var,
            font=("Segoe UI Semibold", 18),
            fg=self.palette["panel_title"],
            bg=self.palette["panel_bg"],
        ).grid(row=0, column=0, sticky=W)
        tk.Label(
            header_band,
            textvariable=self.doc_meta_var,
            font=("Segoe UI Semibold", 10),
            fg=self.palette["panel_badge_fg"],
            bg=self.palette["panel_badge_bg"],
            padx=10,
            pady=4,
        ).grid(row=0, column=1, sticky=E)
        tk.Label(
            header_band,
            textvariable=self.doc_path_var,
            font=("Segoe UI", 10),
            fg=self.palette["text_path"],
            bg=self.palette["panel_bg"],
        ).grid(row=1, column=0, columnspan=2, sticky=W, pady=(6, 0))

        self.doc_surface = tk.Frame(self.doc_panel, bg=self.palette["panel_inner"], padx=2, pady=2)
        self.doc_surface.grid(row=1, column=0, sticky=NSEW)
        self.doc_surface.columnconfigure(0, weight=1)
        self.doc_surface.rowconfigure(0, weight=1)

        doc_frame = tk.Frame(self.doc_surface, bg=self.palette["text_bg"], padx=14, pady=14)
        doc_frame.grid(row=0, column=0, sticky=NSEW)
        doc_frame.rowconfigure(0, weight=1)
        doc_frame.columnconfigure(0, weight=1)

        self.doc_text_widget = tk.Text(
            doc_frame,
            wrap=WORD,
            font=("Consolas", 10),
            padx=16,
            pady=16,
            undo=False,
            bd=0,
            relief="flat",
            highlightthickness=0,
            background=self.palette["text_bg"],
            foreground=self.palette["text_fg"],
            insertbackground=self.palette["text_fg"],
            selectbackground="#4C7398",
            selectforeground="#FFFFFF",
        )
        self.doc_text_widget.grid(row=0, column=0, sticky=NSEW)

        scroll_y = tb.Scrollbar(doc_frame, orient=VERTICAL, command=self.doc_text_widget.yview)
        scroll_y.grid(row=0, column=1, sticky=NS)
        scroll_x = tb.Scrollbar(doc_frame, orient=HORIZONTAL, command=self.doc_text_widget.xview)
        scroll_x.grid(row=1, column=0, sticky=EW)
        scroll_y.configure(bootstyle=SECONDARY)
        scroll_x.configure(bootstyle=SECONDARY)
        self.doc_text_widget.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.doc_text_widget.config(state=DISABLED)

        self.dispatcher.canvas.bind("<Configure>", self.on_viewport_resize, add="+")
        initial_name, initial_path = self.doc_index[0]
        self.show_document(initial_name, initial_path)
        self.parent.after(0, self.apply_viewport_layout)

    def on_viewport_resize(self, _event=None):
        self.apply_viewport_layout()

    def on_link_bar_configure(self, _event=None):
        if self.link_canvas is None:
            return
        self.link_canvas.configure(scrollregion=self.link_canvas.bbox("all"))

    def on_link_canvas_resize(self, event):
        if self.link_canvas is None or self.link_window is None:
            return
        required_width = self.link_bar.winfo_reqwidth() if self.link_bar is not None else event.width
        self.link_canvas.itemconfigure(self.link_window, height=event.height)
        if required_width < event.width:
            self.link_canvas.itemconfigure(self.link_window, width=event.width)
        else:
            self.link_canvas.itemconfigure(self.link_window, width=required_width)

    def on_link_bar_mousewheel(self, event):
        if self.link_canvas is None:
            return
        delta = 0
        if getattr(event, "delta", 0):
            delta = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) in (4, 5):
            delta = -1 if event.num == 4 else 1
        if delta:
            self.link_canvas.xview_scroll(delta * 3, "units")

    def apply_viewport_layout(self):
        if not self.container or not self.doc_panel:
            return

        self.parent.update_idletasks()
        viewport_width = max(self.dispatcher.canvas.winfo_width(), 760)
        viewport_height = max(self.dispatcher.canvas.winfo_height(), 520)

        container_height = max(viewport_height - 14, 460)
        doc_panel_height = max(int(container_height * 0.72), 340)

        self.container.configure(width=viewport_width - 8, height=container_height)
        self.doc_panel.configure(height=doc_panel_height)
        if self.link_canvas is not None:
            self.link_canvas.configure(width=viewport_width - 40)
            self.on_link_bar_configure()

    def show_document(self, doc_name, doc_path):
        self.active_doc_path = doc_path
        self.doc_title_var.set(doc_name)
        self.doc_path_var.set(doc_path)
        self.doc_meta_var.set("Bundled license" if doc_path == "LICENSE.txt" else "Bundled guide")
        content = self.read_doc(doc_path)

        self.doc_text_widget.config(state=NORMAL)
        self.doc_text_widget.delete("1.0", END)
        self.doc_text_widget.insert("1.0", content)
        self.doc_text_widget.config(state=DISABLED)
        self.doc_text_widget.yview_moveto(0)

        for candidate_path, button in self.doc_link_buttons.items():
            button.set_active(candidate_path == doc_path)

    def open_active_document(self):
        if self.active_doc_path:
            self.dispatcher.open_help_document(self.active_doc_path)

    def read_doc(self, relative_path):
        candidate = local_or_resource_path(relative_path)
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return handle.read()
        return f"Missing help document: {relative_path}"


def get_ui(parent, dispatcher):
    return HelpViewer(parent, dispatcher)