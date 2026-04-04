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
from modules.persistence import write_json_with_backup

__module_name__ = "Rate Manager"
__version__ = "1.0.1"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class RateManager:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        
        # Persistence Logic: Local first, then internal default
        self.local_data = "rates.json"
        self.internal_data = resource_path("rates.json")
        
        # Decide which file to load from
        self.data_file = self.local_data if os.path.exists(self.local_data) else self.internal_data
        
        self.rates = self.load_data()
        self.editing_part = None  
        
        self.setup_ui()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading rates: {e}")
                return {}
        return {}

    def save_data(self):
        try:
            write_json_with_backup(
                self.local_data,
                self.rates,
                backup_dir=os.path.join(os.path.abspath("."), "data", "backups", "rates"),
                keep_count=12,
            )
            # Switch current tracking to the local file now that it exists
            self.data_file = self.local_data
        except Exception as e:
            Messagebox.show_error(f"Failed to save rates: {e}", "Save Error")

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=10)
        container.pack(fill=BOTH, expand=True)

        # --- Table ---
        # Note: I added a scrollbar here; once you get 20+ parts, you'll need it!
        table_frame = tb.Frame(container)
        table_frame.pack(fill=BOTH, expand=True)

        self.tree = tb.Treeview(table_frame, columns=("Part", "Rate"), show="headings", bootstyle=INFO)
        self.tree.heading("Part", text="Part Number")
        self.tree.heading("Rate", text="Target Rate (Molds/Hr)")
        
        scrollbar = tb.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # --- Form & Buttons ---
        # [Form layout remains the same as your draft]
        self.form = tb.Labelframe(container, text=" Rate Entry Form ", padding=15)
        self.form.pack(fill=X, pady=15)

        tb.Label(self.form, text="Part #:").grid(row=0, column=0, padx=5)
        self.part_ent = tb.Entry(self.form)
        self.part_ent.grid(row=0, column=1, padx=5, sticky=EW)

        tb.Label(self.form, text="Rate:").grid(row=0, column=2, padx=5)
        self.rate_ent = tb.Entry(self.form)
        self.rate_ent.grid(row=0, column=3, padx=5, sticky=EW)

        self.btn_frame = tb.Frame(self.form)
        self.btn_frame.grid(row=0, column=4, padx=10)

        self.primary_btn = tb.Button(self.btn_frame, text="Add", bootstyle=SUCCESS, command=self.add_rate)
        self.primary_btn.pack(side=LEFT, padx=2)

        self.edit_btn = tb.Button(self.btn_frame, text="Edit", bootstyle=WARNING, command=self.prepare_edit)
        self.edit_btn.pack(side=LEFT, padx=2)

        self.del_btn = tb.Button(self.btn_frame, text="Delete", bootstyle=DANGER, command=self.delete_rate)
        self.del_btn.pack(side=LEFT, padx=2)

        self.clear_btn = tb.Button(self.btn_frame, text="Clear", bootstyle=SECONDARY, command=self.clear_form)
        self.clear_btn.pack(side=LEFT, padx=2)

        self.form.columnconfigure((1, 3), weight=1)
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        # Sort parts alphabetically so it's easier to find them in the list
        sorted_parts = sorted(self.rates.items())
        for part, rate in sorted_parts:
            self.tree.insert("", END, iid=str(part), values=(part, rate))

    def get_selected_part_key(self):
        selection = self.tree.selection()
        if selection:
            return selection[0]
        return self.tree.focus()

    def on_tree_select(self, _event=None):
        if self.tree.selection():
            self.prepare_edit()

    def prepare_edit(self):
        part_key = self.get_selected_part_key()
        if not part_key: return
        
        self.editing_part = part_key
        rate = self.rates[part_key]

        self.part_ent.delete(0, END); self.part_ent.insert(0, part_key)
        self.part_ent.config(state='disabled') # Lock the Part Number
        
        self.rate_ent.delete(0, END); self.rate_ent.insert(0, rate)

        self.primary_btn.config(text="Save", bootstyle=INFO, command=self.save_edit)
        self.edit_btn.config(text="Cancel", bootstyle=SECONDARY, command=self.cancel_edit)

    def save_edit(self):
        new_rate = self.rate_ent.get().strip()
        if self.editing_part and new_rate:
            self.rates[self.editing_part] = new_rate
            self.save_data()
            self.cancel_edit()
            self.refresh_table()

    def cancel_edit(self):
        self.editing_part = None
        self.part_ent.config(state='normal')
        self.part_ent.delete(0, END); self.rate_ent.delete(0, END)
        self.primary_btn.config(text="Add", bootstyle=SUCCESS, command=self.add_rate)
        self.edit_btn.config(text="Edit", bootstyle=WARNING, command=self.prepare_edit)

    def clear_form(self):
        self.cancel_edit()
        self.tree.selection_remove(self.tree.selection())
        self.tree.focus("")
        self.part_ent.focus_set()

    def add_rate(self):
        part = self.part_ent.get().strip()
        rate = self.rate_ent.get().strip()
        if part and rate:
            # Small check to ensure rate is a number
            try:
                float(rate) 
                self.rates[str(part)] = rate
                self.save_data()
                self.refresh_table()
                self.part_ent.delete(0, END)
                self.rate_ent.delete(0, END)
            except ValueError:
                Messagebox.show_error("Rate must be a number (e.g., 240 or 240.5)", "Input Error")

    def delete_rate(self):
        part_key = self.get_selected_part_key()
        if part_key in self.rates:
            del self.rates[part_key]
            self.save_data(); self.refresh_table()
            self.clear_form()
def get_ui(parent, dispatcher):
    RateManager(parent, dispatcher)