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
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from app.app_logging import log_error
from app.downtime_codes import DEFAULT_DT_CODE_MAP
from app.persistence import write_json_with_backup
from app.theme_manager import DEFAULT_THEME, normalize_theme
from app.utils import ensure_external_data_directory, external_data_path

__module_name__ = "Settings Diagnostics"
__version__ = "1.0.1"

DEFAULT_SETTINGS_PAYLOAD = {
    "export_directory": "data/exports",
    "path_overrides": {},
    "organize_exports_by_date": True,
    "default_export_prefix": "Disamatic Production Sheet",
    "update_repository_url": "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion",
    "enable_advanced_dev_updates": False,
    "theme": DEFAULT_THEME,
    "ui_shell_backend": "pyqt6",
    "enable_screen_transitions": True,
    "enable_module_update_notifications": True,
    "screen_transition_duration_ms": 360,
    "toast_duration_sec": 5,
    "auto_save_interval_min": 5,
    "default_shift_hours": 8.0,
    "default_goal_mph": 240.0,
    "downtime_codes": deepcopy(DEFAULT_DT_CODE_MAP),
    "module_whitelist": [],
    "persistent_modules": [],
    "backup_policy": {
        "enabled": True,
        "interval_min": 30,
        "keep_count": 12,
        "draft_auto_save_interval_min": 5,
        "draft_history_keep_count": 20,
        "target_overrides": {},
    },
}


def build_default_settings_payload():
    return deepcopy(DEFAULT_SETTINGS_PAYLOAD)


@dataclass
class SettingsIssue:
    section: str
    key: str
    issue_type: str
    message: str
    original_value: Any = None
    repaired_value: Any = None


@dataclass
class SettingsDiagnosticsResult:
    generated_at: str
    context: str
    issues: list[SettingsIssue] = field(default_factory=list)
    repaired_effective_payload: dict = field(default_factory=dict)
    repaired_persisted_payload: dict = field(default_factory=dict)
    unknown_keys: list[str] = field(default_factory=list)
    repaired: bool = False
    persisted_repairs: bool = False
    persisted_repairs_path: str | None = None
    persisted_repairs_backup_path: str | None = None
    report_path: str | None = None

    def to_dict(self):
        return {
            "generated_at": self.generated_at,
            "context": self.context,
            "issues": [asdict(issue) for issue in self.issues],
            "issue_count": len(self.issues),
            "unknown_keys": list(self.unknown_keys),
            "repaired": bool(self.repaired),
            "persisted_repairs": bool(self.persisted_repairs),
            "persisted_repairs_path": self.persisted_repairs_path,
            "persisted_repairs_backup_path": self.persisted_repairs_backup_path,
            "report_path": self.report_path,
        }


def _coerce_bool(value: Any, default: bool):
    if isinstance(value, bool):
        return value, False
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True, True
        if lowered in {"0", "false", "no", "off"}:
            return False, True
    if isinstance(value, (int, float)):
        return bool(value), True
    return bool(default), True


def _normalize_module_names(raw_value: Any, valid_modules: list[str] | None = None):
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


