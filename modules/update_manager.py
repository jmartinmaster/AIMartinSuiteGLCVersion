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
import json
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from app_identity import LEGACY_EXE_NAME, format_versioned_exe_name, load_version_from_main, normalize_version, parse_version
from modules.persistence import write_json_with_backup, write_text_with_backup
from modules.utils import ensure_external_directory, external_path, local_or_resource_path, resolve_local_venv_python

__module_name__ = "Update Manager"
__version__ = "2.1.0"

GITHUB_REMOTE_PATTERN = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$")
MODULE_NAME_PATTERN = re.compile(r"__module_name__\s*=\s*[\"']([^\"']+)[\"']")
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
MASTER_VERSION_PATH = "main.py"
LEGACY_REMOTE_EXE_PATH = "dist/TheMartinSuite_GLC.exe"
MODULE_PAYLOAD_EXCLUDED_KEYS = {"__init__", "update_manager"}
JSON_PAYLOAD_OPTIONS = [
    {
        "key": "layout_config",
        "relative_path": "layout_config.json",
        "fallback_name": "Layout Config",
        "backup_dir": os.path.join("data", "backups", "layouts"),
    },
    {
        "key": "rates",
        "relative_path": "rates.json",
        "fallback_name": "Rates Config",
        "backup_dir": os.path.join("data", "backups", "rates"),
    },
]
DOCUMENTATION_PAYLOAD_RELATIVE_ROOT = os.path.join("docs", "help")
DOCUMENTATION_PAYLOAD_BACKUP_ROOT = os.path.join("data", "backups", "docs")
DOCUMENTATION_STANDALONE_FILES = ["LICENSE.txt"]


def _default_module_payload_name(module_key):
    return module_key.replace("_", " ").title()


def _parse_json_payload_metadata(file_text, fallback_name):
    normalized_text = (file_text or "").strip()
    if not normalized_text:
        return {
            "module_name": fallback_name,
            "version": "Missing",
            "compare_token": None,
        }
    try:
        payload = json.loads(normalized_text)
    except Exception:
        return {
            "module_name": fallback_name,
            "version": "Unreadable JSON",
            "compare_token": normalized_text,
        }
    return {
        "module_name": fallback_name,
        "version": "Valid JSON",
        "compare_token": json.dumps(payload, sort_keys=True),
        "payload": payload,
    }


def _default_documentation_payload_name(relative_path):
    if os.path.normpath(relative_path).lower() == "license.txt":
        return "Bundled License"

    stem = os.path.splitext(os.path.basename(relative_path))[0]
    return stem.replace("_", " ").title()


def _parse_text_payload_metadata(file_text, fallback_name):
    if file_text is None:
        return {
            "module_name": fallback_name,
            "version": "Missing",
            "compare_token": None,
        }

    normalized_text = file_text.replace("\r\n", "\n")
    return {
        "module_name": fallback_name,
        "version": "Present",
        "compare_token": normalized_text,
        "payload": file_text,
    }


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


def _read_text_payload_metadata_from_path(file_path, fallback_name):
    if not file_path or not os.path.exists(file_path):
        return _parse_text_payload_metadata(None, fallback_name)
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            return _parse_text_payload_metadata(handle.read(), fallback_name)
    except OSError:
        return {
            "module_name": fallback_name,
            "version": "Unreadable",
            "compare_token": None,
        }


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


def _detect_branch_name():
    return "main"


def _detect_remote_info():
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


def discover_module_payload_options(modules_path):
    options = []
    if modules_path and os.path.isdir(modules_path):
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
                "kind": "module",
                "key": module_key,
                "file_name": file_name,
                "relative_path": relative_path,
                "fallback_name": fallback_name,
                "module_name": module_name,
                "display": f"{module_name} ({file_name})",
            })

    for spec in JSON_PAYLOAD_OPTIONS:
        options.append({
            "kind": "json",
            "key": spec["key"],
            "relative_path": spec["relative_path"],
            "fallback_name": spec["fallback_name"],
            "module_name": spec["fallback_name"],
            "backup_dir": spec["backup_dir"],
            "display": f"{spec['fallback_name']} ({os.path.basename(spec['relative_path'])})",
        })

    return options


