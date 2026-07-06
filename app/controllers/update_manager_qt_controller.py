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

from app.controllers.update_manager_runtime_controller import UpdateManagerRuntimeController
from app.models.update_manager_model import UpdateManagerModel
from app.views.update_manager_qt_view import UpdateManagerQtView

__module_name__ = "Update Manager Qt Controller"
__version__ = "2.5.0"


class SimpleVar:
    def __init__(self, value="", on_change=None):
        self._value = value
        self._on_change = on_change

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        if callable(self._on_change):
            self._on_change()


class UpdateManagerQtController:
    SUCCESS_BANNER_AUTOHIDE_MS = UpdateManagerRuntimeController.SUCCESS_BANNER_AUTOHIDE_MS
    RUNTIME_SKIP_BIND_METHODS = {"__init__", "mount", "on_hide", "on_unload"}

    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self._bind_runtime_methods()
        self.requested_view_backend = "qt"
        self.resolved_view_backend = "qt"
        self.view_backend_fallback_reason = None
        self.runtime_manager = None
        self._last_runtime_event_timestamp = None
        self._runtime_listener_registered = False
        self.view = None
        self._view_ready = False
        self.model = self._create_model()
        self.coordinator = self.dispatcher.update_coordinator
        self.branch_name = self.coordinator.branch_name or self.model.detect_branch_name()
        configured_repo_url = self.dispatcher.get_setting("update_repository_url", None)
        self.remote_info = self.coordinator.remote_info if self.coordinator.remote_info.get("display") != "Unknown repository" else self.model.detect_remote_info(preferred_url=configured_repo_url)
        self.local_manifest = self.coordinator.local_manifest
        self.comparison_rows = self.coordinator.comparison_rows
        self.status_var = self._create_var(self.coordinator.status_var.get() if hasattr(self.coordinator.status_var, "get") else "")
        self.branch_var = self._create_var(self.coordinator.branch_var.get() if hasattr(self.coordinator.branch_var, "get") else "")
        self.repo_var = self._create_var(self.coordinator.repo_var.get() if hasattr(self.coordinator.repo_var, "get") else "")
        self.target_name_var = self._create_var(self.coordinator.target_name_var.get() if hasattr(self.coordinator.target_name_var, "get") else "")
        self.local_version_var = self._create_var(self.coordinator.local_version_var.get() if hasattr(self.coordinator.local_version_var, "get") else "")
        self.remote_version_var = self._create_var(self.coordinator.remote_version_var.get() if hasattr(self.coordinator.remote_version_var, "get") else "")
        self.result_var = self._create_var(self.coordinator.result_var.get() if hasattr(self.coordinator.result_var, "get") else "")
        self.note_var = self._create_var(self.coordinator.note_var.get() if hasattr(self.coordinator.note_var, "get") else "")
        self.job_phase_var = self._create_var(self.coordinator.job_phase_var.get() if hasattr(self.coordinator.job_phase_var, "get") else "")
        self.job_detail_var = self._create_var(self.coordinator.job_detail_var.get() if hasattr(self.coordinator.job_detail_var, "get") else "")
        self.stable_artifact_kind = self._discover_stable_artifact_kind()
        self.stable_artifact_label = self._discover_stable_artifact_label()
        self.module_payload_options = self._discover_payload_options()
        self.documentation_payload_options = self.model.discover_documentation_payload_options()
        default_option = next((option for option in self.module_payload_options if option["key"] == "about"), None)
        if default_option is None and self.module_payload_options:
            default_option = self.module_payload_options[0]
        self.module_payload_selection_var = self._create_var(default_option["display"] if default_option else "No module payloads available")
        self.module_payload_name_var = self._create_var(default_option["module_name"] if default_option else "No payload selected")
        self.module_payload_path_var = self._create_var(default_option["relative_path"] if default_option else "Payload updates are not available.")
        self.module_payload_local_version_var = self._create_var("Unknown")
        self.module_payload_remote_version_var = self._create_var("Not checked")
        self.module_payload_status_var = self._create_var("Pending")
        self.module_payload_governance_var = self._create_var("Not checked")
        self.module_payload_checksum_var = self._create_var("Not checked")
        self.module_payload_note_var = self._create_var(self._payload_boundary_note("Select a payload to compare against the repository."))
        self.module_payload_in_progress = False
        self.documentation_payload_tracked_var = self._create_var(f"{len(self.documentation_payload_options)} tracked file(s)")
        self.documentation_payload_remote_state_var = self._create_var("Not checked")
        self.documentation_payload_status_var = self._create_var("Pending")
        self.documentation_payload_note_var = self._create_var("Documentation restores are grouped into one action so bundled help files can be refreshed without choosing individual documents.")
        self.documentation_payload_in_progress = False
        self.container = None
        self.coordinator.branch_name = self.branch_name
        self.coordinator.remote_info = self.remote_info
        self.branch_var.set(self.branch_name or "Unknown")
        self.repo_var.set(self.remote_info.get("display", "Unknown repository"))
        payload = self._build_view_payload()
        self.view = UpdateManagerQtView(self, payload, parent_widget=parent)
        self._view_ready = True
        if hasattr(self.dispatcher, "register_runtime_settings_listener"):
            self.dispatcher.register_runtime_settings_listener(self._handle_runtime_settings_change)
            self._runtime_listener_registered = True
        self.refresh_local_manifest()
        self.refresh_summary()
        self.refresh_module_payload_summary()
        if not self._updates_configured():
            self.refresh_documentation_payload_summary(
                remote_state="Not configured",
                status="Unavailable",
                note=self._update_configuration_note(),
            )
        else:
            self.refresh_documentation_payload_summary(
                remote_state="Not checked",
                status="Pending",
                note="Check and apply grouped documentation restores from the repository.",
            )
        self._render_from_state()
        self.view.show()

    def _bind_runtime_methods(self):
        for method_name, descriptor in UpdateManagerRuntimeController.__dict__.items():
            if method_name.startswith("__"):
                continue
            if method_name in self.RUNTIME_SKIP_BIND_METHODS:
                continue
            if method_name in type(self).__dict__:
                continue
            if hasattr(descriptor, "__get__"):
                self.__dict__[method_name] = descriptor.__get__(self, type(self))
            else:
                self.__dict__[method_name] = descriptor

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is not None:
            return getattr(view, attribute_name)
        raise AttributeError(attribute_name)

    def _create_model(self):
        if hasattr(self, "model") and self.model is not None:
            return self.model
        return UpdateManagerModel(data_registry=getattr(self.dispatcher, "external_data_registry", None))

    def _create_var(self, value=""):
        return SimpleVar(value=value, on_change=self._render_from_state)

    def _render_from_state(self):
        if not self._view_ready or self.view is None:
            return
        selected_option = self._get_selected_module_payload_option()
        selected_key = str((selected_option or {}).get("key") or "")
        snapshot = {
            "repository": self.repo_var.get() or "Unknown repository",
            "branch": self.branch_var.get() or "Unknown",
            "stable_artifact": self.stable_artifact_label,
            "target_name": self.target_name_var.get() or f"Dispatcher Core ({self.stable_artifact_label})",
            "updates_configured": "Yes" if self._updates_configured() else "No",
            "local_version": self.local_version_var.get() or "Unknown",
            "remote_version": self.remote_version_var.get() or "Not checked",
            "status": self.result_var.get() or "Pending",
            "runtime_status": self.status_var.get() or "Ready",
            "job_phase": self.job_phase_var.get() or "Idle",
            "job_detail": self.job_detail_var.get() or "No update job is running.",
            "summary_note": self.note_var.get() or "Run a repository check to compare the packaged release target.",
            "configuration_note": self._update_configuration_note(),
            "module_payloads": str(len(self.module_payload_options or [])),
            "module_payload_selected": self.module_payload_name_var.get() or "No payload selected",
            "module_payload_path": self.module_payload_path_var.get() or "Payload updates are not available.",
            "module_payload_local_version": self.module_payload_local_version_var.get() or "Unknown",
            "module_payload_remote_version": self.module_payload_remote_version_var.get() or "Not checked",
            "module_payload_status": self.module_payload_status_var.get() or "Pending",
            "module_payload_governance": self.module_payload_governance_var.get() or "Not checked",
            "module_payload_checksum_status": self.module_payload_checksum_var.get() or "Not checked",
            "module_payload_note": self.module_payload_note_var.get() or self._payload_boundary_note("Select a payload to compare against the repository."),
            "documentation_payloads": self.documentation_payload_tracked_var.get() or "0 tracked file(s)",
            "documentation_remote_state": self.documentation_payload_remote_state_var.get() or "Not checked",
            "documentation_status": self.documentation_payload_status_var.get() or "Pending",
            "documentation_note": self.documentation_payload_note_var.get() or "Check and apply grouped documentation restores from the repository.",
            "advanced_channel_enabled": "Yes" if bool(self.dispatcher.get_setting("enable_advanced_dev_updates", False)) else "No",
            "advanced_source_phase": str(self.coordinator.job_phase or "idle"),
            "advanced_source_detail": str(self.coordinator.job_detail or "No update job is running."),
            "advanced_recovery_available": "Yes" if self._has_recoverable_source_job() else "No",
            "advanced_build_log": str(self.coordinator.source_build_log_path or "Not available"),
            "note": "Manage stable updates, payload restores, documentation restores, and advanced source operations from this page.",
        }
        self.view.render_snapshot(snapshot)
        self.view.set_module_payload_options(self.module_payload_options, selected_key)
        try:
            self.view.refresh_rollback_list(self.model.list_rollback_backups())
        except Exception:
            pass

    def _build_view_payload(self):
        theme_tokens = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "Update Manager - Production Logging Center",
            "title": "Update Manager",
            "subtitle": "Manage stable releases, payload restores, and advanced source updates from this page.",
            "theme_tokens": theme_tokens,
        }

    def _discover_stable_artifact_kind(self):
        return self.coordinator.stable_artifact_kind if hasattr(self.coordinator, "stable_artifact_kind") and self.coordinator.stable_artifact_kind else getattr(type(self), "stable_artifact_kind", None) or __import__("app.app_platform", fromlist=["get_platform_update_artifact_kind"]).get_platform_update_artifact_kind()

    def _discover_stable_artifact_label(self):
        return self.coordinator.stable_artifact_label if hasattr(self.coordinator, "stable_artifact_label") and self.coordinator.stable_artifact_label else __import__("app.app_platform", fromlist=["get_platform_update_artifact_label"]).get_platform_update_artifact_label()

    def _show_error_dialog(self, title, message):
        view = self.view
        if view is not None:
            view.show_error(title, message)
            return
        self.dispatcher.host_ui_adapter.show_error(str(title), str(message))

    def _ask_yes_no_dialog(self, title, message):
        view = self.view
        if view is not None:
            return view.ask_yes_no(title, message)
        return bool(self.dispatcher.host_ui_adapter.ask_yes_no(str(title), str(message)))

    def on_payload_selection_changed(self, payload_key):
        payload_key = str(payload_key or "").strip().lower()
        for option in self.module_payload_options:
            if str(option.get("key") or "").strip().lower() == payload_key:
                self.module_payload_selection_var.set(option.get("display", self.module_payload_selection_var.get()))
                self.handle_module_payload_selection_change()
                return

    def refresh_snapshot(self, initial=False):
        self.refresh_local_manifest()
        self.refresh_summary()
        self.refresh_module_payload_summary()
        self._render_from_state()
        return None

    def setup_ui(self):
        self._render_from_state()
        return None

    def apply_theme(self):
        if self.view is not None:
            self.view.apply_theme(theme_tokens=self._build_view_payload().get("theme_tokens") or {})

    def show(self):
        if self.view is None:
            return
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False, runtime_event=None, metadata=None):
        _ = status
        _ = message
        _ = dirty
        _ = runtime_event
        _ = metadata
        self._render_from_state()

    def poll_commands(self):
        return None

    def handle_close(self):
        return None

    def on_hide(self):
        return None

    def on_unload(self):
        if self._runtime_listener_registered:
            self.dispatcher.unregister_runtime_settings_listener(self._handle_runtime_settings_change)
            self._runtime_listener_registered = False
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

    def restore_rollback(self, backup_dir):
        try:
            self.model.restore_rollback_backup(backup_dir)
            self.view.show_info("Rollback Complete", "Revert completed successfully! Restarting the suite...")
            if self.dispatcher is not None and hasattr(self.dispatcher, "shutdown"):
                # Attempt silent/clean restart if platform supports it, or simply shutdown
                import sys
                import subprocess
                try:
                    subprocess.Popen([sys.executable] + sys.argv)
                except Exception:
                    pass
                self.dispatcher.shutdown()
        except Exception as exc:
            self.view.show_error("Rollback Error", f"Failed to restore rollback payload: {exc}")

    def refresh_rollback_list(self):
        self.refresh_snapshot()
