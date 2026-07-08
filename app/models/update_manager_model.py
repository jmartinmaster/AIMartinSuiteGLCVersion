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
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from app.app_identity import DEFAULT_DEV_UPDATE_BRANCH, DEFAULT_STABLE_UPDATE_BRANCH, DEFAULT_UPDATE_REPOSITORY_URL, DEB_PACKAGE_NAME, LEGACY_EXE_NAME, format_versioned_deb_name, format_versioned_exe_name, load_version_from_main, normalize_version, parse_version
from app.app_platform import is_ubuntu_runtime, open_with_system_default
from app.external_data_registry import ExternalDataRegistry
from app.form_definition_registry import DEFAULT_FORM_ID, DEFAULT_FORM_NAME, FormDefinitionRegistry
from app.persistence import write_json_with_backup, write_text_with_backup
from app.update_integrity import compute_integrity_hashes, compute_sha256_hex, verify_expected_hash
from app.utils import ensure_external_directory, external_path, local_or_resource_path, resolve_local_venv_python

__module_name__ = "Update Manager"
__version__ = "2.5.1"


GITHUB_REMOTE_PATTERN = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$")
MODULE_NAME_PATTERN = re.compile(r"__module_name__\s*=\s*[\"']([^\"']+)[\"']")
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
MASTER_VERSION_PATH = "launcher.py"
LEGACY_REMOTE_EXE_PATH = "dist/TheMartinSuite_GLC.exe"
LEGACY_REMOTE_DEB_PATH = f"dist/ubuntu/{DEB_PACKAGE_NAME}.deb"
MODULE_PAYLOAD_EXCLUDED_KEYS = {"__init__", "update_manager"}
DOCUMENTATION_PAYLOAD_RELATIVE_ROOT = os.path.join("docs", "help")
DOCUMENTATION_PAYLOAD_BACKUP_ROOT = os.path.join("data", "backups", "docs")
DOCUMENTATION_STANDALONE_FILES = [
    "docs/legal/LICENSE.txt",
    "docs/production_log_json_architecture.md",
]
MODULE_PAYLOAD_MVC_PATH_SPECS = [
    ("controllers", "{module_key}_qt_controller.py"),
    ("models", "{module_key}_model.py"),
    ("views", "{module_key}_qt_view.py"),
]
UBUNTU_PACKAGE_VERSION_PATTERN = re.compile(r"(?P<version>\d+\.\d+(?:\.\d+)?)")


def _default_module_payload_name(module_key):
    return module_key.replace("_", " ").title()


def _get_external_data_registry(data_registry=None):
    return data_registry or ExternalDataRegistry()


def discover_json_payload_options(data_registry=None):
    registry = _get_external_data_registry(data_registry)
    return [registry.build_update_payload_option(spec.key) for spec in registry.get_update_payload_specs()]


def _build_module_payload_paths(modules_path, module_key, file_name):
    payload_paths = [f"app/{file_name}"]
    for subdirectory, file_template in MODULE_PAYLOAD_MVC_PATH_SPECS:
        related_file_name = file_template.format(module_key=module_key)
        related_absolute_path = os.path.join(modules_path, subdirectory, related_file_name)
        relative_payload_path = f"app/{subdirectory}/{related_file_name}"
        if os.path.isfile(related_absolute_path) and relative_payload_path not in payload_paths:
            payload_paths.append(relative_payload_path)
    return payload_paths


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
        "compare_token": file_text.replace("\r\n", "\n") if file_text else None,
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
    if branch_name is None or relative_path is None:
        raise ValueError("branch_name and relative_path must not be None.")

    # Accept string-like inputs such as Path objects while normalizing
    # separators before percent-encoding the GitHub URL path segments.
    branch_str = str(branch_name)
    path_str = str(relative_path)
    normalized_branch = branch_str.replace("\\", "/").strip("/")
    normalized_path = path_str.replace("\\", "/").lstrip("/")
    quoted_branch = urllib.parse.quote(normalized_branch, safe="/")
    quoted_path = urllib.parse.quote(normalized_path, safe="/")
    base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{quoted_branch}/{quoted_path}"
    if cache_bust is None:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}cb={cache_bust}"


def _build_snapshot_github_url(owner, repo, branch_name):
    return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch_name}"


def _verify_payload_hash(expected_hash, payload_bytes, relative_path):
    # Build-time hash generation and runtime verification must stay aligned.
    # Use the shared helper so manifest/.sha256 changes cannot silently drift.
    return verify_expected_hash(expected_hash, payload_bytes, relative_path)


def _parse_sha256_text(payload_text, relative_path):
    raw_text = str(payload_text or "").strip()
    if not raw_text:
        raise RuntimeError(f"Repository checksum file is empty for {relative_path}.sha256.")
    first_line = raw_text.splitlines()[0].strip()
    if not first_line:
        raise RuntimeError(f"Repository checksum file is empty for {relative_path}.sha256.")
    candidate_hash = first_line.split()[0].strip().lower()
    if len(candidate_hash) != 64 or any(character not in "0123456789abcdef" for character in candidate_hash):
        raise RuntimeError(f"Repository checksum file is invalid for {relative_path}.sha256.")
    return candidate_hash


def _fetch_remote_sha256_hex(remote_info, branch_name, relative_path, timeout=15):
    checksum_path = f"{relative_path}.sha256"
    try:
        payload_text = fetch_remote_payload_text(remote_info, branch_name, checksum_path, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                f"Missing repository checksum: {checksum_path}. "
                "Create the .sha256 file in the selected update repository before distributing this artifact."
            ) from exc
        raise
    return _parse_sha256_text(payload_text, relative_path)


