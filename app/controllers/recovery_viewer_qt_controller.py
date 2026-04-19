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

from app.models.recovery_viewer_model import RecoveryViewerModel
from app.views.recovery_viewer_qt_view import RecoveryViewerQtView

__module_name__ = "Recovery Viewer Qt Controller"
__version__ = "1.0.0"


class RecoveryViewerQtController:
    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.selected_record_key = None
        self.payload = self._build_view_payload()
        data_registry = getattr(dispatcher, "external_data_registry", None)
        self.model = RecoveryViewerModel(data_registry=data_registry)
        self.records = []
        self.view = RecoveryViewerQtView(self, self.payload, parent_widget=parent)
        self.refresh_records(initial=True)
        self.view.show()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "Backup / Recovery - Production Logging Center",
            "title": "Backup / Recovery",
            "subtitle": (
                "Browse pending drafts, recovery snapshots, and backup artifacts directly in the PyQt6 workspace."
            ),
            "theme_tokens": theme_tokens,
        }

    def _record_key(self, record):
        if not isinstance(record, dict):
            return None
        return (
            str(record.get("record_type") or ""),
            str(record.get("path") or ""),
            str(record.get("restore_target") or ""),
        )

    def _sync_selected_record_key(self):
        selected_index = getattr(self.view, "get_selected_index", lambda: None)()
        if selected_index is not None and 0 <= selected_index < len(self.records):
            self.selected_record_key = self._record_key(self.records[selected_index])
        elif selected_index is None:
            self.selected_record_key = None
        return self.selected_record_key

    def _restore_selected_record(self, record_key):
        if record_key is None:
            if hasattr(self.view, "set_selected_index"):
                self.view.set_selected_index(None)
            return None

        for row_index, record in enumerate(self.records):
            if self._record_key(record) == record_key:
                if hasattr(self.view, "set_selected_index"):
                    self.view.set_selected_index(row_index)
                self.selected_record_key = record_key
                return row_index

        if hasattr(self.view, "set_selected_index"):
            self.view.set_selected_index(None)
        self.selected_record_key = None
        return None

    def _open_production_log_draft(self, draft_path):
        draft_path = str(draft_path or "").strip()
        if not draft_path:
            return False
        if self.dispatcher is not None:
            opener = getattr(self.dispatcher, "open_production_log_draft", None)
            if callable(opener):
                return bool(opener(draft_path))
        self._open_path(draft_path)
        return True

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def refresh_records(self, initial=False, selected_record_key=None):
        if selected_record_key is None:
            selected_record_key = self._sync_selected_record_key()
        self.records = self.model.refresh_records()
        self.view.refresh_table(self.records)
        self._restore_selected_record(selected_record_key)
        _ = initial

    def get_selected_record(self):
        selected_index = self.view.get_selected_index()
        if selected_index is None:
            self.view.show_info("Recovery Viewer", "Select an item first.")
            return None
        if selected_index < 0 or selected_index >= len(self.records):
            self.view.show_info("Recovery Viewer", "The selected item is no longer available. Refresh and try again.")
            return None
        return self.records[selected_index]

    def _open_path(self, path):
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                webbrowser.open(f"file://{path}")
        except Exception as exc:
            self.view.show_error("Recovery Viewer", f"Could not open path:\n{exc}")

    def open_selected_file(self):
        record = self.get_selected_record()
        if record:
            self._open_path(record["path"])

    def open_selected_folder(self):
        record = self.get_selected_record()
        if record:
            self._open_path(os.path.dirname(record["path"]))

    def restore_selected(self):
        record = self.get_selected_record()
        if not record:
            return

        if record["record_type"] == "config_backup":
            self.restore_config_record(record)
            return

        if record["record_type"] == "snapshot":
            self.restore_snapshot_record(record)
            return

        if record["record_type"] == "draft":
            self.resume_selected()
            return

        self.view.show_info("Recovery Viewer", "Restore is not supported for the selected item type.")

    def resume_selected(self):
        record = self.get_selected_record()
        if not record:
            return
        if record["record_type"] not in {"draft", "snapshot"}:
            self.view.show_info("Recovery Viewer", "Resume is only available for drafts and recovery snapshots.")
            return

        if record["record_type"] == "snapshot":
            restored_path = self.restore_snapshot_record(record, prompt_to_open=False)
            if not restored_path:
                return
            draft_path = restored_path
        else:
            draft_path = record["path"]

        if self._open_production_log_draft(draft_path):
            self.view.set_status(f"Loaded {os.path.basename(draft_path)} into Production Log.")
            return

        self.view.show_error("Recovery Viewer", "The selected draft could not be loaded into Production Log.")

    def restore_config_record(self, record):
        if not self.view.ask_yes_no(
            "Restore Backup",
            (
                f"Restore {record['name']} to {record['restore_target']}?\n\n"
                "The current file will be backed up before restore."
            ),
        ):
            return

        try:
            self.model.restore_config_backup(record)
            if record.get("notifies_active_form") and hasattr(self.dispatcher, "notify_active_form_changed"):
                self.dispatcher.notify_active_form_changed(source_instance=self)
            self.refresh_records(selected_record_key=self._record_key(record))
            self.view.show_info("Restore Complete", f"Restored {record['restore_target']} from backup.")
        except Exception as exc:
            self.view.show_error("Restore Error", f"Could not restore backup:\n{exc}")

    def restore_snapshot_record(self, record, prompt_to_open=True):
        if not self.view.ask_yes_no(
            "Restore Draft Snapshot",
            (
                f"Restore {record['name']} as {record['restore_target']}?\n\n"
                "The current draft will be snapshotted before replacement if it exists."
            ),
        ):
            return

        try:
            restored_path = self.model.restore_snapshot_as_draft(record)
            self.refresh_records(selected_record_key=self._record_key(record))
            if prompt_to_open and self.view.ask_yes_no("Open Restored Draft", "Draft snapshot restored. Open it in Production Log now?"):
                if not self._open_production_log_draft(restored_path):
                    self.view.show_error("Restore Error", "The restored draft could not be opened in Production Log.")
            else:
                self.view.set_status(f"Restored draft snapshot to {record['restore_target']}.")
            return restored_path
        except Exception as exc:
            self.view.show_error("Restore Error", f"Could not restore draft snapshot:\n{exc}")
            return None

    def on_active_form_changed(self, active_form_info=None, form_id=None):
        _ = active_form_info
        _ = form_id
        self.refresh_records(selected_record_key=self._sync_selected_record_key())

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        selected_record_key = self._sync_selected_record_key()
        if hasattr(self.view, "apply_theme"):
            self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})
        self.view.refresh_table(self.records)
        self._restore_selected_record(selected_record_key)

    def on_hide(self):
        self._sync_selected_record_key()
        return None

    def on_unload(self):
        self._sync_selected_record_key()
        try:
            self.view.close()
        except Exception:
            pass

    def handle_close(self):
        return None
