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
import shutil
from dataclasses import dataclass

from app.persistence import write_json_with_backup
from app.utils import external_path, resource_path

__module_name__ = "External Data Registry"
__version__ = "1.0.0"

DATA_CONFIG_ROOT = os.path.join("data", "config")


@dataclass(frozen=True)
class ExternalDataSpec:
    key: str
    display_name: str
    external_relative_path: str
    backup_relative_path: str = None
    legacy_relative_paths: tuple = ()
    resource_relative_path: str = None
    allow_resource_fallback: bool = False
    include_in_recovery: bool = False
    recovery_kind: str = None
    include_in_update_payloads: bool = False
    update_fallback_name: str = None
    repo_relative_path: str = None
    notifies_active_form: bool = False


DEFAULT_EXTERNAL_DATA_SPECS = (
    ExternalDataSpec(
        key="settings",
        display_name="Settings",
        external_relative_path=os.path.join(DATA_CONFIG_ROOT, "settings.json"),
        backup_relative_path=os.path.join("data", "backups", "settings"),
        legacy_relative_paths=("settings.json",),
        include_in_recovery=True,
        recovery_kind="Settings Backup",
        repo_relative_path="settings.json",
    ),
    ExternalDataSpec(
        key="layout_config",
        display_name="Default Layout",
        external_relative_path=os.path.join(DATA_CONFIG_ROOT, "layout_config.json"),
        backup_relative_path=os.path.join("data", "backups", "layouts"),
        legacy_relative_paths=("layout_config.json",),
        resource_relative_path="layout_config.json",
        allow_resource_fallback=True,
        include_in_recovery=True,
        recovery_kind="Default Layout Backup",
        include_in_update_payloads=True,
        update_fallback_name="Production Logging Center Layout",
        repo_relative_path="layout_config.json",
        notifies_active_form=True,
    ),
    ExternalDataSpec(
        key="form_definitions",
        display_name="Form Definitions",
        external_relative_path=os.path.join(DATA_CONFIG_ROOT, "form_definitions.json"),
        backup_relative_path=os.path.join("data", "backups", "forms"),
        legacy_relative_paths=("form_definitions.json",),
        include_in_recovery=True,
        recovery_kind="Form Definitions Backup",
        include_in_update_payloads=True,
        update_fallback_name="Form Definitions",
        repo_relative_path="form_definitions.json",
        notifies_active_form=True,
    ),
    ExternalDataSpec(
        key="rates",
        display_name="Rates",
        external_relative_path=os.path.join(DATA_CONFIG_ROOT, "rates.json"),
        backup_relative_path=os.path.join("data", "backups", "rates"),
        legacy_relative_paths=("rates.json",),
        resource_relative_path="rates.json",
        allow_resource_fallback=True,
        include_in_recovery=True,
        recovery_kind="Rates Backup",
        include_in_update_payloads=True,
        update_fallback_name="Rates Config",
        repo_relative_path="rates.json",
    ),
    ExternalDataSpec(
        key="production_log_calculations",
        display_name="Production Log Calculations",
        external_relative_path=os.path.join(DATA_CONFIG_ROOT, "production_log_calculations.json"),
        backup_relative_path=os.path.join("data", "backups", "production_log_calculations"),
        legacy_relative_paths=("production_log_calculations.json",),
        resource_relative_path="production_log_calculations.json",
        allow_resource_fallback=True,
        include_in_recovery=True,
        recovery_kind="Production Log Calculations Backup",
        include_in_update_payloads=True,
        update_fallback_name="Production Log Calculations",
        repo_relative_path="production_log_calculations.json",
    ),
)


class ExternalDataRegistryError(RuntimeError):
    pass


