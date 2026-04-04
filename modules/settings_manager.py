# The Martin Suite (GLC Edition)
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog
import json
import os
import sys
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
                "auto_save_interval_min": 5,
                "default_shift_hours": 8.0,
                "default_goal_mph": 240
            }
        self.settings["theme"] = normalize_theme(self.settings.get("theme", DEFAULT_THEME))

    def save_settings(self):
        for key, entry in self.entries.items():
            if isinstance(entry, tb.Checkbutton):
                self.settings[key] = entry.instate(['selected'])
            else:
                val = entry.get()
                if key in ['auto_save_interval_min', 'default_shift_hours', 'default_goal_mph']:
                    try:
                        val = float(val) if '.' in val else int(val)
                    except:
                        pass
                self.settings[key] = val

        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=4)
        
        Messagebox.show_info("Settings saved! Some changes (like Theme) will apply on next restart.", "Success")

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
                self.entries[key] = cb

        tb.Button(container, text="Save Settings", bootstyle=SUCCESS, command=self.save_settings).pack(pady=20)

def get_ui(parent, dispatcher):
    return SettingsManager(parent, dispatcher)
