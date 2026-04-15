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
import sys
import time

from app.app_identity import format_versioned_deb_name, format_versioned_exe_name
from app.app_platform import get_platform_update_artifact_label
from app.models.update_manager_model import UpdateManagerModel
from app.views.update_manager_qt_view import UpdateManagerQtView

__module_name__ = "Update Manager Qt Controller"
__version__ = "1.3.0"


class UpdateManagerQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.configured_repo_url = self.payload.get("configured_repo_url")
        self.module_payload_options = list(self.payload.get("module_payload_options") or [])
        self.documentation_payload_count = int(self.payload.get("documentation_payload_count") or 0)
        self.advanced_dev_updates_enabled = bool(self.payload.get("advanced_dev_updates_enabled", False))
        self.source_job_phase = str(self.payload.get("source_job_phase") or "idle")
        self.source_job_detail = str(self.payload.get("source_job_detail") or "No update job is running.")
        self.source_recovery_available = bool(self.payload.get("source_recovery_available", False))
        self.source_build_log_path = str(self.payload.get("source_build_log_path") or "")
        self.model = UpdateManagerModel()
        self.stable_artifact_kind = str(self.payload.get("stable_artifact_kind") or "exe")
        self.stable_artifact_label = str(self.payload.get("stable_artifact_label") or get_platform_update_artifact_label())
        self.branch_name = "Unknown"
        self.remote_info = {}
        self.local_manifest = []
        self.comparison_rows = []
        self.job_phase = "Idle"
        self.job_detail = "No update job is running."
        self.selected_payload_key = ""
        self.view = UpdateManagerQtView(self, self.payload)
        self._initialize_payload_selection()
        self.refresh_snapshot(initial=True)

    def _initialize_payload_selection(self):
        default_option = next((option for option in self.module_payload_options if option.get("key") == "about"), None)
        if default_option is None and self.module_payload_options:
            default_option = self.module_payload_options[0]
        self.selected_payload_key = str((default_option or {}).get("key") or "")

    def _stable_artifact_noun(self, plural=False):
        if self.stable_artifact_kind == "exe":
            return "executables" if plural else "executable"
        if self.stable_artifact_kind == "deb":
            return "packages" if plural else "package"
        return "artifacts" if plural else "artifact"

    def _stable_artifact_status_label(self):
        if self.stable_artifact_kind in {"exe", "deb"}:
            return self.stable_artifact_kind.upper()
        return "release"

    def _stable_artifact_name_for_version(self, version_text):
        if self.stable_artifact_kind == "deb":
            return format_versioned_deb_name(version_text)
        return format_versioned_exe_name(version_text)

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
            "module": "update_manager",
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

    def _refresh_local_manifest(self):
        dispatcher_module = sys.modules.get("main") or sys.modules.get("__main__")
        self.local_manifest = self.model.build_local_manifest(dispatcher_module)

    def _refresh_remote_target(self):
        self.branch_name = self.model.detect_branch_name() or "Unknown"
        self.remote_info = self.model.detect_remote_info(preferred_url=self.configured_repo_url)

    def _updates_configured(self):
        return self.model.remote_updates_available(self.remote_info, self.branch_name)

    def _latest_row(self):
        return self.comparison_rows[0] if self.comparison_rows else None

    def refresh_snapshot(self, initial=False):
        self._refresh_remote_target()
        self._refresh_local_manifest()
        configured = self._updates_configured()
        row = self._latest_row()
        local_version = (self.local_manifest[0].get("local_version") if self.local_manifest else "Unknown")
        remote_version = row.get("remote_version", "Not checked") if row else "Not checked"
        status_text = row.get("status", "Pending") if row else ("Pending" if configured else "Unavailable")

        note_text = self.model.update_configuration_note(self.remote_info)
        if configured:
            if row and row.get("update_available"):
                note_text = f"A newer stable {self._stable_artifact_noun()} target is available from the repository branch."
            elif row:
                note_text = f"No newer stable {self._stable_artifact_noun()} target is available right now."
            else:
                note_text = "Run a repository check to compare the packaged release target."

        snapshot = {
            "repository": self.remote_info.get("display", "Unknown repository"),
            "branch": self.branch_name,
            "stable_artifact": self.stable_artifact_label,
            "updates_configured": "Yes" if configured else "No",
            "local_version": local_version,
            "remote_version": remote_version,
            "status": status_text,
            "job_phase": self.job_phase,
            "job_detail": self.job_detail,
            "configuration_note": self.model.update_configuration_note(self.remote_info),
            "module_payloads": str(len(self.model.discover_module_payload_options(None))),
            "documentation_payloads": str(self.documentation_payload_count),
            "documentation_remote_state": "Not checked",
            "documentation_status": "Pending",
            "documentation_note": "Check and apply grouped documentation restores from the repository.",
            "advanced_channel_enabled": "Yes" if self.advanced_dev_updates_enabled else "No",
            "advanced_source_phase": self.source_job_phase,
            "advanced_source_detail": self.source_job_detail,
            "advanced_recovery_available": "Yes" if self.source_recovery_available else "No",
            "advanced_build_log": self.source_build_log_path or "Not available",
            "note": (
                "Slice 4 Qt sidecar: stable, module payload, documentation payload, and advanced source operations are available via host runtime requests."
            ),
            "summary_note": note_text,
        }
        selected_option = self._get_selected_payload_option()
        snapshot["module_payload_selected"] = selected_option.get("module_name") if selected_option else "No payload selected"
        snapshot["module_payload_path"] = selected_option.get("relative_path") if selected_option else "Payload updates are not available."
        self.view.render_snapshot(snapshot)
        self.view.set_module_payload_options(self.module_payload_options, self.selected_payload_key)
        message = "Update Manager Qt window ready." if initial else "Refreshed Update Manager snapshot."
        self.write_state(status="ready", message=message)

    def _get_selected_payload_option(self):
        selected_key = str(self.selected_payload_key or "").strip().lower()
        if not selected_key:
            return None
        for option in self.module_payload_options:
            if str(option.get("key") or "").strip().lower() == selected_key:
                return option
        return None

    def on_payload_selection_changed(self, payload_key):
        self.selected_payload_key = str(payload_key or "").strip()
        option = self._get_selected_payload_option()
        if option:
            self.write_state(status="ready", message=f"Selected payload: {option.get('module_name', self.selected_payload_key)}.", dirty=True)

    def request_check_module_payload(self):
        option = self._get_selected_payload_option()
        if option is None:
            self.view.show_info("Update Manager", "No module payload is selected.")
            return
        self.write_state(
            status="ready",
            message=f"Requested payload check for {option.get('module_name')}.",
            runtime_event="check_module_payload_requested",
            metadata={"payload_key": self.selected_payload_key},
        )
        self.view.show_info("Update Manager", "Module payload check was requested in the host runtime.")

    def request_apply_module_payload(self):
        option = self._get_selected_payload_option()
        if option is None:
            self.view.show_info("Update Manager", "No module payload is selected.")
            return
        self.write_state(
            status="ready",
            message=f"Requested payload install for {option.get('module_name')}.",
            runtime_event="apply_module_payload_requested",
            metadata={"payload_key": self.selected_payload_key},
        )
        self.view.show_info("Update Manager", "Module payload install was requested in the host runtime.")

    def request_apply_all_module_payloads(self):
        self.write_state(
            status="ready",
            message="Requested install for all available module payload updates.",
            runtime_event="apply_all_module_payload_updates_requested",
        )
        self.view.show_info("Update Manager", "Bulk module payload install was requested in the host runtime.")

    def request_check_documentation_payload_updates(self):
        self.write_state(
            status="ready",
            message="Requested documentation payload check.",
            runtime_event="check_documentation_payload_updates_requested",
        )
        self.view.show_info("Update Manager", "Documentation restore check was requested in the host runtime.")

    def request_apply_documentation_payload_updates(self):
        self.write_state(
            status="ready",
            message="Requested grouped documentation payload restore.",
            runtime_event="apply_documentation_payload_updates_requested",
        )
        self.view.show_info("Update Manager", "Documentation restore install was requested in the host runtime.")

    def request_start_advanced_source_update(self):
        self.write_state(
            status="ready",
            message="Requested advanced source update start.",
            runtime_event="start_advanced_source_update_requested",
        )
        self.view.show_info("Update Manager", "Advanced source update start was requested in the host runtime.")

    def request_retry_source_job(self):
        self.write_state(
            status="ready",
            message="Requested retry for source update job.",
            runtime_event="retry_source_job_requested",
        )
        self.view.show_info("Update Manager", "Source update retry was requested in the host runtime.")

    def request_cleanup_source_job(self):
        self.write_state(
            status="ready",
            message="Requested cleanup for source update job artifacts.",
            runtime_event="cleanup_source_job_requested",
        )
        self.view.show_info("Update Manager", "Source update cleanup was requested in the host runtime.")

    def request_open_source_build_log(self):
        self.write_state(
            status="ready",
            message="Requested open source build log.",
            runtime_event="open_source_build_log_requested",
        )
        self.view.show_info("Update Manager", "Open source build log request was sent to the host runtime.")

    def check_repository(self):
        self.job_phase = "Checking"
        self.job_detail = f"Checking the repository for newer stable {self._stable_artifact_noun(plural=True)}."
        self.refresh_snapshot(initial=False)

        if not self._updates_configured():
            self.comparison_rows = []
            self.job_phase = "Idle"
            self.job_detail = self.model.update_configuration_note(self.remote_info)
            self.refresh_snapshot(initial=False)
            return

        try:
            self.comparison_rows = self.model.build_stable_update_rows(
                self.local_manifest,
                self.remote_info,
                self.branch_name,
                self.stable_artifact_kind,
                self._stable_artifact_name_for_version,
                self._stable_artifact_status_label(),
            )
        except Exception as exc:
            self.job_phase = "Failed"
            self.job_detail = f"Repository check failed: {exc}"
            self.refresh_snapshot(initial=False)
            self.view.show_error("Update Manager", f"Could not check repository updates:\n{exc}")
            return

        available_count = sum(1 for row in self.comparison_rows if row.get("update_available"))
        if available_count:
            self.job_phase = "Ready"
            self.job_detail = f"{available_count} stable {self._stable_artifact_noun(plural=True)} are ready."
        else:
            self.job_phase = "Idle"
            self.job_detail = f"No stable {self._stable_artifact_noun(plural=True)} are ready."
        self.refresh_snapshot(initial=False)

    def request_apply_stable_updates(self):
        if not self.comparison_rows:
            self.check_repository()

        update_rows = [row for row in self.comparison_rows if row.get("update_available")]
        if not update_rows:
            self.view.show_info("Update Manager", f"No stable {self._stable_artifact_noun(plural=True)} are available to apply.")
            return

        self.job_phase = "Applying"
        self.job_detail = f"Requested stable {self._stable_artifact_noun()} apply in the host runtime."
        self.refresh_snapshot(initial=False)
        self.write_state(
            status="ready",
            message="Requested stable update apply from Qt sidecar.",
            runtime_event="apply_stable_updates_requested",
            metadata={
                "remote_version": str(update_rows[0].get("remote_version") or "Unknown"),
                "stable_artifact_label": self.stable_artifact_label,
            },
        )
        self.view.show_info(
            "Update Manager",
            (
                "Stable update apply was requested. The host runtime handles download/installer launch, "
                "and may close the app when handoff begins."
            ),
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
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Update Manager Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="Update Manager Qt window closed.")