def discover_documentation_payload_options():
    options = []
    discovered_paths = []

    docs_root = local_or_resource_path(DOCUMENTATION_PAYLOAD_RELATIVE_ROOT)
    if os.path.isdir(docs_root):
        for file_name in sorted(os.listdir(docs_root)):
            if file_name.lower().endswith(".md"):
                discovered_paths.append(f"{DOCUMENTATION_PAYLOAD_RELATIVE_ROOT}/{file_name}".replace("\\", "/"))

    for relative_path in sorted(set(discovered_paths + DOCUMENTATION_STANDALONE_FILES)):
        fallback_name = _default_documentation_payload_name(relative_path)
        backup_subdir = "help" if relative_path.startswith("docs/help/") else "root"
        options.append({
            "kind": "documentation",
            "key": relative_path.replace("/", "_").replace(".", "_"),
            "relative_path": relative_path,
            "fallback_name": fallback_name,
            "module_name": fallback_name,
            "backup_dir": os.path.join(DOCUMENTATION_PAYLOAD_BACKUP_ROOT, backup_subdir),
        })

    return options


def get_local_module_payload_metadata(dispatcher, option):
    if not option:
        return {"module_name": "No payload selected", "version": "Unknown"}

    if option.get("kind") == "json":
        local_path = external_path(option["relative_path"])
        if not os.path.exists(local_path):
            return _parse_json_payload_metadata("", option["fallback_name"])
        try:
            with open(local_path, "r", encoding="utf-8") as handle:
                return _parse_json_payload_metadata(handle.read(), option["fallback_name"])
        except OSError:
            return {"module_name": option["module_name"], "version": "Unreadable JSON", "compare_token": None}

    override_path = dispatcher.get_external_module_override_path(option["key"])
    override_metadata = _read_module_metadata_from_path(override_path, option["fallback_name"])
    if override_metadata:
        return override_metadata

    local_module_path = os.path.join(dispatcher.modules_path, option["file_name"])
    local_metadata = _read_module_metadata_from_path(local_module_path, option["fallback_name"])
    if local_metadata:
        return local_metadata

    module = dispatcher.loaded_modules.get(option["key"]) or sys.modules.get(f"modules.{option['key']}")
    if module is not None:
        return {
            "module_name": getattr(module, "__module_name__", option["fallback_name"]),
            "version": getattr(module, "__version__", "Unknown"),
        }

    return {"module_name": option["module_name"], "version": "Unknown"}


def get_local_documentation_payload_metadata(option):
    if not option:
        return {"module_name": "Documentation", "version": "Unknown", "compare_token": None}

    local_path = external_path(option["relative_path"])
    if not os.path.exists(local_path):
        local_path = local_or_resource_path(option["relative_path"])

    metadata = _read_text_payload_metadata_from_path(local_path, option["fallback_name"])
    metadata["source_path"] = local_path
    return metadata


