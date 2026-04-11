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
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import zipfile
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from app.app_identity import format_versioned_deb_name, format_versioned_exe_name
from app.app_platform import get_platform_update_artifact_kind, get_platform_update_artifact_label, is_windows_runtime, open_with_system_default
from app.models.update_manager_model import (
    _detect_branch_name,
    _detect_remote_info,
    _parse_json_payload_metadata,
    _read_module_metadata_from_path,
    _remote_updates_available,
    _update_configuration_note,
    build_local_manifest,
    cleanup_source_stage_dir,
    discover_documentation_payload_options,
    discover_module_payload_options,
    download_remote_executable,
    evaluate_module_payload_option,
    evaluate_stable_update_entry,
    fetch_remote_bytes,
    fetch_remote_payload_text,
    fetch_remote_snapshot_bytes,
    get_local_module_payload_metadata,
    install_documentation_payload_option,
    install_module_payload_option,
    locate_extracted_source_root,
    probe_remote_executable,
    remote_executable_candidates,
    remove_paths,
    resolve_built_executable,
    resolve_build_python_command,
    resolve_download_directory,
    resolve_final_built_executable_path,
    resolve_source_log_directory,
    resolve_source_workspace,
    scan_available_documentation_payload_updates,
    scan_available_module_payload_updates,
    validate_source_snapshot,
    write_source_build_log,
)
from app.views.update_manager_view import UpdateManagerView

__module_name__ = "Update Manager"
__version__ = "2.1.4"


