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
__version__ = "1.0.2"


class RecoveryViewerQtController:
    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.selected_record_key = None
        data_registry = getattr(dispatcher, "external_data_registry", None)
        self.model = RecoveryViewerModel(data_registry=data_registry)
        self.payload = self._build_view_payload()
        self.records = []
        self.view = RecoveryViewerQtView(self, self.payload, parent_widget=parent)
        self.refresh_backup_policy(initial=True)
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
            "backup_policy": self.model.load_backup_policy(),
            "backup_targets": self.model.get_backup_target_definitions(),
        }

    def _record_key(self, record):
        if not isinstance(record, dict):
            return None
        return (
            str(record.get("record_type") or ""),
            str(record.get("path") or ""),
            str(record.get("restore_target") or ""),
        )

    def _find_record_key_by_path(self, record_path):
        record_path = str(record_path or "").strip()
        if not record_path:
            return None
        for record in self.records:
            if str(record.get("path") or "").strip() == record_path:
                return self._record_key(record)
        return None

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

    def show_toast(self, title, message, bootstyle=None):
        dispatcher = self.dispatcher
        show_toast = getattr(dispatcher, "show_toast", None)
        if callable(show_toast):
            show_toast(title, message, bootstyle)
            self.view.set_status(str(message or ""))
            return
        self.view.show_info(title, message)

    def refresh_records(self, initial=False, selected_record_key=None):
        if selected_record_key is None:
            selected_record_key = self._sync_selected_record_key()
        self.records = self.model.refresh_records()
        self.view.refresh_table(self.records)
        self._restore_selected_record(selected_record_key)
        _ = initial

    def refresh_backup_policy(self, initial=False):
        policy = self.model.load_backup_policy()
        targets = self.model.get_backup_target_definitions()
        if hasattr(self.view, "set_backup_policy"):
            self.view.set_backup_policy(policy, targets)
        if not initial:
            self.view.set_status("Backup policy refreshed.")

    def save_backup_policy(self):
        form_values = getattr(self.view, "get_backup_policy_values", lambda: {})()
        try:
            saved_policy = self.model.save_backup_policy(form_values)
        except Exception as exc:
            self.view.show_error("Backup Policy", f"Could not save backup policy:\n{exc}")
            return False

        if hasattr(self.view, "set_backup_policy"):
            self.view.set_backup_policy(saved_policy, self.model.get_backup_target_definitions())
        self.view.set_status("Backup policy saved.")
        self.show_toast("Backup Policy", "Saved backup policy.", "success")
        return True

    def reset_backup_policy_defaults(self):
        policy = self.model.normalize_backup_policy(None)
        if hasattr(self.view, "set_backup_policy"):
            self.view.set_backup_policy(policy, self.model.get_backup_target_definitions())
        self.view.set_status("Backup policy reset to defaults.")

    def clean_backups(self):
        if not self.view.ask_yes_no(
            "Clean Backups",
            "Delete all config backup files except the newest backup for each target?",
        ):
            return False

        result = self.model.prune_config_backups()
        self.refresh_records(selected_record_key=None)
        self.show_toast(
            "Clean Backups",
            f"Deleted {result['deleted']} backup file(s). Kept {result['kept']} newest backup target(s).",
            "success",
        )
        return True

    def clean_drafts(self):
        if not self.view.ask_yes_no(
            "Clean Drafts",
            "Delete all pending drafts except the newest draft?",
        ):
            return False

        result = self.model.prune_pending_drafts()
        self.refresh_records(selected_record_key=None)
        self.show_toast(
            "Clean Drafts",
            f"Deleted {result['deleted']} draft file(s). Kept {result['kept']} newest draft.",
            "success",
        )
        return True

    def clean_snapshots(self):
        if not self.view.ask_yes_no(
            "Clean Recovery Snapshots",
            "Delete all recovery snapshots except the newest snapshot?",
        ):
            return False

        result = self.model.prune_recovery_snapshots()
        self.refresh_records(selected_record_key=None)
        self.show_toast(
            "Clean Recovery Snapshots",
            f"Deleted {result['deleted']} snapshot file(s). Kept {result['kept']} newest snapshot.",
            "success",
        )
        return True

    def focus_record_path(self, record_path):
        record_key = self._find_record_key_by_path(record_path)
        if record_key is None:
            self._restore_selected_record(None)
            return False
        self._restore_selected_record(record_key)
        return True

    def get_selected_record(self):
        selected_index = self.view.get_selected_index()
        if selected_index is None:
            self.show_toast("Recovery Viewer", "Select an item first.", "info")
            return None
        if selected_index < 0 or selected_index >= len(self.records):
            self.show_toast("Recovery Viewer", "The selected item is no longer available. Refresh and try again.", "info")
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

        self.show_toast("Recovery Viewer", "Restore is not supported for the selected item type.", "info")

    def resume_selected(self):
        record = self.get_selected_record()
        if not record:
            return
        if record["record_type"] not in {"draft", "snapshot"}:
            self.show_toast("Recovery Viewer", "Resume is only available for drafts and recovery snapshots.", "info")
            return

        if record["record_type"] == "snapshot":
            restored_path = self.restore_snapshot_record(record, prompt_to_open=False)
            if not restored_path:
                return
            draft_path = restored_path
        else:
            draft_path = record["path"]

        if self._open_production_log_draft(draft_path):
            self.view.set_status(f"Loaded {os.path.basename(draft_path)} into Form Loader.")
            return

        self.view.show_error("Recovery Viewer", "The selected draft could not be loaded into Form Loader.")

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
            self.show_toast("Restore Complete", f"Restored {record['restore_target']} from backup.", "success")
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
            if prompt_to_open and self.view.ask_yes_no("Open Restored Draft", "Draft snapshot restored. Open it in Form Loader now?"):
                if not self._open_production_log_draft(restored_path):
                    self.view.show_error("Restore Error", "The restored draft could not be opened in Form Loader.")
            else:
                self.show_toast("Restore Complete", f"Restored draft snapshot to {record['restore_target']}.", "success")
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
        if hasattr(self, "view") and self.view is not None:
            if hasattr(self.view, "controller"):
                self.view.controller = None
            self.view = None
        self.dispatcher = None
        self.parent = None

    def handle_close(self):
        return None