def diagnose_and_repair_settings(
    raw_payload: Any,
    defaults: dict,
    context: str,
    valid_navigation_modules: list[str] | None = None,
    valid_persistent_modules: list[str] | None = None,
    drop_unknown_from_effective: bool = True,
    keep_unknown_for_persist: bool = False,
):
    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    issues: list[SettingsIssue] = []
    payload_is_dict = isinstance(raw_payload, dict)
    source_payload = dict(raw_payload) if payload_is_dict else {}
    if not payload_is_dict:
        issues.append(
            SettingsIssue(
                section="root",
                key="settings",
                issue_type="invalid_payload",
                message="Settings payload was not an object. Defaults were applied.",
                original_value=type(raw_payload).__name__,
                repaired_value="dict",
            )
        )

    defaults = dict(defaults or {})
    known_keys = set(defaults)
    unknown_keys = sorted([key for key in source_payload if key not in known_keys])
    for unknown_key in unknown_keys:
        issues.append(
            SettingsIssue(
                section="root",
                key=str(unknown_key),
                issue_type="unknown_key",
                message="Unknown key was excluded from effective runtime settings.",
                original_value=source_payload.get(unknown_key),
                repaired_value=None,
            )
        )

    missing_required_keys = sorted([key for key in known_keys if key not in source_payload])
    for missing_key in missing_required_keys:
        issues.append(
            SettingsIssue(
                section="root",
                key=str(missing_key),
                issue_type="missing_required_key",
                message="Required key was missing and default fallback was applied.",
                original_value=None,
                repaired_value=deepcopy(defaults.get(missing_key)),
            )
        )

    effective = deepcopy(defaults)
    for key in known_keys:
        if key in source_payload:
            effective[key] = source_payload[key]

    def _record_repair(section: str, key: str, issue_type: str, message: str, original: Any, repaired: Any):
        issues.append(
            SettingsIssue(
                section=section,
                key=key,
                issue_type=issue_type,
                message=message,
                original_value=original,
                repaired_value=repaired,
            )
        )

    original_theme = effective.get("theme", DEFAULT_THEME)
    normalized_theme = normalize_theme(original_theme)
    if normalized_theme != original_theme:
        _record_repair(
            "appearance",
            "theme",
            "normalized",
            "Theme value was normalized to a supported preset.",
            original_theme,
            normalized_theme,
        )
    effective["theme"] = normalized_theme

    original_backend = str(effective.get("ui_shell_backend", "pyqt6") or "pyqt6").strip().lower()
    if original_backend not in {"tk", "pyqt6"}:
        _record_repair(
            "runtime",
            "ui_shell_backend",
            "invalid_choice",
            "Unsupported UI shell backend was replaced with 'pyqt6'.",
            original_backend,
            "pyqt6",
        )
        original_backend = "pyqt6"
    effective["ui_shell_backend"] = original_backend

    for key in ("enable_advanced_dev_updates", "enable_screen_transitions", "enable_module_update_notifications", "organize_exports_by_date"):
        original_value = effective.get(key, defaults.get(key, False))
        coerced_value, changed = _coerce_bool(original_value, bool(defaults.get(key, False)))
        if changed:
            _record_repair(
                "flags",
                key,
                "coerced_bool",
                "Boolean-like value was normalized.",
                original_value,
                coerced_value,
            )
        effective[key] = coerced_value

    numeric_specs = {
        "screen_transition_duration_ms": (int, 360, 0, 500),
        "toast_duration_sec": (int, 5, 1, None),
        "auto_save_interval_min": (int, 5, 1, None),
        "default_shift_hours": (float, 8.0, None, None),
        "default_goal_mph": (float, 240.0, None, None),
    }
    for key, (caster, fallback, minimum, maximum) in numeric_specs.items():
        if key not in defaults and key not in source_payload:
            continue
        original_value = effective.get(key, fallback)
        try:
            normalized_value = caster(original_value)
        except Exception:
            normalized_value = fallback
            _record_repair(
                "numeric",
                key,
                "type_error",
                "Numeric value was invalid and reset to default.",
                original_value,
                normalized_value,
            )
        if minimum is not None and normalized_value < minimum:
            _record_repair(
                "numeric",
                key,
                "below_min",
                "Numeric value was below minimum and clamped.",
                normalized_value,
                minimum,
            )
            normalized_value = minimum
        if maximum is not None and normalized_value > maximum:
            _record_repair(
                "numeric",
                key,
                "above_max",
                "Numeric value was above maximum and clamped.",
                normalized_value,
                maximum,
            )
            normalized_value = maximum
        effective[key] = normalized_value

    for key, fallback_value in {
        "update_repository_url": defaults.get("update_repository_url", ""),
        "export_directory": defaults.get("export_directory", "data/exports"),
        "default_export_prefix": defaults.get("default_export_prefix", "Disamatic Production Sheet"),
    }.items():
        original_value = effective.get(key, fallback_value)
        normalized_value = str(original_value or "").strip() or str(fallback_value)
        if normalized_value != original_value:
            _record_repair(
                "text",
                key,
                "normalized_text",
                "Text value was normalized.",
                original_value,
                normalized_value,
            )
        effective[key] = normalized_value

    raw_path_overrides = effective.get("path_overrides", {})
    normalized_path_overrides = {}
    if isinstance(raw_path_overrides, dict):
        for raw_key, raw_value in raw_path_overrides.items():
            key_text = str(raw_key or "").strip()
            value_text = str(raw_value or "").strip()
            if key_text and value_text:
                normalized_path_overrides[key_text] = value_text
            else:
                _record_repair(
                    "runtime_paths",
                    "path_overrides",
                    "invalid_entry",
                    "Runtime path override entry with blank key/value was ignored.",
                    {"key": raw_key, "value": raw_value},
                    None,
                )
    else:
        _record_repair(
            "runtime_paths",
            "path_overrides",
            "type_error",
            "Runtime path overrides value was not an object and was reset.",
            raw_path_overrides,
            {},
        )
    if normalized_path_overrides != raw_path_overrides:
        _record_repair(
            "runtime_paths",
            "path_overrides",
            "normalized_map",
            "Runtime path overrides were normalized to valid key/value pairs.",
            raw_path_overrides,
            normalized_path_overrides,
        )
    effective["path_overrides"] = normalized_path_overrides

    if "module_whitelist" in defaults or "module_whitelist" in source_payload:
        raw_modules = effective.get("module_whitelist", [])
        normalized_modules = _normalize_module_names(raw_modules, valid_modules=valid_navigation_modules)
        if normalized_modules != raw_modules:
            _record_repair(
                "modules",
                "module_whitelist",
                "normalized_list",
                "Module whitelist entries were normalized against known modules.",
                raw_modules,
                normalized_modules,
            )
        effective["module_whitelist"] = normalized_modules

    if "persistent_modules" in defaults or "persistent_modules" in source_payload:
        raw_modules = effective.get("persistent_modules", [])
        normalized_modules = _normalize_module_names(raw_modules, valid_modules=valid_persistent_modules)
        if normalized_modules != raw_modules:
            _record_repair(
                "modules",
                "persistent_modules",
                "normalized_list",
                "Persistent module entries were normalized against known modules.",
                raw_modules,
                normalized_modules,
            )
        effective["persistent_modules"] = normalized_modules

    if "downtime_codes" in defaults or "downtime_codes" in source_payload:
        original_codes = effective.get("downtime_codes")
        normalized_codes = deepcopy(DEFAULT_DT_CODE_MAP)
        if isinstance(original_codes, dict):
            for raw_code, raw_label in original_codes.items():
                code_text = str(raw_code).strip()
                label_text = str(raw_label or "").strip()
                if code_text and label_text:
                    normalized_codes[code_text] = label_text
                else:
                    _record_repair(
                        "downtime_codes",
                        "downtime_codes",
                        "invalid_entry",
                        "Downtime code entry was empty and ignored.",
                        {"code": raw_code, "label": raw_label},
                        None,
                    )
        else:
            _record_repair(
                "downtime_codes",
                "downtime_codes",
                "type_error",
                "Downtime codes payload was not an object and was reset to defaults.",
                original_codes,
                normalized_codes,
            )
        if normalized_codes != original_codes:
            _record_repair(
                "downtime_codes",
                "downtime_codes",
                "normalized_map",
                "Downtime codes were normalized to valid key/value pairs.",
                original_codes,
                normalized_codes,
            )
        effective["downtime_codes"] = normalized_codes

    if drop_unknown_from_effective:
        effective = {key: effective.get(key, defaults.get(key)) for key in defaults}

    if keep_unknown_for_persist and payload_is_dict:
        persisted = dict(source_payload)
        for key in defaults:
            persisted[key] = deepcopy(effective.get(key, defaults.get(key)))
    else:
        persisted = deepcopy(effective)

    repaired = bool(issues)
    return SettingsDiagnosticsResult(
        generated_at=now_iso,
        context=str(context or "settings"),
        issues=issues,
        repaired_effective_payload=effective,
        repaired_persisted_payload=persisted,
        unknown_keys=unknown_keys,
        repaired=repaired,
    )


