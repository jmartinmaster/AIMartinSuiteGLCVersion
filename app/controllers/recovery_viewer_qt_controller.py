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
import json
import os
import time
import webbrowser

from app.models.recovery_viewer_model import RecoveryViewerModel
from app.views.recovery_viewer_qt_view import RecoveryViewerQtView

__module_name__ = "Recovery Viewer Qt Controller"
__version__ = "1.0.0"


class RecoveryViewerQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.model = RecoveryViewerModel()
        self.records = []
        self.view = RecoveryViewerQtView(self, self.payload)
        self.refresh_records(initial=True)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False):
        if not self.state_path:
            return
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": "recovery_viewer",
            "record_count": len(self.records),
            "updated_at": time.time(),
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def refresh_records(self, initial=False):
        self.records = self.model.refresh_records()
        self.view.refresh_table(self.records)
        state_message = "Recovery Viewer Qt window ready." if initial else "Recovery records refreshed."
        self.write_state(status="ready", message=state_message)

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
            self.write_state(status="ready", message=f"Opened {os.path.basename(path)}.")
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
            self._open_path(record["path"])
            return

        self.view.show_info("Recovery Viewer", "Restore is not supported for the selected item type.")

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
            self.refresh_records()
            self.view.show_info("Restore Complete", f"Restored {record['restore_target']} from backup.")
        except Exception as exc:
            self.view.show_error("Restore Error", f"Could not restore backup:\n{exc}")

    def restore_snapshot_record(self, record):
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
            self.refresh_records()
            if self.view.ask_yes_no("Open Restored Draft", "Draft snapshot restored. Open the restored draft file now?"):
                self._open_path(restored_path)
            else:
                self.view.set_status(f"Restored draft snapshot to {record['restore_target']}.")
        except Exception as exc:
            self.view.show_error("Restore Error", f"Could not restore draft snapshot:\n{exc}")

    def poll_commands(self):
        if not self.command_path or not os.path.exists(self.command_path):
            return
        try:
            with open(self.command_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            payload = {}
        try:
            os.remove(self.command_path)
        except OSError:
            pass

        action = str(payload.get("action") or "").strip().lower()
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Recovery Viewer Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="Recovery Viewer Qt window closed.")