def fetch_remote_payload_text(remote_info, branch_name, relative_path, timeout=15):
    owner = remote_info.get("owner") if isinstance(remote_info, dict) else None
    repo = remote_info.get("repo") if isinstance(remote_info, dict) else None
    if not owner or not repo or not branch_name:
        raise RuntimeError("Repository origin or branch could not be determined.")

    url = _build_raw_github_url(owner, repo, branch_name, relative_path, cache_bust=int(time.time() * 1000))
    request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def evaluate_module_payload_option(dispatcher, option, branch_name, remote_info):
    local_metadata = get_local_module_payload_metadata(dispatcher, option)
    local_version = local_metadata.get("version", "Unknown")
    module_name = local_metadata.get("module_name", option.get("module_name", option.get("fallback_name", "Unknown")))

    try:
        remote_text = fetch_remote_payload_text(remote_info, branch_name, option["relative_path"])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {
                "option": option.copy(),
                "module_name": module_name,
                "local_metadata": local_metadata,
                "remote_version": "Missing",
                "status": "Not in repository branch",
                "note": f"The selected {module_name} payload does not exist on the repository branch.",
                "update_available": False,
                "remote_text": None,
            }
        return {
            "option": option.copy(),
            "module_name": module_name,
            "local_metadata": local_metadata,
            "remote_version": "Unavailable",
            "status": "Module check failed",
            "note": f"Could not read the remote {module_name} payload: {exc}",
            "update_available": False,
            "remote_text": None,
        }
    except Exception as exc:
        return {
            "option": option.copy(),
            "module_name": module_name,
            "local_metadata": local_metadata,
            "remote_version": "Unavailable",
            "status": "Module check failed",
            "note": f"Could not read the remote {module_name} payload: {exc}",
            "update_available": False,
            "remote_text": None,
        }

    current_option = option.copy()
    update_available = False
    if option.get("kind") == "json":
        remote_metadata = _parse_json_payload_metadata(remote_text, option["fallback_name"])
        remote_version = remote_metadata.get("version", "Unknown")
        local_token = local_metadata.get("compare_token")
        remote_token = remote_metadata.get("compare_token")
        if remote_version != "Valid JSON":
            status = "Repository JSON unreadable"
            note = f"The repository copy for {module_name} is not valid JSON and cannot be restored safely."
        elif local_version == "Missing":
            status = "JSON restore available"
            note = f"The local {module_name} file is missing and can be restored from the repository copy."
            update_available = True
        elif local_version == "Unreadable JSON":
            status = "JSON restore available"
            note = f"The local {module_name} file is unreadable and can be restored from the repository copy."
            update_available = True
        elif local_token == remote_token:
            status = "Up to date"
            note = f"The selected {module_name} JSON file already matches the repository copy."
        else:
            status = "JSON restore available"
            note = f"The local {module_name} JSON file differs from the repository copy and can be restored."
            update_available = True
    else:
        remote_metadata = _parse_module_metadata(remote_text, option["fallback_name"])
        remote_version = remote_metadata.get("version", "Unknown")
        module_name = remote_metadata.get("module_name", module_name)
        current_option["module_name"] = module_name
        local_compare = parse_version(local_version)
        remote_compare = parse_version(remote_version)

        if remote_compare and local_compare and normalize_version(remote_compare) > normalize_version(local_compare):
            status = "Module update available"
            note = f"A newer {module_name} payload is available and can be installed without rebuilding the EXE."
            update_available = True
        elif remote_version == local_version:
            status = "Up to date"
            note = f"The selected {module_name} payload already matches the repository version."
        else:
            status = "Module version unreadable"
            note = f"The selected {module_name} payload could not be compared cleanly."

    return {
        "option": current_option,
        "module_name": module_name,
        "local_metadata": local_metadata,
        "remote_version": remote_version,
        "status": status,
        "note": note,
        "update_available": update_available,
        "remote_text": remote_text,
    }


