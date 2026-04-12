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
import threading
from dataclasses import dataclass, field

from app.app_platform import get_obsolete_local_executables
from app.theme_manager import DEFAULT_THEME, normalize_theme

__module_name__ = "Application Shell"
__version__ = "2.1.5"


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

    def ensure_external_modules_directory(self):
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
        if module_name not in managed_module_names:
            return None
        candidate = os.path.join(self.external_modules_path, f"{module_name}.py")
        return candidate if os.path.exists(candidate) else None

    def has_external_modules_directory(self):
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
        target_path = os.path.join(self.external_modules_path, f"{module_name}.py")
        self._write_text_file(target_path, module_text)
        return target_path

    def write_module_override_files(self, file_payloads, primary_relative_path=None):
        self.ensure_external_modules_directory()
        written_paths = []
        primary_path = None
        resolved_primary_relative_path = str(primary_relative_path or "").replace("\\", "/").lstrip("/")

        for relative_path, file_text in file_payloads.items():
            normalized_relative_path = str(relative_path).replace("\\", "/").lstrip("/")
            if normalized_relative_path.startswith("app/"):
                normalized_relative_path = normalized_relative_path[4:]
            target_path = os.path.join(self.external_modules_path, normalized_relative_path.replace("/", os.sep))
            self._write_text_file(target_path, file_text)
            written_paths.append(target_path)
            if normalized_relative_path == resolved_primary_relative_path.removeprefix("app/"):
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
        settings = {
            "theme": DEFAULT_THEME,
            "enable_screen_transitions": True,
            "screen_transition_duration_ms": 360,
            "toast_duration_sec": 5,
            "enable_module_update_notifications": True,
            "persistent_modules": [],
        }
        loaded = None
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass

        try:
            settings["toast_duration_sec"] = max(1, int(settings.get("toast_duration_sec", 5)))
        except Exception:
            settings["toast_duration_sec"] = 5

        settings["enable_screen_transitions"] = bool(settings.get("enable_screen_transitions", True))
        settings["enable_module_update_notifications"] = bool(settings.get("enable_module_update_notifications", True))
        try:
            settings["screen_transition_duration_ms"] = max(0, min(500, int(settings.get("screen_transition_duration_ms", 360))))
        except Exception:
            settings["screen_transition_duration_ms"] = 360

        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
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
