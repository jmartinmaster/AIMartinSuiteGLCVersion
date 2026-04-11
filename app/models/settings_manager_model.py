from copy import deepcopy
import json
import os

from app.app_identity import DEFAULT_UPDATE_REPOSITORY_URL
from app.downtime_codes import DEFAULT_DT_CODE_MAP
from app.theme_manager import DEFAULT_THEME, normalize_theme
from app.utils import external_path


class SettingsManagerModel:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.settings_path = external_path("settings.json")
        self.settings = {}
        self.saved_theme = DEFAULT_THEME
        self.preview_theme = DEFAULT_THEME
        self.load_settings()

    def build_default_settings(self):
        return {
            "export_directory": "exports",
            "organize_exports_by_date": True,
            "default_export_prefix": "Disamatic Production Sheet",
            "update_repository_url": DEFAULT_UPDATE_REPOSITORY_URL,
            "enable_advanced_dev_updates": False,
            "theme": DEFAULT_THEME,
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
        loaded = self.build_default_settings()
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    loaded.update(payload)
            except Exception:
                pass
        self.settings = self.normalize_settings(loaded)
        self.saved_theme = self.settings["theme"]
        self.preview_theme = self.saved_theme
        return self.settings

    def normalize_settings(self, payload):
        settings = self.build_default_settings()
        if isinstance(payload, dict):
            settings.update(payload)

        raw_module_whitelist = settings.get("module_whitelist", [])
        settings["module_whitelist"] = self.dispatcher.normalize_module_whitelist(raw_module_whitelist)

        raw_persistent_modules = settings.get("persistent_modules", [])
        settings["persistent_modules"] = self.dispatcher.normalize_persistent_modules(raw_persistent_modules)

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