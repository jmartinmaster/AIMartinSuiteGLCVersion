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

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from app_identity import LEGACY_EXE_NAME, format_versioned_exe_name, load_version_from_main, normalize_version, parse_version
from modules.utils import ensure_external_directory

__module_name__ = "Update Manager"
__version__ = "1.0.0"

GITHUB_REMOTE_PATTERN = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$")
MODULE_NAME_PATTERN = re.compile(r"__module_name__\s*=\s*[\"']([^\"']+)[\"']")
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
MASTER_VERSION_PATH = "main.py"
LEGACY_REMOTE_EXE_PATH = "dist/TheMartinSuite_GLC.exe"
MODULE_PAYLOAD_EXCLUDED_KEYS = {"__init__", "update_manager"}


def _default_module_payload_name(module_key):
    return module_key.replace("_", " ").title()


def _parse_module_metadata(file_text, fallback_name):
    module_name_match = MODULE_NAME_PATTERN.search(file_text)
    version_match = VERSION_PATTERN.search(file_text)
    return {
        "module_name": module_name_match.group(1) if module_name_match else fallback_name,
        "version": version_match.group(1) if version_match else "Unknown",
    }


def _read_module_metadata_from_path(file_path, fallback_name):
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            return _parse_module_metadata(handle.read(), fallback_name)
    except OSError:
        return None


def _build_raw_github_url(owner, repo, branch_name, relative_path, cache_bust=None):
    base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_name}/{relative_path}"
    if cache_bust is None:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}cb={cache_bust}"


def _build_snapshot_github_url(owner, repo, branch_name):
    return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch_name}"


def _is_supported_update_version(version_parts):
    if version_parts is None:
        return False
    if len(version_parts) == 2:
        return True
    return len(version_parts) == 3 and version_parts[2] % 2 == 0


