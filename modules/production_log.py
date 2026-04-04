# The Martin Suite (GLC Edition)
# Copyright (C) 2026 Jamie Martin
# Licensed under GNU GPLv3.

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from datetime import datetime
import json
import os
import sys

__module_name__ = "Production Log"
__version__ = "1.0.2"

def resource_path(relative_path):
    """ Get absolute path to internal resource (Read-Only) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def external_path(relative_path):
    """ Get path to external file (Write-Enabled) """
    return os.path.join(os.path.abspath("."), relative_path)

class ProductionLog:
    def __init__(self, parent, dispatcher):
        self.parent = parent 
        self.dispatcher = dispatcher
        
        # Prefer the local config so Layout Manager saves are used immediately in dev and packaged builds.
        self.config_path = external_path("layout_config.json")
        if not os.path.exists(self.config_path):
            self.config_path = resource_path("layout_config.json")

        self.dt_codes = [
            "1 Misc Reason", "2 Machine Repairs", "3 AMC, SBC, Shakeout", 
            "4 Pattern Change", "5 Pattern Repair", "6 No Iron (Cupola)",
            "7 No Iron (Transfer)", "8 Auto Pour", "9 Inoculator", "10 No Sand"
        ]

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
            except: pass
        
        self.default_hours = str(self.settings.get("default_shift_hours", 8.0))
        self.default_goal = str(self.settings.get("default_goal_mph", 240))
        self.auto_save_interval = int(self.settings.get("auto_save_interval_min", 5)) * 60000

        self.setup_ui()
        self.parent.after(self.auto_save_interval, self.auto_save)

    def auto_save(self):
        self.save_draft(is_auto=True)
        self.parent.after(self.auto_save_interval, self.auto_save) 

    def save_draft(self, is_auto=False):
        try:
            header_data = {fid: ent.get() for fid, ent in self.entries.items()}
            prod_data = [{k: (v.get() if hasattr(v, 'get') else v.cget("text")) for k, v in row.items()} for row in self.production_rows]
            dt_data = [{k: (v.get() if hasattr(v, 'get') else v.cget("text")) for k, v in row.items()} for row in self.downtime_rows]

            data = {"header": header_data, "production": prod_data, "downtime": dt_data}

            raw_date = header_data.get("date", "unsaved").replace("/", "-")
            shift_str = header_data.get("shift", "0")
            filename = f"draft_{raw_date}_shift{shift_str}.json"
            
            # FORCE EXTERNAL SAVE
            pending_dir = external_path("data/pending")
            os.makedirs(pending_dir, exist_ok=True)
            
            with open(os.path.join(pending_dir, filename), "w") as f:
                json.dump(data, f, indent=4)
            
            if not is_auto:
                print(f"Saved to: {filename}")
        except Exception as e:
            print(f"Save Error: {e}")

    def setup_ui(self):
        header_wrapper = tb.Labelframe(self.parent, text=" Form 510-09: Production Header ", padding=15)
        header_wrapper.pack(fill=X, padx=10, pady=10)
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            for field in config["header_fields"]:
                tb.Label(header_wrapper, text=field["label"]).grid(row=field["row"], column=field["col"], padx=5, pady=5, sticky=W)
                ent = tb.Entry(header_wrapper, width=field.get("width", 10))
                
                default_val = field.get("default", "")
                if field["id"] == "hours":
                    default_val = self.default_hours
                elif field["id"] == "goal_mph":
                    default_val = self.default_goal
                    
                if default_val: ent.insert(0, default_val)
                if field.get("readonly"): ent.config(state="readonly", bootstyle=INFO)
                ent.grid(row=field["row"], column=field["col"]+1, padx=5, pady=5, sticky=W)
                self.entries[field["id"]] = ent

            if "date" in self.entries:
                self.entries["date"].bind("<FocusOut>", self.sync_julian_cast_date)
        except Exception as e:
            tb.Label(header_wrapper, text=f"Layout Error: {e}", bootstyle=DANGER).pack()

        prod_wrapper = tb.Labelframe(self.parent, text=" Production Jobs ", padding=10)
        prod_wrapper.pack(fill=X, padx=10, pady=5)
        self.production_container = tb.Frame(prod_wrapper)
        self.production_container.pack(fill=X)
        tb.Button(prod_wrapper, text="+ Add Production", command=self.add_production_row, bootstyle=SUCCESS).pack(pady=5)

        dt_wrapper = tb.Labelframe(self.parent, text=" Downtime Issues ", padding=10)
        dt_wrapper.pack(fill=X, padx=10, pady=5)
        self.downtime_container = tb.Frame(dt_wrapper)
        self.downtime_container.pack(fill=X)
        tb.Button(dt_wrapper, text="+ Add Downtime", command=self.add_downtime_row, bootstyle=SUCCESS).pack(pady=5)

        footer = tb.Frame(self.parent, padding=20)
        footer.pack(fill=X)
        self.eff_display_lbl = tb.Label(footer, text="EFF%: 0.00", font=('-size 14 -weight bold'))
        self.eff_display_lbl.pack(side=LEFT, padx=10)
        
        tb.Button(footer, text="Calculate All", command=self.calculate_metrics, bootstyle=INFO).pack(side=RIGHT)
        tb.Button(footer, text="Save Draft", command=self.save_draft, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        tb.Button(footer, text="Export Excel", command=self.export_to_excel, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        tb.Button(footer, text="Import Excel", command=self.import_from_excel_ui, bootstyle=INFO).pack(side=LEFT, padx=5)
        tb.Button(footer, text="📁 Pending", command=self.show_pending, bootstyle=OUTLINE).pack(side=LEFT, padx=5)

        self.add_production_row()

    def add_production_row(self):
        row_frame = tb.Frame(self.production_container)
        row_frame.pack(fill=X, pady=2)
        row = {
            "shop_order": tb.Entry(row_frame, width=15),
            "part_number": tb.Entry(row_frame, width=15),
            "molds": tb.Entry(row_frame, width=10),
            "time_calc": tb.Label(row_frame, text="0 min", width=10, font=('', 10, 'bold'))
        }
        for k, w in row.items():
            if k != "time_calc": w.pack(side=LEFT, padx=5)
        row["time_calc"].pack(side=RIGHT, padx=10)
        
        row["part_number"].bind("<KeyRelease>", lambda e: self.update_row_math())
        row["molds"].bind("<KeyRelease>", lambda e: self.update_row_math())
        self.production_rows.append(row)

    def add_downtime_row(self):
        row_frame = tb.Frame(self.downtime_container)
        row_frame.pack(fill=X, pady=2)
        row = {
            "start": tb.Entry(row_frame, width=10),
            "stop": tb.Entry(row_frame, width=10),
            "code": tb.Combobox(row_frame, values=self.dt_codes, width=25, state="readonly"),
            "cause": tb.Entry(row_frame),
            "time_calc": tb.Label(row_frame, text="0 min", width=10, foreground="red", font=('', 10, 'bold'))
        }
        row["start"].pack(side=LEFT, padx=5)
        row["stop"].pack(side=LEFT, padx=5)
        row["code"].pack(side=LEFT, padx=5)
        row["time_calc"].pack(side=RIGHT, padx=10)
        row["cause"].pack(side=LEFT, fill=X, expand=True, padx=5)
        
        row["start"].bind("<KeyRelease>", lambda e: self.update_row_math())
        row["stop"].bind("<KeyRelease>", lambda e: self.update_row_math())
        self.downtime_rows.append(row)

    def update_row_math(self):
        rates_data = {}
        r_path = external_path("rates.json")
        if os.path.exists(r_path):
            try:
                with open(r_path, 'r') as f: rates_data = json.load(f)
            except: pass

        try:
            global_goal = float(self.entries["goal_mph"].get() or 240)
        except:
            global_goal = 240

        for row in self.production_rows:
            try:
                part = row["part_number"].get().strip()
                molds = float(row["molds"].get() or 0)
                rate = float(rates_data.get(part, global_goal))
                minutes = (molds / rate) * 60 if rate > 0 else 0
                row["time_calc"].config(text=f"{int(minutes)} min")
            except: row["time_calc"].config(text="0 min")

        for row in self.downtime_rows:
            try:
                s_raw, e_raw = row["start"].get().zfill(4), row["stop"].get().zfill(4)
                if len(s_raw) == 4 and len(e_raw) == 4:
                    s_m = int(s_raw[:2])*60 + int(s_raw[2:])
                    e_m = int(e_raw[:2])*60 + int(e_raw[2:])
                    diff = (e_m - s_m) if e_m >= s_m else (1440 - s_m + e_m)
                    row["time_calc"].config(text=f"{diff} min")
            except: row["time_calc"].config(text="--")

    def calculate_metrics(self):
        try:
            total_molds = sum(int(row["molds"].get() or 0) for row in self.production_rows)
            hours = float(self.entries["hours"].get() or 8.0)
            goal = float(self.entries["goal_mph"].get() or 240)
            eff = (total_molds / (hours * goal)) * 100 if hours and goal else 0
            self.eff_display_lbl.config(text=f"EFF%: {eff:.2f}")
        except: pass

    def export_to_excel(self):
        try:
            from modules.data_handler import DataHandler
            handler = DataHandler()
            ui_data = {
                "header": {fid: ent.get() for fid, ent in self.entries.items()},
                "production": [{k: (v.get() if hasattr(v, 'get') else v.cget("text")) for k, v in row.items()} for row in self.production_rows],
                "downtime": [{k: (v.get() if hasattr(v, 'get') else v.cget("text")) for k, v in row.items()} for row in self.downtime_rows]
            }
            shift = ui_data["header"].get("shift", "0")
            date = ui_data["header"].get("date", "00-00-00").replace("/", "")
            handler.export_to_template(ui_data, shift, date)
            Messagebox.show_info("Excel Export Successful!", "Success")
        except Exception as e:
            Messagebox.show_error(f"Export failed: {e}", "Error")

    def show_pending(self):
        top = tb.Toplevel(title="Pending Shifts")
        top.geometry("400x400")
        p_dir = external_path("data/pending")
        os.makedirs(p_dir, exist_ok=True)
        files = os.listdir(p_dir)
        if not files:
            tb.Label(top, text="No pending shifts found.").pack(pady=20)
            return
        for f in files:
            tb.Button(top, text=f, bootstyle=LINK, command=lambda fn=f: self.load_from_file(fn, top)).pack(fill=X, padx=10, pady=2)

    def load_from_file(self, filename, window):
        path = os.path.join(external_path("data/pending"), filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            # 1. Load Header
            if 'header' in data:
                for fid, val in data['header'].items():
                    if fid in self.entries:
                        self.entries[fid].config(state="normal")
                        self.entries[fid].delete(0, END)
                        self.entries[fid].insert(0, str(val) if val is not None else "")
            
            # 2. Clear current rows
            for widget in self.production_container.winfo_children():
                widget.destroy()
            self.production_rows.clear()
            
            for widget in self.downtime_container.winfo_children():
                widget.destroy()
            self.downtime_rows.clear()
            
            # 3. Rebuild Production Rows
            for p_data in data.get('production', []):
                self.add_production_row()
                current_row = self.production_rows[-1]
                for key, val in p_data.items():
                    if key in current_row:
                        widget = current_row[key]
                        if hasattr(widget, 'insert'):
                            widget.delete(0, END)
                            widget.insert(0, str(val) if val is not None else "")
                            
            # 4. Rebuild Downtime Rows
            for d_data in data.get('downtime', []):
                self.add_downtime_row()
                current_row = self.downtime_rows[-1]
                for key, val in d_data.items():
                    if key in current_row:
                        widget = current_row[key]
                        if hasattr(widget, 'set'):
                            widget.set(str(val) if val is not None else "")
                        elif hasattr(widget, 'insert'):
                            widget.delete(0, END)
                            widget.insert(0, str(val) if val is not None else "")
                            
            self.update_row_math()
            self.calculate_metrics()
        except Exception as e:
            print(f"Error loading draft: {e}")
        
        window.destroy()

    def import_from_excel_ui(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Excel File to Import",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            try:
                from modules.data_handler import DataHandler
                handler = DataHandler()
                data = handler.import_from_excel(file_path)
                
                if 'header' in data:
                    for fid, val in data['header'].items():
                        if fid in self.entries:
                            self.entries[fid].config(state="normal")
                            self.entries[fid].delete(0, END)
                            self.entries[fid].insert(0, str(val) if val is not None else "")
                
                for widget in self.production_container.winfo_children():
                    widget.destroy()
                self.production_rows.clear()
                
                for widget in self.downtime_container.winfo_children():
                    widget.destroy()
                self.downtime_rows.clear()
                
                for p_data in data.get('production', []):
                    self.add_production_row()
                    current_row = self.production_rows[-1]
                    for key, val in p_data.items():
                        if key in current_row:
                            widget = current_row[key]
                            if hasattr(widget, 'insert'):
                                widget.delete(0, END)
                                widget.insert(0, str(val) if val is not None else "")
                                
                for d_data in data.get('downtime', []):
                    self.add_downtime_row()
                    current_row = self.downtime_rows[-1]
                    for key, val in d_data.items():
                        if key in current_row:
                            widget = current_row[key]
                            if hasattr(widget, 'set'):
                                widget.set(str(val) if val is not None else "")
                            elif hasattr(widget, 'insert'):
                                widget.delete(0, END)
                                widget.insert(0, str(val) if val is not None else "")
                                
                self.update_row_math()
                self.calculate_metrics()
                Messagebox.show_info("Excel Import Successful!", "Success")
            except Exception as e:
                Messagebox.show_error(f"Failed to import Excel: {e}", "Import Error")

    def sync_julian_cast_date(self, event=None):
        try:
            date_box = self.entries.get("date")
            cast_box = self.entries.get("cast_date")
            date_obj = datetime.strptime(date_box.get().strip(), "%m/%d/%Y")
            julian = f"{date_obj.timetuple().tm_yday:03}"
            cast_box.config(state="normal")
            cast_box.delete(0, END); cast_box.insert(0, julian)
            cast_box.config(state="readonly")
        except: pass

def get_ui(parent, dispatcher):
    return ProductionLog(parent, dispatcher)