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
from tkinter import filedialog
import json
import os
import sys
from modules.persistence import write_json_with_backup
from modules.theme_manager import DEFAULT_THEME, get_theme_names, normalize_theme

__module_name__ = "Settings Manager"
__version__ = "1.0.0"

def external_path(relative_path):
    return os.path.join(os.path.abspath("."), relative_path)

class SettingsManager:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.settings_path = external_path("settings.json")
        self.settings = {}
        self.entries = {}
        self.saved_theme = DEFAULT_THEME
        self.preview_theme = DEFAULT_THEME
        self.load_settings()
        self.setup_ui()

    def load_settings(self):
        if os.path.exists(self.settings_path):
            with open(self.settings_path, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = {
                "export_directory": "exports",
                "organize_exports_by_date": True,
                "default_export_prefix": "Disamatic Production Sheet",
                "theme": DEFAULT_THEME,
                "toast_duration_sec": 5,
                "auto_save_interval_min": 5,
                "default_shift_hours": 8.0,
                "default_goal_mph": 240
            }
        self.settings["theme"] = normalize_theme(self.settings.get("theme", DEFAULT_THEME))
        try:
            self.settings["toast_duration_sec"] = max(1, int(self.settings.get("toast_duration_sec", 5)))
        except Exception:
            self.settings["toast_duration_sec"] = 5
        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme

    def save_settings(self):
        for key, entry in self.entries.items():
            if isinstance(entry, tb.Checkbutton):
                self.settings[key] = entry.instate(['selected'])
            else:
                val = entry.get()
                if key in ['auto_save_interval_min', 'default_shift_hours', 'default_goal_mph', 'toast_duration_sec']:
                    try:
                        val = float(val) if '.' in val else int(val)
                    except:
                        pass
                if key == 'theme':
                    val = normalize_theme(val)
                self.settings[key] = val

        try:
            self.settings['toast_duration_sec'] = max(1, int(self.settings.get('toast_duration_sec', 5)))
        except Exception:
            self.settings['toast_duration_sec'] = 5

        backup_info = write_json_with_backup(
            self.settings_path,
            self.settings,
            backup_dir=external_path("data/backups/settings"),
            keep_count=12,
        )

        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme
        self.preview_theme = self.dispatcher.apply_theme(self.saved_theme, redraw=True)
        self.dispatcher.refresh_runtime_settings()
        
        backup_note = ""
        if backup_info.get("versioned_backup_path"):
            backup_note = " A recovery copy was stored in data/backups/settings."

        self.dispatcher.show_toast(
            "Settings Saved",
            f"Theme changes were applied immediately.{backup_note}",
            SUCCESS,
        )

    def preview_selected_theme(self, _event=None):
        theme_entry = self.entries.get('theme')
        if not theme_entry:
            return

        selected_theme = normalize_theme(theme_entry.get())
        self.preview_theme = self.dispatcher.apply_theme(selected_theme, redraw=False)
        if hasattr(self, 'theme_status'):
            self.theme_status.config(text=f"Previewing theme: {self.preview_theme}")

    def revert_theme_preview(self):
        reverted_theme = self.dispatcher.apply_theme(self.saved_theme, redraw=False)
        self.preview_theme = reverted_theme
        if 'theme' in self.entries:
            self.entries['theme'].set(reverted_theme)
        if hasattr(self, 'theme_status'):
            self.theme_status.config(text=f"Theme reverted to: {reverted_theme}")

    def on_unload(self):
        if self.preview_theme != self.saved_theme:
            self.dispatcher.apply_theme(self.saved_theme, redraw=False)

    def browse_export_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.entries['export_directory'].delete(0, END)
            self.entries['export_directory'].insert(0, dir_path)

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Application Settings", font=("-size 16 -weight bold")).pack(pady=(0, 20))

        # Build form fields
        fields = [
            ("export_directory", "Base Export Directory", "entry_browse"),
            ("organize_exports_by_date", "Organize Exports by YYYY/MM", "check"),
            ("default_export_prefix", "Default Export Prefix", "entry"),
            ("theme", "Application Theme", "combo", get_theme_names()),
            ("toast_duration_sec", "Toast Duration (Seconds)", "entry"),
            ("auto_save_interval_min", "Auto-Save Interval (Minutes)", "entry"),
            ("default_shift_hours", "Default Shift Hours", "entry"),
            ("default_goal_mph", "Default Goal MPH", "entry")
        ]

        for item in fields:
            key = item[0]
            label = item[1]
            ftype = item[2]
            
            row_frame = tb.Frame(container)
            row_frame.pack(fill=X, pady=5)
            
            tb.Label(row_frame, text=label, width=30).pack(side=LEFT)
            
            if ftype == "entry":
                ent = tb.Entry(row_frame)
                ent.insert(0, str(self.settings.get(key, "")))
                ent.pack(side=LEFT, fill=X, expand=True)
                self.entries[key] = ent
            elif ftype == "entry_browse":
                ent = tb.Entry(row_frame)
                ent.insert(0, str(self.settings.get(key, "")))
                ent.pack(side=LEFT, fill=X, expand=True)
                tb.Button(row_frame, text="Browse", bootstyle=SECONDARY, command=self.browse_export_dir).pack(side=LEFT, padx=5)
                self.entries[key] = ent
            elif ftype == "check":
                chk = tb.Checkbutton(row_frame, bootstyle="round-toggle")
                if self.settings.get(key, False):
                    chk.state(['selected'])
                chk.pack(side=LEFT)
                self.entries[key] = chk
            elif ftype == "combo":
                opts = item[3]
                cb = tb.Combobox(row_frame, values=opts, state="readonly")
                cb.set(self.settings.get(key, opts[0]))
                cb.pack(side=LEFT, fill=X, expand=True)
                if key == 'theme':
                    cb.bind("<<ComboboxSelected>>", self.preview_selected_theme)
                self.entries[key] = cb

        theme_controls = tb.Frame(container)
        theme_controls.pack(fill=X, pady=(5, 10))
        tb.Button(theme_controls, text="Revert Theme Preview", bootstyle=SECONDARY, command=self.revert_theme_preview).pack(side=LEFT)
        self.theme_status = tb.Label(theme_controls, text=f"Current theme: {self.saved_theme}", bootstyle=SECONDARY)
        self.theme_status.pack(side=LEFT, padx=10)

        tb.Button(container, text="Save Settings", bootstyle=SUCCESS, command=self.save_settings).pack(pady=20)

def get_ui(parent, dispatcher):
    return SettingsManager(parent, dispatcher)
