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
import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, END, INFO, LEFT, PRIMARY, RIGHT, SECONDARY, SUCCESS, VERTICAL, W, X, Y
from ttkbootstrap.dialogs import Messagebox

__module_name__ = "Backup / Recovery"
__version__ = "1.0.1"


class RecoveryViewerView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.status_var = tb.StringVar(value="Ready")
        self.tree = None
        self.setup_ui()

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Backup / Recovery", font=("Helvetica", 18, "bold")).pack(anchor=W, pady=(0, 8))
        tb.Label(
            container,
            text=(
                "Browse pending drafts, recovery snapshots, form-aware layout backups, and system configuration backups. "
                "Use Restore to copy a selected backup back into the correct working file for that form or system resource."
            ),
            bootstyle=SECONDARY,
            wraplength=760,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 12))

        action_row = tb.Frame(container)
        action_row.pack(fill=X, pady=(0, 12))
        tb.Button(action_row, text="Refresh", bootstyle=PRIMARY, command=self.controller.refresh_records).pack(side=LEFT)
        tb.Button(action_row, text="Restore Selected", bootstyle=SUCCESS, command=self.controller.restore_selected).pack(side=LEFT, padx=8)
        tb.Button(action_row, text="Resume Selected Draft", bootstyle=INFO, command=self.controller.resume_selected).pack(side=LEFT, padx=8)
        tb.Button(action_row, text="Open Selected File", bootstyle=SECONDARY, command=self.controller.open_selected_file).pack(side=LEFT, padx=8)
        tb.Button(action_row, text="Open Containing Folder", bootstyle=SECONDARY, command=self.controller.open_selected_folder).pack(side=LEFT, padx=8)

        table_frame = tb.Frame(container)
        table_frame.pack(fill=BOTH, expand=True)

        columns = ("kind", "name", "form", "saved", "target")
        self.tree = tb.Treeview(table_frame, columns=columns, show="headings", bootstyle=INFO)
        self.tree.heading("kind", text="Type")
        self.tree.heading("name", text="File")
        self.tree.heading("form", text="Form")
        self.tree.heading("saved", text="Saved")
        self.tree.heading("target", text="Restore Target")
        self.tree.column("kind", width=170, anchor=W)
        self.tree.column("name", width=250, anchor=W)
        self.tree.column("form", width=190, anchor=W)
        self.tree.column("saved", width=170, anchor=W)
        self.tree.column("target", width=220, anchor=W)

        y_scroll = tb.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        y_scroll.pack(side=RIGHT, fill=Y)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.tree, self.tree)

        tb.Label(container, textvariable=self.status_var, bootstyle=SECONDARY).pack(anchor=W, pady=(12, 0))

    def refresh_table(self, records):
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        for index, record in enumerate(records):
            self.tree.insert(
                "",
                END,
                iid=str(index),
                values=(record["kind"], record["name"], record.get("form_name", "System"), record["saved_at"], record["restore_target"]),
            )
        self.status_var.set(f"Loaded {len(records)} recovery item(s).")

    def get_selected_index(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def set_status(self, message):
        self.status_var.set(message)

    def show_error(self, title, message):
        Messagebox.show_error(message, title)

    def show_toast(self, title, message, bootstyle=SUCCESS):
        self.dispatcher.show_toast(title, message, bootstyle)

    def on_hide(self):
        return None

    def on_unload(self):
        return None
