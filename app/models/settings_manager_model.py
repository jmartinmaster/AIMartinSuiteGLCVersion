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

from app.app_identity import DEFAULT_UPDATE_REPOSITORY_URL
from app.downtime_codes import DEFAULT_DT_CODE_MAP
from app.external_data_registry import ExternalDataRegistry
from app.theme_manager import DEFAULT_THEME, normalize_theme


class SettingsManagerModel:
    def __init__(self):
        self.data_registry = ExternalDataRegistry()
        self.settings_path = self.data_registry.resolve_write_path("settings")
        self.settings = {}
        self.valid_navigation_modules = []
        self.valid_persistent_modules = []
        self.saved_theme = DEFAULT_THEME
        self.preview_theme = DEFAULT_THEME
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
        return {
            "export_directory": "exports",
            "organize_exports_by_date": True,
            "default_export_prefix": "Disamatic Production Sheet",
            "update_repository_url": DEFAULT_UPDATE_REPOSITORY_URL,
            "enable_advanced_dev_updates": False,
            "theme": DEFAULT_THEME,
            "ui_shell_backend": "pyqt6",
            "enable_screen_transitions": True,
            "enable_module_update_notifications": True,
            "screen_transition_duration_ms": 360,
            "toast_duration_sec": 5,
            "auto_save_interval_min": 5,
            "default_shift_hours": 8.0,
            "default_goal_mph": 240,
            "downtime_codes": deepcopy(DEFAULT_DT_CODE_MAP),
            "module_whitelist": [],
            "persistent_modules": [],
        }

    def load_settings(self):
        loaded = self.data_registry.load_json("settings", default_factory=self.build_default_settings)
        if not isinstance(loaded, dict):
            loaded = self.build_default_settings()
        self.settings = self.normalize_settings(loaded)
        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme
        return self.settings

    def normalize_settings(self, payload):
        settings = self.build_default_settings()
        if isinstance(payload, dict):
            settings.update(payload)

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

        settings["update_repository_url"] = str(settings.get("update_repository_url", DEFAULT_UPDATE_REPOSITORY_URL) or "").strip()
        settings["export_directory"] = str(settings.get("export_directory", "exports") or "exports").strip() or "exports"
        settings["default_export_prefix"] = str(settings.get("default_export_prefix", "Disamatic Production Sheet") or "").strip() or "Disamatic Production Sheet"
        return settings

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
                raise ValueError("Each downtime code row needs a code number.")
            if not code.isdigit():
                raise ValueError(f"Code '{code}' must be numeric.")
            if not label:
                raise ValueError(f"Code {code} cannot be blank.")
            if code in updated_codes:
                raise ValueError(f"Code {code} is duplicated.")
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