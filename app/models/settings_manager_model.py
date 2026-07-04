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
from copy import deepcopy
import os
import time

from app.app_identity import DEFAULT_UPDATE_REPOSITORY_URL
from app.downtime_codes import DEFAULT_DT_CODE_MAP
from app.external_data_registry import ExternalDataRegistry
from app.settings_diagnostics import (
    build_default_settings_payload,
    diagnose_and_repair_settings,
    log_settings_diagnostics_summary,
    persist_repaired_settings,
    write_settings_diagnostics_report,
)
from app.theme_manager import DEFAULT_THEME, normalize_theme
from app.utils import external_data_path


__module_name__ = "Settings Manager"
__version__ = "1.0.2"

PATH_OVERRIDE_DEFINITIONS = (
    {
        "key": "exports_root",
        "label": "Exports Root",
        "default_relative": "data/exports",
        "required_right": "developer:update_configuration",
        "description": "Base folder used for exported Excel workbooks.",
        "high_impact": False,
    },
    {
        "key": "forms_root",
        "label": "Forms Root",
        "default_relative": "data/forms",
        "required_right": "developer:update_configuration",
        "description": "Root for runtime form assets.",
        "high_impact": False,
    },
    {
        "key": "pending_root",
        "label": "Pending Drafts Root",
        "default_relative": "data/pending",
        "required_right": "developer:update_configuration",
        "description": "Storage root for pending drafts and history.",
        "high_impact": False,
    },
    {
        "key": "backups_root",
        "label": "Backups Root",
        "default_relative": "data/backups",
        "required_right": "developer:update_configuration",
        "description": "Root for runtime backup artifacts.",
        "high_impact": False,
    },
    {
        "key": "modules_root",
        "label": "External Modules Root",
        "default_relative": "data/modules",
        "required_right": "developer:external_module_overrides",
        "description": "External override location for managed Python modules.",
        "high_impact": True,
    },
    {
        "key": "security_root",
        "label": "Security Root",
        "default_relative": "data/security",
        "required_right": "developer:external_module_overrides",
        "description": "Storage root for vault files and persisted security settings.",
        "high_impact": True,
    },
)