def evaluate_documentation_payload_option(option, branch_name, remote_info):
    local_metadata = get_local_documentation_payload_metadata(option)
    module_name = local_metadata.get("module_name", option.get("module_name", option.get("fallback_name", "Documentation")))

    try:
        remote_text = fetch_remote_payload_text(remote_info, branch_name, option["relative_path"])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {
                "option": option.copy(),
                "module_name": module_name,
                "local_metadata": local_metadata,
                "remote_version": "Missing",
                "status": "Not in repository branch",
                "note": f"The repository copy for {module_name} does not exist on the current branch.",
                "update_available": False,
                "remote_text": None,
            }
        return {
            "option": option.copy(),
            "module_name": module_name,
            "local_metadata": local_metadata,
            "remote_version": "Unavailable",
            "status": "Documentation check failed",
            "note": f"Could not read the remote {module_name} file: {exc}",
            "update_available": False,
            "remote_text": None,
        }
    except Exception as exc:
        return {
            "option": option.copy(),
            "module_name": module_name,
            "local_metadata": local_metadata,
            "remote_version": "Unavailable",
            "status": "Documentation check failed",
            "note": f"Could not read the remote {module_name} file: {exc}",
            "update_available": False,
            "remote_text": None,
        }

    remote_metadata = _parse_text_payload_metadata(remote_text, option["fallback_name"])
    local_version = local_metadata.get("version", "Unknown")
    local_token = local_metadata.get("compare_token")
    remote_token = remote_metadata.get("compare_token")

    if local_version == "Missing":
        status = "Documentation restore available"
        note = f"The local {module_name} file is missing and can be restored from the repository copy."
        update_available = True
    elif local_version == "Unreadable":
        status = "Documentation restore available"
        note = f"The local {module_name} file is unreadable and can be restored from the repository copy."
        update_available = True
    elif local_token == remote_token:
        status = "Up to date"
        note = f"The local {module_name} file already matches the repository copy."
        update_available = False
    else:
        status = "Documentation restore available"
        note = f"The local {module_name} file differs from the repository copy and can be restored."
        update_available = True

    return {
        "option": option.copy(),
        "module_name": module_name,
        "local_metadata": local_metadata,
        "remote_version": remote_metadata.get("version", "Unknown"),
        "status": status,
        "note": note,
        "update_available": update_available,
        "remote_text": remote_text,
    }


def scan_available_module_payload_updates(dispatcher, branch_name=None, remote_info=None):
    resolved_branch_name = branch_name or _detect_branch_name()
    resolved_remote_info = remote_info or _detect_remote_info()
    options = discover_module_payload_options(getattr(dispatcher, "modules_path", None))
    results = [
        evaluate_module_payload_option(dispatcher, option, resolved_branch_name, resolved_remote_info)
        for option in options
    ]
    return {
        "branch_name": resolved_branch_name,
        "remote_info": resolved_remote_info,
        "results": results,
        "available_results": [result for result in results if result.get("update_available")],
    }


def scan_available_documentation_payload_updates(branch_name=None, remote_info=None):
    resolved_branch_name = branch_name or _detect_branch_name()
    resolved_remote_info = remote_info or _detect_remote_info()
    options = discover_documentation_payload_options()
    results = [evaluate_documentation_payload_option(option, resolved_branch_name, resolved_remote_info) for option in options]
    return {
        "branch_name": resolved_branch_name,
        "remote_info": resolved_remote_info,
        "results": results,
        "available_results": [result for result in results if result.get("update_available")],
    }


