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

from app.models.production_log_model import ProductionLogModel
from app.views.production_log_qt_view import ProductionLogQtView

__module_name__ = "Production Log Qt Controller"
__version__ = "1.0.0"


class ProductionLogQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.model = ProductionLogModel()
        self.snapshot = {}
        self.view = ProductionLogQtView(self, self.payload)
        self.refresh_snapshot(initial=True)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False, runtime_event=None, metadata=None):
        if not self.state_path:
            return
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": "production_log",
            "pending_draft_count": int(self.snapshot.get("pending_draft_count") or 0),
            "recovery_snapshot_count": int(self.snapshot.get("recovery_snapshot_count") or 0),
            "updated_at": time.time(),
        }
        if runtime_event:
            payload["runtime_event"] = str(runtime_event)
        if isinstance(metadata, dict):
            payload.update(metadata)
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def build_snapshot(self):
        latest_draft = self.model.get_latest_pending_draft() or {}
        latest_draft_path = str(latest_draft.get("path") or "")
        pending_drafts = self.model.list_pending_drafts()
        recovery_snapshots = self.model.list_recovery_snapshots()
        return {
            "pending_draft_count": len(pending_drafts),
            "recovery_snapshot_count": len(recovery_snapshots),
            "latest_draft_name": os.path.basename(latest_draft_path) if latest_draft_path else "None",
            "dt_code_count": len(self.model.dt_codes or []),
            "form_name": self.model.get_active_form_name(),
            "pending_drafts": pending_drafts,
            "recovery_snapshots": recovery_snapshots,
        }

    def refresh_snapshot(self, initial=False):
        self.snapshot = self.build_snapshot()
        self.view.render_snapshot(self.snapshot)
        state_message = "Production Log Qt window ready." if initial else "Production Log snapshot refreshed."
        self.write_state(status="ready", message=state_message)

    def _open_path(self, path):
        if not path:
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                webbrowser.open(f"file://{path}")
            self.write_state(status="ready", message=f"Opened {os.path.basename(path)}.")
        except Exception as exc:
            self.view.show_error("Production Log", f"Could not open path:\n{exc}")

    def open_pending_folder(self):
        self._open_path(self.model.get_pending_dir())

    def open_recovery_folder(self):
        self._open_path(self.model.get_recovery_dir())

    def request_load_draft(self, draft_path):
        draft_path = str(draft_path or "").strip()
        if not draft_path:
            self.view.show_info("Production Log", "Select a draft to request loading.")
            return
        self.write_state(
            status="ready",
            message=f"Requested host draft load for {os.path.basename(draft_path)}.",
            dirty=True,
            runtime_event="load_draft_requested",
            metadata={"draft_path": draft_path},
        )

    def request_open_recovery(self, snapshot_path=None):
        metadata = {}
        snapshot_path = str(snapshot_path or "").strip()
        if snapshot_path:
            metadata["snapshot_path"] = snapshot_path
        self.write_state(
            status="ready",
            message="Requested host recovery viewer.",
            dirty=True,
            runtime_event="open_recovery_requested",
            metadata=metadata,
        )

    def request_restore_snapshot(self, snapshot_path):
        snapshot_path = str(snapshot_path or "").strip()
        if not snapshot_path:
            self.view.show_info("Production Log", "Select a recovery snapshot to restore first.")
            return
        self.write_state(
            status="ready",
            message=f"Requested host restore for {os.path.basename(snapshot_path)}.",
            dirty=True,
            runtime_event="restore_snapshot_requested",
            metadata={"snapshot_path": snapshot_path},
        )

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
        command_payload = payload if isinstance(payload, dict) else {}
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Production Log Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()
        elif action == "refresh_snapshot":
            reason = str(command_payload.get("reason") or "host_update").strip()
            self.refresh_snapshot(initial=False)
            self.view.set_status(f"Snapshot refreshed after {reason}.")
        elif action == "show_pending":
            self.show()
            self.view.set_status("Pending drafts are listed in the upper table.")
            self.write_state(status="ready", message="Showed pending drafts in Production Log Qt window.")
        elif action == "save_draft":
            self.view.show_info(
                "Production Log",
                "Save Draft from the PyQt6 host File menu is not yet wired to the full Qt form workflow. Use the module window controls until parity lands.",
            )
            self.write_state(status="ready", message="Save Draft requested from File menu.", dirty=True)
        elif action == "export_to_excel":
            self.view.show_info(
                "Production Log",
                "Export to Excel from the PyQt6 host File menu is not yet wired to the full Qt form workflow. Use the module window controls until parity lands.",
            )
            self.write_state(status="ready", message="Export to Excel requested from File menu.", dirty=True)
        elif action == "import_from_excel_ui":
            self.view.show_info(
                "Production Log",
                "Import Excel from the PyQt6 host File menu is not yet wired to the full Qt form workflow. Use the module window controls until parity lands.",
            )
            self.write_state(status="ready", message="Import Excel requested from File menu.", dirty=True)
        elif action == "host_action_completed":
            action_name = str(command_payload.get("action_name") or "host_action").strip()
            success = bool(command_payload.get("success", True))
            message = str(command_payload.get("message") or "Host action completed.")
            self.view.set_status(f"{action_name}: {message}")
            self.write_state(
                status="ready",
                message=f"Received host completion for {action_name}.",
                dirty=not success,
            )

    def handle_close(self):
        self.write_state(status="closed", message="Production Log Qt window closed.")
