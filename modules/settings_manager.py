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
from copy import deepcopy
from modules.app_logging import log_exception
from modules.persistence import write_json_with_backup
from modules.downtime_codes import DEFAULT_DT_CODE_MAP, clear_downtime_code_cache
from modules.theme_manager import DEFAULT_THEME, get_theme_names, normalize_theme
from modules.utils import external_path

__module_name__ = "Settings Manager"
__version__ = "1.1.4"

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
                "enable_screen_transitions": True,
                "screen_transition_duration_ms": 360,
                "toast_duration_sec": 5,
                "auto_save_interval_min": 5,
                "default_shift_hours": 8.0,
                "default_goal_mph": 240,
                "downtime_codes": deepcopy(DEFAULT_DT_CODE_MAP)
            }
        if not isinstance(self.settings.get("downtime_codes"), dict):
            self.settings["downtime_codes"] = deepcopy(DEFAULT_DT_CODE_MAP)
        else:
            normalized_codes = deepcopy(DEFAULT_DT_CODE_MAP)
            for raw_code, raw_label in self.settings["downtime_codes"].items():
                code = str(raw_code).strip()
                if not code:
                    continue
                label = str(raw_label or "").strip()
                if not label:
                    continue
                normalized_codes[code] = label
            self.settings["downtime_codes"] = normalized_codes
        self.settings["theme"] = normalize_theme(self.settings.get("theme", DEFAULT_THEME))
        self.settings["enable_screen_transitions"] = bool(self.settings.get("enable_screen_transitions", True))
        try:
            self.settings["screen_transition_duration_ms"] = max(0, min(500, int(self.settings.get("screen_transition_duration_ms", 360))))
        except Exception:
            self.settings["screen_transition_duration_ms"] = 360
        try:
            self.settings["toast_duration_sec"] = max(1, int(self.settings.get("toast_duration_sec", 5)))
        except Exception:
            self.settings["toast_duration_sec"] = 5
        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme

    def persist_settings(self, toast_title="Settings Saved", toast_message_prefix="Theme changes were applied immediately."):
        clear_downtime_code_cache()
        backup_info = write_json_with_backup(
            self.settings_path,
            self.settings,
            backup_dir=external_path("data/backups/settings"),
            keep_count=12,
        )

        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme
        self.preview_theme = self.dispatcher.apply_theme(self.saved_theme)
        self.dispatcher.refresh_runtime_settings()
        if hasattr(self.dispatcher.active_module_instance, 'refresh_downtime_codes'):
            self.dispatcher.active_module_instance.refresh_downtime_codes()
        
        backup_note = ""
        if backup_info.get("versioned_backup_path"):
            backup_note = " A recovery copy was stored in data/backups/settings."

        self.dispatcher.show_toast(
            toast_title,
            f"{toast_message_prefix}{backup_note}",
            SUCCESS,
        )

    def save_settings(self):
        for key, entry in self.entries.items():
            if isinstance(entry, tb.Checkbutton):
                self.settings[key] = entry.instate(['selected'])
            else:
                val = entry.get()
                if key in ['auto_save_interval_min', 'default_shift_hours', 'default_goal_mph', 'toast_duration_sec', 'screen_transition_duration_ms']:
                    try:
                        val = float(val) if '.' in val else int(val)
                    except ValueError:
                        log_exception(f"settings_manager.invalid_numeric.{key}", ValueError(f"Could not parse '{val}'"))
                if key == 'theme':
                    val = normalize_theme(val)
                self.settings[key] = val

        try:
            self.settings['toast_duration_sec'] = max(1, int(self.settings.get('toast_duration_sec', 5)))
        except Exception:
            self.settings['toast_duration_sec'] = 5
        try:
            self.settings['screen_transition_duration_ms'] = max(0, min(500, int(self.settings.get('screen_transition_duration_ms', 360))))
        except Exception:
            self.settings['screen_transition_duration_ms'] = 360

        self.persist_settings()

    def preview_selected_theme(self, _event=None):
        theme_entry = self.entries.get('theme')
        if not theme_entry:
            return

        selected_theme = normalize_theme(theme_entry.get())
        self.preview_theme = self.dispatcher.apply_theme(selected_theme)
        if hasattr(self, 'theme_status'):
            self.theme_status.config(text=f"Previewing theme: {self.preview_theme}")

    def revert_theme_preview(self):
        reverted_theme = self.dispatcher.apply_theme(self.saved_theme)
        self.preview_theme = reverted_theme
        if 'theme' in self.entries:
            self.entries['theme'].set(reverted_theme)
        if hasattr(self, 'theme_status'):
            self.theme_status.config(text=f"Theme reverted to: {reverted_theme}")

    def on_unload(self):
        if self.preview_theme != self.saved_theme:
            self.dispatcher.apply_theme(self.saved_theme)

    def browse_export_dir(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.entries['export_directory'].delete(0, END)
            self.entries['export_directory'].insert(0, dir_path)

    def open_downtime_codes_dialog(self):
        top = tb.Toplevel(title="Downtime Codes")
        top.geometry("520x520")
        top.minsize(420, 420)

        container = tb.Frame(top, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Downtime Codes", font=("-size 14 -weight bold")).pack(anchor=W)
        tb.Label(
            container,
            text="Edit existing codes or add new ones. Numeric codes are what import and export use.",
            bootstyle=SECONDARY,
            justify=LEFT,
        ).pack(anchor=W, pady=(4, 16))

        list_outer = tb.Frame(container)
        list_outer.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(list_outer, highlightthickness=0)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(list_outer, orient=VERTICAL, command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        list_frame = tb.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")

        def sync_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_window_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        list_frame.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_window_width)
        self.dispatcher.bind_mousewheel_to_widget_tree(list_outer, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(list_frame, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(canvas, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(scrollbar, canvas)

        header = tb.Frame(list_frame)
        header.pack(fill=X, pady=(0, 6))
        tb.Label(header, text="Code", width=8, bootstyle=PRIMARY).pack(side=LEFT)
        tb.Label(header, text="Label", bootstyle=PRIMARY).pack(side=LEFT)

        code_rows = []
        current_codes = self.settings.get("downtime_codes", deepcopy(DEFAULT_DT_CODE_MAP))

        def sort_key(code_text):
            return (int(code_text) if str(code_text).isdigit() else 10**9, str(code_text))

        def add_code_row(code_value="", label_value=""):
            row = tb.Frame(list_frame)
            row.pack(fill=X, pady=4)

            code_entry = tb.Entry(row, width=8)
            code_entry.insert(0, str(code_value))
            code_entry.pack(side=LEFT)

            label_entry = tb.Entry(row)
            label_entry.insert(0, str(label_value))
            label_entry.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))

            remove_button = tb.Button(row, text="Remove", bootstyle=DANGER, width=8)
            remove_button.pack(side=RIGHT, padx=(8, 0))

            row_record = {
                "frame": row,
                "code_entry": code_entry,
                "label_entry": label_entry,
                "remove_button": remove_button,
            }

            def remove_row():
                if len(code_rows) <= 1:
                    code_entry.delete(0, END)
                    label_entry.delete(0, END)
                    return
                row.destroy()
                code_rows.remove(row_record)
                sync_scroll_region()

            remove_button.configure(command=remove_row)
            code_rows.append(row_record)
            self.dispatcher.bind_mousewheel_to_widget_tree(row, canvas)
            sync_scroll_region()

        for code in sorted(current_codes, key=sort_key):
            add_code_row(code, current_codes[code])

        actions = tb.Frame(container)
        actions.pack(fill=X, pady=(18, 0))

        def reset_defaults():
            for row_record in list(code_rows):
                row_record["frame"].destroy()
                code_rows.remove(row_record)
            for code in sorted(DEFAULT_DT_CODE_MAP, key=sort_key):
                add_code_row(code, DEFAULT_DT_CODE_MAP[code])

        def add_next_code():
            numeric_codes = [int(record["code_entry"].get().strip()) for record in code_rows if record["code_entry"].get().strip().isdigit()]
            next_code = str(max(numeric_codes, default=0) + 1)
            add_code_row(next_code, "")

        def save_codes():
            updated_codes = {}
            for row_record in code_rows:
                code = row_record["code_entry"].get().strip()
                label = row_record["label_entry"].get().strip()
                if not code and not label:
                    continue
                if not code:
                    Messagebox.show_error("Each downtime code row needs a code number.", "Downtime Codes")
                    return
                if not code.isdigit():
                    Messagebox.show_error(f"Code '{code}' must be numeric.", "Downtime Codes")
                    return
                if not label:
                    Messagebox.show_error(f"Code {code} cannot be blank.", "Downtime Codes")
                    return
                if code in updated_codes:
                    Messagebox.show_error(f"Code {code} is duplicated.", "Downtime Codes")
                    return
                updated_codes[code] = label
            if not updated_codes:
                Messagebox.show_error("At least one downtime code is required.", "Downtime Codes")
                return
            self.settings["downtime_codes"] = updated_codes
            self.persist_settings(
                toast_title="Downtime Codes Saved",
                toast_message_prefix="Downtime code labels were updated immediately.",
            )
            top.destroy()

        tb.Button(actions, text="Reset Defaults", bootstyle=SECONDARY, command=reset_defaults).pack(side=LEFT)
        tb.Button(actions, text="Add Code", bootstyle=INFO, command=add_next_code).pack(side=LEFT, padx=(8, 0))
        tb.Button(actions, text="Cancel", bootstyle=SECONDARY, command=top.destroy).pack(side=RIGHT)
        tb.Button(actions, text="Save Codes", bootstyle=SUCCESS, command=save_codes).pack(side=RIGHT, padx=(0, 8))

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Application Settings", font=("-size 16 -weight bold")).pack(pady=(0, 20))

        # Build form fields
        fields = [
            ("export_directory", "Base Export Directory", "entry_browse"),
            ("organize_exports_by_date", "Organize Exports by Year/Month", "check"),
            ("default_export_prefix", "Default Export Prefix", "entry"),
            ("theme", "Application Theme", "combo", get_theme_names()),
            ("enable_screen_transitions", "Enable Screen Transitions", "check"),
            ("screen_transition_duration_ms", "Transition Duration (ms)", "entry"),
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

        tb.Label(
            container,
            text="Screen transitions can be disabled or tuned from 0 to 500 ms. Around 250 to 400 ms is usually enough to soften redraw flashes without feeling slow.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))

        extras = tb.Frame(container)
        extras.pack(fill=X, pady=(5, 10))
        tb.Button(extras, text="Edit Downtime Codes", bootstyle=INFO, command=self.open_downtime_codes_dialog).pack(side=LEFT)

        tb.Button(container, text="Save Settings", bootstyle=SUCCESS, command=self.save_settings).pack(pady=20)

def get_ui(parent, dispatcher):
    return SettingsManager(parent, dispatcher)