class UpdateManagerController:
    SUCCESS_BANNER_AUTOHIDE_MS = 5000

    def __init__(self, parent, dispatcher):
        self.parent = None
        self.dispatcher = dispatcher
        self.coordinator = self.dispatcher.update_coordinator
        self.branch_name = self.coordinator.branch_name or _detect_branch_name()
        configured_repo_url = self.dispatcher.get_setting("update_repository_url", None)
        self.remote_info = self.coordinator.remote_info if self.coordinator.remote_info.get("display") != "Unknown repository" else _detect_remote_info(preferred_url=configured_repo_url)
        self.local_manifest = self.coordinator.local_manifest
        self.comparison_rows = self.coordinator.comparison_rows
        self.status_var = self.coordinator.status_var
        self.branch_var = self.coordinator.branch_var
        self.repo_var = self.coordinator.repo_var
        self.target_name_var = self.coordinator.target_name_var
        self.local_version_var = self.coordinator.local_version_var
        self.remote_version_var = self.coordinator.remote_version_var
        self.result_var = self.coordinator.result_var
        self.note_var = self.coordinator.note_var
        self.job_phase_var = self.coordinator.job_phase_var
        self.job_detail_var = self.coordinator.job_detail_var
        self.module_payload_options = self._discover_payload_options()
        self.documentation_payload_options = discover_documentation_payload_options()
        default_option = next((option for option in self.module_payload_options if option["key"] == "about"), None)
        if default_option is None and self.module_payload_options:
            default_option = self.module_payload_options[0]
        self.module_payload_selection_var = tb.StringVar(value=default_option["display"] if default_option else "No module payloads available")
        self.module_payload_name_var = tb.StringVar(value=default_option["module_name"] if default_option else "No payload selected")
        self.module_payload_path_var = tb.StringVar(value=default_option["relative_path"] if default_option else "Payload updates are not available.")
        self.module_payload_local_version_var = tb.StringVar(value="Unknown")
        self.module_payload_remote_version_var = tb.StringVar(value="Not checked")
        self.module_payload_status_var = tb.StringVar(value="Pending")
        self.module_payload_note_var = tb.StringVar(value="Select a payload to compare against the repository. Dispatcher Core (launcher.py) remains an EXE-only update boundary.")
        self.module_payload_in_progress = False
        self.documentation_payload_tracked_var = tb.StringVar(value=f"{len(self.documentation_payload_options)} tracked file(s)")
        self.documentation_payload_remote_state_var = tb.StringVar(value="Not checked")
        self.documentation_payload_status_var = tb.StringVar(value="Pending")
        self.documentation_payload_note_var = tb.StringVar(value="Documentation restores are grouped into one action so bundled help files can be refreshed without choosing individual documents.")
        self.documentation_payload_in_progress = False
        self.container = None
        self.stable_artifact_kind = get_platform_update_artifact_kind()
        self.stable_artifact_label = get_platform_update_artifact_label()
        self.coordinator.branch_name = self.branch_name
        self.coordinator.remote_info = self.remote_info
        self.branch_var.set(self.branch_name or "Unknown")
        self.repo_var.set(self.remote_info.get("display", "Unknown repository"))
        self.dispatcher.register_runtime_settings_listener(self._handle_runtime_settings_change)
        self.refresh_local_manifest()
        self.refresh_summary()
        self.refresh_module_payload_summary()
        self.mount(parent)

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

    def mount(self, parent):
        self.parent = parent
        self.view = UpdateManagerView(parent, self)
        self.container = self.view.container

    def on_hide(self):
        return None

    def on_unload(self):
        self.dispatcher.unregister_runtime_settings_listener(self._handle_runtime_settings_change)
        return None

    def _handle_runtime_settings_change(self, _settings):
        self._apply_remote_configuration()

    def _apply_remote_configuration(self):
        self.branch_name = _detect_branch_name()
        configured_repo_url = self.dispatcher.get_setting("update_repository_url", None)
        self.remote_info = _detect_remote_info(preferred_url=configured_repo_url)
        self.coordinator.branch_name = self.branch_name
        self.coordinator.remote_info = self.remote_info
        self.branch_var.set(self.branch_name or "Unknown")
        self.repo_var.set(self.remote_info.get("display", "Updates not configured"))

    def _updates_configured(self):
        return _remote_updates_available(self.remote_info, self.branch_name)

    def _update_configuration_note(self):
        return _update_configuration_note(self.remote_info)

    def _discover_payload_options(self):
        return discover_module_payload_options(getattr(self.dispatcher, "modules_path", None))

    def _payload_job_is_busy(self):
        return any([
            self.module_payload_in_progress,
            self.documentation_payload_in_progress,
            self.coordinator.download_in_progress,
            self.coordinator.source_job_in_progress,
        ])

    def _get_selected_module_payload_option(self):
        selected_display = self.module_payload_selection_var.get().strip()
        for option in self.module_payload_options:
            if option["display"] == selected_display:
                return option
        return self.module_payload_options[0] if self.module_payload_options else None

    def _get_local_module_payload_metadata(self, option):
        override_path = None
        if option and option.get("kind") == "module" and self.dispatcher.are_external_module_overrides_enabled():
            override_path = self.dispatcher.get_external_module_override_path(option["key"])
        return get_local_module_payload_metadata(
            self.dispatcher.modules_path,
            self.dispatcher.loaded_modules,
            option,
            external_override_path=override_path,
        )

    def _evaluate_selected_module_payload(self, option):
        override_path = None
        if option and option.get("kind") == "module" and self.dispatcher.are_external_module_overrides_enabled():
            override_path = self.dispatcher.get_external_module_override_path(option["key"])
        return evaluate_module_payload_option(
            self.dispatcher.modules_path,
            self.dispatcher.loaded_modules,
            option,
            self.branch_name,
            self.remote_info,
            external_override_path=override_path,
        )

    def handle_module_payload_selection_change(self, _event=None):
        option = self._get_selected_module_payload_option()
        if option is None:
            self.module_payload_name_var.set("No payload selected")
            self.module_payload_path_var.set("Payload updates are not available.")
            self.module_payload_local_version_var.set("Unknown")
            self.module_payload_remote_version_var.set("Not available")
            self.module_payload_status_var.set("Unavailable")
            self.module_payload_note_var.set("No payload-eligible items are available. Dispatcher Core (launcher.py) remains an EXE-only update boundary.")
            return

        local_metadata = self._get_local_module_payload_metadata(option)
        option["module_name"] = local_metadata.get("module_name", option["module_name"])
        self.module_payload_name_var.set(option["module_name"])
        self.module_payload_path_var.set(option["relative_path"])
        if not self._updates_configured():
            self.refresh_module_payload_summary(
                remote_version="Not configured",
                status="Unavailable",
                note=self._update_configuration_note(),
            )
            return
        self.refresh_module_payload_summary(
            remote_version="Not checked",
            status="Pending",
            note=f"Check the repository to compare the selected {option['module_name']} payload. Dispatcher Core (launcher.py) still updates through the EXE path above.",
        )

    def _has_recoverable_source_job(self):
        return any([
            self.coordinator.source_archive_path,
            self.coordinator.source_stage_dir,
            self.coordinator.source_extract_dir,
            self.coordinator.source_root_dir,
            self.coordinator.source_build_log_path,
            self.coordinator.source_built_exe_path,
            self.coordinator.mode == "advanced",
        ])

    def retry_source_job(self):
        if self.coordinator.download_in_progress or self.coordinator.source_job_in_progress:
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
            return

        if self.coordinator.source_root_dir and os.path.isdir(self.coordinator.source_root_dir):
            self.coordinator.set_source_phase("source_building", "Retrying background build work from the recovered staged source snapshot.")
            self._begin_source_build_worker()
            return

        if self._has_recoverable_source_job():
            self.coordinator.set_source_phase("source_manifest", "Retrying the source snapshot download after a recovered or failed source job.")
            self._begin_source_download_worker()
            return

        self.dispatcher.show_toast("Update Manager", "No recoverable source update job is available to retry.", INFO)

    def open_source_build_log(self):
        log_path = self.coordinator.source_build_log_path
        if not log_path or not os.path.exists(log_path):
            self.dispatcher.show_toast("Update Manager", "No source build log is available to open.", INFO)
            return
        try:
            os.startfile(log_path)
        except Exception as exc:
            Messagebox.show_error(f"Could not open the source build log:\n\n{exc}", "Build Log Error")

    def cleanup_source_job(self):
        if self.coordinator.download_in_progress or self.coordinator.source_job_in_progress:
            self.dispatcher.show_toast("Update Manager", "Wait for the active background update job to finish before cleaning up.", WARNING)
            return

        if self.coordinator.source_root_dir and os.path.isdir(self.coordinator.source_root_dir):
            if not messagebox.askyesno(
                "Cleanup Source Job",
                (
                    "A recovered staged source tree is still present for this advanced update.\n\n"
                    "Cleaning up will remove the staged source files and associated logs for this source job.\n\n"
                    "Continue?"
                ),
            ):
                return

        removed_items = remove_paths([self.coordinator.source_build_log_path, self.coordinator.source_stage_dir])

        self.coordinator.clear_source_snapshot()
        self.coordinator.set_build_runtime(None, None)
        self.coordinator.set_job_phase("idle", "No update job is running.", mode=None)
        self.status_var.set("Advanced source job cleanup complete.")
        self.dispatcher.clear_update_status()

        if removed_items:
            self.dispatcher.show_toast("Update Manager", f"Cleaned up {len(removed_items)} source job artifact(s).", SUCCESS)
        else:
            self.dispatcher.show_toast("Update Manager", "No staged source artifacts were found to clean up.", INFO)

    def _get_local_module_payload_version(self, option=None):
        option = option or self._get_selected_module_payload_option()
        return self._get_local_module_payload_metadata(option).get("version", "Unknown")

    def refresh_module_payload_summary(self, remote_version=None, status=None, note=None, option=None):
        option = option or self._get_selected_module_payload_option()
        local_metadata = self._get_local_module_payload_metadata(option)
        if option is not None:
            option["module_name"] = local_metadata.get("module_name", option["module_name"])
            self.module_payload_name_var.set(option["module_name"])
            self.module_payload_path_var.set(option["relative_path"])
        self.module_payload_local_version_var.set(local_metadata.get("version", "Unknown"))
        if remote_version is not None:
            self.module_payload_remote_version_var.set(remote_version)
        if status is not None:
            self.module_payload_status_var.set(status)
        if note is not None:
            self.module_payload_note_var.set(note)

    def refresh_documentation_payload_summary(self, remote_state=None, status=None, note=None):
        self.documentation_payload_tracked_var.set(f"{len(self.documentation_payload_options)} tracked file(s)")
        if remote_state is not None:
            self.documentation_payload_remote_state_var.set(remote_state)
        if status is not None:
            self.documentation_payload_status_var.set(status)
        if note is not None:
            self.documentation_payload_note_var.set(note)

    def check_module_payload_update(self):
        option = self._get_selected_module_payload_option()
        if option is None:
            self.refresh_module_payload_summary(
                remote_version="Not available",
                status="Unavailable",
                note="No payload-eligible items are available. Dispatcher Core (launcher.py) remains an EXE-only update boundary.",
            )
            return

        if not self._updates_configured():
            self.refresh_module_payload_summary(
                remote_version="Not configured",
                status="Unavailable",
                note=self._update_configuration_note(),
                option=option,
            )
            return

        result = self._evaluate_selected_module_payload(option)
        option.update(result.get("option", {}))
        self.refresh_module_payload_summary(
            remote_version=result.get("remote_version", "Unavailable"),
            status=result.get("status", "Module check failed"),
            note=result.get("note", "Could not evaluate the selected payload."),
            option=option,
        )

    def check_documentation_payload_updates(self):
        if not self.documentation_payload_options:
            self.refresh_documentation_payload_summary(
                remote_state="Unavailable",
                status="Unavailable",
                note="No tracked documentation files are available for grouped restore checks.",
            )
            return

        if not self._updates_configured():
            self.refresh_documentation_payload_summary(
                remote_state="Not configured",
                status="Unavailable",
                note=self._update_configuration_note(),
            )
            return

        scan_result = scan_available_documentation_payload_updates(branch_name=self.branch_name, remote_info=self.remote_info)
        available_results = scan_result.get("available_results", [])
        available_count = len(available_results)

        if available_count:
            preview_names = [item.get("module_name") or item["option"].get("module_name") for item in available_results[:3]]
            preview = ", ".join(name for name in preview_names if name)
            if available_count > 3:
                preview = f"{preview}, and {available_count - 3} more"
            self.refresh_documentation_payload_summary(
                remote_state=f"{available_count} update(s) available",
                status="Documentation restore available",
                note=f"{available_count} tracked documentation file(s) differ from the repository and can be restored together: {preview}.",
            )
            return

        self.refresh_documentation_payload_summary(
            remote_state="Matched",
            status="Up to date",
            note=f"All {len(self.documentation_payload_options)} tracked documentation files already match the repository copy.",
        )

    def _finish_module_payload_install(self, option, installed_path, remote_version):
        self.module_payload_in_progress = False
        if option.get("kind") == "json":
            try:
                with open(installed_path, "r", encoding="utf-8") as handle:
                    installed_metadata = _parse_json_payload_metadata(handle.read(), option["fallback_name"])
            except OSError:
                installed_metadata = None
        else:
            installed_metadata = _read_module_metadata_from_path(installed_path, option["fallback_name"])

        if installed_metadata:
            self.module_payload_local_version_var.set(installed_metadata.get("version", "Unknown"))
            option["module_name"] = installed_metadata.get("module_name", option["module_name"])
        if option.get("kind") == "module":
            if self.dispatcher.is_external_module_override_trust_enabled():
                install_note = "Reload that part of the app to verify the change. The app will now prefer this external module file automatically whenever trusted external overrides are enabled."
                toast_message = f"Installed the {option['module_name']} payload. It will be used automatically when that module is reloaded."
            else:
                install_note = "The override file was saved, but it will stay inactive until an admin enables external override trust in Developer & Admin tools."
                toast_message = f"Installed the {option['module_name']} payload, but it remains inactive until override trust is enabled."
        else:
            install_note = "The previous local file was backed up before restore."
            toast_message = f"Installed the {option['module_name']} payload."
        self.refresh_module_payload_summary(
            remote_version=remote_version,
            status="Installed",
            note=(
                f"Installed the {option['module_name']} payload at {installed_path}. "
                f"{install_note}"
            ),
            option=option,
        )
        self.status_var.set(f"{option['module_name']} payload installed.")
        self.dispatcher.set_update_status(f"Installed the {option['module_name']} module payload.", SUCCESS, active=True, mode="module")
        self.dispatcher.clear_update_status_after(self.SUCCESS_BANNER_AUTOHIDE_MS)
        self.dispatcher.show_toast("Update Manager", toast_message, SUCCESS)

    def _finish_documentation_payload_install(self, installed_items, failed_items):
        self.documentation_payload_in_progress = False
        installed_count = len(installed_items)
        failed_count = len(failed_items)

        if failed_count:
            self.status_var.set(f"Installed {installed_count} documentation file(s). {failed_count} failed.")
            self.refresh_documentation_payload_summary(
                remote_state="Errors",
                status="Documentation install failed",
                note=f"Installed {installed_count} documentation file(s), but {failed_count} failed.",
            )
            self.dispatcher.set_update_status("Documentation restore completed with errors.", WARNING, active=True, mode="module")
            failure_lines = [f"{item['option']['module_name']}: {item['error']}" for item in failed_items]
            Messagebox.show_error("Could not restore all documentation files:\n\n" + "\n".join(failure_lines), "Documentation Restore Error")
            if installed_count:
                self.dispatcher.show_toast("Update Manager", f"Installed {installed_count} documentation file(s), but {failed_count} failed.", WARNING)
            return

        if installed_count:
            self.status_var.set(f"Installed {installed_count} documentation file(s).")
            self.refresh_documentation_payload_summary(
                remote_state="Installed",
                status="Installed",
                note=f"Installed {installed_count} tracked documentation file(s) into the external documentation path.",
            )
            self.dispatcher.set_update_status("Installed documentation restores.", SUCCESS, active=True, mode="module")
            self.dispatcher.clear_update_status_after(self.SUCCESS_BANNER_AUTOHIDE_MS)
            self.dispatcher.show_toast("Update Manager", f"Installed {installed_count} documentation file(s).", SUCCESS)
            return

        self.status_var.set("No documentation updates were available.")
        self.refresh_documentation_payload_summary(
            remote_state="Matched",
            status="Up to date",
            note="All tracked documentation files already match the repository copy.",
        )
        self.dispatcher.show_toast("Update Manager", "No documentation updates were available to install.", INFO)

    def _handle_module_payload_failure(self, option, exc):
        self.module_payload_in_progress = False
        self.refresh_module_payload_summary(
            status="Install failed",
            note=f"Could not install the {option['module_name']} payload: {exc}",
            option=option,
        )
        self.dispatcher.set_update_status(f"{option['module_name']} payload install failed.", DANGER, active=True, mode="module")
        Messagebox.show_error(f"Could not install the {option['module_name']} payload:\n\n{exc}", "Module Payload Error")

    def _install_documentation_payload_option(self, option, remote_text=None):
        payload_text = remote_text if remote_text is not None else self._fetch_remote_file(option["relative_path"])
        return install_documentation_payload_option(option, payload_text)

    def _install_module_payload_option(self, option, remote_text=None):
        payload_text = remote_text if remote_text is not None else self._fetch_remote_file(option["relative_path"])
        return install_module_payload_option(option, payload_text, self.dispatcher.install_module_override)

    def apply_module_payload_update(self):
        if self._payload_job_is_busy():
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
            return

        option = self._get_selected_module_payload_option()
        if option is None:
            self.dispatcher.show_toast("Update Manager", "No payload-eligible modules are available to install.", INFO)
            return

        self.module_payload_in_progress = True
        self.refresh_module_payload_summary(status="Downloading", note=f"Downloading and installing the {option['module_name']} payload override...")
        self.status_var.set(f"Installing {option['module_name']} payload override...")
        self.dispatcher.set_update_status(f"Installing the {option['module_name']} payload override...", INFO, active=True, mode="module")

        def worker():
            try:
                installed_path, remote_version = self._install_module_payload_option(option, remote_text=None)
            except Exception as exc:
                self.dispatcher.root.after(0, lambda current_option=option.copy(), error=exc: self._handle_module_payload_failure(current_option, error))
                return

            self.dispatcher.root.after(0, lambda current_option=option.copy(), path=installed_path, version=remote_version: self._finish_module_payload_install(current_option, path, version))

        threading.Thread(target=worker, daemon=True).start()

    def apply_documentation_payload_updates(self):
        if self._payload_job_is_busy():
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
            return

        if not self.documentation_payload_options:
            self.dispatcher.show_toast("Update Manager", "No tracked documentation files are available to restore.", INFO)
            return

        self.documentation_payload_in_progress = True
        self.refresh_documentation_payload_summary(
            remote_state="Checking",
            status="Checking",
            note="Checking the repository for all tracked documentation files before restoring them together.",
        )
        self.status_var.set("Checking documentation updates...")
        self.dispatcher.set_update_status("Checking documentation updates...", INFO, active=True, mode="module")

        def worker():
            installed_items = []
            failed_items = []
            try:
                scan_result = scan_available_documentation_payload_updates(branch_name=self.branch_name, remote_info=self.remote_info)
                available_results = scan_result.get("available_results", [])
                if not available_results:
                    self.dispatcher.root.after(0, lambda: self._finish_documentation_payload_install([], []))
                    return

                for result in available_results:
                    option = result["option"].copy()
                    try:
                        installed_path, remote_version = self._install_documentation_payload_option(option, remote_text=result.get("remote_text"))
                        installed_items.append({
                            "option": option,
                            "installed_path": installed_path,
                            "remote_version": remote_version,
                        })
                    except Exception as exc:
                        failed_items.append({
                            "option": option,
                            "error": exc,
                        })
            except Exception as exc:
                failed_items.append({
                    "option": {"module_name": "Documentation restore"},
                    "error": exc,
                })

            self.dispatcher.root.after(0, lambda installed=installed_items, failed=failed_items: self._finish_documentation_payload_install(installed, failed))

        threading.Thread(target=worker, daemon=True).start()

    def _detect_branch_name(self):
        return _detect_branch_name()

    def _detect_remote_info(self):
        configured_repo_url = self.dispatcher.get_setting("update_repository_url", None)
        return _detect_remote_info(preferred_url=configured_repo_url)

    def refresh_local_manifest(self):
        dispatcher_module = self.dispatcher.loaded_modules.get("main") or sys.modules.get("main") or sys.modules.get("__main__")
        self.local_manifest[:] = build_local_manifest(dispatcher_module)

    def refresh_summary(self):
        entry = self.local_manifest[0] if self.local_manifest else {
            "module_name": "Dispatcher Core",
            "local_version": "Unknown",
        }
        row = self.comparison_rows[0] if self.comparison_rows else None
        self.target_name_var.set(f"{entry['module_name']} ({self.stable_artifact_label})")
        self.local_version_var.set(entry.get("local_version", "Unknown"))
        self.remote_version_var.set(row.get("remote_version", "Not checked") if row else "Not checked")
        if not self._updates_configured():
            self.result_var.set("Unavailable")
            self.note_var.set(self._update_configuration_note())
            return
        self.result_var.set(row.get("status", "Pending") if row else "Pending")
        if row and row.get("update_available"):
            self.note_var.set(f"A newer stable {self._stable_artifact_noun()} target is available from the repository branch.")
        elif row:
            self.note_var.set(f"No newer stable {self._stable_artifact_noun()} target is available right now.")
        else:
            self.note_var.set("Run a repository check to compare the packaged release target.")

    def _fetch_remote_file(self, relative_path):
        return fetch_remote_payload_text(self.remote_info, self.branch_name, relative_path, timeout=15)

    def _finish_apply_all_module_payload_updates(self, installed_items, failed_items):
        self.module_payload_in_progress = False
        installed_count = len(installed_items)
        failed_count = len(failed_items)

        if installed_items:
            last_item = installed_items[-1]
            self.refresh_module_payload_summary(
                remote_version=last_item["remote_version"],
                status="Installed",
                note=f"Installed {installed_count} available payload(s).",
                option=last_item["option"],
            )
            self.handle_module_payload_selection_change()

        if failed_count:
            self.status_var.set(f"Installed {installed_count} payload(s). {failed_count} failed.")
            self.dispatcher.set_update_status("Module payload bulk install completed with errors.", WARNING, active=True, mode="module")
            failure_lines = [f"{item['option']['module_name']}: {item['error']}" for item in failed_items]
            Messagebox.show_error("Could not install all available payloads:\n\n" + "\n".join(failure_lines), "Bulk Module Payload Error")
            if installed_count:
                self.dispatcher.show_toast("Update Manager", f"Installed {installed_count} payload(s), but {failed_count} failed.", WARNING)
            return

        if installed_count:
            self.status_var.set(f"Installed {installed_count} available payload(s).")
            self.dispatcher.set_update_status(f"Installed {installed_count} available module payload(s).", SUCCESS, active=True, mode="module")
            self.dispatcher.clear_update_status_after(self.SUCCESS_BANNER_AUTOHIDE_MS)
            self.dispatcher.show_toast("Update Manager", f"Installed {installed_count} available payload(s).", SUCCESS)
            return

        self.status_var.set("No payload updates were available.")
        self.dispatcher.show_toast("Update Manager", "No payload updates were available to install.", INFO)

    def apply_all_module_payload_updates(self):
        if self._payload_job_is_busy():
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
            return

        if not self._updates_configured():
            self.refresh_module_payload_summary(
                remote_version="Not configured",
                status="Unavailable",
                note=self._update_configuration_note(),
            )
            self.dispatcher.show_toast("Update Manager", "Open Security Admin with the developer vault to configure the Update Repository URL before checking or installing payload updates.", INFO)
            return

        if not self.module_payload_options:
            self.dispatcher.show_toast("Update Manager", "No payload-eligible modules are available to install.", INFO)
            return

        self.module_payload_in_progress = True
        self.module_payload_status_var.set("Checking all payloads")
        self.module_payload_note_var.set("Checking the repository for all available payload restores before installing them.")
        self.status_var.set("Checking all payload updates...")
        self.dispatcher.set_update_status("Checking all payload updates...", INFO, active=True, mode="module")

        def worker():
            installed_items = []
            failed_items = []
            try:
                scan_result = scan_available_module_payload_updates(self.dispatcher, branch_name=self.branch_name, remote_info=self.remote_info)
                available_results = scan_result.get("available_results", [])
                if not available_results:
                    self.dispatcher.root.after(0, lambda: self._finish_apply_all_module_payload_updates([], []))
                    return

                for result in available_results:
                    option = result["option"].copy()
                    try:
                        installed_path, remote_version = self._install_module_payload_option(option, remote_text=result.get("remote_text"))
                        installed_items.append({
                            "option": option,
                            "installed_path": installed_path,
                            "remote_version": remote_version,
                        })
                    except Exception as exc:
                        failed_items.append({
                            "option": option,
                            "error": exc,
                        })
            except Exception as exc:
                failed_items.append({
                    "option": {"module_name": "Module payload scan"},
                    "error": exc,
                })

            self.dispatcher.root.after(0, lambda installed=installed_items, failed=failed_items: self._finish_apply_all_module_payload_updates(installed, failed))

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_remote_bytes(self, relative_path):
        return fetch_remote_bytes(self.remote_info, self.branch_name, relative_path)

    def _fetch_remote_snapshot_bytes(self):
        return fetch_remote_snapshot_bytes(self.remote_info, self.branch_name)

    def _remote_executable_candidates(self, row):
        return remote_executable_candidates(row, self.stable_artifact_kind, self._stable_artifact_name_for_version)

    def _probe_remote_executable(self, row):
        return probe_remote_executable(self.remote_info, self.branch_name, row, self.stable_artifact_kind, self._stable_artifact_name_for_version)

    def check_for_updates(self):
        self.coordinator.set_job_phase("checking", f"Checking the repository for newer stable {self._stable_artifact_noun(plural=True)}.", mode="stable")
        self.refresh_local_manifest()
        comparison_rows = []

        for entry in self.local_manifest:
            try:
                remote_text = self._fetch_remote_file(entry["relative_path"])
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    comparison_rows.append({
                        **entry,
                        "remote_version": "Missing",
                        "status": "Not in repository branch",
                        "update_available": False,
                    })
                    continue
                raise

            comparison_rows.append(
                evaluate_stable_update_entry(
                    entry,
                    remote_text,
                    self._stable_artifact_status_label(),
                    self._stable_artifact_name_for_version,
                )
            )

            current_row = comparison_rows[-1]
            if current_row["update_available"]:
                remote_path, resolved_name = self._probe_remote_executable(current_row)
                if remote_path:
                    current_row["remote_exe_path"] = remote_path
                    current_row["remote_exe_name"] = resolved_name
                else:
                    current_row["status"] = f"{self._stable_artifact_status_label()} artifact missing"
                    current_row["update_available"] = False

        self.comparison_rows[:] = comparison_rows
        self.refresh_summary()
        available_count = sum(1 for row in comparison_rows if row["update_available"])
        self.status_var.set(f"Checked Dispatcher Core on branch '{self.branch_name}'. {available_count} stable {self._stable_artifact_noun(plural=True)} available.")
        if available_count:
            self.coordinator.set_job_phase("ready", f"{available_count} stable {self._stable_artifact_noun(plural=True)} are ready.", mode="stable")
        else:
            self.coordinator.set_job_phase("idle", f"No stable {self._stable_artifact_noun(plural=True)} are ready.", mode="stable")

    def _download_remote_executable(self, row):
        return download_remote_executable(self.remote_info, self.branch_name, row, self.stable_artifact_kind, self._stable_artifact_name_for_version)

    def _finish_downloaded_update(self, downloaded_path):
        self.coordinator.download_in_progress = False
        if not is_windows_runtime():
            try:
                open_with_system_default(downloaded_path)
            except Exception as exc:
                Messagebox.show_error(f"The updated package was downloaded but could not be opened:\n\n{exc}", "Launch Error")
                self.status_var.set("Update package downloaded, but it could not be opened.")
                self.coordinator.set_job_phase("failed", "Stable update package downloaded, but opening it failed.", mode="stable")
                self.dispatcher.set_update_status("Stable update package downloaded, but opening it failed.", DANGER, active=True, mode="stable")
                return

            status_detail = (
                f"Downloaded {os.path.basename(downloaded_path)} and opened it with the system package handler. "
                "Complete the installation there, then restart the app."
            )
            self.status_var.set("Update package opened. Complete the installation in your package tool.")
            self.coordinator.set_job_phase("handoff", status_detail, mode="stable")
            self.dispatcher.set_update_status("Stable update package opened. Complete the installation in your package tool.", SUCCESS, active=True, mode="stable")
            self.dispatcher.clear_update_status_after(self.SUCCESS_BANNER_AUTOHIDE_MS)
            return

        removed_overrides = []
        try:
            removed_overrides = self.dispatcher.remove_external_module_overrides()
        except Exception as exc:
            Messagebox.show_error(f"The update was downloaded, but old module overrides could not be cleared:\n\n{exc}", "Override Cleanup Error")
            self.status_var.set("Update downloaded, but override cleanup failed.")
            self.coordinator.set_job_phase("failed", "Stable update downloaded, but override cleanup failed.", mode="stable")
            self.dispatcher.set_update_status("Stable update downloaded, but override cleanup failed.", DANGER, active=True, mode="stable")
            return

        try:
            os.startfile(downloaded_path)
        except Exception as exc:
            Messagebox.show_error(f"The updated executable was downloaded but could not be launched:\n\n{exc}", "Launch Error")
            self.status_var.set("Update downloaded, but launch failed.")
            self.coordinator.set_job_phase("failed", "Stable update downloaded, but launch failed.", mode="stable")
            self.dispatcher.set_update_status("Stable update downloaded, but launch failed.", DANGER, active=True, mode="stable")
            return

        removed_count = len(removed_overrides)
        status_detail = f"Launched {os.path.basename(downloaded_path)} and cleared {removed_count} stale module override(s) before closing the current version."
        self.status_var.set("Updated executable launched. Closing the current version.")
        self.coordinator.set_job_phase("handoff", status_detail, mode="stable")
        self.dispatcher.set_update_status("Stable update launched. Closing the current version.", SUCCESS, active=True, mode="stable")
        self.dispatcher.root.after(300, self.dispatcher.root.destroy)

    def _handle_download_failure(self, exc):
        self.coordinator.download_in_progress = False
        self.status_var.set(f"{self.stable_artifact_label} update download failed.")
        self.coordinator.set_job_phase("failed", f"Stable {self._stable_artifact_noun()} update download failed.", mode="stable")
        self.dispatcher.set_update_status(f"Stable {self._stable_artifact_noun()} update download failed.", DANGER, active=True, mode="stable")
        Messagebox.show_error(f"Could not download the updated {self._stable_artifact_noun()}:\n\n{exc}", "Update Error")

    def _resolve_download_directory(self):
        return resolve_download_directory()

    def _resolve_source_workspace(self):
        return resolve_source_workspace()

    def _resolve_source_log_directory(self):
        return resolve_source_log_directory()

    def _cleanup_source_stage_dir(self, stage_dir):
        cleanup_source_stage_dir(stage_dir)

    def _locate_extracted_source_root(self, extract_dir):
        return locate_extracted_source_root(extract_dir)

    def _validate_source_snapshot(self, source_root):
        validate_source_snapshot(source_root)

    def _resolve_build_python_command(self):
        return resolve_build_python_command(self._resolve_download_directory())

    def _write_source_build_log(self, log_name, content):
        return write_source_build_log(log_name, content)

    def _resolve_built_executable(self, source_root):
        return resolve_built_executable(source_root)

    def _resolve_final_built_executable_path(self, built_exe_path):
        current_executable = os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else None
        return resolve_final_built_executable_path(
            built_exe_path,
            download_directory=self._resolve_download_directory(),
            current_executable=current_executable,
        )

    def _handle_source_build_failure(self, exc, build_log_path=None):
        self.coordinator.source_job_in_progress = False
        self.coordinator.set_source_snapshot(
            archive_path=self.coordinator.source_archive_path,
            stage_dir=self.coordinator.source_stage_dir,
            extract_dir=self.coordinator.source_extract_dir,
            root_dir=self.coordinator.source_root_dir,
            build_log_path=build_log_path,
            built_exe_path=self.coordinator.source_built_exe_path,
        )
        detail = f"Source build failed: {exc}"
        if self.coordinator.source_build_runtime:
            detail = f"{detail} Runtime: {self.coordinator.source_build_runtime}."
        elif self.coordinator.source_build_runtime_issue:
            detail = f"{detail} Runtime issue: {self.coordinator.source_build_runtime_issue}."
        if build_log_path:
            detail = f"{detail} Log saved to {build_log_path}."
        self.coordinator.set_job_phase("failed", detail, mode="advanced")
        self.status_var.set("Advanced source build failed.")
        self.dispatcher.set_update_status("Advanced source build failed.", DANGER, active=True, mode="advanced")

    def _finish_source_build(self, built_exe_path, final_exe_path, build_log_path, stage_dir):
        self.coordinator.source_job_in_progress = False
        self.coordinator.set_source_snapshot(
            archive_path=self.coordinator.source_archive_path,
            stage_dir=stage_dir,
            extract_dir=self.coordinator.source_extract_dir,
            root_dir=self.coordinator.source_root_dir,
            build_log_path=build_log_path,
            built_exe_path=final_exe_path,
        )

        self.coordinator.set_source_phase("source_packaging", f"Prepared rebuilt executable {os.path.basename(final_exe_path)} for launch.")
        self.coordinator.set_source_phase("source_cleanup", "Cleaning up the temporary source staging area.")
        self._cleanup_source_stage_dir(stage_dir)
        self.coordinator.set_source_snapshot(build_log_path=build_log_path, built_exe_path=final_exe_path)

        self.coordinator.set_source_phase("source_relaunch", f"Launching rebuilt executable {os.path.basename(final_exe_path)}.")
        self.status_var.set("Advanced source rebuild complete. Launching the rebuilt executable.")
        self.dispatcher.set_update_status("Advanced source rebuild complete. Launching the rebuilt executable.", SUCCESS, active=True, mode="advanced")
        try:
            self.dispatcher.remove_external_module_overrides()
        except Exception as exc:
            self.coordinator.set_job_phase("failed", f"Source rebuild succeeded, but override cleanup failed: {exc}", mode="advanced")
            self.dispatcher.set_update_status("Advanced source rebuild succeeded, but override cleanup failed.", DANGER, active=True, mode="advanced")
            return
        try:
            os.startfile(final_exe_path)
        except Exception as exc:
            self.coordinator.set_job_phase("failed", f"Source rebuild succeeded, but relaunch failed: {exc}", mode="advanced")
            self.dispatcher.set_update_status("Advanced source rebuild succeeded, but relaunch failed.", DANGER, active=True, mode="advanced")
            return

        self.dispatcher.root.after(300, self.dispatcher.root.destroy)

    def _begin_source_build_worker(self):
        if self.coordinator.download_in_progress or self.coordinator.source_job_in_progress:
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
            return

        source_root = self.coordinator.source_root_dir
        stage_dir = self.coordinator.source_stage_dir
        if not source_root or not os.path.isdir(source_root):
            self.dispatcher.show_toast("Update Manager", "No staged source snapshot is available for background build work.", WARNING)
            return

        self.coordinator.source_job_in_progress = True
        self.coordinator.set_build_runtime(None, None)
        self.coordinator.set_source_phase("source_building", "Resolving a silent Python build runtime for the staged source snapshot.")
        self.status_var.set("Starting background source rebuild...")
        self.dispatcher.set_update_status("Starting background source rebuild...", INFO, active=True, mode="advanced")

        def worker():
            build_log_path = None
            try:
                command_prefix, runtime_display = self._resolve_build_python_command()
                self.coordinator.set_build_runtime(runtime_display, None)
                self.coordinator.set_source_phase("source_building", f"Building the staged source snapshot with {runtime_display}.")
                build_command = command_prefix + ["build.py"]
                env = os.environ.copy()
                env["MARTIN_KEEP_DIST"] = "1"
                env["MARTIN_SKIP_TASKKILL"] = "1"
                creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    build_command,
                    cwd=source_root,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=1800,
                    env=env,
                    creationflags=creation_flags,
                )
                build_log_text = (
                    f"Command: {' '.join(build_command)}\n"
                    f"Working Directory: {source_root}\n"
                    f"Return Code: {result.returncode}\n\n"
                    f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n"
                )
                log_name = f"source-build-{self.branch_name}.log"
                build_log_path = self._write_source_build_log(log_name, build_log_text)
                if result.returncode != 0:
                    raise RuntimeError(f"The staged build exited with code {result.returncode}.")

                built_exe_path = self._resolve_built_executable(source_root)
                self.coordinator.set_source_phase("source_packaging", f"Copying rebuilt executable {os.path.basename(built_exe_path)} next to the current app.")
                final_exe_path = self._resolve_final_built_executable_path(built_exe_path)
                shutil.copy2(built_exe_path, final_exe_path)
            except Exception as exc:
                if not self.coordinator.source_build_runtime:
                    self.coordinator.set_build_runtime(None, str(exc))
                self.dispatcher.root.after(0, lambda error=exc, log_path=build_log_path: self._handle_source_build_failure(error, log_path))
                return

            self.dispatcher.root.after(
                0,
                lambda built_exe_path=built_exe_path, final_exe_path=final_exe_path, log_path=build_log_path, current_stage_dir=stage_dir: self._finish_source_build(
                    built_exe_path,
                    final_exe_path,
                    log_path,
                    current_stage_dir,
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _handle_source_download_failure(self, exc, stage_dir=None):
        self.coordinator.source_job_in_progress = False
        self.coordinator.set_job_phase("failed", f"Source snapshot download failed: {exc}", mode="advanced")
        self.status_var.set("Advanced source update failed.")
        self.dispatcher.set_update_status("Advanced source update failed.", DANGER, active=True, mode="advanced")
        self._cleanup_source_stage_dir(stage_dir)
        self.coordinator.clear_source_snapshot()

    def _finish_source_download(self, archive_path, stage_dir, extract_dir, source_root):
        self.coordinator.source_job_in_progress = False
        self.coordinator.set_source_snapshot(
            archive_path=archive_path,
            stage_dir=stage_dir,
            extract_dir=extract_dir,
            root_dir=source_root,
        )
        self.coordinator.set_source_phase(
            "source_complete",
            f"Source snapshot staged at {source_root}. Starting background build work next.",
        )
        self.status_var.set("Advanced source snapshot staged. Starting background build work.")
        self.dispatcher.set_update_status(
            "Advanced source snapshot downloaded and staged. Starting background build work.",
            SUCCESS,
            active=True,
            mode="advanced",
        )
        self._begin_source_build_worker()

    def _begin_source_download_worker(self):
        if self.coordinator.download_in_progress or self.coordinator.source_job_in_progress:
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
            return

        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            self.dispatcher.show_toast("Update Manager", "Repository origin or branch could not be determined for the source snapshot.", WARNING)
            return

        previous_stage_dir = self.coordinator.source_stage_dir
        self.coordinator.source_job_in_progress = True
        self.coordinator.clear_source_snapshot()
        self.coordinator.set_source_phase(
            "source_manifest",
            f"Preparing the source snapshot manifest for {owner}/{repo}@{self.branch_name}.",
        )
        self.status_var.set("Preparing source snapshot download...")
        self.dispatcher.set_update_status(
            "Preparing background source snapshot download...",
            INFO,
            active=True,
            mode="advanced",
        )

        def worker():
            stage_dir = None
            try:
                if previous_stage_dir:
                    self._cleanup_source_stage_dir(previous_stage_dir)

                self.coordinator.set_source_phase(
                    "source_downloading",
                    f"Downloading the source snapshot for {owner}/{repo}@{self.branch_name} in the background.",
                )
                snapshot_bytes = self._fetch_remote_snapshot_bytes()

                stage_root = self._resolve_source_workspace()
                stage_dir = tempfile.mkdtemp(prefix="source-update-", dir=stage_root)
                archive_name = f"{repo}-{self.branch_name}.zip"
                archive_path = os.path.join(stage_dir, archive_name)
                with open(archive_path, "wb") as handle:
                    handle.write(snapshot_bytes)

                self.coordinator.set_source_phase(
                    "source_staging",
                    f"Saved the source snapshot archive to {archive_path}.",
                )

                extract_dir = os.path.join(stage_dir, "snapshot")
                os.makedirs(extract_dir, exist_ok=True)
                self.coordinator.set_source_phase(
                    "source_extracting",
                    "Extracting the downloaded source snapshot into the staging area.",
                )
                with zipfile.ZipFile(archive_path) as archive_handle:
                    archive_handle.extractall(extract_dir)

                source_root = self._locate_extracted_source_root(extract_dir)
                self.coordinator.set_source_phase(
                    "source_validating",
                    "Validating the staged source snapshot before handing it to the build worker.",
                )
                self._validate_source_snapshot(source_root)
            except Exception as exc:
                self.dispatcher.root.after(0, lambda error=exc, current_stage_dir=stage_dir: self._handle_source_download_failure(error, current_stage_dir))
                return

            self.dispatcher.root.after(
                0,
                lambda archive_path=archive_path, stage_dir=stage_dir, extract_dir=extract_dir, source_root=source_root: self._finish_source_download(
                    archive_path,
                    stage_dir,
                    extract_dir,
                    source_root,
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _begin_executable_download(self, row):
        if self.coordinator.download_in_progress:
            self.dispatcher.show_toast("Update Manager", f"A stable {self._stable_artifact_noun()} download is already in progress.", WARNING)
            return

        target_name = row.get("remote_exe_name") or self._stable_artifact_name_for_version(row.get("remote_version"))
        download_directory = self._resolve_download_directory()
        if is_windows_runtime() and getattr(sys, "frozen", False):
            prompt_text = (
                f"Download {target_name} in the background?\n\n"
                "The current EXE will stay in place for testing. When the download finishes, the new EXE will be launched and this version will close."
            )
        elif is_windows_runtime():
            prompt_text = (
                f"Download {target_name} into dist and launch it?\n\n"
                "This source session will hand off to the packaged EXE when the download finishes."
            )
        elif getattr(sys, "frozen", False):
            prompt_text = (
                f"Download {target_name} to {download_directory} and open it with the system package installer?\n\n"
                "The current app will stay open. Complete the package installation there, then restart the app."
            )
        else:
            prompt_text = (
                f"Download {target_name} to {download_directory} and open it with the system package installer?\n\n"
                "This source session will stay open while you complete the package installation."
            )
        if not messagebox.askyesno(
            "Download And Apply Update",
            prompt_text,
        ):
            return

        self.coordinator.download_in_progress = True
        self.status_var.set(f"Downloading {target_name} in the background...")
        self.coordinator.set_job_phase("downloading", f"Downloading {target_name} in the background.", mode="stable")
        self.dispatcher.set_update_status(f"Downloading {target_name} in the background...", INFO, active=True, mode="stable")

        def worker():
            try:
                remote_exe_bytes, resolved_name = self._download_remote_executable(row)
                os.makedirs(download_directory, exist_ok=True)
                final_exe_path = os.path.join(download_directory, resolved_name)
                temp_exe_path = f"{final_exe_path}.download"
                with open(temp_exe_path, "wb") as handle:
                    handle.write(remote_exe_bytes)
                os.replace(temp_exe_path, final_exe_path)
            except Exception as exc:
                self.dispatcher.root.after(0, lambda error=exc: self._handle_download_failure(error))
                return

            self.dispatcher.root.after(0, lambda path=final_exe_path: self._finish_downloaded_update(path))

        threading.Thread(target=worker, daemon=True).start()

    def start_advanced_dev_update(self):
        if not getattr(sys, "frozen", False):
            self.dispatcher.show_toast("Update Manager", "Advanced dev updates are only available from packaged builds.", INFO)
            return
        if not is_windows_runtime():
            self.dispatcher.show_toast("Update Manager", "Advanced dev updates currently support packaged Windows builds only. Use the stable package update path on Ubuntu.", INFO)
            self.coordinator.set_job_phase("idle", "Advanced dev updates are Windows-only; use the stable Ubuntu package update path on this runtime.", mode=None)
            self.dispatcher.set_update_status("Advanced dev updates are Windows-only on packaged builds right now.", WARNING, active=True, mode="advanced")
            return
        if not bool(self.dispatcher.get_setting("enable_advanced_dev_updates", False)):
            self.dispatcher.show_toast("Update Manager", "Enable Advanced Dev Updates in Settings before starting a packaged dev update.", WARNING)
            self.coordinator.set_job_phase("idle", "Advanced dev update channel is disabled.", mode=None)
            self.dispatcher.set_update_status("Advanced dev updates are disabled for this EXE.", WARNING, active=True, mode="advanced")
            return

        self.coordinator.set_source_phase(
            "source_armed",
            "Advanced dev update channel is enabled and starting the first background source snapshot download.",
        )
        self._begin_source_download_worker()

    def apply_updates(self):
        if not self.comparison_rows:
            self.check_for_updates()

        update_rows = [row for row in self.comparison_rows if row.get("update_available")]
        if not update_rows:
            self.dispatcher.show_toast("Update Manager", f"No stable {self._stable_artifact_noun(plural=True)} are available from Dispatcher Core.", INFO)
            return

        self._begin_executable_download(update_rows[0])

    def setup_ui(self):
        if self.view is not None:
            self.view.setup_ui()
            self.container = self.view.container

        self.handle_module_payload_selection_change()
        if not self._updates_configured():
            self.refresh_documentation_payload_summary(
                remote_state="Not configured",
                status="Unavailable",
                note=self._update_configuration_note(),
            )


def get_ui(parent, dispatcher):
    return UpdateManagerController(parent, dispatcher)