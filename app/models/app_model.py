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
import hashlib
import json
import os
import threading
from datetime import datetime
from dataclasses import dataclass, field

from app.app_platform import get_obsolete_local_executables
from app.settings_diagnostics import (
    build_default_settings_payload,
    diagnose_and_repair_settings,
    log_settings_diagnostics_summary,
    persist_repaired_settings,
    write_settings_diagnostics_report,
)
from app.theme_manager import DEFAULT_THEME, normalize_theme
from app.utils import external_path

__module_name__ = "Application Shell"
__version__ = "2.5.0"
PROTECTED_OVERRIDE_MODULES = {"layout_manager", "settings_manager", "rate_manager", "update_manager"}


@dataclass
class AppModel:
    modules_path: str
    external_modules_path: str
    layout_config: str
    rate_config: str
    settings_path: str
    shared_data: dict = field(default_factory=dict)
    loaded_modules: dict = field(default_factory=dict)
    persistent_module_instances: dict = field(default_factory=dict)
    runtime_settings_listeners: list = field(default_factory=list)
    active_module_instance: object = None
    active_module_name: str = None
    active_module_frame: object = None
    active_form_info: dict = field(default_factory=dict)
    active_form_listeners: list = field(default_factory=list)
    runtime_settings: dict = field(default_factory=dict)
    window_alpha_supported: bool = False
    transition_duration_ms: int = 360
    transitions_enabled: bool = True
    transition_min_alpha: float = 0.82
    transition_in_progress: bool = False
    module_update_check_in_progress: bool = False
    last_module_update_notification_signature: tuple = None
    managed_source_signature: tuple = field(default_factory=tuple)
    managed_source_generation: int = 0
    preloaded_module_names: set = field(default_factory=set)
    module_import_lock: object = field(default_factory=threading.RLock)
    module_preload_stop_event: object = field(default_factory=threading.Event)
    module_preload_thread: object = None
    module_preload_poll_seconds: float = 1.0
    preload_data_lock: object = field(default_factory=threading.RLock)
    last_settings_diagnostics: object = None

    def _integrity_policy_path(self):
        return external_path(os.path.join("data", "security", "external_module_integrity.json"))

    def _utc_timestamp(self):
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _load_integrity_policy(self):
        defaults = {"module_records": {}}
        policy_path = self._integrity_policy_path()
        if not os.path.exists(policy_path):
            return defaults
        try:
            with open(policy_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                module_records = payload.get("module_records")
                if isinstance(module_records, dict):
                    defaults["module_records"] = module_records
        except Exception:
            pass
        return defaults

    def _save_integrity_policy(self, policy_payload):
        policy_path = self._integrity_policy_path()
        policy_dir = os.path.dirname(policy_path)
        if policy_dir:
            os.makedirs(policy_dir, exist_ok=True)
        temp_path = f"{policy_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(policy_payload, handle, indent=4)
        os.replace(temp_path, policy_path)
        return policy_path

    def _hash_file_sha256(self, file_path):
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def build_override_hashes_for_module(self, module_name):
        module_key = str(module_name or "").strip()
        if not module_key:
            return {}
        hashes = {}
        for relative_path in self._iter_module_override_relative_paths(module_key):
            normalized_relative_path = str(relative_path).replace("\\", "/").lstrip("/")
            absolute_path = os.path.join(self.external_modules_path, normalized_relative_path.replace("/", os.sep))
            if not os.path.isfile(absolute_path):
                continue
            hashes[normalized_relative_path] = self._hash_file_sha256(absolute_path)
        return hashes

    def register_override_hashes(
        self,
        module_name,
        file_hashes,
        source,
        repository_url=None,
        branch_name=None,
        approved=False,
    ):
        module_key = str(module_name or "").strip()
        if not module_key:
            raise ValueError("module_name is required to register override hashes.")
        normalized_hashes = {}
        for relative_path, hash_value in dict(file_hashes or {}).items():
            normalized_relative_path = str(relative_path or "").replace("\\", "/").lstrip("/")
            normalized_hash = str(hash_value or "").strip().lower()
            if not normalized_relative_path or not normalized_hash:
                continue
            normalized_hashes[normalized_relative_path] = normalized_hash
        if not normalized_hashes:
            raise ValueError("At least one override hash is required.")

        policy = self._load_integrity_policy()
        module_records = policy.setdefault("module_records", {})
        module_records[module_key] = {
            "hashes": normalized_hashes,
            "source": str(source or "unknown"),
            "repository_url": str(repository_url or "").strip(),
            "branch_name": str(branch_name or "").strip(),
            "approved": bool(approved),
            "updated_at": self._utc_timestamp(),
            "approved_at": self._utc_timestamp() if approved else "",
        }
        self._save_integrity_policy(policy)
        return dict(module_records[module_key])

    def get_override_verification_state(self, module_name):
        module_key = str(module_name or "").strip()
        current_hashes = self.build_override_hashes_for_module(module_key)
        if not current_hashes:
            return {
                "has_override": False,
                "verified": False,
                "approved": False,
                "current_hashes": {},
                "record": None,
                "reason": "No external override files are present for this module.",
            }

        policy = self._load_integrity_policy()
        module_record = dict((policy.get("module_records") or {}).get(module_key) or {})
        stored_hashes = dict(module_record.get("hashes") or {})

        hashes_match = bool(stored_hashes) and current_hashes == stored_hashes
        verified = hashes_match
        approved = bool(module_record.get("approved", False)) and verified
        
        reason = ""
        if not hashes_match:
            reason = (
                "External override files changed and no longer match the recorded integrity hashes. "
                "Developer approval is required before loading."
            )
        elif not approved:
            reason = "External override integrity is recorded, but developer approval is still required for loading."
        else:
            strict_protected_policy = bool(self.settings.get("strict_protected_override_policy", True))
            require_dual = bool(self.settings.get("require_dual_override_approval", False))
            ttl_days = int(self.settings.get("override_ttl_days", 0))
            if strict_protected_policy and module_key in PROTECTED_OVERRIDE_MODULES:
                require_dual = True
                ttl_days = max(1, ttl_days)

            # Check TTL expiry
            if ttl_days > 0:
                approved_at_str = module_record.get("approved_at")
                if approved_at_str:
                    try:
                        approved_at = datetime.fromisoformat(approved_at_str.rstrip("Z"))
                        age = datetime.utcnow() - approved_at
                        if age.days >= ttl_days:
                            approved = False
                            reason = f"Approved override expired (exceeded TTL of {ttl_days} days)."
                    except Exception:
                        approved = False
                        reason = "Approved override has invalid approved_at timestamp."
            
            # Check dual-approval
            if approved:
                if require_dual:
                    approvers = module_record.get("approved_by_list") or []
                    if len(approvers) < 2:
                        approved = False
                        reason = f"Approved override requires dual-approval (currently has {len(approvers)} approvals)."

            if approved:
                reason = "External override hashes are verified and approved."

        return {
            "has_override": True,
            "verified": verified,
            "approved": approved,
            "current_hashes": current_hashes,
            "record": module_record,
            "reason": reason,
        }

    def approve_override_hashes(self, module_name, file_hashes, approver=None):
        module_key = str(module_name or "").strip()
        if not module_key:
            raise ValueError("module_name is required to approve override hashes.")

        normalized_hashes = {}
        for relative_path, hash_value in dict(file_hashes or {}).items():
            normalized_relative_path = str(relative_path or "").replace("\\", "/").lstrip("/")
            normalized_hash = str(hash_value or "").strip().lower()
            if not normalized_relative_path or not normalized_hash:
                continue
            normalized_hashes[normalized_relative_path] = normalized_hash
        if not normalized_hashes:
            raise ValueError("At least one override hash is required for approval.")

        policy = self._load_integrity_policy()
        module_records = policy.setdefault("module_records", {})
        existing_record = dict(module_records.get(module_key) or {})
        
        approvers = list(existing_record.get("approved_by_list") or [])
        if approver:
            approver_str = str(approver).strip()
            if approver_str and approver_str not in approvers:
                approvers.append(approver_str)
                
        module_records[module_key] = {
            "hashes": normalized_hashes,
            "source": str(existing_record.get("source") or "manual_approval"),
            "repository_url": str(existing_record.get("repository_url") or "").strip(),
            "branch_name": str(existing_record.get("branch_name") or "").strip(),
            "approved": True,
            "approved_by_list": approvers,
            "approved_by": ", ".join(approvers),
            "updated_at": self._utc_timestamp(),
            "approved_at": self._utc_timestamp(),
        }
        self._save_integrity_policy(policy)
        return dict(module_records[module_key])

    def record_internal_editor_override_hash(self, file_path):
        candidate_path = os.path.abspath(str(file_path or ""))
        if not candidate_path or not os.path.isfile(candidate_path):
            return None
        external_root = os.path.abspath(self.external_modules_path)
        try:
            if os.path.commonpath([candidate_path, external_root]) != external_root:
                return None
        except Exception:
            return None

        relative_path = os.path.relpath(candidate_path, external_root).replace("\\", "/")
        normalized_relative_path = relative_path.lstrip("/")
        if not normalized_relative_path.endswith(".py"):
            return None

        if "/" not in normalized_relative_path:
            module_name = os.path.splitext(os.path.basename(normalized_relative_path))[0]
        else:
            base_name = os.path.splitext(os.path.basename(normalized_relative_path))[0]
            module_name = (
                base_name.removesuffix("_qt_controller")
                .removesuffix("_controller")
                .removesuffix("_qt_view")
                .removesuffix("_view")
                .removesuffix("_model")
            )
        module_name = str(module_name or "").strip()
        if not module_name:
            return None

        current_hashes = self.build_override_hashes_for_module(module_name)
        if not current_hashes:
            return None
        return self.register_override_hashes(
            module_name,
            current_hashes,
            source="internal_code_editor",
            approved=False,
        )

    def _sanitize_override_relative_path(self, relative_path):
        normalized_relative_path = str(relative_path or "").replace("\\", "/").lstrip("/")
        if normalized_relative_path.startswith("app/"):
            normalized_relative_path = normalized_relative_path[4:]
        if not normalized_relative_path:
            raise ValueError("Override file path cannot be empty.")
        normalized_relative_path = os.path.normpath(normalized_relative_path.replace("/", os.sep)).replace("\\", "/")
        if normalized_relative_path.startswith("../") or normalized_relative_path == "..":
            raise ValueError("Override file path escapes the external module directory.")
        if os.path.isabs(normalized_relative_path):
            raise ValueError("Override file path must be relative.")
        if not normalized_relative_path.endswith(".py"):
            raise ValueError("Only Python module overrides are supported.")
        return normalized_relative_path

    def _get_legacy_external_modules_path(self):
        return external_path("app")

    def migrate_legacy_external_module_overrides(self):
        legacy_root = self._get_legacy_external_modules_path()
        normalized_legacy_root = os.path.abspath(legacy_root)
        normalized_external_root = os.path.abspath(self.external_modules_path)
        normalized_bundled_root = os.path.abspath(self.modules_path)

        if normalized_legacy_root in {normalized_external_root, normalized_bundled_root}:
            return []
        if not os.path.isdir(legacy_root):
            return []

        moved_paths = []
        for relative_root in ("", "controllers", "models", "views"):
            source_dir = os.path.join(legacy_root, relative_root) if relative_root else legacy_root
            if not os.path.isdir(source_dir):
                continue

            target_dir = os.path.join(self.external_modules_path, relative_root) if relative_root else self.external_modules_path
            os.makedirs(target_dir, exist_ok=True)

            for file_name in os.listdir(source_dir):
                if not file_name.endswith(".py"):
                    continue
                source_path = os.path.join(source_dir, file_name)
                if not os.path.isfile(source_path):
                    continue
                target_path = os.path.join(target_dir, file_name)
                if os.path.exists(target_path):
                    continue
                os.replace(source_path, target_path)
                moved_paths.append(target_path)
        return moved_paths

    def ensure_external_modules_directory(self):
        self.migrate_legacy_external_module_overrides()
        os.makedirs(self.external_modules_path, exist_ok=True)

    def _write_text_file(self, target_path, file_text):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        temp_path = f"{target_path}.tmp"
        with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(file_text)
        os.replace(temp_path, target_path)
        return target_path

    def _iter_module_override_relative_paths(self, module_name):
        return [
            f"{module_name}.py",
            os.path.join("controllers", f"{module_name}_controller.py"),
            os.path.join("models", f"{module_name}_model.py"),
            os.path.join("views", f"{module_name}_view.py"),
        ]

    def get_external_module_override_path(self, module_name, managed_module_names):
        self.migrate_legacy_external_module_overrides()
        if module_name not in managed_module_names:
            return None
        candidate = os.path.join(self.external_modules_path, f"{module_name}.py")
        return candidate if os.path.exists(candidate) else None

    def has_external_modules_directory(self):
        self.migrate_legacy_external_module_overrides()
        return os.path.isdir(self.external_modules_path) and os.path.abspath(self.external_modules_path) != os.path.abspath(self.modules_path)

    def get_external_module_override_names(self, managed_module_names):
        if not self.has_external_modules_directory():
            return []

        module_names = []
        for module_name in managed_module_names:
            override_path = os.path.join(self.external_modules_path, f"{module_name}.py")
            if os.path.isfile(override_path) and module_name not in module_names:
                module_names.append(module_name)
        return sorted(module_names)

    def get_bundled_module_names(self, managed_module_names):
        return [
            module_name
            for module_name in managed_module_names
            if os.path.isfile(os.path.join(self.modules_path, f"{module_name}.py"))
        ]

    def write_module_override(self, module_name, module_text):
        self.ensure_external_modules_directory()
        normalized_module_name = str(module_name or "").strip()
        if not normalized_module_name or any(token in normalized_module_name for token in ("/", "\\", "..", ":")):
            raise ValueError("Invalid module name for external override.")
        target_path = os.path.join(self.external_modules_path, f"{normalized_module_name}.py")
        self._write_text_file(target_path, module_text)
        return target_path

    def write_module_override_files(self, file_payloads, primary_relative_path=None):
        self.ensure_external_modules_directory()
        written_paths = []
        primary_path = None
        resolved_primary_relative_path = self._sanitize_override_relative_path(primary_relative_path) if primary_relative_path else ""
        external_root = os.path.abspath(self.external_modules_path)

        for relative_path, file_text in file_payloads.items():
            normalized_relative_path = self._sanitize_override_relative_path(relative_path)
            target_path = os.path.join(self.external_modules_path, normalized_relative_path.replace("/", os.sep))
            resolved_target_path = os.path.abspath(target_path)
            try:
                if os.path.commonpath([resolved_target_path, external_root]) != external_root:
                    raise ValueError("Override file path escapes the external module directory.")
            except ValueError:
                raise ValueError("Override file path escapes the external module directory.")
            self._write_text_file(target_path, file_text)
            written_paths.append(target_path)
            if normalized_relative_path == resolved_primary_relative_path:
                primary_path = target_path

        if primary_path is None and written_paths:
            primary_path = written_paths[0]
        return primary_path, written_paths

    def remove_external_module_overrides(self, managed_module_names, module_names=None, include_bytecode=True):
        if not self.has_external_modules_directory():
            return []

        selected_names = module_names or self.get_bundled_module_names(managed_module_names)
        removed_paths = []

        for module_name in selected_names:
            for relative_path in self._iter_module_override_relative_paths(module_name):
                normalized_relative_path = relative_path.replace("/", os.sep)
                override_path = os.path.join(self.external_modules_path, normalized_relative_path)
                if os.path.isfile(override_path):
                    os.remove(override_path)
                    removed_paths.append(override_path)

                if not include_bytecode:
                    continue

                parent_directory = os.path.dirname(override_path)
                pycache_dir = os.path.join(parent_directory, "__pycache__")
                cache_prefix = f"{os.path.splitext(os.path.basename(relative_path))[0]}."
                if os.path.isdir(pycache_dir):
                    for cache_name in os.listdir(pycache_dir):
                        if not cache_name.startswith(cache_prefix):
                            continue
                        cache_path = os.path.join(pycache_dir, cache_name)
                        if os.path.isfile(cache_path):
                            os.remove(cache_path)
                            removed_paths.append(cache_path)
                    try:
                        if not os.listdir(pycache_dir):
                            os.rmdir(pycache_dir)
                    except OSError:
                        pass

        return removed_paths

    def normalize_module_names(self, raw_value, valid_modules=None):
        if isinstance(raw_value, str):
            candidates = [part.strip() for part in raw_value.split(",")]
        elif isinstance(raw_value, (list, tuple, set)):
            candidates = [str(part).strip() for part in raw_value]
        else:
            candidates = []

        valid_lookup = {str(module_name).strip() for module_name in (valid_modules or []) if str(module_name).strip()}
        normalized = []
        for module_name in candidates:
            if not module_name or module_name in normalized:
                continue
            if valid_lookup and module_name not in valid_lookup:
                continue
            normalized.append(module_name)
        return normalized

    def load_runtime_settings(self, valid_navigation_modules=None, valid_persistent_modules=None):
        settings = build_default_settings_payload()
        loaded = None
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    diagnostics = diagnose_and_repair_settings(
                        loaded,
                        settings,
                        context="app_model.load_runtime_settings",
                        valid_navigation_modules=valid_navigation_modules,
                        valid_persistent_modules=valid_persistent_modules,
                        drop_unknown_from_effective=True,
                        keep_unknown_for_persist=False,
                    )
                    settings.update(diagnostics.repaired_effective_payload)
                    if diagnostics.repaired:
                        persist_repaired_settings(diagnostics, self.settings_path, keep_count=12)
                        write_settings_diagnostics_report(diagnostics, keep_count=30)
                        log_settings_diagnostics_summary(diagnostics)
                    self.last_settings_diagnostics = diagnostics
            except Exception:
                pass

        try:
            settings["toast_duration_sec"] = max(1, int(settings.get("toast_duration_sec", 5)))
        except Exception:
            settings["toast_duration_sec"] = 5

        settings["enable_screen_transitions"] = bool(settings.get("enable_screen_transitions", True))
        settings["enable_module_update_notifications"] = bool(settings.get("enable_module_update_notifications", True))
        settings["allow_unsigned_dev_updates"] = bool(settings.get("allow_unsigned_dev_updates", False))
        settings["require_dual_override_approval"] = bool(settings.get("require_dual_override_approval", False))
        settings["strict_protected_override_policy"] = bool(settings.get("strict_protected_override_policy", True))
        release_channel = str(settings.get("release_channel", "stable") or "stable").strip().lower()
        settings["release_channel"] = release_channel if release_channel in {"stable", "dev"} else "stable"
        try:
            settings["override_ttl_days"] = max(0, int(settings.get("override_ttl_days", 0)))
        except Exception:
            settings["override_ttl_days"] = 0
        try:
            settings["screen_transition_duration_ms"] = max(0, min(500, int(settings.get("screen_transition_duration_ms", 360))))
        except Exception:
            settings["screen_transition_duration_ms"] = 360

        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
        normalized_shell_backend = str(settings.get("ui_shell_backend", "pyqt6") or "pyqt6").strip().lower()
        if normalized_shell_backend not in {"tk", "pyqt6"}:
            normalized_shell_backend = "pyqt6"
        settings["ui_shell_backend"] = normalized_shell_backend
        settings["module_whitelist"] = self.normalize_module_names(settings.get("module_whitelist", []), valid_navigation_modules)
        settings["persistent_modules"] = self.normalize_module_names(settings.get("persistent_modules", []), valid_persistent_modules)
        settings["_module_update_notifications_explicit"] = isinstance(loaded, dict) and "enable_module_update_notifications" in loaded
        return settings

    def get_obsolete_local_executables(self, current_executable, current_version):
        return get_obsolete_local_executables(os.path.abspath(current_executable), current_version)

    def remove_obsolete_local_executables(self, obsolete_executables):
        removed = []
        failed = []
        for entry in obsolete_executables or []:
            try:
                os.remove(entry["path"])
                removed.append(entry["name"])
            except OSError:
                failed.append(entry["name"])
        return removed, failed