class UpdateManager:
    def __init__(self, parent, dispatcher):
        self.parent = None
        self.dispatcher = dispatcher
        self.coordinator = self.dispatcher.update_coordinator
        self.branch_name = self.coordinator.branch_name or _detect_branch_name()
        self.remote_info = self.coordinator.remote_info if self.coordinator.remote_info.get("display") != "Unknown repository" else _detect_remote_info()
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
        self.module_payload_note_var = tb.StringVar(value="Select a payload to compare against the repository. Dispatcher Core (main.py) remains an EXE-only update boundary.")
        self.module_payload_in_progress = False
        self.documentation_payload_tracked_var = tb.StringVar(value=f"{len(self.documentation_payload_options)} tracked file(s)")
        self.documentation_payload_remote_state_var = tb.StringVar(value="Not checked")
        self.documentation_payload_status_var = tb.StringVar(value="Pending")
        self.documentation_payload_note_var = tb.StringVar(value="Documentation restores are grouped into one action so bundled help files can be refreshed without choosing individual documents.")
        self.documentation_payload_in_progress = False
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
        return get_local_module_payload_metadata(self.dispatcher, option)

    def _evaluate_selected_module_payload(self, option):
        return evaluate_module_payload_option(self.dispatcher, option, self.branch_name, self.remote_info)

    def handle_module_payload_selection_change(self, _event=None):
        option = self._get_selected_module_payload_option()
        if option is None:
            self.module_payload_name_var.set("No payload selected")
            self.module_payload_path_var.set("Payload updates are not available.")
            self.module_payload_local_version_var.set("Unknown")
            self.module_payload_remote_version_var.set("Not available")
            self.module_payload_status_var.set("Unavailable")
            self.module_payload_note_var.set("No payload-eligible items are available. Dispatcher Core (main.py) remains an EXE-only update boundary.")
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
                note="No payload-eligible items are available. Dispatcher Core (main.py) remains an EXE-only update boundary.",
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
            install_note = "Reload that part of the app to verify the change. The app will now prefer this external module file automatically whenever it exists beside the executable."
            toast_message = f"Installed the {option['module_name']} payload. It will be used automatically when that module is reloaded."
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
        target_path = external_path(option["relative_path"])
        write_text_with_backup(
            target_path,
            payload_text,
            backup_dir=external_path(option["backup_dir"]),
            keep_count=12,
        )
        return target_path, "Present"

    def _install_module_payload_option(self, option, remote_text=None):
        payload_text = remote_text if remote_text is not None else self._fetch_remote_file(option["relative_path"])
        if option.get("kind") == "json":
            remote_metadata = _parse_json_payload_metadata(payload_text, option["fallback_name"])
            if remote_metadata.get("version") != "Valid JSON":
                raise RuntimeError(f"The repository copy for {option['module_name']} is not valid JSON.")
            target_path = external_path(option["relative_path"])
            write_json_with_backup(
                target_path,
                remote_metadata["payload"],
                backup_dir=external_path(option["backup_dir"]),
                keep_count=12,
            )
            return target_path, remote_metadata.get("version", "Unknown")

        remote_metadata = _parse_module_metadata(payload_text, option["fallback_name"])
        option["module_name"] = remote_metadata.get("module_name", option["module_name"])
        installed_path, _module = self.dispatcher.install_module_override(option["key"], payload_text)
        return installed_path, remote_metadata.get("version", "Unknown")

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
        return _detect_remote_info()

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
            self.dispatcher.show_toast("Update Manager", f"Installed {installed_count} available payload(s).", SUCCESS)
            return

        self.status_var.set("No payload updates were available.")
        self.dispatcher.show_toast("Update Manager", "No payload updates were available to install.", INFO)

    def apply_all_module_payload_updates(self):
        if self._payload_job_is_busy():
            self.dispatcher.show_toast("Update Manager", "Another update job is already running in the background.", WARNING)
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
        python_candidates = []

        def add_candidate(command_prefix, display_name):
            if not command_prefix:
                return
            if any(existing_display == display_name for _existing_prefix, existing_display in python_candidates):
                return
            python_candidates.append((command_prefix, display_name))

        adjacent_venv_python = resolve_local_venv_python()
        add_candidate([adjacent_venv_python] if adjacent_venv_python else None, adjacent_venv_python)

        external_venv_python = resolve_local_venv_python(self._resolve_download_directory())
        if external_venv_python != adjacent_venv_python:
            add_candidate([external_venv_python] if external_venv_python else None, external_venv_python)

        configured_python = os.environ.get("MARTIN_BUILD_PYTHON", "").strip()
        if configured_python:
            add_candidate([configured_python], configured_python)

        python_on_path = shutil.which("python")
        if python_on_path:
            add_candidate([python_on_path], python_on_path)

        py_launcher = shutil.which("py")
        if py_launcher:
            add_candidate([py_launcher, "-3"], f"{py_launcher} -3")

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
            "No usable Python build runtime with PyInstaller was found. The app checks its local .venv first, then MARTIN_BUILD_PYTHON and system Python fallbacks."
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

        module_payload = tb.Labelframe(container, text=" Payload Restores ", padding=14)
        module_payload.pack(fill=X, pady=(12, 0))
        tb.Label(
            module_payload,
            text="Choose a single module or tracked config payload to compare and restore without rebuilding the EXE. Dispatcher Core (main.py) stays outside this list and continues to update through the stable EXE path above.",
            wraplength=720,
            justify=LEFT,
        ).pack(anchor=W)
        payload_grid = tb.Frame(module_payload)
        payload_grid.pack(fill=X, pady=(10, 0))
        tb.Label(payload_grid, text="Payload", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        module_payload_selector = tb.Combobox(
            payload_grid,
            textvariable=self.module_payload_selection_var,
            values=[option["display"] for option in self.module_payload_options],
            state="readonly" if self.module_payload_options else "disabled",
            width=42,
        )
        module_payload_selector.grid(row=0, column=1, sticky=W, pady=2)
        module_payload_selector.bind("<<ComboboxSelected>>", self.handle_module_payload_selection_change)
        tb.Label(payload_grid, text="Name", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_name_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Repository Path", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_path_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Local State", bootstyle=SECONDARY).grid(row=3, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_local_version_var).grid(row=3, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Repository State", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_remote_version_var).grid(row=4, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Status", bootstyle=SECONDARY).grid(row=5, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.module_payload_status_var).grid(row=5, column=1, sticky=W, pady=2)
        tb.Label(module_payload, textvariable=self.module_payload_note_var, bootstyle=INFO, wraplength=720, justify=LEFT).pack(anchor=W, pady=(10, 0))
        payload_controls = tb.Frame(module_payload)
        payload_controls.pack(anchor=W, pady=(10, 0))
        tb.Button(payload_controls, text="Check Selected Payload", bootstyle=PRIMARY, command=self.check_module_payload_update).pack(side=LEFT)
        tb.Button(payload_controls, text="Install Selected Payload", bootstyle=SUCCESS, command=self.apply_module_payload_update).pack(side=LEFT, padx=(8, 0))
        tb.Button(payload_controls, text="Install All Available Module/Config Payloads", bootstyle=WARNING, command=self.apply_all_module_payload_updates).pack(side=LEFT, padx=(8, 0))

        documentation_payload = tb.Labelframe(container, text=" Documentation Restores ", padding=14)
        documentation_payload.pack(fill=X, pady=(12, 0))
        tb.Label(
            documentation_payload,
            text="Restore the bundled Help Center documents as one grouped update. Individual documentation files are not selectable here.",
            wraplength=720,
            justify=LEFT,
        ).pack(anchor=W)
        documentation_grid = tb.Frame(documentation_payload)
        documentation_grid.pack(fill=X, pady=(10, 0))
        tb.Label(documentation_grid, text="Tracked Files", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(documentation_grid, textvariable=self.documentation_payload_tracked_var).grid(row=0, column=1, sticky=W, pady=2)
        tb.Label(documentation_grid, text="Repository State", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(documentation_grid, textvariable=self.documentation_payload_remote_state_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(documentation_grid, text="Status", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(documentation_grid, textvariable=self.documentation_payload_status_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(documentation_payload, textvariable=self.documentation_payload_note_var, bootstyle=INFO, wraplength=720, justify=LEFT).pack(anchor=W, pady=(10, 0))
        documentation_controls = tb.Frame(documentation_payload)
        documentation_controls.pack(anchor=W, pady=(10, 0))
        tb.Button(documentation_controls, text="Check Documentation Updates", bootstyle=PRIMARY, command=self.check_documentation_payload_updates).pack(side=LEFT)
        tb.Button(documentation_controls, text="Install Documentation Updates", bootstyle=SUCCESS, command=self.apply_documentation_payload_updates).pack(side=LEFT, padx=(8, 0))

        tb.Label(container, textvariable=self.status_var, bootstyle=SECONDARY).pack(anchor=W, pady=(12, 0))


def get_ui(parent, dispatcher):
    return UpdateManager(parent, dispatcher)