class UpdateManager:
    def __init__(self, parent, dispatcher):
        self.parent = None
        self.dispatcher = dispatcher
        self.coordinator = self.dispatcher.update_coordinator
        self.branch_name = self.coordinator.branch_name or self._detect_branch_name()
        self.remote_info = self.coordinator.remote_info if self.coordinator.remote_info.get("display") != "Unknown repository" else self._detect_remote_info()
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
        self.module_payload_options = self._discover_module_payload_options()
        default_option = next((option for option in self.module_payload_options if option["key"] == "about"), None)
        if default_option is None and self.module_payload_options:
            default_option = self.module_payload_options[0]
        self.module_payload_selection_var = tb.StringVar(value=default_option["display"] if default_option else "No module payloads available")
        self.module_payload_name_var = tb.StringVar(value=default_option["module_name"] if default_option else "No module selected")
        self.module_payload_path_var = tb.StringVar(value=default_option["relative_path"] if default_option else "Payload updates are not available.")
        self.module_payload_local_version_var = tb.StringVar(value="Unknown")
        self.module_payload_remote_version_var = tb.StringVar(value="Not checked")
        self.module_payload_status_var = tb.StringVar(value="Pending")
        self.module_payload_note_var = tb.StringVar(value="Select a module payload to compare against the repository. Dispatcher Core (main.py) remains an EXE-only update boundary.")
        self.module_payload_in_progress = False
        self.container = None
        self.coordinator.branch_name = self.branch_name
        self.coordinator.remote_info = self.remote_info
        self.branch_var.set(self.branch_name or "Unknown")
        self.repo_var.set(self.remote_info.get("display", "Unknown repository"))
        self.refresh_local_manifest()
        self.refresh_summary()
        self.refresh_module_payload_summary()
        self.mount(parent)

    def mount(self, parent):
        self.parent = parent
        self.setup_ui()

    def on_hide(self):
        return None

    def on_unload(self):
        return None

    def _discover_module_payload_options(self):
        options = []
        modules_path = getattr(self.dispatcher, "modules_path", None)
        if not modules_path or not os.path.isdir(modules_path):
            return options

        for file_name in sorted(os.listdir(modules_path)):
            if not file_name.endswith(".py"):
                continue
            module_key = os.path.splitext(file_name)[0]
            if module_key in MODULE_PAYLOAD_EXCLUDED_KEYS:
                continue

            relative_path = f"modules/{file_name}"
            fallback_name = _default_module_payload_name(module_key)
            metadata = _read_module_metadata_from_path(os.path.join(modules_path, file_name), fallback_name) or {
                "module_name": fallback_name,
                "version": "Unknown",
            }
            module_name = metadata.get("module_name", fallback_name)
            options.append({
                "key": module_key,
                "file_name": file_name,
                "relative_path": relative_path,
                "fallback_name": fallback_name,
                "module_name": module_name,
                "display": f"{module_name} ({file_name})",
            })

        return options

    def _get_selected_module_payload_option(self):
        selected_display = self.module_payload_selection_var.get().strip()
        for option in self.module_payload_options:
            if option["display"] == selected_display:
                return option
        return self.module_payload_options[0] if self.module_payload_options else None

    def _get_local_module_payload_metadata(self, option):
        if not option:
            return {"module_name": "No module selected", "version": "Unknown"}

        override_path = self.dispatcher.get_external_module_override_path(option["key"])
        override_metadata = _read_module_metadata_from_path(override_path, option["fallback_name"])
        if override_metadata:
            return override_metadata

        local_module_path = os.path.join(self.dispatcher.modules_path, option["file_name"])
        local_metadata = _read_module_metadata_from_path(local_module_path, option["fallback_name"])
        if local_metadata:
            return local_metadata

        module = self.dispatcher.loaded_modules.get(option["key"]) or sys.modules.get(f"modules.{option['key']}")
        if module is not None:
            return {
                "module_name": getattr(module, "__module_name__", option["fallback_name"]),
                "version": getattr(module, "__version__", "Unknown"),
            }

        return {"module_name": option["module_name"], "version": "Unknown"}

    def handle_module_payload_selection_change(self, _event=None):
        option = self._get_selected_module_payload_option()
        if option is None:
            self.module_payload_name_var.set("No module selected")
            self.module_payload_path_var.set("Payload updates are not available.")
            self.module_payload_local_version_var.set("Unknown")
            self.module_payload_remote_version_var.set("Not available")
            self.module_payload_status_var.set("Unavailable")
            self.module_payload_note_var.set("No payload-eligible modules are available. Dispatcher Core (main.py) remains an EXE-only update boundary.")
            return

        local_metadata = self._get_local_module_payload_metadata(option)
        option["module_name"] = local_metadata.get("module_name", option["module_name"])
        self.module_payload_name_var.set(option["module_name"])
        self.module_payload_path_var.set(option["relative_path"])
        self.refresh_module_payload_summary(
            remote_version="Not checked",
            status="Pending",
            note=f"Check the repository to compare the selected {option['module_name']} payload. Dispatcher Core (main.py) still updates through the EXE path above.",
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

        removed_items = []
        for path_value in [self.coordinator.source_build_log_path, self.coordinator.source_stage_dir]:
            if not path_value:
                continue
            try:
                if os.path.isdir(path_value):
                    shutil.rmtree(path_value, ignore_errors=False)
                elif os.path.exists(path_value):
                    os.remove(path_value)
                removed_items.append(path_value)
            except OSError:
                continue

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

    def check_module_payload_update(self):
        option = self._get_selected_module_payload_option()
        if option is None:
            self.refresh_module_payload_summary(
                remote_version="Not available",
                status="Unavailable",
                note="No payload-eligible modules are available. Dispatcher Core (main.py) remains an EXE-only update boundary.",
            )
            return

        local_version = self._get_local_module_payload_version()
        try:
            remote_text = self._fetch_remote_file(option["relative_path"])
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                self.refresh_module_payload_summary(
                    remote_version="Missing",
                    status="Not in repository branch",
                    note=f"The selected {option['module_name']} payload does not exist on the repository branch.",
                )
                return
            self.refresh_module_payload_summary(
                remote_version="Unavailable",
                status="Module check failed",
                note=f"Could not read the remote {option['module_name']} payload: {exc}",
            )
            return
        except Exception as exc:
            self.refresh_module_payload_summary(
                remote_version="Unavailable",
                status="Module check failed",
                note=f"Could not read the remote {option['module_name']} payload: {exc}",
            )
            return

        remote_metadata = _parse_module_metadata(remote_text, option["fallback_name"])
        remote_version = remote_metadata.get("version", "Unknown")
        option["module_name"] = remote_metadata.get("module_name", option["module_name"])
        local_compare = parse_version(local_version)
        remote_compare = parse_version(remote_version)

        if remote_compare and local_compare and normalize_version(remote_compare) > normalize_version(local_compare):
            status = "Module update available"
            note = f"A newer {option['module_name']} payload is available and can be installed without rebuilding the EXE."
        elif remote_version == local_version:
            status = "Up to date"
            note = f"The selected {option['module_name']} payload already matches the repository version."
        else:
            status = "Module version unreadable"
            note = f"The selected {option['module_name']} payload could not be compared cleanly."

        self.refresh_module_payload_summary(remote_version=remote_version, status=status, note=note)

    def _finish_module_payload_install(self, option, installed_path, remote_version):
        self.module_payload_in_progress = False
        installed_metadata = _read_module_metadata_from_path(installed_path, option["fallback_name"])
        if installed_metadata:
            self.module_payload_local_version_var.set(installed_metadata.get("version", "Unknown"))
            option["module_name"] = installed_metadata.get("module_name", option["module_name"])
        self.refresh_module_payload_summary(
            remote_version=remote_version,
            status="Installed",
            note=f"Installed the {option['module_name']} payload override at {installed_path}. Reload that part of the app to verify the change.",
            option=option,
        )
        self.status_var.set(f"{option['module_name']} payload installed.")
        self.dispatcher.set_update_status(f"Installed the {option['module_name']} module payload.", SUCCESS, active=True, mode="module")
        self.dispatcher.show_toast("Update Manager", f"Installed the {option['module_name']} payload override.", SUCCESS)

    def _handle_module_payload_failure(self, option, exc):
        self.module_payload_in_progress = False
        self.refresh_module_payload_summary(
            status="Install failed",
            note=f"Could not install the {option['module_name']} payload: {exc}",
            option=option,
        )
        self.dispatcher.set_update_status(f"{option['module_name']} payload install failed.", DANGER, active=True, mode="module")
        Messagebox.show_error(f"Could not install the {option['module_name']} payload:\n\n{exc}", "Module Payload Error")

    def apply_module_payload_update(self):
        if self.module_payload_in_progress or self.coordinator.download_in_progress or self.coordinator.source_job_in_progress:
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
                remote_text = self._fetch_remote_file(option["relative_path"])
                remote_metadata = _parse_module_metadata(remote_text, option["fallback_name"])
                installed_path, _module = self.dispatcher.install_module_override(option["key"], remote_text)
                remote_version = remote_metadata.get("version", "Unknown")
            except Exception as exc:
                self.dispatcher.root.after(0, lambda current_option=option.copy(), error=exc: self._handle_module_payload_failure(current_option, error))
                return

            self.dispatcher.root.after(0, lambda current_option=option.copy(), path=installed_path, version=remote_version: self._finish_module_payload_install(current_option, path, version))

        threading.Thread(target=worker, daemon=True).start()

    def _detect_branch_name(self):
        return "main"

    def _detect_remote_info(self):
        remote_url = None
        git_config_path = os.path.join(os.path.abspath("."), ".git", "config")
        if os.path.exists(git_config_path):
            try:
                with open(git_config_path, "r", encoding="utf-8") as handle:
                    config_text = handle.read()
                match = re.search(r"url\s*=\s*(.+)", config_text)
                if match:
                    remote_url = match.group(1).strip()
            except Exception:
                remote_url = None
        remote_url = remote_url or "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion.git"
        match = GITHUB_REMOTE_PATTERN.search(remote_url)
        if not match:
            return {"owner": None, "repo": None, "url": remote_url, "display": remote_url}
        owner = match.group("owner")
        repo = match.group("repo")
        return {
            "owner": owner,
            "repo": repo,
            "url": remote_url,
            "display": f"{owner}/{repo}",
        }

    def refresh_local_manifest(self):
        dispatcher_module = self.dispatcher.loaded_modules.get("main") or sys.modules.get("main") or sys.modules.get("__main__")
        self.local_manifest[:] = [{
            "relative_path": MASTER_VERSION_PATH,
            "module_name": getattr(dispatcher_module, "__module_name__", "Dispatcher Core"),
            "local_version": getattr(dispatcher_module, "__version__", "Unknown"),
        }]

    def refresh_summary(self):
        entry = self.local_manifest[0] if self.local_manifest else {
            "module_name": "Dispatcher Core",
            "local_version": "Unknown",
        }
        row = self.comparison_rows[0] if self.comparison_rows else None
        self.target_name_var.set(entry["module_name"])
        self.local_version_var.set(entry.get("local_version", "Unknown"))
        self.remote_version_var.set(row.get("remote_version", "Not checked") if row else "Not checked")
        self.result_var.set(row.get("status", "Pending") if row else "Pending")
        if row and row.get("update_available"):
            self.note_var.set("A newer stable executable target is available from the repository branch.")
        elif row:
            self.note_var.set("No newer stable executable target is available right now.")
        else:
            self.note_var.set("Run a repository check to compare the packaged release target.")

    def _fetch_remote_file(self, relative_path):
        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            raise RuntimeError("Repository origin or branch could not be determined.")

        url = _build_raw_github_url(owner, repo, self.branch_name, relative_path, cache_bust=int(time.time() * 1000))
        request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")

    def _fetch_remote_bytes(self, relative_path):
        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            raise RuntimeError("Repository origin or branch could not be determined.")

        url = _build_raw_github_url(owner, repo, self.branch_name, relative_path, cache_bust=int(time.time() * 1000))
        request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()

    def _fetch_remote_snapshot_bytes(self):
        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            raise RuntimeError("Repository origin or branch could not be determined.")

        url = _build_snapshot_github_url(owner, repo, self.branch_name)
        request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()

    def _remote_executable_candidates(self, row):
        versioned_name = row.get("remote_exe_name") or format_versioned_exe_name(row.get("remote_version"))
        candidates = []
        if versioned_name:
            candidates.append((f"dist/{versioned_name}", versioned_name))
        candidates.append((LEGACY_REMOTE_EXE_PATH, versioned_name or LEGACY_EXE_NAME))
        return candidates

    def _probe_remote_executable(self, row):
        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            raise RuntimeError("Repository origin or branch could not be determined.")

        last_not_found = None
        for remote_path, target_name in self._remote_executable_candidates(row):
            url = _build_raw_github_url(owner, repo, self.branch_name, remote_path)
            request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "MartinSuiteUpdater/1.0"})
            try:
                with urllib.request.urlopen(request, timeout=15):
                    return remote_path, target_name
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    last_not_found = exc
                    continue
                raise

        if last_not_found is not None:
            return None, None
        return None, None

    def check_for_updates(self):
        self.coordinator.set_job_phase("checking", "Checking the repository for newer executable targets.", mode="stable")
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

            remote_metadata = _parse_module_metadata(remote_text, entry["module_name"])
            remote_version = remote_metadata["version"]
            remote_compare = parse_version(remote_version)
            local_compare = parse_version(entry["local_version"])

            if remote_compare is None:
                status = "Remote version unreadable"
                update_available = False
            elif len(remote_compare) == 3 and remote_compare[2] % 2 != 0:
                status = "Remote odd patch ignored"
                update_available = False
            elif not _is_supported_update_version(remote_compare):
                status = "Remote version ignored"
                update_available = False
            elif local_compare is None:
                status = "Local version unreadable"
                update_available = False
            elif normalize_version(remote_compare) > normalize_version(local_compare):
                status = "EXE update available"
                update_available = True
            else:
                status = "Up to date"
                update_available = False

            comparison_rows.append({
                **entry,
                "module_name": remote_metadata["module_name"],
                "remote_version": remote_version,
                "remote_exe_name": format_versioned_exe_name(remote_version) if remote_compare else LEGACY_EXE_NAME,
                "status": status,
                "update_available": update_available,
            })

            current_row = comparison_rows[-1]
            if current_row["update_available"]:
                remote_path, resolved_name = self._probe_remote_executable(current_row)
                if remote_path:
                    current_row["remote_exe_path"] = remote_path
                    current_row["remote_exe_name"] = resolved_name
                else:
                    current_row["status"] = "EXE artifact missing"
                    current_row["update_available"] = False

        self.comparison_rows[:] = comparison_rows
        self.refresh_summary()
        available_count = sum(1 for row in comparison_rows if row["update_available"])
        self.status_var.set(f"Checked Dispatcher Core on branch '{self.branch_name}'. {available_count} executable update(s) available.")
        if available_count:
            self.coordinator.set_job_phase("ready", f"{available_count} stable executable update(s) are ready.", mode="stable")
        else:
            self.coordinator.set_job_phase("idle", "No stable executable updates are ready.", mode="stable")

    def _download_remote_executable(self, row):
        last_not_found = None
        for remote_path, target_name in self._remote_executable_candidates(row):
            try:
                return self._fetch_remote_bytes(remote_path), target_name
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    last_not_found = exc
                    continue
                raise

        if last_not_found is not None:
            raise last_not_found
        raise RuntimeError("No packaged executable artifact was found for the remote version.")

    def _finish_downloaded_update(self, downloaded_path):
        self.coordinator.download_in_progress = False
        try:
            os.startfile(downloaded_path)
        except Exception as exc:
            Messagebox.show_error(f"The updated executable was downloaded but could not be launched:\n\n{exc}", "Launch Error")
            self.status_var.set("Update downloaded, but launch failed.")
            self.coordinator.set_job_phase("failed", "Stable update downloaded, but launch failed.", mode="stable")
            self.dispatcher.set_update_status("Stable update downloaded, but launch failed.", DANGER, active=True, mode="stable")
            return

        self.status_var.set("Updated executable launched. Closing the current version.")
        self.coordinator.set_job_phase("handoff", f"Launched {os.path.basename(downloaded_path)} and closing the current version.", mode="stable")
        self.dispatcher.set_update_status("Stable update launched. Closing the current version.", SUCCESS, active=True, mode="stable")
        self.dispatcher.root.after(300, self.dispatcher.root.destroy)

    def _handle_download_failure(self, exc):
        self.coordinator.download_in_progress = False
        self.status_var.set("Executable update download failed.")
        self.coordinator.set_job_phase("failed", "Stable update download failed.", mode="stable")
        self.dispatcher.set_update_status("Stable update download failed.", DANGER, active=True, mode="stable")
        Messagebox.show_error(f"Could not download the updated executable:\n\n{exc}", "Update Error")

    def _resolve_download_directory(self):
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.abspath("dist")

    def _resolve_source_workspace(self):
        return ensure_external_directory(os.path.join("data", "updater", "source-staging"))

    def _resolve_source_log_directory(self):
        return ensure_external_directory(os.path.join("data", "updater", "logs"))

    def _cleanup_source_stage_dir(self, stage_dir):
        if stage_dir and os.path.isdir(stage_dir):
            shutil.rmtree(stage_dir, ignore_errors=True)

    def _locate_extracted_source_root(self, extract_dir):
        if not os.path.isdir(extract_dir):
            raise RuntimeError("The extracted source directory is missing.")

        child_directories = [
            os.path.join(extract_dir, entry)
            for entry in os.listdir(extract_dir)
            if os.path.isdir(os.path.join(extract_dir, entry))
        ]
        if len(child_directories) == 1:
            return child_directories[0]
        if os.path.isfile(os.path.join(extract_dir, "main.py")):
            return extract_dir
        raise RuntimeError("The downloaded source snapshot did not contain a single project root.")

    def _validate_source_snapshot(self, source_root):
        required_files = ["main.py", "build.py", os.path.join("modules", "update_manager.py")]
        missing = [relative_path for relative_path in required_files if not os.path.exists(os.path.join(source_root, relative_path))]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(f"The downloaded source snapshot is incomplete: {missing_text}")

    def _resolve_build_python_command(self):
        configured_python = os.environ.get("MARTIN_BUILD_PYTHON", "").strip()
        python_candidates = []
        if configured_python:
            python_candidates.append(([configured_python], configured_python))

        adjacent_venv_python = os.path.join(os.path.abspath("."), ".venv", "Scripts", "python.exe")
        if os.path.exists(adjacent_venv_python):
            python_candidates.append(([adjacent_venv_python], adjacent_venv_python))

        external_venv_python = os.path.join(self._resolve_download_directory(), ".venv", "Scripts", "python.exe")
        if os.path.exists(external_venv_python) and external_venv_python != adjacent_venv_python:
            python_candidates.append(([external_venv_python], external_venv_python))

        python_on_path = shutil.which("python")
        if python_on_path:
            python_candidates.append(([python_on_path], python_on_path))

        py_launcher = shutil.which("py")
        if py_launcher:
            python_candidates.append(([py_launcher, "-3"], f"{py_launcher} -3"))

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        for command_prefix, display_name in python_candidates:
            try:
                probe = subprocess.run(
                    command_prefix + ["-c", "import PyInstaller"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=creation_flags,
                )
            except Exception:
                continue
            if probe.returncode == 0:
                return command_prefix, display_name

        raise RuntimeError(
            "No usable Python build runtime with PyInstaller was found. Set MARTIN_BUILD_PYTHON or place a working .venv next to the app."
        )

    def _write_source_build_log(self, log_name, content):
        log_directory = self._resolve_source_log_directory()
        log_path = os.path.join(log_directory, log_name)
        with open(log_path, "w", encoding="utf-8", errors="replace") as handle:
            handle.write(content)
        return log_path

    def _resolve_built_executable(self, source_root):
        staged_version = load_version_from_main(os.path.join(source_root, "main.py"), default="0.0.0")
        expected_name = format_versioned_exe_name(staged_version)
        expected_path = os.path.join(source_root, "dist", expected_name)
        if os.path.exists(expected_path):
            return expected_path

        dist_dir = os.path.join(source_root, "dist")
        if not os.path.isdir(dist_dir):
            raise RuntimeError("The staged build completed without creating a dist directory.")

        exe_candidates = [
            os.path.join(dist_dir, file_name)
            for file_name in os.listdir(dist_dir)
            if file_name.lower().endswith(".exe")
        ]
        if len(exe_candidates) == 1:
            return exe_candidates[0]
        if not exe_candidates:
            raise RuntimeError("The staged build completed without producing an executable.")
        raise RuntimeError("The staged build produced multiple executables and the target could not be resolved.")

    def _resolve_final_built_executable_path(self, built_exe_path):
        target_directory = self._resolve_download_directory()
        target_path = os.path.join(target_directory, os.path.basename(built_exe_path))
        current_executable = os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else None
        if current_executable and os.path.normcase(os.path.abspath(target_path)) == os.path.normcase(current_executable):
            raise RuntimeError(
                "The rebuilt executable has the same name as the running EXE. Bump the version before using packaged source rebuild updates."
            )
        return target_path

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
            self.dispatcher.show_toast("Update Manager", "An executable download is already in progress.", WARNING)
            return

        target_name = row.get("remote_exe_name") or format_versioned_exe_name(row.get("remote_version"))
        if getattr(sys, "frozen", False):
            prompt_text = (
                f"Download {target_name} in the background?\n\n"
                "The current EXE will stay in place for testing. When the download finishes, the new EXE will be launched and this version will close."
            )
        else:
            prompt_text = (
                f"Download {target_name} into dist and launch it?\n\n"
                "This source session will hand off to the packaged EXE when the download finishes."
            )
        if not messagebox.askyesno(
            "Download And Launch Update",
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
                download_directory = self._resolve_download_directory()
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
            self.dispatcher.show_toast("Update Manager", "No executable updates are available from Dispatcher Core.", INFO)
            return

        self._begin_executable_download(update_rows[0])

    def setup_ui(self):
        if self.container is not None and self.container.winfo_exists():
            self.container.destroy()

        container = tb.Frame(self.parent, padding=20)
        container.pack(fill=BOTH, expand=True)
        self.container = container

        tb.Label(container, text="Update Manager", font=("Helvetica", 18, "bold")).pack(anchor=W, pady=(0, 10))
        tb.Label(
            container,
            text=(
                "Compare the local Dispatcher Core version with the repository branch release target. "
                "Odd third patch numbers stay in-progress and are ignored by the updater. "
                "Stable EXE updates require a published EXE artifact and can be launched from either source mode or the packaged build."
            ),
            wraplength=760,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 12))

        summary = tb.Labelframe(container, text=" Release Target ", padding=14)
        summary.pack(fill=X, pady=(0, 12))
        tb.Label(summary, textvariable=self.target_name_var, font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 8))
        tb.Label(summary, text="Repository", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.repo_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Branch", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.branch_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Local Version", bootstyle=SECONDARY).grid(row=3, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.local_version_var).grid(row=3, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Repository Version", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.remote_version_var).grid(row=4, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Status", bootstyle=SECONDARY).grid(row=5, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.result_var).grid(row=5, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Job Phase", bootstyle=SECONDARY).grid(row=6, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.job_phase_var).grid(row=6, column=1, sticky=W, pady=2)
        tb.Label(summary, textvariable=self.note_var, bootstyle=INFO, wraplength=720, justify=LEFT).grid(row=7, column=0, columnspan=2, sticky=W, pady=(10, 0))
        tb.Label(summary, textvariable=self.job_detail_var, bootstyle=SECONDARY, wraplength=720, justify=LEFT).grid(row=8, column=0, columnspan=2, sticky=W, pady=(8, 0))

        controls = tb.Frame(container)
        controls.pack(fill=X, pady=(12, 0))
        tb.Button(controls, text="Check Repository", bootstyle=PRIMARY, command=self.check_for_updates).pack(side=LEFT)
        tb.Button(controls, text="Apply Stable Updates", bootstyle=SUCCESS, command=self.apply_updates).pack(side=LEFT, padx=8)

        module_payload = tb.Labelframe(container, text=" Module Payloads ", padding=14)
        module_payload.pack(fill=X, pady=(12, 0))
        tb.Label(
            module_payload,
            text="Choose a single module payload to compare and install without rebuilding the EXE. Dispatcher Core (main.py) stays outside this list and continues to update through the stable EXE path above.",
            wraplength=720,
            justify=LEFT,
        ).pack(anchor=W)
        payload_grid = tb.Frame(module_payload)
        payload_grid.pack(fill=X, pady=(10, 0))
        tb.Label(payload_grid, text="Module", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        module_payload_selector = tb.Combobox(
            payload_grid,
            textvariable=self.module_payload_selection_var,
            values=[option["display"] for option in self.module_payload_options],
            state="readonly" if self.module_payload_options else "disabled",
            width=42,
        )
        module_payload_selector.grid(row=0, column=1, sticky=W, pady=2)
        module_payload_selector.bind("<<ComboboxSelected>>", self.handle_module_payload_selection_change)
        tb.Label(payload_grid, text="Module Name", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_name_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Repository Path", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_path_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Local Version", bootstyle=SECONDARY).grid(row=3, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_local_version_var).grid(row=3, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Repository Version", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_remote_version_var).grid(row=4, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Status", bootstyle=SECONDARY).grid(row=5, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_status_var).grid(row=5, column=1, sticky=W, pady=2)
        tb.Label(module_payload, textvariable=self.module_payload_note_var, bootstyle=INFO, wraplength=720, justify=LEFT).pack(anchor=W, pady=(10, 0))
        payload_controls = tb.Frame(module_payload)
        payload_controls.pack(anchor=W, pady=(10, 0))
        tb.Button(payload_controls, text="Check Selected Module", bootstyle=PRIMARY, command=self.check_module_payload_update).pack(side=LEFT)
        tb.Button(payload_controls, text="Install Selected Module", bootstyle=SUCCESS, command=self.apply_module_payload_update).pack(side=LEFT, padx=(8, 0))

        tb.Label(container, textvariable=self.status_var, bootstyle=SECONDARY).pack(anchor=W, pady=(12, 0))


def get_ui(parent, dispatcher):
    return UpdateManager(parent, dispatcher)