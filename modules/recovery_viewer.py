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

import json
import os
from datetime import datetime
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

from modules.persistence import write_json_with_backup
from modules.theme_manager import get_theme_tokens
from modules.utils import external_path

__module_name__ = "Backup / Recovery"
__version__ = "1.1.0"


class RecoveryViewer:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.records = []
        self.tree = None
        self.status_var = tb.StringVar(value="Ready")
        self.setup_ui()
        self.refresh_records()

    def setup_ui(self):
        get_theme_tokens(root=self.parent.winfo_toplevel())
        container = tb.Frame(self.parent, padding=20, style="Martin.Content.TFrame")
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Backup / Recovery", style="Martin.PageTitle.TLabel").pack(anchor=W, pady=(0, 8))
        tb.Label(
            container,
            text=(
                "Browse pending drafts, recovery snapshots, and configuration backups. "
                "Use Restore to copy a selected backup back into the active working file."
            ),
            style="Martin.Subtitle.TLabel",
            wraplength=680,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 12))

        action_row = tb.Frame(container)
        action_row.pack(fill=X, pady=(0, 12))
        tb.Button(action_row, text="Refresh", bootstyle=PRIMARY, command=self.refresh_records).pack(side=LEFT)
        tb.Button(action_row, text="Restore Selected", bootstyle=SUCCESS, command=self.restore_selected).pack(side=LEFT, padx=8)
        tb.Button(action_row, text="Resume Selected Draft", bootstyle=INFO, command=self.resume_selected).pack(side=LEFT, padx=8)
        tb.Button(action_row, text="Open Selected File", bootstyle=SECONDARY, command=self.open_selected_file).pack(side=LEFT, padx=8)
        tb.Button(action_row, text="Open Containing Folder", bootstyle=SECONDARY, command=self.open_selected_folder).pack(side=LEFT, padx=8)

        table_card = tb.Labelframe(container, text=" Recovery Items ", padding=14, style="Martin.Card.TLabelframe")
        table_card.pack(fill=BOTH, expand=True)
        table_frame = tb.Frame(table_card, style="Martin.Surface.TFrame")
        table_frame.pack(fill=BOTH, expand=True)

        columns = ("kind", "name", "saved", "target")
        self.tree = tb.Treeview(table_frame, columns=columns, show="headings", bootstyle=INFO)
        self.tree.heading("kind", text="Type")
        self.tree.heading("name", text="File")
        self.tree.heading("saved", text="Saved")
        self.tree.heading("target", text="Restore Target")
        self.tree.column("kind", width=135, minwidth=110, anchor=W, stretch=False)
        self.tree.column("name", width=220, minwidth=150, anchor=W, stretch=True)
        self.tree.column("saved", width=150, minwidth=130, anchor=W, stretch=False)
        self.tree.column("target", width=190, minwidth=140, anchor=W, stretch=True)

        y_scroll = tb.Scrollbar(table_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        y_scroll.pack(side=RIGHT, fill=Y)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.tree, self.tree)

        tb.Label(container, textvariable=self.status_var, style="Martin.Muted.TLabel").pack(anchor=W, pady=(12, 0))

    def refresh_records(self):
        self.records = []
        self.records.extend(self.collect_draft_records())
        self.records.extend(self.collect_snapshot_records())
        self.records.extend(self.collect_config_backup_records())

        self.records.sort(key=lambda item: item["sort_key"], reverse=True)

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for index, record in enumerate(self.records):
            self.tree.insert(
                "",
                END,
                iid=str(index),
                values=(record["kind"], record["name"], record["saved_at"], record["restore_target"]),
            )

        self.status_var.set(f"Loaded {len(self.records)} recovery item(s).")

    def collect_draft_records(self):
        pending_dir = external_path("data/pending")
        os.makedirs(pending_dir, exist_ok=True)
        records = []
        for filename in os.listdir(pending_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(pending_dir, filename)
            if os.path.isdir(path):
                continue
            saved_at = self._read_saved_at(path)
            records.append({
                "record_type": "draft",
                "kind": "Pending Draft",
                "name": filename,
                "path": path,
                "saved_at": saved_at,
                "sort_key": self._sort_key(saved_at, path),
                "restore_target": filename,
                "target_path": path,
            })
        return records

    def collect_snapshot_records(self):
        history_dir = external_path("data/pending/history")
        os.makedirs(history_dir, exist_ok=True)
        records = []
        for filename in os.listdir(history_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(history_dir, filename)
            saved_at = self._read_saved_at(path)
            payload = self._load_json(path)
            draft_name = payload.get("meta", {}).get("draft_name") or filename
            records.append({
                "record_type": "snapshot",
                "kind": "Recovery Snapshot",
                "name": filename,
                "path": path,
                "saved_at": saved_at,
                "sort_key": self._sort_key(saved_at, path),
                "restore_target": draft_name,
                "target_path": os.path.join(external_path("data/pending"), draft_name),
            })
        return records

    def collect_config_backup_records(self):
        sources = [
            {
                "kind": "Settings Backup",
                "target_path": external_path("settings.json"),
                "backup_dir": external_path("data/backups/settings"),
            },
            {
                "kind": "Layout Backup",
                "target_path": external_path("layout_config.json"),
                "backup_dir": external_path("data/backups/layouts"),
            },
            {
                "kind": "Rates Backup",
                "target_path": external_path("rates.json"),
                "backup_dir": external_path("data/backups/rates"),
            },
        ]

        records = []
        for source in sources:
            os.makedirs(source["backup_dir"], exist_ok=True)
            adjacent_backup = f"{source['target_path']}.bak"
            if os.path.exists(adjacent_backup):
                saved_at = self._read_saved_at(adjacent_backup)
                records.append({
                    "record_type": "config_backup",
                    "kind": f"{source['kind']} (.bak)",
                    "name": os.path.basename(adjacent_backup),
                    "path": adjacent_backup,
                    "saved_at": saved_at,
                    "sort_key": self._sort_key(saved_at, adjacent_backup),
                    "restore_target": os.path.basename(source["target_path"]),
                    "target_path": source["target_path"],
                    "backup_dir": source["backup_dir"],
                })

            for filename in os.listdir(source["backup_dir"]):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(source["backup_dir"], filename)
                saved_at = self._read_saved_at(path)
                records.append({
                    "record_type": "config_backup",
                    "kind": source["kind"],
                    "name": filename,
                    "path": path,
                    "saved_at": saved_at,
                    "sort_key": self._sort_key(saved_at, path),
                    "restore_target": os.path.basename(source["target_path"]),
                    "target_path": source["target_path"],
                    "backup_dir": source["backup_dir"],
                })
        return records

    def _read_saved_at(self, path):
        payload = self._load_json(path)
        saved_at = payload.get("meta", {}).get("saved_at")
        if saved_at:
            return saved_at
        return datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")

    def _sort_key(self, saved_at, path):
        try:
            return datetime.fromisoformat(saved_at)
        except Exception:
            return datetime.fromtimestamp(os.path.getmtime(path))

    def _load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    def get_selected_record(self):
        selection = self.tree.selection()
        if not selection:
            self.dispatcher.show_toast("Recovery Viewer", "Select an item first.", INFO)
            return None
        return self.records[int(selection[0])]

    def open_selected_file(self):
        record = self.get_selected_record()
        if not record:
            return
        try:
            os.startfile(record["path"])
        except Exception as exc:
            Messagebox.show_error(f"Could not open file: {exc}", "Recovery Viewer")

    def open_selected_folder(self):
        record = self.get_selected_record()
        if not record:
            return
        try:
            os.startfile(os.path.dirname(record["path"]))
        except Exception as exc:
            Messagebox.show_error(f"Could not open folder: {exc}", "Recovery Viewer")

    def resume_selected(self):
        record = self.get_selected_record()
        if not record:
            return
        if record["record_type"] not in {"draft", "snapshot"}:
            self.dispatcher.show_toast("Recovery Viewer", "Resume is only available for drafts and recovery snapshots.", INFO)
            return

        if record["record_type"] == "snapshot":
            restored_path = self.restore_snapshot_record(record, prompt_to_open=False)
            if not restored_path:
                return
            draft_path = restored_path
        else:
            draft_path = record["path"]

        self.dispatcher.load_module("production_log")
        if hasattr(self.dispatcher.active_module_instance, "load_draft_path"):
            self.dispatcher.active_module_instance.load_draft_path(draft_path)
            self.status_var.set(f"Loaded {os.path.basename(draft_path)} into Production Log.")

    def restore_selected(self):
        record = self.get_selected_record()
        if not record:
            return

        if record["record_type"] == "config_backup":
            self.restore_config_record(record)
        elif record["record_type"] == "snapshot":
            self.restore_snapshot_record(record, prompt_to_open=True)
        elif record["record_type"] == "draft":
            self.resume_selected()

    def restore_config_record(self, record):
        if not messagebox.askyesno(
            "Restore Backup",
            f"Restore {record['name']} to {record['restore_target']}?\n\nThe current file will be backed up before restore.",
        ):
            return

        try:
            payload = self._load_json(record["path"])
            write_json_with_backup(
                record["target_path"],
                payload,
                backup_dir=record.get("backup_dir"),
                keep_count=12,
            )
            self.refresh_records()
            self.dispatcher.show_toast("Restore Complete", f"Restored {record['restore_target']} from backup.", SUCCESS)
        except Exception as exc:
            Messagebox.show_error(f"Could not restore backup: {exc}", "Restore Error")

    def restore_snapshot_record(self, record, prompt_to_open=True):
        if not messagebox.askyesno(
            "Restore Draft Snapshot",
            f"Restore {record['name']} as {record['restore_target']}?\n\nThe current draft will be snapshotted before replacement if it exists.",
        ):
            return None

        try:
            payload = self._load_json(record["path"])
            write_json_with_backup(
                record["target_path"],
                payload,
                backup_dir=external_path("data/pending/history"),
                keep_count=20,
            )
            self.refresh_records()
            if prompt_to_open and messagebox.askyesno("Open Restored Draft", "Draft snapshot restored. Open it in Production Log now?"):
                self.dispatcher.load_module("production_log")
                if hasattr(self.dispatcher.active_module_instance, "load_draft_path"):
                    self.dispatcher.active_module_instance.load_draft_path(record["target_path"])
            else:
                self.dispatcher.show_toast("Restore Complete", f"Restored draft snapshot to {record['restore_target']}.", SUCCESS)
            return record["target_path"]
        except Exception as exc:
            Messagebox.show_error(f"Could not restore draft snapshot: {exc}", "Restore Error")
            return None


def get_ui(parent, dispatcher):
    return RecoveryViewer(parent, dispatcher)