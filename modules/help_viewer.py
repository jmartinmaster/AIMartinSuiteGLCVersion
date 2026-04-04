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
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from modules.utils import local_or_resource_path

__module_name__ = "Help Viewer"
__version__ = "1.1.4"


class HelpViewer:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.container = None
        self.notebook = None
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
        self.container = tb.Frame(self.parent, padding=18)
        self.container.pack(fill=BOTH, expand=False)
        self.container.pack_propagate(False)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(3, weight=1)

        tb.Label(self.container, text="Help Center", font=("Helvetica", 18, "bold")).grid(row=0, column=0, sticky=W)
        tb.Label(
            self.container,
            text="Use these guides to understand the workflow, file formats, and editable JSON structures used by the suite.",
            style="Martin.Muted.TLabel"
        ).grid(row=1, column=0, sticky=W, pady=(4, 12))

        action_row = tb.Frame(self.container)
        action_row.grid(row=2, column=0, sticky=EW, pady=(0, 12))
        tb.Button(
            action_row,
            text="Open User Guide File",
            bootstyle=PRIMARY,
            command=lambda: self.dispatcher.open_help_document("docs/help/user_guide.md")
        ).pack(side=LEFT)
        tb.Button(
            action_row,
            text="Open License File",
            bootstyle=SECONDARY,
            command=lambda: self.dispatcher.open_help_document("LICENSE.txt")
        ).pack(side=LEFT, padx=8)

        self.notebook = ttk.Notebook(self.container)
        self.notebook.grid(row=3, column=0, sticky=NSEW)

        for tab_name, doc_path in self.doc_index:
            tab = tb.Frame(self.notebook)
            self.notebook.add(tab, text=tab_name)
            self.populate_doc_tab(tab, doc_path)

        self.dispatcher.canvas.bind("<Configure>", self.on_viewport_resize, add="+")
        self.parent.after(0, self.apply_viewport_layout)

    def on_viewport_resize(self, _event=None):
        self.apply_viewport_layout()

    def apply_viewport_layout(self):
        if not self.container or not self.notebook:
            return

        self.parent.update_idletasks()
        viewport_width = max(self.dispatcher.canvas.winfo_width(), 700)
        viewport_height = max(self.dispatcher.canvas.winfo_height(), 500)

        container_height = max(viewport_height - 12, 420)
        notebook_height = max(int(container_height * 0.85), 320)

        self.container.configure(width=viewport_width - 8, height=container_height)
        self.notebook.configure(height=notebook_height)

    def populate_doc_tab(self, tab, doc_path):
        frame = tb.Frame(tab)
        frame.pack(fill=BOTH, expand=True)

        text_widget = tk.Text(frame, wrap=WORD, font=("Consolas", 10), padx=12, pady=12, undo=False)
        text_widget.grid(row=0, column=0, sticky=NSEW)

        scroll_y = tb.Scrollbar(frame, orient=VERTICAL, command=text_widget.yview)
        scroll_y.grid(row=0, column=1, sticky=NS)
        scroll_x = tb.Scrollbar(frame, orient=HORIZONTAL, command=text_widget.xview)
        scroll_x.grid(row=1, column=0, sticky=EW)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text_widget.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        content = self.read_doc(doc_path)
        text_widget.insert("1.0", content)
        text_widget.config(state=DISABLED)

    def read_doc(self, relative_path):
        candidate = local_or_resource_path(relative_path)
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return handle.read()
        return f"Missing help document: {relative_path}"


def get_ui(parent, dispatcher):
    return HelpViewer(parent, dispatcher)