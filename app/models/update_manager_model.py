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
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

from app.app_identity import DEFAULT_UPDATE_REPOSITORY_URL, DEB_PACKAGE_NAME, LEGACY_EXE_NAME, format_versioned_deb_name, format_versioned_exe_name, load_version_from_main, normalize_version, parse_version
from app.app_platform import is_ubuntu_runtime
from app.persistence import write_json_with_backup, write_text_with_backup
from app.utils import ensure_external_directory, external_path, local_or_resource_path, resolve_local_venv_python


GITHUB_REMOTE_PATTERN = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$")
MODULE_NAME_PATTERN = re.compile(r"__module_name__\s*=\s*[\"']([^\"']+)[\"']")
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
MASTER_VERSION_PATH = "main.py"
LEGACY_REMOTE_EXE_PATH = "dist/TheMartinSuite_GLC.exe"
LEGACY_REMOTE_DEB_PATH = f"dist/ubuntu/{DEB_PACKAGE_NAME}.deb"
MODULE_PAYLOAD_EXCLUDED_KEYS = {"__init__", "update_manager"}
SETTINGS_RELATIVE_PATH = "settings.json"
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
DOCUMENTATION_STANDALONE_FILES = ["docs/legal/LICENSE.txt"]


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
    if os.path.basename(os.path.normpath(relative_path)).lower() == "license.txt":
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


def _normalize_update_repository_url(raw_value):
    return str(raw_value or "").strip()


