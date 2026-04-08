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

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter.ttk as ttk
from ttkbootstrap.dialogs import Messagebox
from datetime import datetime
import json
import os
import re
import sys
import webbrowser

from modules import recovery_viewer
from modules.data_handler import DataHandler
from modules.downtime_codes import get_code_options, normalize_code_value
from modules.persistence import write_json_with_backup
from modules.theme_manager import get_theme_tokens
from modules.utils import external_path, local_or_resource_path, resource_path

__module_name__ = "Production Logging Center"
__version__ = "1.2.8"
BALANCE_DOWNTIME_CAUSE = "Time Balance Adjustment"
DEFAULT_GHOST_LABEL = "Ghost Time: 0 min"

class ProductionLog:
    def get_widget_value(self, widget):
        # Robustly extract value from Entry, Label, StringVar, or fallback
        if isinstance(widget, tk.StringVar):
            return widget.get()
        # Prefer .get() if available (Entry, custom, etc.)
        if hasattr(widget, 'get'):
            try:
                return widget.get()
            except Exception:
                pass
        # Only call .cget('text') if it's a Label and does not have .get()
        # (should never be reached for StringVar or Entry)
        # Defensive: skip .cget if .get exists
        if isinstance(widget, (tk.Label, tb.Label, ttk.Label)) and not hasattr(widget, 'get'):
            try:
                return widget.cget("text")
            except Exception:
                pass
        return str(widget)
    def __init__(self, parent, dispatcher):
        self.parent = parent 
        self.dispatcher = dispatcher
        self.theme_tokens = get_theme_tokens(root=self.parent.winfo_toplevel())
        
        # Prefer the local config so Layout Manager saves are used immediately in dev and packaged builds.
        self.config_path = local_or_resource_path("layout_config.json")

        self.dt_codes = get_code_options()
        self.data_handler = DataHandler()

        self.production_rows = []
        self.downtime_rows = []
        self.entries = {}
        
        # Load Settings defaults
        settings_path = external_path("settings.json")
        self.settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    self.settings = json.load(f)
            except Exception:
                pass
        
        self.default_hours = str(self.settings.get("default_shift_hours", 8.0))
        self.default_goal = str(self.settings.get("default_goal_mph", 240))
        # Robustly parse auto_save_interval_min, fallback to 5 if missing/invalid
        asi_raw = self.settings.get("auto_save_interval_min", 5)
        try:
            asi_int = int(str(asi_raw).strip())
            if asi_int <= 0:
                asi_int = 5
        except Exception:
            asi_int = 5
        self.auto_save_interval = asi_int * 60000
        self.current_draft_path = None
        self.latest_draft_path = None
        self.last_export_path = None
        self.has_unsaved_changes = False
        self.last_saved_signature = None

        self.setup_ui()
        self.parent.after(self.auto_save_interval, self.auto_save)

    def auto_save(self):
        if self.has_unsaved_changes and not self.is_form_blank():
            self.save_draft(is_auto=True)
        self.parent.after(self.auto_save_interval, self.auto_save) 

    def get_pending_dir(self):
        pending_dir = external_path("data/pending")
        os.makedirs(pending_dir, exist_ok=True)
        return pending_dir

    def get_pending_history_dir(self):
        history_dir = os.path.join(self.get_pending_dir(), "history")
        os.makedirs(history_dir, exist_ok=True)
        return history_dir

    def get_raw_header_data(self):
        # Use helper for all header fields
        return {fid: self.get_widget_value(ent) for fid, ent in self.entries.items()}

    def collect_header_data(self):
        # Collect and normalize header data, then inject total_molds
        header = self.data_handler.normalize_header_data(self.get_raw_header_data())
        # Calculate total_molds from production rows
        def safe_int(val):
            try:
                return int(val)
            except Exception:
                return 0
        try:
            total_molds = sum(safe_int(row["molds"].get()) for row in self.production_rows)
        except Exception:
            total_molds = 0
        header["total_molds"] = str(total_molds)
        return header

    def apply_header_data(self, header_data, mark_dirty=False):
        normalized_header = self.data_handler.normalize_header_data(header_data)
        for field_id, value in normalized_header.items():
            self.set_entry_value(field_id, value)
        if mark_dirty:
            self.mark_dirty()
        return normalized_header

    def collect_ui_data(self):
        header_data = self.collect_header_data()
        prod_data = []
        for row in self.production_rows:
            prod_data.append({
                "shop_order": self.get_widget_value(row["shop_order"]),
                "part_number": self.get_widget_value(row["part_number"]),
                "rate_lookup": self.get_widget_value(row["rate_lookup"]),
                "rate_override_enabled": bool(self.get_widget_value(row["rate_override_enabled_var"])),
                "molds": self.get_widget_value(row["molds"]),
                "time_calc": self.get_widget_value(row["time_calc"])
            })
        dt_data = []
        for row in self.downtime_rows:
            dt_row = {k: self.get_widget_value(v) for k, v in row.items()}
            dt_data.append(dt_row)
        return {"header": header_data, "production": prod_data, "downtime": dt_data}

    def serialize_ui_data(self, data=None):
        if data is None:
            data = self.collect_ui_data()
        return json.dumps(data, sort_keys=True, default=str)

    def is_form_blank(self):
        data = self.collect_ui_data()
        header = data["header"]
        significant_header_values = [
            value for key, value in header.items()
            if key not in {"hours", "goal_mph", "cast_date", "target_time"} and str(value).strip()
        ]
        production_has_data = any(
            any(str(row.get(key, "")).strip() for key in ("shop_order", "part_number", "molds"))
            for row in data["production"]
        )
        downtime_has_data = any(
            any(str(row.get(key, "")).strip() for key in ("start", "stop", "code", "cause"))
            for row in data["downtime"]
        )
        return not significant_header_values and not production_has_data and not downtime_has_data

    def mark_dirty(self, _event=None):
        self.has_unsaved_changes = True
        self.update_recovery_ui()

    def mark_clean(self, data=None):
        self.has_unsaved_changes = False
        self.last_saved_signature = self.serialize_ui_data(data)
        self.update_recovery_ui()

    def bind_dirty_tracking(self, widget, events):
        for event_name in events:
            widget.bind(event_name, self.mark_dirty, add="+")

    def row_has_input(self, row, field_names):
        for field_name in field_names:
            widget = row.get(field_name)
            if widget is None or not hasattr(widget, "get"):
                continue
            if str(widget.get()).strip():
                return True
        return False

    def ensure_open_production_row(self):
        if not self.production_rows:
            self.add_production_row()
            return
        if any(not self.row_has_input(row, ("shop_order", "part_number", "molds")) for row in self.production_rows):
            return
        self.add_production_row()

    def ensure_open_downtime_row(self):
        if not self.downtime_rows:
            self.add_downtime_row()
            return
        if any(not self.row_has_input(row, ("start", "stop", "code", "cause")) for row in self.downtime_rows):
            return
        self.add_downtime_row()

    def on_production_row_edited(self, _event=None):
        self.ensure_open_production_row()

    def on_downtime_row_edited(self, _event=None):
        self.ensure_open_downtime_row()

    def build_draft_path(self, header_data):
        raw_date = str(header_data.get("date", "unsaved") or "unsaved").replace("/", "-")
        shift_str = str(header_data.get("shift", "0") or "0")
        filename = f"draft_{raw_date}_shift{shift_str}.json"
        return os.path.join(self.get_pending_dir(), filename)

    def save_draft(self, is_auto=False, suppress_toast=False):
        try:
            data = self.collect_ui_data()
            if is_auto and not self.has_unsaved_changes:
                return
            if self.is_form_blank():
                return

            draft_path = self.build_draft_path(data["header"])
            payload = {
                "meta": {
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "auto_save": is_auto,
                    "version": __version__,
                    "draft_name": os.path.basename(draft_path),
                },
                **data,
            }

            backup_info = write_json_with_backup(
                draft_path,
                payload,
                backup_dir=self.get_pending_history_dir(),
                keep_count=20,
            )

            self.current_draft_path = draft_path
            self.mark_clean(data)

            if not is_auto and not suppress_toast:
                message = f"Draft saved to {os.path.basename(draft_path)}."
                if backup_info.get("versioned_backup_path"):
                    message += " A recovery snapshot of the previous draft was stored in data/pending/history."
                self.dispatcher.show_toast("Draft Saved", message, SUCCESS)
        except Exception as e:
            Messagebox.show_error(f"Could not save draft: {e}", "Draft Save Error")

    def setup_ui(self):
        self.build_recovery_section()
        self.build_header_section()
        self.build_production_section()
        self.build_downtime_section()
        self.build_footer_section()

        self.add_production_row()
        self.add_downtime_row()
        self.apply_header_data(self.get_raw_header_data(), mark_dirty=False)
        self.update_target_time_display()
        self.update_ghost_total_display()
        self.update_export_action_state()
        self.mark_clean()
        self.update_recovery_ui()

    def build_recovery_section(self):
        recovery_wrapper = tb.Labelframe(self.parent, text=" Draft Status ", padding=10, style="Martin.Recovery.TLabelframe")
        recovery_wrapper.pack(fill=X, padx=10, pady=(10, 0))
        self.recovery_status_lbl = tb.Label(recovery_wrapper, text="Checking draft state...", style="Martin.Muted.TLabel")
        self.recovery_status_lbl.pack(side=LEFT, padx=(0, 10))
        self.resume_latest_btn = tb.Button(recovery_wrapper, text="Resume Latest", bootstyle=PRIMARY, command=self.resume_latest_draft)
        self.resume_latest_btn.pack(side=LEFT, padx=5)
        tb.Button(recovery_wrapper, text="Pending Drafts", bootstyle=SECONDARY, command=self.show_pending).pack(side=LEFT, padx=5)
        # Add Refresh View button to reload the module and open previous draft
        tb.Button(recovery_wrapper, text="Refresh View", bootstyle=INFO, command=self.refresh_view).pack(side=LEFT, padx=5)
        self.delete_current_draft_btn = tb.Button(recovery_wrapper, text="Delete Current Draft", bootstyle=DANGER, command=self.delete_current_draft)
        self.delete_current_draft_btn.pack(side=LEFT, padx=5)

    def refresh_view(self):
        """
        Reloads the module and opens the previous draft (latest draft).
        """
        latest = self.get_latest_pending_draft()
        if latest:
            self.load_draft_path(latest["path"])
        else:
            self.dispatcher.show_toast("Refresh View", "No previous draft found to reload.", INFO)

    def build_header_section(self):
        header_wrapper = tb.Labelframe(self.parent, text=" Form 510-09: Production Logging Center Header ", padding=15, style="Martin.Card.TLabelframe")
        header_wrapper.pack(fill=X, padx=10, pady=10)
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            for field in config["header_fields"]:
                tb.Label(header_wrapper, text=field["label"], style="Martin.Section.TLabel").grid(row=field["row"], column=field["col"], padx=5, pady=5, sticky=W)
                if field["id"] == "total_molds":
                    # Display as readonly label, not entry
                    val = tk.StringVar(value="0")
                    ent = tb.Label(header_wrapper, textvariable=val, width=field.get("width", 10), style="Martin.Section.TLabel")
                    ent.grid(row=field["row"], column=field["col"]+1, padx=5, pady=5, sticky=W)
                    self.entries[field["id"]] = val
                else:
                    ent = tb.Entry(header_wrapper, width=field.get("width", 10))
                    default_val = field.get("default", "")
                    if field["id"] == "hours":
                        default_val = self.default_hours
                    elif field["id"] == "goal_mph":
                        default_val = self.default_goal
                    if default_val:
                        ent.insert(0, default_val)
                    if field.get("readonly"):
                        ent.config(state="readonly", bootstyle=INFO)
                    ent.grid(row=field["row"], column=field["col"]+1, padx=5, pady=5, sticky=W)
                    self.entries[field["id"]] = ent
                    if not field.get("readonly"):
                        self.bind_dirty_tracking(ent, ("<KeyRelease>",))
                        ent.bind("<FocusOut>", self.on_header_field_focus_out, add="+")
            if "hours" in self.entries:
                self.entries["hours"].bind("<KeyRelease>", self.on_hours_changed, add="+")
            if "goal_mph" in self.entries:
                self.entries["goal_mph"].bind("<KeyRelease>", self.on_goal_changed, add="+")
        except Exception as e:
            tb.Label(header_wrapper, text=f"Layout Error: {e}", bootstyle=DANGER).pack()

    def build_production_section(self):
        prod_wrapper = tb.Labelframe(self.parent, text=" Production Logging Center Jobs ", padding=10, style="Martin.Card.TLabelframe")
        prod_wrapper.pack(fill=X, padx=10, pady=5)
        prod_columns = tb.Frame(prod_wrapper, style="Martin.Surface.TFrame")
        prod_columns.pack(fill=X, pady=(0, 4))
        for text, width, side in (
            ("Shop Order", 12, LEFT),
            ("Part Number", 12, LEFT),
            ("Rate", 9, LEFT),
            ("Override", 7, LEFT),
            ("Molds", 8, LEFT),
            ("Time", 8, RIGHT),
        ):
            tb.Label(prod_columns, text=text, width=width, anchor=W if side == LEFT else E, style="Martin.Muted.TLabel").pack(side=side, padx=5)
        self.production_container = tb.Frame(prod_wrapper, style="Martin.Surface.TFrame")
        self.production_container.pack(fill=X)

    def build_downtime_section(self):
        dt_wrapper = tb.Labelframe(self.parent, text=" Production Logging Center Downtime Issues ", padding=10, style="Martin.Card.TLabelframe")
        dt_wrapper.pack(fill=X, padx=10, pady=5)
        self.downtime_container = tb.Frame(dt_wrapper, style="Martin.Surface.TFrame")
        self.downtime_container.pack(fill=X)

    def build_footer_section(self):
        footer = tb.Frame(self.parent, padding=20, style="Martin.Content.TFrame")
        footer.pack(fill=X)
        self.eff_display_lbl = tb.Label(footer, text="EFF%: 0.00", font=('-size 14 -weight bold'))
        self.eff_display_lbl.pack(side=LEFT, padx=10)
        self.ghost_total_lbl = tb.Label(footer, text=DEFAULT_GHOST_LABEL, font=('-size 12 -weight bold'))
        self.ghost_total_lbl.pack(side=LEFT, padx=10)
        
        tb.Button(footer, text="Calculate All", command=self.calculate_metrics, bootstyle=INFO).pack(side=RIGHT)
        tb.Button(footer, text="Save Draft", command=self.save_draft, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        tb.Button(footer, text="Save and Open", command=self.export_to_excel, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        self.open_export_btn = tb.Button(footer, text="Open Last Export", command=self.open_last_exported_file, bootstyle=INFO)
        self.open_export_btn.pack(side=LEFT, padx=5)
        self.print_export_btn = tb.Button(footer, text="Print Last Export", command=self.print_last_exported_file, bootstyle=WARNING)
        self.print_export_btn.pack(side=LEFT, padx=5)
        tb.Button(footer, text="Balance Downtime", command=self.balance_downtime_to_shift, bootstyle=WARNING).pack(side=LEFT, padx=5)
        tb.Button(footer, text="Import Excel", command=self.import_from_excel_ui, bootstyle=INFO).pack(side=LEFT, padx=5)

    def add_production_row(self):
        row_frame = tb.Frame(self.production_container)
        row_frame.pack(fill=X, pady=2)
        row = {
            "shop_order": tb.Entry(row_frame, width=12),
            "part_number": tb.Entry(row_frame, width=12),
            "rate_lookup": tb.Entry(row_frame, width=9),
            "molds": tb.Entry(row_frame, width=8),
            "time_calc": tb.Label(row_frame, text="0 min", width=8, font=('', 10, 'bold'))
        }
        row["rate_override_enabled_var"] = tk.BooleanVar(value=False)
        row["rate_override_enabled"] = tb.Checkbutton(
            row_frame,
            variable=row["rate_override_enabled_var"],
            command=lambda current_row=row: self.on_rate_override_toggled(current_row),
        )
        # Add delete button at the start
        del_btn = tb.Button(row_frame, text="✖", width=2, bootstyle=DANGER, command=lambda r=row: self.delete_production_row_with_save_reload(r))
        del_btn.pack(side=LEFT, padx=(0, 2))
        row["_delete_btn"] = del_btn
        row["rate_lookup"].config(state="readonly")
        for key in ("shop_order", "part_number", "rate_lookup", "rate_override_enabled", "molds"):
            row[key].pack(side=LEFT, padx=5)
        row["time_calc"].pack(side=RIGHT, padx=10)
        
        row["part_number"].bind("<KeyRelease>", lambda e: self.update_row_math(), add="+")
        row["rate_lookup"].bind("<KeyRelease>", lambda e: self.update_row_math(), add="+")
        row["molds"].bind("<KeyRelease>", lambda e: self.update_row_math(), add="+")
        row["shop_order"].bind("<KeyRelease>", self.on_production_row_edited, add="+")
        self.bind_dirty_tracking(row["shop_order"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["part_number"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["rate_lookup"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["molds"], ("<KeyRelease>",))
        self.production_rows.append(row)
        self.update_ghost_total_display()
        return row

    def add_downtime_row(self):
        row_frame = tb.Frame(self.downtime_container)
        row_frame.pack(fill=X, pady=2)
        row = {
            "start": tb.Entry(row_frame, width=8),
            "stop": tb.Entry(row_frame, width=8),
            "code": tb.Combobox(row_frame, values=self.dt_codes, width=18, state="readonly"),
            "cause": tb.Entry(row_frame),
            "time_calc": tb.Label(row_frame, text="0 min", width=8, foreground="red", font=('', 10, 'bold'))
        }
        # Add delete button at the start
        del_btn = tb.Button(row_frame, text="✖", width=2, bootstyle=DANGER, command=lambda r=row: self.delete_downtime_row_with_save_reload(r))
        del_btn.pack(side=LEFT, padx=(0, 2))
        row["_delete_btn"] = del_btn
        row["start"].pack(side=LEFT, padx=5)
        row["stop"].pack(side=LEFT, padx=5)
        row["code"].pack(side=LEFT, padx=5)
        row["time_calc"].pack(side=RIGHT, padx=10)
        row["cause"].pack(side=LEFT, fill=X, expand=True, padx=5)
        
        row["start"].bind("<KeyRelease>", lambda e: self.update_row_math(), add="+")
        row["stop"].bind("<KeyRelease>", lambda e: self.update_row_math(), add="+")
        row["code"].bind("<<ComboboxSelected>>", self.mark_dirty, add="+")
        row["code"].bind("<<ComboboxSelected>>", self.on_downtime_row_edited, add="+")
        row["cause"].bind("<KeyRelease>", self.on_downtime_row_edited, add="+")
        self.bind_dirty_tracking(row["start"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["stop"], ("<KeyRelease>",))
        self.bind_dirty_tracking(row["cause"], ("<KeyRelease>",))
        self.downtime_rows.append(row)
        return row

    def delete_production_row_with_save_reload(self, row):
        # Save draft, delete row from draft file, reload draft (no toast)
        self.save_draft(suppress_toast=True)
        if self.current_draft_path and os.path.exists(self.current_draft_path):
            try:
                with open(self.current_draft_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Find the index of the row to delete by matching unique fields
                prod_data = data.get('production', [])
                # Try to match by all fields in the row
                def row_match(d):
                    return (
                        str(d.get('shop_order', '')) == str(self.get_widget_value(row['shop_order'])) and
                        str(d.get('part_number', '')) == str(self.get_widget_value(row['part_number'])) and
                        str(d.get('rate_lookup', '')) == str(self.get_widget_value(row['rate_lookup'])) and
                        str(d.get('molds', '')) == str(self.get_widget_value(row['molds'])) and
                        str(d.get('time_calc', '')) == str(self.get_widget_value(row['time_calc']))
                    )
                idx = next((i for i, d in enumerate(prod_data) if row_match(d)), None)
                if idx is not None:
                    del prod_data[idx]
                    data['production'] = prod_data
                    with open(self.current_draft_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                Messagebox.show_error(f"Could not update draft after row delete: {e}", "Draft Update Error")
            self.load_draft_path(self.current_draft_path)


    def delete_downtime_row_with_save_reload(self, row):
        # Save draft, delete row from draft file, reload draft (no toast)
        self.save_draft(suppress_toast=True)
        if self.current_draft_path and os.path.exists(self.current_draft_path):
            try:
                with open(self.current_draft_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                dt_data = data.get('downtime', [])
                def row_match(d):
                    return (
                        str(d.get('start', '')) == str(self.get_widget_value(row['start'])) and
                        str(d.get('stop', '')) == str(self.get_widget_value(row['stop'])) and
                        str(d.get('code', '')) == str(self.get_widget_value(row['code'])) and
                        str(d.get('cause', '')) == str(self.get_widget_value(row['cause'])) and
                        str(d.get('time_calc', '')) == str(self.get_widget_value(row['time_calc']))
                    )
                idx = next((i for i, d in enumerate(dt_data) if row_match(d)), None)
                if idx is not None:
                    del dt_data[idx]
                    data['downtime'] = dt_data
                    with open(self.current_draft_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                Messagebox.show_error(f"Could not update draft after row delete: {e}", "Draft Update Error")
            self.load_draft_path(self.current_draft_path)

    def refresh_downtime_codes(self):
        self.dt_codes = get_code_options()
        for row in self.downtime_rows:
            code_widget = row.get("code")
            if code_widget is None:
                continue
            current_value = normalize_code_value(code_widget.get())
            code_widget.configure(values=self.dt_codes)
            if current_value:
                code_widget.set(current_value)

    def parse_minutes_label(self, value):
        text = str(value or "").strip().lower().replace(" min", "")
        try:
            return int(float(text))
        except Exception:
            return 0

    def on_hours_changed(self, _event=None):
        self.update_target_time_display()
        self.calculate_metrics()

    def on_goal_changed(self, _event=None):
        self.update_row_math()
        self.calculate_metrics()

    def on_header_field_focus_out(self, _event=None):
        self.apply_header_data(self.get_raw_header_data(), mark_dirty=False)

    def load_rates_data(self):
        rates_data = {}
        rates_path = local_or_resource_path("rates.json")
        if os.path.exists(rates_path):
            try:
                with open(rates_path, 'r', encoding='utf-8') as rate_file:
                    loaded_rates = json.load(rate_file)
                if isinstance(loaded_rates, dict):
                    for part_number, rate in loaded_rates.items():
                        for lookup_key in self.build_part_lookup_keys(part_number):
                            if lookup_key not in rates_data:
                                rates_data[lookup_key] = rate
            except Exception:
                pass
        return rates_data

    def get_global_goal_rate(self):
        try:
            return float(self.entries["goal_mph"].get() or 240)
        except Exception:
            return 240

    def format_rate_value(self, value):
        try:
            numeric_value = float(value)
        except Exception:
            return ""
        if numeric_value.is_integer():
            return str(int(numeric_value))
        return f"{numeric_value:.2f}".rstrip("0").rstrip(".")

    def normalize_part_number(self, value):
        part_text = str(value or "").strip().upper()
        return " ".join(part_text.split())

    def strip_leading_zeros_from_segments(self, value):
        def replace_match(match):
            digits = match.group(0)
            stripped = digits.lstrip("0")
            return stripped or "0"

        return re.sub(r"\d+", replace_match, value)

    def build_part_lookup_keys(self, value):
        normalized = self.normalize_part_number(value)
        if not normalized:
            return []

        candidates = []
        compact = normalized.replace(" ", "")
        zero_normalized = self.strip_leading_zeros_from_segments(normalized)
        zero_compact = self.strip_leading_zeros_from_segments(compact)

        for candidate in (normalized, compact, zero_normalized, zero_compact):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        return candidates

    def resolve_lookup_rate(self, part_number, rates_data, global_goal):
        part_keys = self.build_part_lookup_keys(part_number)
        if not part_keys:
            return None

        raw_rate = None
        for part_key in part_keys:
            if part_key in rates_data:
                raw_rate = rates_data[part_key]
                break
        if raw_rate is None:
            raw_rate = global_goal
        try:
            return float(raw_rate)
        except Exception:
            return None

    def set_rate_lookup_value(self, row, value, editable=False):
        rate_entry = row["rate_lookup"]
        rate_entry.config(state="normal")
        rate_entry.delete(0, END)
        rate_entry.insert(0, value)
        rate_entry.config(state=("normal" if editable else "readonly"))

    def get_row_rate(self, row, rates_data, global_goal):
        if bool(row["rate_override_enabled_var"].get()):
            try:
                return float(row["rate_lookup"].get().strip())
            except Exception:
                return None
        return self.resolve_lookup_rate(row["part_number"].get(), rates_data, global_goal)

    def on_rate_override_toggled(self, row):
        override_enabled = bool(row["rate_override_enabled_var"].get())
        if override_enabled:
            lookup_rate = self.resolve_lookup_rate(
                row["part_number"].get(),
                self.load_rates_data(),
                self.get_global_goal_rate(),
            )
            current_value = row["rate_lookup"].get().strip() or self.format_rate_value(lookup_rate)
            self.set_rate_lookup_value(row, current_value, editable=True)
            row["rate_lookup"].focus_set()
            row["rate_lookup"].selection_range(0, END)
        else:
            self.set_rate_lookup_value(row, self.format_rate_value(self.resolve_lookup_rate(
                row["part_number"].get(),
                self.load_rates_data(),
                self.get_global_goal_rate(),
            )), editable=False)
        self.mark_dirty()
        self.update_row_math()

    def update_target_time_display(self):
        target_time_entry = self.entries.get("target_time")
        if target_time_entry is None:
            return
        target_value = self.data_handler.compute_target_time(self.entries.get("hours").get() if self.entries.get("hours") else "")
        # Only call .cget('state') if widget supports it
        original_state = None
        if hasattr(target_time_entry, 'cget'):
            try:
                original_state = target_time_entry.cget("state")
            except Exception:
                original_state = None
        if original_state == "readonly":
            target_time_entry.config(state="normal")
        if hasattr(target_time_entry, 'delete') and hasattr(target_time_entry, 'insert'):
            target_time_entry.delete(0, END)
            target_time_entry.insert(0, target_value)
        if original_state == "readonly":
            target_time_entry.config(state="readonly")

    def update_ghost_total_display(self):
        if not hasattr(self, "ghost_total_lbl"):
            return
        ghost_minutes = self.get_ghost_time_minutes()
        if ghost_minutes > 0:
            message = f"Ghost Time: {ghost_minutes} min missing"
            bootstyle = DANGER
        elif ghost_minutes < 0:
            message = f"Ghost Time: {abs(ghost_minutes)} min extra"
            bootstyle = SUCCESS
        else:
            message = "Ghost Time: 0 min"
            bootstyle = SECONDARY
        self.ghost_total_lbl.config(text=message, bootstyle=bootstyle)

    def parse_clock_value(self, value):
        text = str(value or "").strip()
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        digits = digits.zfill(4)[-4:]
        hours = int(digits[:2])
        minutes = int(digits[2:])
        if hours > 23 or minutes > 59:
            return None
        return hours * 60 + minutes

    def format_clock_value(self, total_minutes):
        normalized = int(total_minutes) % (24 * 60)
        return f"{normalized // 60:02}{normalized % 60:02}"

    def get_row_duration_minutes(self, row):
        start_minutes = self.parse_clock_value(row["start"].get())
        stop_minutes = self.parse_clock_value(row["stop"].get())
        if start_minutes is not None and stop_minutes is not None:
            if stop_minutes < start_minutes:
                stop_minutes += 24 * 60
            return stop_minutes - start_minutes
        # Robustly get time_calc text
        tc = row["time_calc"]
        val = self.get_widget_value(tc)
        return self.parse_minutes_label(val)

    def is_balance_downtime_row(self, row):
        return row["cause"].get().strip() == BALANCE_DOWNTIME_CAUSE

    def find_balance_downtime_row(self):
        for row in self.downtime_rows:
            if self.is_balance_downtime_row(row):
                return row
        return None

    def remove_downtime_row(self, row):
        row["start"].master.destroy()
        if row in self.downtime_rows:
            self.downtime_rows.remove(row)

    def set_downtime_row_duration(self, row, duration_minutes, set_balance_metadata=False):
        duration_minutes = max(0, int(duration_minutes))
        start_minutes = self.parse_clock_value(row["start"].get())
        if start_minutes is None:
            start_minutes = 0
            row["start"].delete(0, END)
            row["start"].insert(0, self.format_clock_value(start_minutes))

        row["stop"].delete(0, END)
        row["stop"].insert(0, self.format_clock_value(start_minutes + duration_minutes))
        if set_balance_metadata:
            if not row["code"].get().strip() and self.dt_codes:
                row["code"].set(normalize_code_value(self.dt_codes[0]))
            row["cause"].delete(0, END)
            row["cause"].insert(0, BALANCE_DOWNTIME_CAUSE)

    def get_shift_total_minutes(self):
        try:
            return int(round(float(self.entries["hours"].get() or 0) * 60))
        except Exception:
            return 0

    def get_production_total_minutes(self):
        total = 0
        for row in self.production_rows:
            tc = row["time_calc"]
            val = self.get_widget_value(tc)
            total += self.parse_minutes_label(val)
        return total

    def get_total_downtime_minutes(self):
        return sum(self.get_row_duration_minutes(row) for row in self.downtime_rows)

    def get_ghost_time_minutes(self):
        shift_total = self.get_shift_total_minutes()
        if shift_total <= 0:
            return 0
        return shift_total - self.get_production_total_minutes() - self.get_total_downtime_minutes()

    def get_manual_downtime_total_minutes(self):
        return sum(self.get_row_duration_minutes(row) for row in self.downtime_rows if not self.is_balance_downtime_row(row))

    def get_weighted_downtime_rows(self):
        weighted_rows = []
        for row in self.downtime_rows:
            if self.is_balance_downtime_row(row):
                continue
            duration = self.get_row_duration_minutes(row)
            if duration > 0:
                weighted_rows.append((row, duration))
        return weighted_rows

    def allocate_weighted_minutes(self, weighted_rows, target_total_minutes):
        target_total_minutes = max(0, int(target_total_minutes))
        total_weight = sum(duration for _, duration in weighted_rows)
        if total_weight <= 0:
            return []

        allocations = []
        used_minutes = 0
        for row, duration in weighted_rows:
            exact = target_total_minutes * (duration / total_weight)
            allocated = int(exact)
            allocations.append({
                "row": row,
                "allocated": allocated,
                "remainder": exact - allocated,
            })
            used_minutes += allocated

        leftover = target_total_minutes - used_minutes
        for item in sorted(allocations, key=lambda entry: entry["remainder"], reverse=True):
            if leftover <= 0:
                break
            item["allocated"] += 1
            leftover -= 1

        return allocations

    def build_downtime_timeline(self, weighted_rows):
        timeline = []
        day_offset = 0
        previous_start = None
        for row, _duration in weighted_rows:
            start_minutes = self.parse_clock_value(row["start"].get())
            absolute_start = None
            if start_minutes is not None:
                if previous_start is not None and start_minutes < previous_start:
                    day_offset += 24 * 60
                absolute_start = day_offset + start_minutes
                previous_start = start_minutes
            timeline.append({
                "row": row,
                "start_absolute": absolute_start,
            })
        return timeline

    def apply_spillover_allocations(self, weighted_rows, target_total_minutes):
        allocations = self.allocate_weighted_minutes(weighted_rows, target_total_minutes)
        timeline = self.build_downtime_timeline(weighted_rows)
        spill_minutes = 0

        for index, (timeline_item, allocation_item) in enumerate(zip(timeline, allocations)):
            row = timeline_item["row"]
            desired_minutes = allocation_item["allocated"] + spill_minutes
            spill_minutes = 0

            actual_minutes = desired_minutes
            current_start = timeline_item["start_absolute"]
            next_start = timeline[index + 1]["start_absolute"] if index + 1 < len(timeline) else None
            if current_start is not None and next_start is not None:
                max_minutes = max(0, next_start - current_start)
                if actual_minutes > max_minutes:
                    spill_minutes = actual_minutes - max_minutes
                    actual_minutes = max_minutes

            self.set_downtime_row_duration(row, actual_minutes, set_balance_metadata=False)

        if spill_minutes > 0 and timeline:
            last_row = timeline[-1]["row"]
            last_duration = self.get_row_duration_minutes(last_row)
            self.set_downtime_row_duration(last_row, last_duration + spill_minutes, set_balance_metadata=False)

    def apply_weighted_downtime_balance(self, target_total_minutes):
        weighted_rows = self.get_weighted_downtime_rows()
        if not weighted_rows:
            return False

        balance_row = self.find_balance_downtime_row()
        if balance_row is not None:
            self.remove_downtime_row(balance_row)

        self.apply_spillover_allocations(weighted_rows, target_total_minutes)
        return True

    def balance_downtime_to_shift(self):
        self.update_row_math()

        shift_total = self.get_shift_total_minutes()
        production_total = self.get_production_total_minutes()
        current_downtime_total = self.get_total_downtime_minutes()
        ghost_minutes = self.get_ghost_time_minutes()
        target_downtime_total = shift_total - production_total
        delta_minutes = target_downtime_total - current_downtime_total
        balance_row = self.find_balance_downtime_row()

        if shift_total <= 0:
            self.dispatcher.show_toast("Balance Downtime", "Enter a valid shift hour value before balancing.", WARNING)
            return

        if ghost_minutes < 0:
            self.dispatcher.show_toast(
                "Balance Downtime",
                f"Accounted time exceeds the shift total by {abs(ghost_minutes)} minutes. Review or remove downtime manually before export.",
                WARNING,
            )
            return

        if target_downtime_total == 0:
            self.dispatcher.show_toast(
                "Balance Downtime",
                "Accounted time already matches the shift total.",
                INFO,
            )
            return

        if delta_minutes < 0:
            self.dispatcher.show_toast(
                "Balance Downtime",
                f"Recorded downtime exceeds the remaining shift time by {abs(delta_minutes)} minutes. Remove downtime manually if you want to rebalance.",
                WARNING,
            )
            return

        if self.apply_weighted_downtime_balance(target_downtime_total):
            self.update_row_math()
            self.mark_dirty()
            if delta_minutes > 0:
                message = f"Added {delta_minutes} downtime minutes across the existing downtime rows to match the shift total."
            else:
                message = "Existing downtime rows already matched the shift total."
            self.dispatcher.show_toast(
                "Balance Downtime",
                message,
                SUCCESS,
            )
            return

        if balance_row is None:
            balance_row = self.add_downtime_row()

        self.set_downtime_row_duration(balance_row, target_downtime_total, set_balance_metadata=True)
        self.update_row_math()
        self.mark_dirty()
        if delta_minutes > 0:
            message = f"Added {delta_minutes} downtime minutes to the balance row because there were no existing downtime durations to distribute."
        elif delta_minutes < 0:
            message = f"Removed {abs(delta_minutes)} downtime minutes from the balance row to match the shift total."
        else:
            message = "The downtime balance row already matched the shift total."
        self.dispatcher.show_toast(
            "Balance Downtime",
            message,
            SUCCESS,
        )

    def set_entry_value(self, field_id, value):
        if field_id not in self.entries:
            return
        entry = self.entries[field_id]
        # Only call .cget('state') if widget supports it
        original_state = None
        if hasattr(entry, 'cget'):
            try:
                original_state = entry.cget("state")
            except Exception:
                original_state = None
        if original_state == "readonly":
            entry.config(state="normal")
        if hasattr(entry, 'delete') and hasattr(entry, 'insert'):
            entry.delete(0, END)
            entry.insert(0, str(value) if value is not None else "")
        if original_state == "readonly":
            entry.config(state="readonly")

    def clear_dynamic_rows(self):
        for widget in self.production_container.winfo_children():
            widget.destroy()
        self.production_rows.clear()

        for widget in self.downtime_container.winfo_children():
            widget.destroy()
        self.downtime_rows.clear()

    def populate_from_data(self, data, source_path=None, mark_dirty_after_load=False):
        self.apply_header_data(data.get("header", {}), mark_dirty=False)

        self.clear_dynamic_rows()

        for p_data in data.get("production", []):
            current_row = self.add_production_row()
            for key, val in p_data.items():
                if key == "rate_override_enabled":
                    current_row["rate_override_enabled_var"].set(str(val).strip().lower() in {"1", "true", "yes", "on"})
                    continue
                if key == "rate_lookup":
                    self.set_rate_lookup_value(current_row, str(val) if val is not None else "", editable=True)
                    continue
                if key in current_row and hasattr(current_row[key], 'insert'):
                    current_row[key].delete(0, END)
                    current_row[key].insert(0, str(val) if val is not None else "")
            if current_row["rate_override_enabled_var"].get():
                current_row["rate_lookup"].config(state="normal")

        for d_data in data.get("downtime", []):
            current_row = self.add_downtime_row()
            for key, val in d_data.items():
                if key in current_row:
                    widget = current_row[key]
                    if hasattr(widget, 'set'):
                        widget.set(str(val) if val is not None else "")
                    elif hasattr(widget, 'insert'):
                        widget.delete(0, END)
                        widget.insert(0, str(val) if val is not None else "")

        if not self.production_rows:
            self.add_production_row()
        if not self.downtime_rows:
            self.add_downtime_row()

        self.update_row_math()
        self.calculate_metrics()
        self.update_target_time_display()
        self.update_ghost_total_display()
        self.current_draft_path = source_path
        if mark_dirty_after_load:
            self.mark_dirty()
        else:
            self.mark_clean(data)

    def list_pending_drafts(self):
        drafts = []
        pending_dir = self.get_pending_dir()
        for filename in os.listdir(pending_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(pending_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                saved_at = meta.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
                header = data.get("header", {})
                drafts.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": saved_at,
                    "date": header.get("date", ""),
                    "shift": header.get("shift", ""),
                })
            except Exception:
                drafts.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
                    "date": "",
                    "shift": "",
                })
        drafts.sort(key=lambda item: item["saved_at"], reverse=True)
        return drafts

    def list_recovery_snapshots(self):
        snapshots = []
        history_dir = self.get_pending_history_dir()
        for filename in os.listdir(history_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(history_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                saved_at = meta.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
                header = data.get("header", {})
                snapshots.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": saved_at,
                    "date": header.get("date", ""),
                    "shift": header.get("shift", ""),
                    "source": "Recovery Snapshot",
                })
            except Exception:
                snapshots.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
                    "date": "",
                    "shift": "",
                    "source": "Recovery Snapshot",
                })
        snapshots.sort(key=lambda item: item["saved_at"], reverse=True)
        return snapshots

    def get_latest_pending_draft(self):
        drafts = self.list_pending_drafts()
        return drafts[0] if drafts else None

    def update_recovery_ui(self):
        drafts = self.list_pending_drafts()
        recovery_snapshots = self.list_recovery_snapshots()
        latest = drafts[0] if drafts else None
        self.latest_draft_path = latest["path"] if latest else None
        current_name = os.path.basename(self.current_draft_path) if self.current_draft_path else "No active draft"
        pending_count = len(drafts)
        snapshot_count = len(recovery_snapshots)
        dirty_text = "Unsaved changes" if self.has_unsaved_changes else "Saved"

        if latest:
            latest_text = f"Latest: {latest['filename']} ({latest['saved_at']})"
        else:
            latest_text = "No pending drafts"

        self.recovery_status_lbl.config(text=f"{latest_text} | Current: {current_name} | State: {dirty_text} | Pending: {pending_count} | Recovery: {snapshot_count}")
        self.resume_latest_btn.config(state=(NORMAL if latest else DISABLED))
        self.delete_current_draft_btn.config(state=(NORMAL if self.current_draft_path and os.path.exists(self.current_draft_path) else DISABLED))

    def confirm_discard_unsaved_changes(self):
        if not self.has_unsaved_changes:
            return True
        return messagebox.askyesno("Unsaved Changes", "You have unsaved changes in the current session. Continue and discard them?")

    def resume_latest_draft(self):
        latest = self.get_latest_pending_draft()
        if not latest:
            self.dispatcher.show_toast("Resume Latest", "No pending drafts are available.", INFO)
            return
        self.load_draft_path(latest["path"])

    def open_recovery_viewer(self):
        top = tb.Toplevel(title="Backup / Recovery")
        top.geometry("980x620")
        top.minsize(820, 520)
        recovery_viewer.get_ui(top, self.dispatcher)

    def delete_current_draft(self):
        if not self.current_draft_path or not os.path.exists(self.current_draft_path):
            self.dispatcher.show_toast("Delete Draft", "There is no saved draft attached to the current session.", INFO)
            return
        if not messagebox.askyesno("Delete Current Draft", f"Delete {os.path.basename(self.current_draft_path)}?"):
            return
        self.delete_draft_file(self.current_draft_path)
        self.current_draft_path = None
        self.mark_dirty()

    def delete_draft_file(self, draft_path):
        if os.path.exists(draft_path):
            os.remove(draft_path)
        if self.current_draft_path == draft_path:
            self.current_draft_path = None
        self.update_recovery_ui()

    def load_draft_path(self, draft_path, window=None):
        if not self.confirm_discard_unsaved_changes():
            return
        try:
            with open(draft_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.populate_from_data(data, source_path=draft_path, mark_dirty_after_load=False)
        except Exception as e:
            Messagebox.show_error(f"Error loading draft: {e}", "Draft Load Error")
        if window is not None:
            window.destroy()

    def update_row_math(self):
        rates_data = self.load_rates_data()
        global_goal = self.get_global_goal_rate()

        total_molds = 0
        for row in self.production_rows:
            if not bool(row["rate_override_enabled_var"].get()):
                lookup_rate = self.resolve_lookup_rate(row["part_number"].get(), rates_data, global_goal)
                self.set_rate_lookup_value(row, self.format_rate_value(lookup_rate), editable=False)
            try:
                molds = float(row["molds"].get() or 0)
                total_molds += int(molds)
                rate = self.get_row_rate(row, rates_data, global_goal)
                minutes = (molds / rate) * 60 if rate and rate > 0 else 0
                row["time_calc"].config(text=f"{int(minutes)} min")
            except Exception:
                row["time_calc"].config(text="0 min")
        # Update total_molds header field if present
        if "total_molds" in self.entries:
            entry = self.entries["total_molds"]
            if hasattr(entry, "set"):
                entry.set(str(total_molds))

        for row in self.downtime_rows:
            try:
                s_raw, e_raw = row["start"].get().zfill(4), row["stop"].get().zfill(4)
                if len(s_raw) == 4 and len(e_raw) == 4:
                    s_m = int(s_raw[:2])*60 + int(s_raw[2:])
                    e_m = int(e_raw[:2])*60 + int(e_raw[2:])
                    diff = (e_m - s_m) if e_m >= s_m else (1440 - s_m + e_m)
                    row["time_calc"].config(text=f"{diff} min")
            except Exception:
                row["time_calc"].config(text="--")

        self.ensure_open_production_row()
        self.ensure_open_downtime_row()
        self.update_target_time_display()
        self.update_ghost_total_display()

    def calculate_metrics(self):
        def safe_int(val):
            try:
                return int(val)
            except Exception:
                return 0
        try:
            total_molds = sum(safe_int(row["molds"].get()) for row in self.production_rows)
            hours = float(self.entries["hours"].get() or 8.0)
            goal = float(self.entries["goal_mph"].get() or 240)
            eff = (total_molds / (hours * goal)) * 100 if hours and goal else 0
            self.eff_display_lbl.config(text=f"EFF%: {eff:.2f}")
        except Exception:
            pass
        self.update_target_time_display()
        self.update_ghost_total_display()

    def export_to_excel(self):
        ghost_minutes = self.get_ghost_time_minutes()
        if ghost_minutes != 0:
            if messagebox.askyesno("Unbalanced Time", f"Your accounted time is off by {abs(ghost_minutes)} minutes. Do you want to Auto-Balance your downtime before exporting?"):
                self.balance_downtime_to_shift()

        try:
            from modules.data_handler import DataHandler
            handler = DataHandler()
            ui_data = self.collect_ui_data()
            shift = ui_data["header"].get("shift", "0")
            date = ui_data["header"].get("date", "00-00-00").replace("/", "")
            target_path = handler.export_to_template(ui_data, shift, date)
            self.last_export_path = target_path
            self.update_export_action_state()
            self.dispatcher.show_toast(
                "Export Complete",
                f"Excel export completed successfully: {os.path.basename(target_path)}",
                SUCCESS,
            )

            # Always open the file automatically after export
            self.open_last_exported_file(show_prompt=False)
        except Exception as e:
            Messagebox.show_error(f"Export failed: {e}", "Error")

    def get_last_export_path(self):
        if self.last_export_path and os.path.exists(self.last_export_path):
            return self.last_export_path
        return None

    def update_export_action_state(self):
        state = NORMAL if self.get_last_export_path() else DISABLED
        if hasattr(self, "open_export_btn"):
            self.open_export_btn.config(state=state)
        if hasattr(self, "print_export_btn"):
            self.print_export_btn.config(state=state)

    def open_last_exported_file(self, show_prompt=True):
        export_path = self.get_last_export_path()
        if not export_path:
            if show_prompt:
                Messagebox.show_error("No exported workbook is available yet.", "Open Export")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(export_path)
            else:
                webbrowser.open(export_path)
        except Exception as e:
            Messagebox.show_error(f"Could not open exported workbook: {e}", "Open Export")

    def print_last_exported_file(self):
        export_path = self.get_last_export_path()
        if not export_path:
            Messagebox.show_error("Export a workbook first so there is something to print.", "Print Export")
            return

        if not messagebox.askyesno(
            "Print Export",
            f"Print this workbook using the default application print action?\n\n{export_path}\n\nReview it first with 'Open Last Export' if needed.",
        ):
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(export_path, "print")
                self.dispatcher.show_toast("Printing", "Sent Excel file to the default printer.", INFO)
            else:
                self.open_last_exported_file(show_prompt=False)
                self.dispatcher.show_toast("Print Review", "Opened the exported workbook for manual printing in the default application.", INFO)
        except Exception as e:
            Messagebox.show_error(f"Could not print exported workbook: {e}", "Print Export")

    def show_pending(self):
        top = tb.Toplevel(title="Pending Drafts")
        top.geometry("560x420")
        drafts = self.list_pending_drafts()
        if not drafts:
            tb.Label(top, text="No pending drafts found.").pack(pady=20)
            return

        outer = tb.Frame(top, padding=10)
        outer.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, background=self.theme_tokens["canvas_bg"])
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = tb.Scrollbar(outer, orient=VERTICAL, command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        container = tb.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")

        def sync_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_window_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        container.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_window_width)

        tb.Label(container, text="Pending Drafts", font=("TkDefaultFont", 10, "bold"), bootstyle=PRIMARY).pack(anchor=W, pady=(0, 6))
        for draft in drafts:
            self.add_pending_draft_card(container, draft, top)
        self.dispatcher.bind_mousewheel_to_widget_tree(canvas, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(container, canvas)

    def add_pending_draft_card(self, container, draft_record, window):
        card = tb.Labelframe(container, text=f" {draft_record['filename']} ", padding=10, style="Martin.Card.TLabelframe")
        card.pack(fill=X, pady=5)
        tb.Label(card, text=f"Saved: {draft_record['saved_at']}", style="Martin.Muted.TLabel").pack(anchor=W)
        tb.Label(card, text=f"Date: {draft_record['date'] or '(unknown)'} | Shift: {draft_record['shift'] or '(unknown)'}", style="Martin.Muted.TLabel").pack(anchor=W)
        actions = tb.Frame(card)
        actions.pack(fill=X, pady=(8, 0))
        tb.Button(actions, text="Resume", bootstyle=SUCCESS, command=lambda path=draft_record['path'], win=window: self.load_draft_path(path, win)).pack(side=LEFT, padx=(0, 6))
        tb.Button(actions, text="Delete", bootstyle=DANGER, command=lambda path=draft_record['path'], win=window: self.delete_pending_from_window(path, win)).pack(side=LEFT)

    def delete_pending_from_window(self, draft_path, window):
        if not messagebox.askyesno("Delete Draft", f"Delete {os.path.basename(draft_path)}?"):
            return
        self.delete_draft_file(draft_path)
        window.destroy()
        self.show_pending()

    def load_from_file(self, filename, window):
        path = os.path.join(self.get_pending_dir(), filename)
        self.load_draft_path(path, window)

    def import_from_excel_ui(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Excel File to Import",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            if not self.confirm_discard_unsaved_changes():
                return
            try:
                from modules.data_handler import DataHandler
                handler = DataHandler()
                data = handler.import_from_excel(file_path)
                self.populate_from_data(data, source_path=None, mark_dirty_after_load=True)
                self.dispatcher.show_toast("Import Complete", "Excel import completed successfully.", SUCCESS)
            except Exception as e:
                Messagebox.show_error(f"Failed to import Excel: {e}", "Import Error")

    def sync_julian_cast_date(self, event=None):
        try:
            self.apply_header_data(self.get_raw_header_data(), mark_dirty=True)
        except Exception:
            pass

def get_ui(parent, dispatcher):
    return ProductionLog(parent, dispatcher)