def persist_repaired_settings(result: SettingsDiagnosticsResult, settings_path: str, keep_count: int = 12):
    if not isinstance(result, SettingsDiagnosticsResult):
        return result
    backup_info = write_json_with_backup(
        settings_path,
        result.repaired_persisted_payload,
        backup_dir=external_data_path("backups/settings"),
        keep_count=keep_count,
    )
    result.persisted_repairs = True
    result.persisted_repairs_path = str(backup_info.get("target_path") or settings_path)
    result.persisted_repairs_backup_path = str(backup_info.get("versioned_backup_path") or "") or None
    return result


def write_settings_diagnostics_report(result: SettingsDiagnosticsResult, keep_count: int = 30):
    if not isinstance(result, SettingsDiagnosticsResult):
        return None
    diagnostics_dir = ensure_external_data_directory("backups/settings/diagnostics")
    report_target = external_data_path("backups/settings/diagnostics/settings_diagnostics_report.json")
    result.report_path = report_target
    report_payload = result.to_dict()
    report_payload["effective_payload_preview_keys"] = sorted(list(result.repaired_effective_payload.keys()))
    report_payload["persisted_payload_preview_keys"] = sorted(list(result.repaired_persisted_payload.keys()))
    backup_info = write_json_with_backup(
        report_target,
        report_payload,
        backup_dir=diagnostics_dir,
        keep_count=keep_count,
    )
    report_path = str(backup_info.get("versioned_backup_path") or backup_info.get("target_path") or report_target)
    result.report_path = report_path
    return report_path


def log_settings_diagnostics_summary(result: SettingsDiagnosticsResult):
    if not isinstance(result, SettingsDiagnosticsResult):
        return
    if not result.issues:
        return
    log_error(
        "settings.diagnostics",
        f"{result.context}: {len(result.issues)} issue(s) detected; report={result.report_path or 'pending'}",
    )