class SettingsManagerModel:
    def __init__(self):
        self.data_registry = ExternalDataRegistry()
        self.settings_path = self.data_registry.resolve_write_path("settings")
        self.settings = {}
        self.valid_navigation_modules = []
        self.valid_persistent_modules = []
        self.saved_theme = DEFAULT_THEME
        self.preview_theme = DEFAULT_THEME
        self.last_settings_diagnostics = None
        self.load_settings()

    def normalize_module_names(self, raw_value, valid_modules=None):
        if isinstance(raw_value, str):
            candidates = [part.strip() for part in raw_value.split(",")]
        elif isinstance(raw_value, (list, tuple, set)):
            candidates = [str(part).strip() for part in raw_value]
        else:
            candidates = []

        valid_lookup = None
        if valid_modules:
            valid_lookup = {str(module_name).strip() for module_name in valid_modules if str(module_name).strip()}

        normalized = []
        for module_name in candidates:
            if not module_name or module_name in normalized:
                continue
            if valid_lookup is not None and module_name not in valid_lookup:
                continue
            normalized.append(module_name)
        return normalized

    def set_valid_modules(self, navigation_modules=None, persistent_modules=None):
        self.valid_navigation_modules = self.normalize_module_names(navigation_modules)
        self.valid_persistent_modules = self.normalize_module_names(persistent_modules)
        self.settings = self.normalize_settings(self.settings)
        return self.settings

    def build_default_settings(self):
        defaults = build_default_settings_payload()
        defaults["update_repository_url"] = DEFAULT_UPDATE_REPOSITORY_URL
        defaults.setdefault("path_overrides", {})
        defaults.setdefault("backup_policy", {})
        return defaults

    def normalize_backup_policy(self, raw_policy):
        policy = {
            "enabled": True,
            "interval_min": 30,
            "keep_count": 12,
            "draft_auto_save_interval_min": 5,
            "draft_history_keep_count": 20,
            "target_overrides": {},
        }
        if isinstance(raw_policy, dict):
            policy.update(raw_policy)

        try:
            policy["enabled"] = bool(policy.get("enabled", True))
        except Exception:
            policy["enabled"] = True

        try:
            policy["interval_min"] = max(1, int(policy.get("interval_min", 30)))
        except Exception:
            policy["interval_min"] = 30

        try:
            policy["keep_count"] = max(1, int(policy.get("keep_count", 12)))
        except Exception:
            policy["keep_count"] = 12

        try:
            policy["draft_auto_save_interval_min"] = max(1, int(policy.get("draft_auto_save_interval_min", 5)))
        except Exception:
            policy["draft_auto_save_interval_min"] = 5

        try:
            policy["draft_history_keep_count"] = max(1, int(policy.get("draft_history_keep_count", 20)))
        except Exception:
            policy["draft_history_keep_count"] = 20

        normalized_targets = {}
        raw_targets = policy.get("target_overrides")
        if isinstance(raw_targets, dict):
            for target_key, raw_target_policy in raw_targets.items():
                normalized_key = str(target_key or "").strip()
                if not normalized_key:
                    continue
                target_policy = {
                    "enabled": True,
                    "interval_min": policy["interval_min"],
                    "keep_count": policy["keep_count"],
                }
                if isinstance(raw_target_policy, dict):
                    target_policy.update(raw_target_policy)
                try:
                    target_policy["enabled"] = bool(target_policy.get("enabled", True))
                except Exception:
                    target_policy["enabled"] = True
                try:
                    target_policy["interval_min"] = max(1, int(target_policy.get("interval_min", policy["interval_min"])))
                except Exception:
                    target_policy["interval_min"] = policy["interval_min"]
                try:
                    target_policy["keep_count"] = max(1, int(target_policy.get("keep_count", policy["keep_count"])))
                except Exception:
                    target_policy["keep_count"] = policy["keep_count"]
                normalized_targets[normalized_key] = target_policy
        policy["target_overrides"] = normalized_targets
        return policy

    def _normalize_runtime_root_override(self, raw_value, default_relative):
        normalized_default = str(default_relative or "").strip().replace("\\", "/").lstrip("/")
        if raw_value is None:
            return ""
        normalized_value = str(raw_value or "").strip()
        if not normalized_value:
            return ""
        normalized_comp = normalized_value.replace("\\", "/").rstrip("/")
        if normalized_comp.lower() == normalized_default.lower():
            return ""
        return normalized_value

    def _resolve_runtime_root_path(self, override_value, default_relative):
        if str(override_value or "").strip():
            normalized_override = str(override_value).strip()
            return normalized_override if os.path.isabs(normalized_override) else os.path.abspath(normalized_override)
        return external_data_path(default_relative)

    def _default_export_directory_setting(self):
        return "data/exports"

    def load_settings(self):
        loaded = self.data_registry.load_json("settings", default_factory=self.build_default_settings)
        if not isinstance(loaded, dict):
            loaded = self.build_default_settings()
        diagnostics = diagnose_and_repair_settings(
            loaded,
            self.build_default_settings(),
            context="settings_manager_model.load_settings",
            valid_navigation_modules=self.valid_navigation_modules or None,
            valid_persistent_modules=self.valid_persistent_modules or None,
            drop_unknown_from_effective=True,
            keep_unknown_for_persist=False,
        )
        self.last_settings_diagnostics = diagnostics
        self.settings = self.normalize_settings(diagnostics.repaired_effective_payload)
        if diagnostics.repaired:
            diagnostics.repaired_effective_payload = dict(self.settings)
            diagnostics.repaired_persisted_payload.update(self.settings)
            persist_repaired_settings(diagnostics, self.settings_path, keep_count=12)
            write_settings_diagnostics_report(diagnostics, keep_count=30)
            log_settings_diagnostics_summary(diagnostics)
        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme
        return self.settings

    def get_last_diagnostics_warning(self, max_items=5):
        diagnostics = self.last_settings_diagnostics
        if diagnostics is None or not diagnostics.issues:
            return ""
        issue_lines = []
        for issue in diagnostics.issues[:max(1, int(max_items))]:
            issue_lines.append(f"- {issue.key}: {issue.message}")
        remainder = len(diagnostics.issues) - len(issue_lines)
        if remainder > 0:
            issue_lines.append(f"- ...and {remainder} more")
        report_note = f"\n\nDiagnostics report: {diagnostics.report_path}" if diagnostics.report_path else ""
        return (
            "Settings auto-repair detected invalid entries and corrected them.\n"
            + "\n".join(issue_lines)
            + report_note
        )

    def normalize_settings(self, payload):
        settings = self.build_default_settings()
        if isinstance(payload, dict):
            settings.update(payload)

        settings["path_overrides"] = self.normalize_path_overrides(
            settings.get("path_overrides", {}),
            export_directory=settings.get("export_directory", self._default_export_directory_setting()),
        )

        raw_module_whitelist = settings.get("module_whitelist", [])
        settings["module_whitelist"] = self.normalize_module_names(
            raw_module_whitelist,
            self.valid_navigation_modules or None,
        )

        raw_persistent_modules = settings.get("persistent_modules", [])
        settings["persistent_modules"] = self.normalize_module_names(
            raw_persistent_modules,
            self.valid_persistent_modules or None,
        )

        raw_codes = settings.get("downtime_codes")
        if not isinstance(raw_codes, dict):
            settings["downtime_codes"] = deepcopy(DEFAULT_DT_CODE_MAP)
        else:
            normalized_codes = deepcopy(DEFAULT_DT_CODE_MAP)
            for raw_code, raw_label in raw_codes.items():
                code = str(raw_code).strip()
                label = str(raw_label or "").strip()
                if code and label:
                    normalized_codes[code] = label
            settings["downtime_codes"] = normalized_codes

        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
        normalized_shell_backend = str(settings.get("ui_shell_backend", "pyqt6") or "pyqt6").strip().lower()
        if normalized_shell_backend not in {"tk", "pyqt6"}:
            normalized_shell_backend = "pyqt6"
        settings["ui_shell_backend"] = normalized_shell_backend
        settings["backup_policy"] = self.normalize_backup_policy(settings.get("backup_policy"))
        settings["enable_advanced_dev_updates"] = bool(settings.get("enable_advanced_dev_updates", False))
        settings["enable_screen_transitions"] = bool(settings.get("enable_screen_transitions", True))
        settings["enable_module_update_notifications"] = bool(settings.get("enable_module_update_notifications", True))
        settings["organize_exports_by_date"] = bool(settings.get("organize_exports_by_date", True))

        try:
            settings["screen_transition_duration_ms"] = max(0, min(500, int(settings.get("screen_transition_duration_ms", 360))))
        except Exception:
            settings["screen_transition_duration_ms"] = 360

        try:
            settings["toast_duration_sec"] = max(1, int(settings.get("toast_duration_sec", 5)))
        except Exception:
            settings["toast_duration_sec"] = 5

        try:
            settings["auto_save_interval_min"] = max(1, int(settings.get("auto_save_interval_min", 5)))
        except Exception:
            settings["auto_save_interval_min"] = 5

        try:
            settings["default_shift_hours"] = float(settings.get("default_shift_hours", 8.0))
        except Exception:
            settings["default_shift_hours"] = 8.0

        try:
            settings["default_goal_mph"] = float(settings.get("default_goal_mph", 240))
        except Exception:
            settings["default_goal_mph"] = 240.0

        settings["update_repository_url"] = str(settings.get("update_repository_url", DEFAULT_UPDATE_REPOSITORY_URL) or "").strip().strip("'\"")
        default_export_directory = self._default_export_directory_setting()
        export_override = settings.get("path_overrides", {}).get("exports_root")
        settings["export_directory"] = str(export_override or default_export_directory).strip() or default_export_directory
        return settings

    def get_path_override_definitions(self):
        return [dict(definition) for definition in PATH_OVERRIDE_DEFINITIONS]

    def normalize_path_overrides(self, raw_overrides=None, export_directory=None):
        raw_lookup = raw_overrides if isinstance(raw_overrides, dict) else {}
        normalized = {}
        for definition in PATH_OVERRIDE_DEFINITIONS:
            override_key = definition["key"]
            raw_value = raw_lookup.get(override_key)
            if raw_value in (None, "") and override_key == "exports_root":
                raw_value = export_directory
            normalized_value = self._normalize_runtime_root_override(raw_value, definition["default_relative"])
            if normalized_value:
                normalized[override_key] = normalized_value
        return normalized

    def _probe_directory_write_access(self, directory_path):
        os.makedirs(directory_path, exist_ok=True)
        probe_name = f".path-write-probe-{os.getpid()}-{time.time_ns()}.tmp"
        probe_path = os.path.join(directory_path, probe_name)
        with open(probe_path, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(probe_path)

    def validate_path_override_values(self, raw_overrides, export_directory=None):
        normalized = self.normalize_path_overrides(raw_overrides, export_directory=export_directory)
        validated = {}
        for definition in PATH_OVERRIDE_DEFINITIONS:
            override_key = definition["key"]
            if override_key not in normalized:
                continue
            effective_path = self._resolve_runtime_root_path(normalized[override_key], definition["default_relative"])
            if os.path.exists(effective_path) and not os.path.isdir(effective_path):
                raise ValueError(f"{definition['label']} must point to a directory, not a file.")
            try:
                self._probe_directory_write_access(effective_path)
            except OSError as exc:
                raise ValueError(f"{definition['label']} is not writable: {exc}") from exc
            validated[override_key] = normalized[override_key]
        return validated

    def apply_path_overrides(self, raw_overrides, export_directory=None):
        self.settings["path_overrides"] = self.validate_path_override_values(raw_overrides, export_directory=export_directory)
        self.settings["export_directory"] = str(
            self.settings["path_overrides"].get("exports_root") or export_directory or self._default_export_directory_setting()
        )
        return self.settings

    def get_runtime_path_state(self):
        overrides = dict(self.settings.get("path_overrides", {}))
        path_entries = []
        for definition in PATH_OVERRIDE_DEFINITIONS:
            override_key = definition["key"]
            override_value = overrides.get(override_key, "")
            effective_path = self._resolve_runtime_root_path(override_value, definition["default_relative"])
            default_path = self._resolve_runtime_root_path(None, definition["default_relative"])
            path_entries.append(
                {
                    **definition,
                    "override_value": override_value,
                    "effective_path": effective_path,
                    "default_path": default_path,
                    "is_overridden": bool(override_value),
                }
            )
        return {
            "settings_path": self.settings_path,
            "entries": path_entries,
        }

    def get_settings_copy(self):
        return deepcopy(self.settings)

    def build_settings_from_form(self, form_values):
        settings = self.get_settings_copy()
        if isinstance(form_values, dict):
            settings.update(form_values)

        numeric_fields = [
            "auto_save_interval_min",
            "default_shift_hours",
            "default_goal_mph",
            "toast_duration_sec",
            "screen_transition_duration_ms",
        ]
        for key in numeric_fields:
            value = settings.get(key)
            try:
                settings[key] = float(value) if isinstance(value, str) and "." in value else int(value)
            except Exception:
                continue

        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
        return self.normalize_settings(settings)

    def update_settings(self, new_settings):
        self.settings = self.normalize_settings(new_settings)
        return self.settings

    def update_downtime_codes(self, downtime_codes):
        self.settings["downtime_codes"] = self.normalize_settings({"downtime_codes": downtime_codes}).get("downtime_codes", deepcopy(DEFAULT_DT_CODE_MAP))
        return self.settings["downtime_codes"]

    def set_preview_theme(self, theme_name):
        self.preview_theme = normalize_theme(theme_name)
        return self.preview_theme

    def commit_theme(self):
        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme
        return self.saved_theme

    def revert_preview_theme(self):
        self.preview_theme = self.saved_theme
        return self.saved_theme

    def save_settings_with_backup(self):
        backup_info = self.data_registry.save_json("settings", self.settings, keep_count=12)
        self.commit_theme()
        return backup_info

    def validate_downtime_code_rows(self, rows):
        updated_codes = {}
        for row in rows or []:
            code = str((row or {}).get("code", "") or "").strip()
            label = str((row or {}).get("label", "") or "").strip()
            if not code and not label:
                continue
            if not code:
                raise ValueError("Each downtime code row needs a code identifier.")
            if not label:
                raise ValueError(f"Code '{code}' cannot have a blank label.")
            if code in updated_codes:
                raise ValueError(f"Code '{code}' is duplicated.")
            updated_codes[code] = label

        if not updated_codes:
            raise ValueError("At least one downtime code is required.")
        return updated_codes

    def get_next_downtime_code(self, rows):
        numeric_codes = []
        for row in rows or []:
            code = str((row or {}).get("code", "") or "").strip()
            if code.isdigit():
                numeric_codes.append(int(code))
        return str(max(numeric_codes, default=0) + 1)

    def build_external_module_editor_state(self, module_name, override_path=None, bundled_path=None, trust_enabled=False):
        if not module_name:
            return {
                "text": "",
                "status": "Choose a bundled module to inspect or override.",
                "source": "None",
            }

        if override_path and os.path.exists(override_path):
            with open(override_path, "r", encoding="utf-8") as handle:
                status = f"Editing external override: {override_path}"
                if not trust_enabled:
                    status = f"Editing external override: {override_path}. This file is currently inactive until an admin enables override trust."
                return {
                    "text": handle.read(),
                    "status": status,
                    "source": "External override",
                }

        if bundled_path and os.path.exists(bundled_path):
            with open(bundled_path, "r", encoding="utf-8") as handle:
                return {
                    "text": handle.read(),
                    "status": f"Editing bundled source preview for {module_name}. Saving will create an external override.",
                    "source": "Bundled module",
                }

        return {
            "text": "",
            "status": f"No bundled module source was found for {module_name}.",
            "source": "Unavailable",
        }