def _verify_remote_payload_integrity(remote_info, branch_name, relative_path, payload_bytes, timeout=15):
    expected_hash = _fetch_remote_sha256_hex(
        remote_info,
        branch_name,
        relative_path,
        timeout=timeout,
    )
    return _verify_payload_hash(expected_hash, payload_bytes, relative_path)


def _resolve_checksum_governance(remote_info, branch_name, relative_path, payload_bytes, timeout=15):
    checksum_path = f"{relative_path}.sha256"
    try:
        expected_hash = _fetch_remote_sha256_hex(remote_info, branch_name, relative_path, timeout=timeout)
    except RuntimeError as exc:
        message = str(exc)
        if "Missing repository checksum" in message:
            return (
                "Missing checksum file",
                f"Missing {checksum_path}. Create this checksum file in the update repository so installs can proceed.",
            )
        if "invalid" in message.lower():
            return (
                "Invalid checksum file",
                f"{checksum_path} is malformed. Regenerate the checksum file using SHA-256 and commit it.",
            )
        return ("Checksum unavailable", message)
    except Exception as exc:
        return ("Checksum unavailable", f"Could not read {checksum_path}: {exc}")

    expected_hash = str(expected_hash or "").strip().lower()
    actual_hash = compute_sha256_hex(payload_bytes)
    if expected_hash not in compute_integrity_hashes(payload_bytes, relative_path):
        return (
            "Checksum mismatch",
            (
                f"Checksum mismatch for {relative_path}. Expected {expected_hash}, got {actual_hash}. "
                "Do not install this artifact until repository checksums are corrected."
            ),
        )
    return ("Checksum verified", f"Repository checksum verified for {relative_path}.")


def _safe_extract_zip(archive_handle, extract_dir):
    extract_root = os.path.abspath(extract_dir)
    for member in archive_handle.infolist():
        member_name = str(member.filename or "")
        normalized_member_name = member_name.replace("\\", "/")
        if not normalized_member_name:
            continue
        if normalized_member_name.startswith("/") or normalized_member_name.startswith("../"):
            raise RuntimeError(f"Unsafe archive member path detected: {member_name}")
        destination_path = os.path.abspath(os.path.join(extract_root, normalized_member_name))
        try:
            if os.path.commonpath([destination_path, extract_root]) != extract_root:
                raise RuntimeError(f"Unsafe archive member path detected: {member_name}")
        except ValueError as exc:
            raise RuntimeError(f"Unsafe archive member path detected: {member_name}") from exc
        unix_mode = (member.external_attr >> 16) & 0o170000
        if unix_mode == 0o120000:
            raise RuntimeError(f"Symlink entries are not allowed in update archives: {member_name}")
        archive_handle.extract(member, extract_root)


def _normalize_update_repository_url(raw_value):
    val = str(raw_value or "").strip()
    return val.strip("'\"")


