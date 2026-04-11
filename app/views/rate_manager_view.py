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

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, DANGER, END, EW, INFO, LEFT, RIGHT, SECONDARY, SUCCESS, WARNING, W, X
from ttkbootstrap.dialogs import Messagebox

__module_name__ = "Rate Manager"
__version__ = "1.0.0"


class RateManagerView:
    def __init__(self, parent, dispatcher, controller, model):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.model = model
        self.setup_ui()

    def setup_ui(self):
        self.main_container = tb.Frame(self.parent, padding=10)
        self.main_container.pack(fill=BOTH, expand=True)

        header = tb.Frame(self.main_container)
        header.pack(fill=X, pady=(0, 10))
        tb.Label(header, text="Rate Manager", font=("Helvetica", 16, "bold")).pack(side=LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_args: self.controller.refresh_table())
        tb.Entry(header, textvariable=self.search_var, width=20).pack(side=RIGHT, padx=5)
        tb.Label(header, text="Search:", bootstyle=SECONDARY).pack(side=RIGHT)

        self.tree = tb.Treeview(self.main_container, columns=("Part", "Rate"), show="headings", bootstyle=INFO)
        self.tree.heading("Part", text="Part Number")
        self.tree.heading("Rate", text="Target Rate")
        self.tree.pack(fill=BOTH, expand=True)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.tree, self.tree)

        self.form = tb.Labelframe(self.main_container, text=" Part Details ", padding=15)
        self.form.pack(fill=X, pady=15)

        tb.Label(self.form, text="Part #:").grid(row=0, column=0, padx=5, sticky=W)
        self.part_ent = tb.Entry(self.form)
        self.part_ent.grid(row=0, column=1, padx=5, sticky=EW)

        tb.Label(self.form, text="Rate:").grid(row=0, column=2, padx=5, sticky=W)
        self.rate_ent = tb.Entry(self.form)
        self.rate_ent.grid(row=0, column=3, padx=5, sticky=EW)

        self.btn_frame = tb.Frame(self.form)
        self.btn_frame.grid(row=0, column=4, padx=10)
        self.primary_btn = tb.Button(self.btn_frame, text="Add", bootstyle=SUCCESS, command=self.controller.add_rate, width=10)
        self.primary_btn.pack(side=LEFT, padx=2)
        self.secondary_btn = tb.Button(self.btn_frame, text="Edit", bootstyle=WARNING, command=self.controller.enter_edit_mode, width=10)
        self.secondary_btn.pack(side=LEFT, padx=2)
        self.del_btn = tb.Button(self.btn_frame, text="Delete", bootstyle=DANGER, command=self.controller.delete_rate, width=10)
        self.del_btn.pack(side=LEFT, padx=2)
        self.form.columnconfigure((1, 3), weight=1)

    def get_search_text(self):
        return self.search_var.get()

    def refresh_table(self, rows):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for part, rate in rows:
            self.tree.insert("", END, iid=str(part), values=(str(part), str(rate)))

    def get_selected_part(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.focus()

    def populate_edit_form(self, part_key, rate):
        self.part_ent.delete(0, END)
        self.part_ent.insert(0, part_key)
        self.part_ent.config(state="disabled")
        self.rate_ent.delete(0, END)
        self.rate_ent.insert(0, rate)
        self.primary_btn.config(text="Save", bootstyle=INFO, command=self.controller.save_edit)
        self.secondary_btn.config(text="Cancel", bootstyle=SECONDARY, command=self.controller.cancel_edit)
        self.del_btn.config(state="disabled")

    def reset_form(self):
        self.part_ent.config(state="normal")
        self.part_ent.delete(0, END)
        self.rate_ent.delete(0, END)
        self.primary_btn.config(text="Add", bootstyle=SUCCESS, command=self.controller.add_rate)
        self.secondary_btn.config(text="Edit", bootstyle=WARNING, command=self.controller.enter_edit_mode)
        self.del_btn.config(state="normal")

    def get_form_values(self):
        return self.part_ent.get().strip(), self.rate_ent.get().strip()

    def show_error(self, title, message):
        Messagebox.show_error(message, title)

    def show_toast(self, title, message, bootstyle=SUCCESS):
        self.dispatcher.show_toast(title, message, bootstyle)

    def on_hide(self):
        return None

    def on_unload(self):
        return None