class ExternalDataRegistry:
    def __init__(self, specs=None):
        self._specs = tuple(specs or DEFAULT_EXTERNAL_DATA_SPECS)
        self._spec_map = {spec.key: spec for spec in self._specs}

    def get_spec(self, key):
        if key not in self._spec_map:
            raise ExternalDataRegistryError(f"Unknown external data key '{key}'.")
        return self._spec_map[key]

    def list_specs(self):
        return list(self._specs)

    def resolve_write_path(self, key):
        return external_path(self.get_spec(key).external_relative_path)

    def resolve_backup_dir(self, key):
        backup_relative_path = self.get_spec(key).backup_relative_path
        if not backup_relative_path:
            return None
        return external_path(backup_relative_path)

    def resolve_resource_path(self, key):
        resource_relative_path = self.get_spec(key).resource_relative_path
        if not resource_relative_path:
            return None
        return resource_path(resource_relative_path)

    def resolve_legacy_paths(self, key):
        write_path = os.path.abspath(self.resolve_write_path(key))
        legacy_paths = []
        for relative_path in self.get_spec(key).legacy_relative_paths:
            candidate_path = os.path.abspath(external_path(relative_path))
            if candidate_path not in legacy_paths and candidate_path != write_path:
                legacy_paths.append(candidate_path)
        return legacy_paths

    def _migrate_adjacent_backup(self, source_path, target_path):
        source_backup_path = f"{source_path}.bak"
        target_backup_path = f"{target_path}.bak"
        if not os.path.exists(source_backup_path) or os.path.exists(target_backup_path):
            return
        try:
            os.makedirs(os.path.dirname(target_backup_path), exist_ok=True)
            os.replace(source_backup_path, target_backup_path)
        except OSError:
            return

    def _restore_from_legacy_backup(self, source_backup_path, target_path):
        if not os.path.exists(source_backup_path):
            return None
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_backup_path, target_path)
            return target_path
        except OSError:
            return None

    def migrate_legacy_file(self, key):
        write_path = self.resolve_write_path(key)
        if os.path.exists(write_path):
            return write_path

        for legacy_path in self.resolve_legacy_paths(key):
            restored_path = self._restore_from_legacy_backup(f"{legacy_path}.bak", write_path)
            if restored_path:
                return restored_path

            if not os.path.exists(legacy_path):
                continue
            try:
                os.makedirs(os.path.dirname(write_path), exist_ok=True)
                os.replace(legacy_path, write_path)
                self._migrate_adjacent_backup(legacy_path, write_path)
                return write_path
            except OSError:
                return legacy_path

        restored_path = self._restore_from_legacy_backup(f"{write_path}.bak", write_path)
        if restored_path:
            return restored_path
        return write_path

    def resolve_read_path(self, key, migrate_legacy=True):
        if migrate_legacy:
            migrated_path = self.migrate_legacy_file(key)
            if os.path.exists(migrated_path):
                return migrated_path

        write_path = self.resolve_write_path(key)
        if os.path.exists(write_path):
            return write_path

        for legacy_path in self.resolve_legacy_paths(key):
            if os.path.exists(legacy_path):
                return legacy_path

        spec = self.get_spec(key)
        resource_path_value = self.resolve_resource_path(key)
        if spec.allow_resource_fallback and resource_path_value and os.path.exists(resource_path_value):
            return resource_path_value
        return write_path if write_path else resource_path_value

    def load_json(self, key, default_factory=None):
        read_path = self.resolve_read_path(key)
        if not read_path or not os.path.exists(read_path):
            return default_factory() if callable(default_factory) else {}
        try:
            with open(read_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else (default_factory() if callable(default_factory) else {})
        except (OSError, json.JSONDecodeError):
            return default_factory() if callable(default_factory) else {}

    def save_json(self, key, payload, keep_count=12):
        self.migrate_legacy_file(key)
        return write_json_with_backup(
            self.resolve_write_path(key),
            payload,
            backup_dir=self.resolve_backup_dir(key),
            keep_count=keep_count,
        )

    def get_recovery_specs(self):
        return [spec for spec in self._specs if spec.include_in_recovery]

    def get_update_payload_specs(self):
        return [spec for spec in self._specs if spec.include_in_update_payloads]

    def build_update_payload_option(self, key, fallback_name=None):
        spec = self.get_spec(key)
        resolved_name = fallback_name or spec.update_fallback_name or spec.display_name
        return {
            "kind": "json",
            "key": spec.key,
            "relative_path": spec.repo_relative_path or spec.resource_relative_path or spec.external_relative_path.replace("\\", "/"),
            "local_target_path": self.resolve_write_path(key),
            "local_source_path": self.resolve_read_path(key),
            "fallback_name": resolved_name,
            "module_name": resolved_name,
            "backup_dir": self.resolve_backup_dir(key),
            "notifies_active_form": bool(spec.notifies_active_form),
        }

    def warm_cache(self):
        return {spec.key: self.resolve_read_path(spec.key) for spec in self._specs}