def _load_external_settings_payload(settings_path=None):
    resolved_settings_path = settings_path or external_path(SETTINGS_RELATIVE_PATH)
    if not os.path.exists(resolved_settings_path):
        return {}
    try:
        with open(resolved_settings_path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _get_configured_update_repository_url(settings_lookup=None):
    configured_value = None
    if callable(settings_lookup):
        try:
            configured_value = settings_lookup("update_repository_url", None)
        except TypeError:
            try:
                configured_value = settings_lookup("update_repository_url")
            except Exception:
                configured_value = None
        except Exception:
            configured_value = None
    if configured_value is not None:
        return _normalize_update_repository_url(configured_value)

    settings_payload = _load_external_settings_payload()
    return _normalize_update_repository_url(settings_payload.get("update_repository_url", DEFAULT_UPDATE_REPOSITORY_URL))


def _build_remote_info_from_url(remote_url):
    normalized_url = _normalize_update_repository_url(remote_url)
    if not normalized_url:
        return {"owner": None, "repo": None, "url": "", "display": "Updates not configured"}

    match = GITHUB_REMOTE_PATTERN.search(normalized_url)
    if not match:
        return {"owner": None, "repo": None, "url": normalized_url, "display": "Unsupported update URL"}

    owner = match.group("owner")
    repo = match.group("repo")
    return {
        "owner": owner,
        "repo": repo,
        "url": normalized_url,
        "display": f"{owner}/{repo}",
    }


def _remote_updates_available(remote_info, branch_name=None):
    if not isinstance(remote_info, dict):
        return False
    return bool(remote_info.get("owner") and remote_info.get("repo") and (branch_name or "").strip())


def _update_configuration_note(remote_info=None):
    normalized_remote_info = remote_info if isinstance(remote_info, dict) else {}
    if normalized_remote_info.get("display") == "Unsupported update URL":
        return "The configured Update Repository URL is not a supported GitHub repository address. Open Security Admin with a developer login and enter a standard GitHub repository URL to enable updates."
    return "No Update Repository URL is configured yet. Open Security Admin and sign in with the developer vault to enable update checks and payload restores."


def _is_supported_update_version(version_parts):
    if version_parts is None:
        return False
    if len(version_parts) == 2:
        return True
    return len(version_parts) == 3 and version_parts[2] % 2 == 0


def _detect_branch_name():
    return "main"


def _detect_remote_info(preferred_url=None):
    remote_url = _normalize_update_repository_url(preferred_url)
    git_config_path = os.path.join(os.path.abspath("."), ".git", "config")
    if not remote_url and os.path.exists(git_config_path):
        try:
            with open(git_config_path, "r", encoding="utf-8") as handle:
                config_text = handle.read()
            match = re.search(r"url\s*=\s*(.+)", config_text)
            if match:
                remote_url = match.group(1).strip()
        except Exception:
            remote_url = ""
    remote_url = remote_url or DEFAULT_UPDATE_REPOSITORY_URL
    return _build_remote_info_from_url(remote_url)


def discover_module_payload_options(modules_path):
    options = []
    if modules_path and os.path.isdir(modules_path):
        for file_name in sorted(os.listdir(modules_path)):
            if not file_name.endswith(".py"):
                continue
            module_key = os.path.splitext(file_name)[0]
            if module_key in MODULE_PAYLOAD_EXCLUDED_KEYS:
                continue

            relative_path = f"app/{file_name}"
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


def get_local_module_payload_metadata(modules_path, loaded_modules, option, external_override_path=None):
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

    override_metadata = _read_module_metadata_from_path(external_override_path, option["fallback_name"])
    if override_metadata:
        return override_metadata

    local_module_path = os.path.join(modules_path or "", option.get("file_name", ""))
    local_metadata = _read_module_metadata_from_path(local_module_path, option["fallback_name"])
    if local_metadata:
        return local_metadata

    resolved_loaded_modules = loaded_modules or {}
    module = resolved_loaded_modules.get(option["key"]) or sys.modules.get(f"app.{option['key']}")
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


def evaluate_module_payload_option(modules_path, loaded_modules, option, branch_name, remote_info, external_override_path=None):
    local_metadata = get_local_module_payload_metadata(modules_path, loaded_modules, option, external_override_path=external_override_path)
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
    configured_url = None
    loaded_modules = None
    modules_path = None
    external_override_path_resolver = None

    if dispatcher is not None:
        modules_path = getattr(dispatcher, "modules_path", None)
        loaded_modules = getattr(dispatcher, "loaded_modules", None)
        if getattr(dispatcher, "are_external_module_overrides_enabled", None) and dispatcher.are_external_module_overrides_enabled():
            external_override_path_resolver = getattr(dispatcher, "get_external_module_override_path", None)
        if hasattr(dispatcher, "get_setting"):
            configured_url = _get_configured_update_repository_url(dispatcher.get_setting)

    resolved_branch_name = branch_name or _detect_branch_name()
    resolved_remote_info = remote_info or _detect_remote_info(preferred_url=configured_url)
    options = discover_module_payload_options(modules_path)
    if not _remote_updates_available(resolved_remote_info, resolved_branch_name):
        return {
            "branch_name": resolved_branch_name,
            "remote_info": resolved_remote_info,
            "results": [],
            "available_results": [],
            "configured": False,
            "note": _update_configuration_note(resolved_remote_info),
        }

    results = []
    for option in options:
        override_path = None
        if callable(external_override_path_resolver) and option.get("kind") == "module":
            try:
                override_path = external_override_path_resolver(option["key"])
            except Exception:
                override_path = None
        results.append(
            evaluate_module_payload_option(
                modules_path,
                loaded_modules,
                option,
                resolved_branch_name,
                resolved_remote_info,
                external_override_path=override_path,
            )
        )
    return {
        "branch_name": resolved_branch_name,
        "remote_info": resolved_remote_info,
        "results": results,
        "available_results": [result for result in results if result.get("update_available")],
    }


def scan_available_documentation_payload_updates(branch_name=None, remote_info=None, configured_url=None):
    resolved_branch_name = branch_name or _detect_branch_name()
    resolved_remote_info = remote_info or _detect_remote_info(preferred_url=configured_url)
    options = discover_documentation_payload_options()
    if not _remote_updates_available(resolved_remote_info, resolved_branch_name):
        return {
            "branch_name": resolved_branch_name,
            "remote_info": resolved_remote_info,
            "results": [],
            "available_results": [],
            "configured": False,
            "note": _update_configuration_note(resolved_remote_info),
        }
    results = [evaluate_documentation_payload_option(option, resolved_branch_name, resolved_remote_info) for option in options]
    return {
        "branch_name": resolved_branch_name,
        "remote_info": resolved_remote_info,
        "results": results,
        "available_results": [result for result in results if result.get("update_available")],
    }


def install_documentation_payload_option(option, payload_text):
    target_path = external_path(option["relative_path"])
    write_text_with_backup(
        target_path,
        payload_text,
        backup_dir=external_path(option["backup_dir"]),
        keep_count=12,
    )
    return target_path, "Present"


def install_module_payload_option(option, payload_text, install_module_override):
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
    installed_result = install_module_override(option["key"], payload_text)
    installed_path = installed_result[0] if isinstance(installed_result, tuple) else installed_result
    return installed_path, remote_metadata.get("version", "Unknown")


def build_local_manifest(dispatcher_module):
    return [{
        "relative_path": MASTER_VERSION_PATH,
        "module_name": getattr(dispatcher_module, "__module_name__", "Dispatcher Core"),
        "local_version": getattr(dispatcher_module, "__version__", "Unknown"),
    }]


def evaluate_stable_update_entry(entry, remote_text, stable_artifact_status_label, stable_artifact_name_for_version):
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
        status = f"{stable_artifact_status_label} update available"
        update_available = True
    else:
        status = "Up to date"
        update_available = False

    return {
        **entry,
        "module_name": remote_metadata["module_name"],
        "remote_version": remote_version,
        "remote_exe_name": stable_artifact_name_for_version(remote_version) if remote_compare else None,
        "status": status,
        "update_available": update_available,
    }


def fetch_remote_bytes(remote_info, branch_name, relative_path, timeout=30):
    owner = remote_info.get("owner") if isinstance(remote_info, dict) else None
    repo = remote_info.get("repo") if isinstance(remote_info, dict) else None
    if not owner or not repo or not branch_name:
        raise RuntimeError("Repository origin or branch could not be determined.")

    url = _build_raw_github_url(owner, repo, branch_name, relative_path, cache_bust=int(time.time() * 1000))
    request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_remote_snapshot_bytes(remote_info, branch_name):
    owner = remote_info.get("owner") if isinstance(remote_info, dict) else None
    repo = remote_info.get("repo") if isinstance(remote_info, dict) else None
    if not owner or not repo or not branch_name:
        raise RuntimeError("Repository origin or branch could not be determined.")

    url = _build_snapshot_github_url(owner, repo, branch_name)
    request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def remote_executable_candidates(row, stable_artifact_kind, stable_artifact_name_for_version):
    versioned_name = row.get("remote_exe_name") or stable_artifact_name_for_version(row.get("remote_version"))
    candidates = []
    if stable_artifact_kind == "deb":
        if versioned_name:
            candidates.append((f"dist/ubuntu/{versioned_name}", versioned_name))
        candidates.append((LEGACY_REMOTE_DEB_PATH, versioned_name or os.path.basename(LEGACY_REMOTE_DEB_PATH)))
        return candidates

    if versioned_name:
        candidates.append((f"dist/{versioned_name}", versioned_name))
    candidates.append((LEGACY_REMOTE_EXE_PATH, versioned_name or LEGACY_EXE_NAME))
    return candidates


def probe_remote_executable(remote_info, branch_name, row, stable_artifact_kind, stable_artifact_name_for_version):
    owner = remote_info.get("owner") if isinstance(remote_info, dict) else None
    repo = remote_info.get("repo") if isinstance(remote_info, dict) else None
    if not owner or not repo or not branch_name:
        raise RuntimeError("Repository origin or branch could not be determined.")

    last_not_found = None
    for remote_path, target_name in remote_executable_candidates(row, stable_artifact_kind, stable_artifact_name_for_version):
        url = _build_raw_github_url(owner, repo, branch_name, remote_path)
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


def download_remote_executable(remote_info, branch_name, row, stable_artifact_kind, stable_artifact_name_for_version):
    last_not_found = None
    for remote_path, target_name in remote_executable_candidates(row, stable_artifact_kind, stable_artifact_name_for_version):
        try:
            return fetch_remote_bytes(remote_info, branch_name, remote_path), target_name
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                last_not_found = exc
                continue
            raise

    if last_not_found is not None:
        raise last_not_found
    raise RuntimeError("No packaged artifact was found for the remote version.")


def resolve_download_directory():
    if is_ubuntu_runtime():
        if getattr(sys, "frozen", False):
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            return downloads_dir
        return os.path.abspath(os.path.join("dist", "ubuntu"))
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.abspath("dist")


def resolve_source_workspace():
    return ensure_external_directory(os.path.join("data", "updater", "source-staging"))


def resolve_source_log_directory():
    return ensure_external_directory(os.path.join("data", "updater", "logs"))


def cleanup_source_stage_dir(stage_dir):
    if stage_dir and os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir, ignore_errors=True)


