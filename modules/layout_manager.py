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

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import json
import os
import sys

__module_name__ = "Layout Manager"
__version__ = "1.0.1"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LayoutManager:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        
        # 1. Logic: Read from local config when present, otherwise fall back to the packaged default.
        self.local_config = "layout_config.json"
        self.internal_config = resource_path("layout_config.json")
        
        # Save operations always target the local config so packaged builds remain editable.
        self.config_path = self.local_config if os.path.exists(self.local_config) else self.internal_config
        self.save_path = self.local_config
        
        self.setup_ui()

    def setup_ui(self):
        self.main_container = tb.Frame(self.parent, padding=10)
        self.main_container.pack(fill=BOTH, expand=True)

        # LEFT SIDE: Editor
        editor_frame = tb.Frame(self.main_container)
        editor_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        tb.Label(editor_frame, text="JSON Editor", font=("-size 12 -weight bold")).pack(anchor=W)
        self.source_label = tb.Label(editor_frame, bootstyle=SECONDARY)
        self.source_label.pack(anchor=W)
        self.text_area = tk.Text(editor_frame, wrap=NONE, font=("Monospace", 10), undo=True)
        self.text_area.pack(fill=BOTH, expand=True, pady=5)

        # RIGHT SIDE: Preview
        self.preview_wrapper = tb.Labelframe(self.main_container, text=" Live Grid Preview ", padding=10)
        self.preview_wrapper.pack(side=RIGHT, fill=BOTH, expand=True, padx=5)
        
        self.preview_canvas = tb.Frame(self.preview_wrapper)
        self.preview_canvas.pack(fill=BOTH, expand=True)

        # BUTTONS
        btn_frame = tb.Frame(editor_frame)
        btn_frame.pack(fill=X, pady=5)

        tb.Button(btn_frame, text="Reload Current", bootstyle=SECONDARY, command=self.load_config).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Load Default", bootstyle=WARNING, command=self.load_default_config).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Update Preview", bootstyle=INFO, command=self.update_preview).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Save to File", bootstyle=SUCCESS, command=self.save_config).pack(side=RIGHT, padx=5)

        self.load_config()
        self.update_preview()

    def set_editor_text(self, config_data):
        self.text_area.delete("1.0", END)
        self.text_area.insert("1.0", json.dumps(config_data, indent=4))

    def update_source_label(self):
        if self.config_path == self.local_config:
            source_text = f"Editing local config: {self.local_config}"
        else:
            source_text = f"Editing packaged default: {self.internal_config}"
        self.source_label.config(text=source_text)

    def update_preview(self):
        """Renders the current text area JSON into a visual grid."""
        # Clear existing preview
        for child in self.preview_canvas.winfo_children():
            child.destroy()

        try:
            raw_data = self.text_area.get("1.0", END).strip()
            config = json.loads(raw_data)
            
            # Draw dummy widgets to show the layout
            for field in config.get("header_fields", []):
                r = field.get("row", 0)
                c = field.get("col", 0)
                
                # We draw a "ghost" label and box to show positioning
                lbl = tb.Label(self.preview_canvas, text=field["label"], bootstyle=SECONDARY)
                lbl.grid(row=r, column=c, padx=2, pady=2, sticky=W)
                
                box = tb.Frame(self.preview_canvas, bootstyle=LIGHT, width=60, height=25)
                box.grid(row=r, column=c+1, padx=2, pady=2, sticky=W)
                box.pack_propagate(False) # Keep fixed size for preview

        except Exception as e:
            tb.Label(self.preview_canvas, text=f"Preview Error: {e}", bootstyle=DANGER).pack()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                self.set_editor_text(data)
                self.update_source_label()
                self.update_preview()

    def load_default_config(self):
        if os.path.exists(self.internal_config):
            with open(self.internal_config, 'r') as f:
                data = json.load(f)
            self.config_path = self.internal_config
            self.set_editor_text(data)
            self.update_source_label()
            self.update_preview()

    def save_config(self):
        try:
            raw_data = self.text_area.get("1.0", END).strip()
            json_data = json.loads(raw_data)
            with open(self.save_path, 'w') as f:
                json.dump(json_data, f, indent=4)
            self.config_path = self.save_path
            self.update_source_label()
            Messagebox.show_info("Layout saved! Production Log will update next time it's opened.", "Success")
            self.update_preview()
        except Exception as e:
            Messagebox.show_error(f"Error saving: {e}", "Error")

def get_ui(parent, dispatcher):
    return LayoutManager(parent, dispatcher)