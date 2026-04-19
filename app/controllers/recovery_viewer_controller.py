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
import os
import webbrowser
from tkinter import messagebox

from ttkbootstrap.constants import INFO, SUCCESS

from app.models.recovery_viewer_model import RecoveryViewerModel
from app.views.recovery_viewer_view import RecoveryViewerView

__module_name__ = "Recovery Viewer"
__version__ = "1.1.0"


class RecoveryViewerController:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = RecoveryViewerModel(data_registry=getattr(dispatcher, "external_data_registry", None))
        self.view = RecoveryViewerView(parent, dispatcher, self)
        self.refresh_records()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def get_active_form_info(self):
        getter = getattr(self.dispatcher, "get_active_form_info", None)
        if callable(getter):
            return dict(getter() or {})
        return dict(getattr(getattr(self.dispatcher, "model", None), "active_form_info", {}) or {})

    def refresh_records(self):
        self.view.refresh_table(self.model.refresh_records())

    def on_active_form_changed(self, active_form_info=None, form_id=None):
        _ = active_form_info
        _ = form_id
        self.refresh_records()

    def get_selected_record(self):
        selected_index = self.view.get_selected_index()
        if selected_index is None:
            self.view.show_toast("Recovery Viewer", "Select an item first.", INFO)
            return None
        return self.model.records[selected_index]

    def _open_path(self, path):
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                webbrowser.open(f"file://{path}")
        except Exception as exc:
            self.view.show_error("Recovery Viewer", f"Could not open path: {exc}")

    def open_selected_file(self):
        record = self.get_selected_record()
        if record:
            self._open_path(record["path"])

    def open_selected_folder(self):
        record = self.get_selected_record()
        if record:
            self._open_path(os.path.dirname(record["path"]))

    def resume_selected(self):
        record = self.get_selected_record()
        if not record:
            return
        if record["record_type"] not in {"draft", "snapshot"}:
            self.view.show_toast("Recovery Viewer", "Resume is only available for drafts and recovery snapshots.", INFO)
            return

        if record["record_type"] == "snapshot":
            restored_path = self.restore_snapshot_record(record, prompt_to_open=False)
            if not restored_path:
                return
            draft_path = restored_path
        else:
            draft_path = record["path"]

        if bool(getattr(self.dispatcher, "open_production_log_draft", lambda _path: False)(draft_path)):
            self.view.set_status(f"Loaded {os.path.basename(draft_path)} into Production Log.")

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
            self.model.restore_config_backup(record)
            if record.get("notifies_active_form") and hasattr(self.dispatcher, "notify_active_form_changed"):
                self.dispatcher.notify_active_form_changed(source_instance=self)
            self.refresh_records()
            self.view.show_toast("Restore Complete", f"Restored {record['restore_target']} from backup.", SUCCESS)
        except Exception as exc:
            self.view.show_error("Restore Error", f"Could not restore backup: {exc}")

    def restore_snapshot_record(self, record, prompt_to_open=True):
        if not messagebox.askyesno(
            "Restore Draft Snapshot",
            f"Restore {record['name']} as {record['restore_target']}?\n\nThe current draft will be snapshotted before replacement if it exists.",
        ):
            return None

        try:
            restored_path = self.model.restore_snapshot_as_draft(record)
            self.refresh_records()
            if prompt_to_open and messagebox.askyesno("Open Restored Draft", "Draft snapshot restored. Open it in Production Log now?"):
                if not bool(getattr(self.dispatcher, "open_production_log_draft", lambda _path: False)(restored_path)):
                    self.view.show_error("Restore Error", "The restored draft could not be opened in Production Log.")
            else:
                self.view.show_toast("Restore Complete", f"Restored draft snapshot to {record['restore_target']}.", SUCCESS)
            return restored_path
        except Exception as exc:
            self.view.show_error("Restore Error", f"Could not restore draft snapshot: {exc}")
            return None

    def on_hide(self):
        on_hide = getattr(self.view, "on_hide", None)
        if callable(on_hide):
            return on_hide()
        return None

    def on_unload(self):
        on_unload = getattr(self.view, "on_unload", None)
        if callable(on_unload):
            return on_unload()
        return None