def _load_external_settings_payload(settings_path=None, data_registry=None):
    if settings_path is None:
        return _get_external_data_registry(data_registry).load_json("settings", default_factory=dict)

    resolved_settings_path = settings_path
    if not os.path.exists(resolved_settings_path):
        return {}
    try:
        with open(resolved_settings_path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _get_configured_update_repository_url(settings_lookup=None, data_registry=None):
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

    settings_payload = _load_external_settings_payload(data_registry=data_registry)
    return _normalize_update_repository_url(settings_payload.get("update_repository_url", DEFAULT_UPDATE_REPOSITORY_URL))


def _resolve_release_channel(settings_lookup=None, data_registry=None):
    configured_value = None
    if callable(settings_lookup):
        try:
            configured_value = settings_lookup("release_channel", None)
        except TypeError:
            try:
                configured_value = settings_lookup("release_channel")
            except Exception:
                configured_value = None
        except Exception:
            configured_value = None
    if configured_value is None:
        settings_payload = _load_external_settings_payload(data_registry=data_registry)
        configured_value = settings_payload.get("release_channel", "stable")
    normalized_channel = str(configured_value or "stable").strip().lower()
    return normalized_channel if normalized_channel in {"stable", "dev"} else "stable"


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


def _is_supported_update_version(version_parts, allow_odd_patch=False):
    if version_parts is None:
        return False
    if len(version_parts) == 2:
        return True
    if len(version_parts) != 3:
        return False
    if allow_odd_patch:
        return True
    return version_parts[2] % 2 == 0


def _detect_branch_name(settings_lookup=None, data_registry=None):
    channel = _resolve_release_channel(settings_lookup=settings_lookup, data_registry=data_registry)
    if channel == "dev":
        return DEFAULT_DEV_UPDATE_BRANCH
    return DEFAULT_STABLE_UPDATE_BRANCH


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


def discover_module_payload_options(modules_path, data_registry=None):
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
                "payload_paths": _build_module_payload_paths(modules_path, module_key, file_name),
                "fallback_name": fallback_name,
                "module_name": module_name,
                "display": f"{module_name} ({file_name})",
            })

    for spec in discover_json_payload_options(data_registry=data_registry):
        option = dict(spec)
        option.setdefault("kind", "json")
        option.setdefault("display", f"{option['fallback_name']} ({os.path.basename(option['relative_path'])})")
        options.append(option)

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
        local_path = option.get("local_source_path") or option.get("local_target_path") or external_path(option["relative_path"])
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

    settings = _load_external_settings_payload()
    allow_unsigned = bool(settings.get("allow_unsigned_dev_updates", False))
    gov = "[Bypassed] Unsigned updates allowed" if allow_unsigned else "[Verified] Signed manifest required"
    checksum_status = "Not checked"
    checksum_note = "Run a payload check to verify repository checksum governance."

    try:
        remote_text = fetch_remote_payload_text(remote_info, branch_name, option["relative_path"])
        remote_bytes = remote_text.encode("utf-8")
        checksum_status, checksum_note = _resolve_checksum_governance(
            remote_info,
            branch_name,
            option["relative_path"],
            remote_bytes,
            timeout=15,
        )
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
                "governance": gov,
                "checksum_status": "Payload missing",
                "checksum_note": "The repository payload is missing on this branch, so checksum verification could not run.",
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
            "governance": gov,
            "checksum_status": "Checksum unavailable",
            "checksum_note": f"Payload check failed before checksum validation: {exc}",
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
            "governance": gov,
            "checksum_status": "Checksum unavailable",
            "checksum_note": f"Payload check failed before checksum validation: {exc}",
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
        
        # Channel gating
        settings = _load_external_settings_payload()
        channel = str(settings.get("release_channel", "stable")).strip().lower()
        ver_lower = str(remote_version).lower()
        is_dev = any(tag in ver_lower for tag in ("dev", "alpha", "beta", "rc", "pre"))
        if channel == "stable" and is_dev:
            return {
                "option": current_option,
                "module_name": module_name,
                "local_metadata": local_metadata,
                "remote_version": remote_version,
                "status": "Dev release filtered",
                "note": "Dev release was filtered because the stable channel is active.",
                "update_available": False,
                "remote_text": None,
                "governance": gov,
            }
            
        module_name = remote_metadata.get("module_name", module_name)
        current_option["module_name"] = module_name
        local_compare = parse_version(local_version)
        remote_compare = parse_version(remote_version)

        if remote_compare and local_compare:
            remote_normalized = normalize_version(remote_compare)
            local_normalized = normalize_version(local_compare)
            if remote_normalized > local_normalized:
                status = "Module update available"
                note = f"A newer {module_name} payload is available and can be installed without rebuilding the EXE."
                update_available = True
            elif remote_normalized == local_normalized:
                status = "Up to date"
                note = f"The selected {module_name} payload already matches the repository version."
            else:
                status = "Local module is newer"
                note = f"The local {module_name} payload is newer than the repository version."
        elif remote_version == local_version and remote_version != "Unknown":
            status = "Up to date"
            note = f"The selected {module_name} payload already matches the repository version."
        elif remote_version == "Unknown" or local_version == "Unknown":
            # Fallback to source code comparison only when semantic versions are unavailable.
            local_token = local_metadata.get("compare_token")
            remote_token = remote_metadata.get("compare_token")
            if local_token and remote_token:
                if local_token.strip() == remote_token.strip():
                    status = "Up to date"
                    note = f"The selected {module_name} payload already matches the repository version."
                else:
                    status = "Module update available"
                    note = f"The local {module_name} payload differs from the repository version and can be updated."
                    update_available = True
            else:
                status = "Module version unreadable"
                note = f"The selected {module_name} payload could not be compared cleanly."
        else:
            status = "Module version unreadable"
            note = f"The selected {module_name} payload could not be compared cleanly."

    # Determine governance status
    settings = _load_external_settings_payload()
    allow_unsigned = bool(settings.get("allow_unsigned_dev_updates", False))
    gov = "[Bypassed] Unsigned updates allowed" if allow_unsigned else "[Verified] Signed manifest required"

    return {
        "option": current_option,
        "module_name": module_name,
        "local_metadata": local_metadata,
        "remote_version": remote_version,
        "status": status,
        "note": note,
        "update_available": update_available,
        "remote_text": remote_text,
        "governance": gov,
        "checksum_status": checksum_status,
        "checksum_note": checksum_note,
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
    data_registry = None

    if dispatcher is not None:
        modules_path = getattr(dispatcher, "modules_path", None)
        loaded_modules = getattr(dispatcher, "loaded_modules", None)
        data_registry = getattr(dispatcher, "external_data_registry", None)
        if getattr(dispatcher, "are_external_module_overrides_enabled", None) and dispatcher.are_external_module_overrides_enabled():
            external_override_path_resolver = getattr(dispatcher, "get_external_module_override_path", None)
        if hasattr(dispatcher, "get_setting"):
            configured_url = _get_configured_update_repository_url(dispatcher.get_setting, data_registry=data_registry)

    resolved_branch_name = branch_name or _detect_branch_name(data_registry=data_registry)
    resolved_remote_info = remote_info or _detect_remote_info(preferred_url=configured_url)
    options = discover_module_payload_options(modules_path, data_registry=data_registry)
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


def scan_available_documentation_payload_updates(branch_name=None, remote_info=None, configured_url=None, data_registry=None):
    resolved_branch_name = branch_name or _detect_branch_name(data_registry=data_registry)
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
        target_path = option.get("local_target_path") or external_path(option["relative_path"])
        backup_dir = option.get("backup_dir")
        if backup_dir and not os.path.isabs(backup_dir):
            backup_dir = external_path(backup_dir)
        write_json_with_backup(
            target_path,
            remote_metadata["payload"],
            backup_dir=backup_dir,
            keep_count=12,
        )
        return target_path, remote_metadata.get("version", "Unknown")

    primary_relative_path = option.get("relative_path")
    primary_payload_text = payload_text.get(primary_relative_path, "") if isinstance(payload_text, dict) else payload_text
    remote_metadata = _parse_module_metadata(primary_payload_text, option["fallback_name"])
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


def evaluate_stable_update_entry(
    entry,
    remote_text,
    stable_artifact_status_label,
    stable_artifact_name_for_version,
    allow_odd_patch=False,
):
    remote_metadata = _parse_module_metadata(remote_text, entry["module_name"])
    remote_version = remote_metadata["version"]
    remote_compare = parse_version(remote_version)
    local_compare = parse_version(entry["local_version"])

    if remote_compare is None:
        status = "Remote version unreadable"
        update_available = False
    elif len(remote_compare) == 3 and remote_compare[2] % 2 != 0 and not allow_odd_patch:
        status = "Remote odd patch ignored"
        update_available = False
    elif not _is_supported_update_version(remote_compare, allow_odd_patch=allow_odd_patch):
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
        candidates.append((f"dist/variants/public/{versioned_name}", versioned_name))
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
            with urllib.request.urlopen(request, timeout=30):
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
    last_integrity_error = None
    for remote_path, target_name in remote_executable_candidates(row, stable_artifact_kind, stable_artifact_name_for_version):
        try:
            payload_bytes = fetch_remote_bytes(remote_info, branch_name, remote_path)
            _verify_remote_payload_integrity(remote_info, branch_name, remote_path, payload_bytes, timeout=15)
            return payload_bytes, target_name
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                last_not_found = exc
                continue
            raise
        except RuntimeError as exc:
            last_integrity_error = exc
            continue

    if last_not_found is not None:
        if last_integrity_error is not None:
            raise RuntimeError(
                f"{last_integrity_error} No checksum-verified packaged artifact was available for this update."
            ) from last_integrity_error
        raise last_not_found
    if last_integrity_error is not None:
        raise RuntimeError(
            f"{last_integrity_error} No checksum-verified packaged artifact was available for this update."
        ) from last_integrity_error
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


def _extract_ubuntu_package_version(version_text):
    parsed = parse_version(version_text)
    if parsed is not None:
        return normalize_version(parsed)

    match = UBUNTU_PACKAGE_VERSION_PATTERN.search(str(version_text or ""))
    if not match:
        return None
    return normalize_version(parse_version(match.group("version")))


def _run_ubuntu_query_command(command, timeout=15):
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def detect_installed_ubuntu_package_version(package_name=DEB_PACKAGE_NAME):
    dpkg_query_path = shutil.which("dpkg-query")
    if not dpkg_query_path:
        return None

    result = _run_ubuntu_query_command([dpkg_query_path, "-W", "-f=${Status}\t${Version}", package_name])
    if result is None or result.returncode != 0:
        return None

    output_text = (result.stdout or "").strip()
    if not output_text:
        return None

    try:
        status_text, version_text = output_text.split("\t", 1)
    except ValueError:
        return None

    if status_text.strip() != "install ok installed":
        return None
    return version_text.strip() or None


def detect_ubuntu_repo_candidate_version(package_name=DEB_PACKAGE_NAME):
    apt_cache_path = shutil.which("apt-cache")
    if not apt_cache_path:
        return None

    result = _run_ubuntu_query_command([apt_cache_path, "policy", package_name])
    if result is None or result.returncode != 0:
        return None

    for line in (result.stdout or "").splitlines():
        stripped_line = line.strip()
        if not stripped_line.startswith("Candidate:"):
            continue
        candidate_text = stripped_line.split(":", 1)[1].strip()
        if candidate_text == "(none)":
            return None
        return candidate_text or None

    return None


def resolve_ubuntu_repo_upgrade_handoff(downloaded_path, target_version=None):
    if not is_ubuntu_runtime():
        return None

    normalized_path = os.path.abspath(downloaded_path)
    pkexec_path = shutil.which("pkexec")
    apt_manager_path = shutil.which("apt-get") or shutil.which("apt")
    shell_path = shutil.which("sh") or ("/bin/sh" if os.path.exists("/bin/sh") else None)
    if not pkexec_path or not apt_manager_path or not shell_path:
        return None

    installed_version = detect_installed_ubuntu_package_version()
    repo_candidate_version = detect_ubuntu_repo_candidate_version()
    if not installed_version or not repo_candidate_version:
        return None

    installed_compare = _extract_ubuntu_package_version(installed_version)
    candidate_compare = _extract_ubuntu_package_version(repo_candidate_version)
    target_compare = _extract_ubuntu_package_version(target_version)
    if candidate_compare is None:
        return None
    if installed_compare is not None and candidate_compare <= installed_compare:
        return None
    if target_compare is not None and candidate_compare < target_compare:
        return None

    repo_upgrade_command = (
        f'"{apt_manager_path}" update && '
        f'"{apt_manager_path}" install --only-upgrade -y {DEB_PACKAGE_NAME}'
    )
    result = _build_ubuntu_package_install_result(
        normalized_path,
        "pkexec apt repository upgrade",
        mode="command",
        command=[pkexec_path, shell_path, "-lc", repo_upgrade_command],
    )
    file_name = os.path.basename(normalized_path)
    result.update({
        "upgrade_source": "repository",
        "repo_candidate_version": repo_candidate_version,
        "installed_version": installed_version,
        "status_message": "Ubuntu repository update started. Restart the app after installation finishes.",
        "detail": (
            f"Downloaded {file_name}, detected repository candidate {repo_candidate_version}, and started a privileged apt upgrade for {DEB_PACKAGE_NAME}. "
            "Ubuntu will refresh package metadata, apply the repository upgrade, and then you can restart the app."
        ),
        "toast_message": f"Started the Ubuntu repository update for {DEB_PACKAGE_NAME}.",
    })
    return result


def _build_ubuntu_package_install_result(downloaded_path, installer_label, *, mode, command=None, fallback_reason=None):
    file_name = os.path.basename(downloaded_path)
    if mode == "command":
        detail = (
            f"Downloaded {file_name} and started a privileged {installer_label} handoff for the installed {DEB_PACKAGE_NAME} Ubuntu package. "
            "Authenticate the Ubuntu prompt if one appears, let the package update finish, then restart the app."
        )
        if fallback_reason:
            detail = f"{detail} The direct installer launch reported: {fallback_reason}"
        return {
            "mode": mode,
            "installer_label": installer_label,
            "command": list(command or []),
            "status_message": "Ubuntu package updater started. Restart the app after installation finishes.",
            "detail": detail,
            "toast_message": f"Started the Ubuntu package updater via {installer_label}.",
        }

    detail = (
        f"Downloaded {file_name} and opened it with the {installer_label}. "
        "Complete the package installation there, then restart the app."
    )
    if fallback_reason:
        detail = f"{detail} The automatic installer handoff fell back to the package handler after: {fallback_reason}"
    return {
        "mode": mode,
        "installer_label": installer_label,
        "command": [],
        "status_message": "Ubuntu package opened. Complete the installation, then restart the app.",
        "detail": detail,
        "toast_message": "Opened the Ubuntu package in the system package handler.",
    }


def resolve_ubuntu_package_install_handoff(downloaded_path):
    if not is_ubuntu_runtime():
        raise RuntimeError("Ubuntu package install handoff is only available on Ubuntu runtimes.")

    normalized_path = os.path.abspath(downloaded_path)
    if not os.path.exists(normalized_path):
        raise FileNotFoundError(f"The downloaded Ubuntu package could not be found: {normalized_path}")

    pkexec_path = shutil.which("pkexec")
    apt_path = shutil.which("apt")
    gdebi_path = shutil.which("gdebi")
    dpkg_path = shutil.which("dpkg")

    if pkexec_path and apt_path:
        return _build_ubuntu_package_install_result(
            normalized_path,
            "pkexec apt install",
            mode="command",
            command=[pkexec_path, apt_path, "install", "-y", normalized_path],
        )

    if pkexec_path and gdebi_path:
        return _build_ubuntu_package_install_result(
            normalized_path,
            "pkexec gdebi",
            mode="command",
            command=[pkexec_path, gdebi_path, "-n", normalized_path],
        )

    if pkexec_path and dpkg_path:
        return _build_ubuntu_package_install_result(
            normalized_path,
            "pkexec dpkg",
            mode="command",
            command=[pkexec_path, dpkg_path, "-i", normalized_path],
        )

    return _build_ubuntu_package_install_result(
        normalized_path,
        "system package handler",
        mode="open",
    )


def launch_ubuntu_package_install(downloaded_path, target_version=None):
    handoff = resolve_ubuntu_repo_upgrade_handoff(downloaded_path, target_version=target_version)
    if handoff is None:
        handoff = resolve_ubuntu_package_install_handoff(downloaded_path)
    if handoff["mode"] == "open":
        open_with_system_default(downloaded_path)
        return handoff

    try:
        subprocess.Popen(
            handoff["command"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        open_with_system_default(downloaded_path)
        return _build_ubuntu_package_install_result(
            os.path.abspath(downloaded_path),
            "system package handler",
            mode="open",
            fallback_reason=str(exc),
        )

    return handoff


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
    required_files = [
        "main.py",
        "build.py",
        os.path.join("app", "update_manager.py"),
        os.path.join("app", "controllers", "update_manager_qt_controller.py"),
    ]
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


class UpdateManagerModel:
    def __init__(self, data_registry=None):
        self.data_registry = data_registry or ExternalDataRegistry()

    def parse_json_payload_metadata(self, file_text, fallback_name):
        return _parse_json_payload_metadata(file_text, fallback_name)

    def read_module_metadata_from_path(self, file_path, fallback_name):
        return _read_module_metadata_from_path(file_path, fallback_name)

    def detect_branch_name(self):
        return _detect_branch_name(data_registry=self.data_registry)

    def detect_remote_info(self, preferred_url=None):
        return _detect_remote_info(preferred_url=preferred_url)

    def remote_updates_available(self, remote_info, branch_name=None):
        return _remote_updates_available(remote_info, branch_name)

    def update_configuration_note(self, remote_info=None):
        return _update_configuration_note(remote_info)

    def discover_module_payload_options(self, modules_path):
        return discover_module_payload_options(modules_path, data_registry=self.data_registry)

    def discover_documentation_payload_options(self):
        return discover_documentation_payload_options()

    def get_local_module_payload_metadata(self, modules_path, loaded_modules, option, external_override_path=None):
        return get_local_module_payload_metadata(
            modules_path,
            loaded_modules,
            option,
            external_override_path=external_override_path,
        )

    def evaluate_module_payload_option(self, modules_path, loaded_modules, option, branch_name, remote_info, external_override_path=None):
        return evaluate_module_payload_option(
            modules_path,
            loaded_modules,
            option,
            branch_name,
            remote_info,
            external_override_path=external_override_path,
        )

    def scan_available_module_payload_updates(self, dispatcher, branch_name=None, remote_info=None):
        return scan_available_module_payload_updates(dispatcher, branch_name=branch_name, remote_info=remote_info)

    def scan_available_documentation_payload_updates(self, branch_name=None, remote_info=None, configured_url=None):
        return scan_available_documentation_payload_updates(
            branch_name=branch_name,
            remote_info=remote_info,
            configured_url=configured_url,
            data_registry=self.data_registry,
        )

    def install_documentation_payload(self, option, remote_info, branch_name, remote_text=None):
        payload_text = remote_text if remote_text is not None else fetch_remote_payload_text(remote_info, branch_name, option["relative_path"], timeout=15)
        return install_documentation_payload_option(option, payload_text)

    def load_settings(self):
        settings_path = self.data_registry.resolve_write_path("settings")
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    def verify_remote_manifest(self, remote_info, branch_name):
        settings = self.load_settings()
        allow_unsigned = bool(settings.get("allow_unsigned_dev_updates", False))
        channel = str(settings.get("release_channel", "stable")).strip().lower()

        try:
            manifest_text = fetch_remote_payload_text(remote_info, branch_name, "manifest.json", timeout=15)
            manifest = json.loads(manifest_text)
        except Exception as exc:
            if allow_unsigned:
                from app.security_audit import log_security_event
                log_security_event("update_manifest_verify", "Remote manifest.json missing, but unsigned dev updates are allowed.", "success")
                return None
            from app.security_audit import log_security_event
            log_security_event("update_manifest_verify", f"Failed to load manifest.json: {exc}", "failure")
            raise RuntimeError(f"Updates require a signed manifest.json. Error: {exc}")

        if not allow_unsigned:
            from app.utils.crypto_utils import verify_manifest
            try:
                if not verify_manifest(manifest):
                    raise ValueError("Signature check returned False.")
                from app.security_audit import log_security_event
                log_security_event("update_manifest_verify", f"Verified manifest signature for version {manifest.get('version')}", "success")
            except Exception as exc:
                from app.security_audit import log_security_event
                log_security_event("update_manifest_verify", f"Manifest signature check failed: {exc}", "failure")
                raise RuntimeError(f"Fail-closed update block: remote manifest has an invalid signature. {exc}")
        else:
            from app.security_audit import log_security_event
            log_security_event("manifest_verification_bypass", "Bypassed remote manifest signature check (allow_unsigned_dev_updates enabled).", "success")

        manifest_channel = str(manifest.get("release_channel", "stable")).strip().lower()
        if channel == "stable" and manifest_channel == "dev":
            raise RuntimeError("Gating check failed: cannot install a 'dev' channel package on the 'stable' update channel.")

        return manifest

    def _compute_file_sha256(self, file_path):
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def _create_rollback_backup(self, option, source_verified=False):
        import shutil
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        option_key = option.get("key") or "module"
        
        rollback_dir = external_path(f"data/backups/rollbacks/{timestamp}_{option_key}")
        os.makedirs(rollback_dir, exist_ok=True)
        
        payload_paths = option.get("payload_paths") or [option["relative_path"]]
        
        backup_files = []
        for rel_path in payload_paths:
            target_path = option.get("local_target_path") or external_path(rel_path)
            if os.path.exists(target_path):
                dest_path = os.path.join(rollback_dir, os.path.basename(target_path))
                shutil.copy2(target_path, dest_path)
                backup_files.append({
                    "original_path": target_path,
                    "backup_path": dest_path,
                    "relative_path": rel_path,
                    "backup_sha256": self._compute_file_sha256(dest_path),
                })
                
        if backup_files:
            meta = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "option_key": option_key,
                "module_name": option.get("module_name"),
                "version": option.get("local_version", "Unknown"),
                "files": backup_files,
                "source_verified": bool(source_verified),
            }
            with open(os.path.join(rollback_dir, "rollback_metadata.json"), "w", encoding="utf-8") as handle:
                json.dump(meta, handle, indent=2)

    def _verify_rollback_metadata(self, metadata):
        files = list(metadata.get("files") or [])
        if not files:
            return False, "Rollback metadata has no tracked backup files."
        if not bool(metadata.get("source_verified", False)):
            return False, "Rollback candidate was not created from a verified update source."
        for file_info in files:
            backup_path = str(file_info.get("backup_path") or "").strip()
            expected_hash = str(file_info.get("backup_sha256") or "").strip().lower()
            if not backup_path or not os.path.exists(backup_path):
                return False, f"Missing backup file: {backup_path or 'unknown path'}."
            if not expected_hash:
                return False, f"Missing backup checksum metadata for {backup_path}."
            actual_hash = self._compute_file_sha256(backup_path).strip().lower()
            if actual_hash != expected_hash:
                return False, f"Backup checksum mismatch for {backup_path}."
        return True, "Verified"

    def list_rollback_backups(self):
        rollback_root = external_path("data/backups/rollbacks")
        if not os.path.exists(rollback_root):
            return []
        
        candidates = []
        try:
            for item in os.listdir(rollback_root):
                item_path = os.path.join(rollback_root, item)
                if not os.path.isdir(item_path):
                    continue
                meta_path = os.path.join(item_path, "rollback_metadata.json")
                if not os.path.exists(meta_path):
                    continue
                try:
                    with open(meta_path, "r", encoding="utf-8") as handle:
                        meta = json.load(handle)
                    verified, verify_note = self._verify_rollback_metadata(meta)
                    timestamp_str = meta.get("timestamp") or item
                    candidates.append({
                        "path": item_path,
                        "dir_name": item,
                        "timestamp_str": timestamp_str,
                        "module_name": meta.get("module_name") or "-",
                        "version": meta.get("version") or "Unknown",
                        "verified": bool(verified),
                        "verify_note": verify_note,
                    })
                except Exception:
                    pass
        except Exception:
            pass
        candidates.sort(key=lambda x: x["timestamp_str"], reverse=True)
        return candidates

    def restore_rollback_backup(self, backup_dir):
        meta_path = os.path.join(backup_dir, "rollback_metadata.json")
        if not os.path.exists(meta_path):
            raise RuntimeError("Rollback metadata is missing.")
            
        with open(meta_path, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        verified, verify_note = self._verify_rollback_metadata(meta)
        if not verified:
            raise RuntimeError(f"Rollback blocked: {verify_note}")
            
        files = meta.get("files") or []
        import shutil
        for file_info in files:
            src = file_info["backup_path"]
            dst = file_info["original_path"]
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                
        from app.security_audit import log_security_event
        log_security_event("update_rollback", f"Restored backup files to revert to version {meta.get('version')}", "success", {"module_name": meta.get("module_name")})

    def install_module_payload(self, option, remote_info, branch_name, install_module_override, remote_text=None):
        manifest = self.verify_remote_manifest(remote_info, branch_name)
        
        # Create rollback backup of existing files
        self._create_rollback_backup(option, source_verified=True)
        
        payload_paths = option.get("payload_paths") or [option["relative_path"]]
        if option.get("kind") == "module":
            payload_text = {}
            for relative_path in payload_paths:
                payload_bytes = fetch_remote_bytes(remote_info, branch_name, relative_path, timeout=15)
                
                # Check manifest hash if manifest is present
                if manifest and "artifacts" in manifest:
                    norm_path = relative_path.replace("\\", "/").lstrip("/")
                    artifact_meta = manifest["artifacts"].get(norm_path)
                    if artifact_meta and "sha256" in artifact_meta:
                        # NOTE: build.py refreshes these manifest hashes through
                        # app.update_integrity before packaging/module-key updates.
                        expected_hash = artifact_meta["sha256"]
                        try:
                            _verify_payload_hash(expected_hash, payload_bytes, relative_path)
                        except RuntimeError as exc:
                            from app.security_audit import log_security_event
                            log_security_event("update_install", f"Integrity hash mismatch for '{relative_path}' during update.", "failure")
                            raise RuntimeError(str(exc))
                    else:
                        _verify_remote_payload_integrity(remote_info, branch_name, relative_path, payload_bytes, timeout=15)
                else:
                    _verify_remote_payload_integrity(remote_info, branch_name, relative_path, payload_bytes, timeout=15)
                    
                payload_text[relative_path] = payload_bytes.decode("utf-8")
        else:
            payload_text = remote_text if remote_text is not None else fetch_remote_payload_text(remote_info, branch_name, option["relative_path"], timeout=15)
            
        from app.security_audit import log_security_event
        log_security_event("update_install", f"Successfully installed module override payload option '{option.get('module_name')}'", "success", {"module_name": option.get("module_name")})
        
        return install_module_payload_option(option, payload_text, install_module_override)

    def build_local_manifest(self, dispatcher_module):
        return build_local_manifest(dispatcher_module)

    def evaluate_stable_update_entry(
        self,
        entry,
        remote_text,
        stable_artifact_status_label,
        stable_artifact_name_for_version,
        allow_odd_patch=False,
    ):
        return evaluate_stable_update_entry(
            entry,
            remote_text,
            stable_artifact_status_label,
            stable_artifact_name_for_version,
            allow_odd_patch=allow_odd_patch,
        )

    def fetch_remote_file(self, remote_info, branch_name, relative_path, timeout=15):
        return fetch_remote_payload_text(remote_info, branch_name, relative_path, timeout=timeout)

    def fetch_remote_bytes(self, remote_info, branch_name, relative_path, timeout=30):
        return fetch_remote_bytes(remote_info, branch_name, relative_path, timeout=timeout)

    def fetch_remote_snapshot_bytes(self, remote_info, branch_name):
        return fetch_remote_snapshot_bytes(remote_info, branch_name)

    def remote_executable_candidates(self, row, stable_artifact_kind, stable_artifact_name_for_version):
        return remote_executable_candidates(row, stable_artifact_kind, stable_artifact_name_for_version)

    def probe_remote_executable(self, remote_info, branch_name, row, stable_artifact_kind, stable_artifact_name_for_version):
        return probe_remote_executable(remote_info, branch_name, row, stable_artifact_kind, stable_artifact_name_for_version)

    def download_remote_executable(self, remote_info, branch_name, row, stable_artifact_kind, stable_artifact_name_for_version):
        return download_remote_executable(remote_info, branch_name, row, stable_artifact_kind, stable_artifact_name_for_version)

    def resolve_download_directory(self):
        return resolve_download_directory()

    def resolve_source_workspace(self):
        return resolve_source_workspace()

    def resolve_source_log_directory(self):
        return resolve_source_log_directory()

    def cleanup_source_stage_dir(self, stage_dir):
        return cleanup_source_stage_dir(stage_dir)

    def remove_paths(self, path_values):
        return remove_paths(path_values)

    def locate_extracted_source_root(self, extract_dir):
        return locate_extracted_source_root(extract_dir)

    def validate_source_snapshot(self, source_root):
        return validate_source_snapshot(source_root)

    def resolve_build_python_command(self, download_directory=None):
        return resolve_build_python_command(download_directory)

    def write_source_build_log(self, log_name, content):
        return write_source_build_log(log_name, content)

    def resolve_built_executable(self, source_root):
        return resolve_built_executable(source_root)

    def resolve_final_built_executable_path(self, built_exe_path, download_directory=None, current_executable=None):
        return resolve_final_built_executable_path(
            built_exe_path,
            download_directory=download_directory,
            current_executable=current_executable,
        )

    def build_stable_update_rows(
        self,
        local_manifest,
        remote_info,
        branch_name,
        stable_artifact_kind,
        stable_artifact_name_for_version,
        stable_artifact_status_label,
        allow_odd_patch=False,
    ):
        comparison_rows = []
        for entry in local_manifest or []:
            try:
                remote_text = self.fetch_remote_file(remote_info, branch_name, entry["relative_path"])
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    comparison_rows.append(
                        {
                            **entry,
                            "remote_version": "Missing",
                            "status": "Not in repository branch",
                            "update_available": False,
                        }
                    )
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                comparison_rows.append(
                    {
                        **entry,
                        "remote_version": "Unavailable",
                        "status": "Repository check timed out",
                        "note": f"Could not reach {branch_name} for update metadata: {exc}",
                        "update_available": False,
                    }
                )
                continue

            current_row = self.evaluate_stable_update_entry(
                entry,
                remote_text,
                stable_artifact_status_label,
                stable_artifact_name_for_version,
                allow_odd_patch=allow_odd_patch,
            )
            if current_row["update_available"]:
                try:
                    remote_path, resolved_name = self.probe_remote_executable(
                        remote_info,
                        branch_name,
                        current_row,
                        stable_artifact_kind,
                        stable_artifact_name_for_version,
                    )
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    current_row["status"] = f"{stable_artifact_status_label} check timed out"
                    current_row["note"] = f"Timed out while probing packaged artifacts on {branch_name}: {exc}"
                    current_row["update_available"] = False
                    comparison_rows.append(current_row)
                    continue
                if remote_path:
                    current_row["remote_exe_path"] = remote_path
                    current_row["remote_exe_name"] = resolved_name
                else:
                    current_row["status"] = f"{stable_artifact_status_label} artifact missing"
                    current_row["update_available"] = False
            comparison_rows.append(current_row)
        return comparison_rows

    def stage_downloaded_artifact(self, row, remote_info, branch_name, stable_artifact_kind, stable_artifact_name_for_version, download_directory):
        remote_exe_bytes, resolved_name = self.download_remote_executable(
            remote_info,
            branch_name,
            row,
            stable_artifact_kind,
            stable_artifact_name_for_version,
        )
        os.makedirs(download_directory, exist_ok=True)
        final_exe_path = os.path.join(download_directory, resolved_name)
        temp_exe_path = f"{final_exe_path}.download"
        with open(temp_exe_path, "wb") as handle:
            handle.write(remote_exe_bytes)
        os.replace(temp_exe_path, final_exe_path)
        return final_exe_path

    def resolve_ubuntu_package_install_handoff(self, downloaded_path):
        return resolve_ubuntu_package_install_handoff(downloaded_path)

    def launch_ubuntu_package_install(self, downloaded_path, target_version=None):
        return launch_ubuntu_package_install(downloaded_path, target_version=target_version)

    def stage_source_snapshot(self, remote_info, branch_name, stage_root):
        owner = remote_info.get("owner") if isinstance(remote_info, dict) else None
        repo = remote_info.get("repo") if isinstance(remote_info, dict) else None
        if not owner or not repo or not branch_name:
            raise RuntimeError("Repository origin or branch could not be determined for the source snapshot.")

        snapshot_bytes = self.fetch_remote_snapshot_bytes(remote_info, branch_name)
        stage_dir = tempfile.mkdtemp(prefix="source-update-", dir=stage_root)
        archive_name = f"{repo}-{branch_name}.zip"
        archive_path = os.path.join(stage_dir, archive_name)
        with open(archive_path, "wb") as handle:
            handle.write(snapshot_bytes)

        extract_dir = os.path.join(stage_dir, "snapshot")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive_handle:
            _safe_extract_zip(archive_handle, extract_dir)

        source_root = self.locate_extracted_source_root(extract_dir)
        self.validate_source_snapshot(source_root)
        return {
            "archive_path": archive_path,
            "stage_dir": stage_dir,
            "extract_dir": extract_dir,
            "source_root": source_root,
        }

    def run_source_build(self, source_root, branch_name, download_directory=None, current_executable=None):
        if is_ubuntu_runtime() or os.name != "nt":
            raise RuntimeError("Advanced source rebuilds currently target packaged Windows builds only.")

        command_prefix, runtime_display = self.resolve_build_python_command(download_directory)
        build_command = command_prefix + ["build.py", "--target", "windows", "--non-interactive"]
        env = os.environ.copy()
        env["MARTIN_KEEP_DIST"] = "1"
        env["MARTIN_SKIP_TASKKILL"] = "1"
        env["MARTIN_BUILD_TARGET"] = "windows"
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
        log_name = f"source-build-{branch_name}.log"
        build_log_path = self.write_source_build_log(log_name, build_log_text)
        if result.returncode != 0:
            raise RuntimeError(f"The staged build exited with code {result.returncode}.")

        built_exe_path = self.resolve_built_executable(source_root)
        final_exe_path = self.resolve_final_built_executable_path(
            built_exe_path,
            download_directory=download_directory,
            current_executable=current_executable,
        )
        shutil.copy2(built_exe_path, final_exe_path)
        return {
            "runtime_display": runtime_display,
            "build_log_path": build_log_path,
            "built_exe_path": built_exe_path,
            "final_exe_path": final_exe_path,
        }