def remove_paths(path_values):
    removed_items = []
    for path_value in path_values or []:
        if not path_value:
            continue
        try:
            if os.path.isdir(path_value):
                shutil.rmtree(path_value, ignore_errors=False)
            elif os.path.exists(path_value):
                os.remove(path_value)
            else:
                continue
            removed_items.append(path_value)
        except OSError:
            continue
    return removed_items


def locate_extracted_source_root(extract_dir):
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


def validate_source_snapshot(source_root):
    required_files = ["main.py", "build.py", os.path.join("app", "controllers", "update_manager_controller.py")]
    missing = [relative_path for relative_path in required_files if not os.path.exists(os.path.join(source_root, relative_path))]
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(f"The downloaded source snapshot is incomplete: {missing_text}")


def resolve_build_python_command(download_directory=None):
    python_candidates = []

    def add_candidate(command_prefix, display_name):
        if not command_prefix:
            return
        if any(existing_display == display_name for _existing_prefix, existing_display in python_candidates):
            return
        python_candidates.append((command_prefix, display_name))

    adjacent_venv_python = resolve_local_venv_python()
    add_candidate([adjacent_venv_python] if adjacent_venv_python else None, adjacent_venv_python)

    external_venv_python = resolve_local_venv_python(download_directory or resolve_download_directory())
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


def write_source_build_log(log_name, content):
    log_directory = resolve_source_log_directory()
    log_path = os.path.join(log_directory, log_name)
    with open(log_path, "w", encoding="utf-8", errors="replace") as handle:
        handle.write(content)
    return log_path


def resolve_built_executable(source_root):
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


def resolve_final_built_executable_path(built_exe_path, download_directory=None, current_executable=None):
    target_directory = download_directory or resolve_download_directory()
    target_path = os.path.join(target_directory, os.path.basename(built_exe_path))
    normalized_current = os.path.abspath(current_executable) if current_executable else None
    if normalized_current and os.path.normcase(os.path.abspath(target_path)) == os.path.normcase(normalized_current):
        raise RuntimeError(
            "The rebuilt executable has the same name as the running EXE. Bump the version before using packaged source rebuild updates."
        )
    return target_path