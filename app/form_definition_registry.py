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
from copy import deepcopy

from app.external_data_registry import ExternalDataRegistry
from app.persistence import write_json_with_backup
from app.utils import ensure_external_directory, external_path, local_or_resource_path

__module_name__ = "Form Definition Registry"
__version__ = "1.0.2"

DEFAULT_FORM_ID = "temp_form_title"
DEFAULT_FORM_NAME = "Temp Form Title"
DEFAULT_FORM_DESCRIPTION = "Default form definition backed by layout_config.json"
LEGACY_DEFAULT_FORM_IDS = {"production_logging_center"}


class FormDefinitionRegistry:
    def __init__(self):
        self.data_registry = ExternalDataRegistry()
        self.registry_path = self.data_registry.resolve_write_path("form_definitions")
        self.forms_root_relative = os.path.join("data", "forms")
        self.forms_root = ensure_external_directory(self.forms_root_relative)
        self.registry_backup_dir = ensure_external_directory(os.path.join("data", "backups", "forms"))
        self.default_layout_relative_path = "layout_config.json"

    def _default_form_record(self):
        return {
            "id": DEFAULT_FORM_ID,
            "name": DEFAULT_FORM_NAME,
            "description": DEFAULT_FORM_DESCRIPTION,
            "layout_relative_path": self.default_layout_relative_path,
            "layout_path_mode": "local_or_resource",
            "built_in": True,
        }

    def _default_registry_payload(self):
        return {
            "schema_version": 1,
            "active_form_id": DEFAULT_FORM_ID,
            "forms": [self._default_form_record()],
        }

    def normalize_form_id(self, value):
        normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
        if not normalized:
            normalized = "form"
        if normalized[0].isdigit():
            normalized = f"form_{normalized}"
        return normalized[:64]

    def canonical_form_id(self, value):
        normalized = self.normalize_form_id(value)
        if normalized in LEGACY_DEFAULT_FORM_IDS:
            return DEFAULT_FORM_ID
        return normalized

    def _build_default_relative_path(self, form_id):
        return os.path.join("data", "forms", form_id, "layout.json").replace("\\", "/")

    def _build_default_calculations_relative_path(self, form_id):
        return os.path.join("data", "forms", form_id, "calculations.json").replace("\\", "/")

    def _build_calculation_backup_dir(self, form_id):
        return ensure_external_directory(os.path.join("data", "backups", "form_calculations", form_id))

    def _build_default_calculation_payload(self):
        try:
            from app.models.production_log_model import DEFAULT_CALCULATION_SETTINGS

            return deepcopy(DEFAULT_CALCULATION_SETTINGS)
        except Exception:
            return {}

    def _ensure_calculation_metadata(self, config, form_id):
        config_data = dict(config) if isinstance(config, dict) else {}
        calculations = config_data.get("calculations") if isinstance(config_data.get("calculations"), dict) else {}
        calculation_relative_path = self._build_default_calculations_relative_path(form_id)
        calculations["companion_relative_path"] = calculation_relative_path

        sections = config_data.get("sections") if isinstance(config_data.get("sections"), list) else []
        default_profiles = []
        seen_section_ids = set()
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_type = str(section.get("section_type") or "single").strip().lower()
            if section_type != "repeating":
                continue
            section_id = str(section.get("id") or "").strip().lower()
            if not section_id or section_id in seen_section_ids:
                continue
            behavior_profile = str(section.get("behavior_profile") or section_id).strip().lower()
            default_profiles.append(
                {
                    "section_id": section_id,
                    "requires_calculations": behavior_profile in {"production", "downtime"},
                    "calculation_profile": behavior_profile,
                }
            )
            seen_section_ids.add(section_id)

        raw_profiles = calculations.get("section_profiles") if isinstance(calculations.get("section_profiles"), list) else []
        normalized_profiles = []
        seen_profile_sections = set()
        for profile in raw_profiles:
            if not isinstance(profile, dict):
                continue
            section_id = str(profile.get("section_id") or "").strip().lower()
            if not section_id or section_id in seen_profile_sections:
                continue
            normalized_profiles.append(
                {
                    "section_id": section_id,
                    "requires_calculations": bool(profile.get("requires_calculations", True)),
                    "calculation_profile": str(profile.get("calculation_profile") or section_id).strip().lower(),
                }
            )
            seen_profile_sections.add(section_id)

        calculations["section_profiles"] = normalized_profiles or default_profiles
        config_data["calculations"] = calculations
        return config_data

    def _normalize_form_record(self, record, seen_ids):
        if not isinstance(record, dict):
            return None

        raw_form_id = str(record.get("id") or "").strip()
        proposed_id = raw_form_id or record.get("name")
        form_id = self.canonical_form_id(raw_form_id) if raw_form_id else self.normalize_form_id(proposed_id)
        if form_id in seen_ids:
            return None

        name = str(record.get("name") or form_id.replace("_", " ").title()).strip()
        description = str(record.get("description") or "").strip()
        built_in = bool(record.get("built_in"))
        layout_relative_path = str(record.get("layout_relative_path") or "").strip().replace("\\", "/")
        layout_path_mode = str(record.get("layout_path_mode") or "external").strip().lower()

        if form_id == DEFAULT_FORM_ID:
            built_in = True
            if not layout_relative_path:
                layout_relative_path = self.default_layout_relative_path
            if layout_path_mode != "local_or_resource":
                layout_path_mode = "local_or_resource"
        else:
            built_in = False
            if not layout_relative_path:
                layout_relative_path = self._build_default_relative_path(form_id)
            layout_path_mode = "external"

        return {
            "id": form_id,
            "name": name,
            "description": description,
            "layout_relative_path": layout_relative_path,
            "layout_path_mode": layout_path_mode,
            "built_in": built_in,
        }

    def _normalize_registry_payload(self, payload):
        candidate = dict(payload) if isinstance(payload, dict) else {}
        normalized_forms = []
        seen_ids = set()

        for record in candidate.get("forms", []):
            normalized_record = self._normalize_form_record(record, seen_ids)
            if normalized_record is None:
                continue
            normalized_forms.append(normalized_record)
            seen_ids.add(normalized_record["id"])

        if DEFAULT_FORM_ID not in seen_ids:
            normalized_forms.insert(0, self._default_form_record())
            seen_ids.add(DEFAULT_FORM_ID)

        active_form_id = self.canonical_form_id(candidate.get("active_form_id") or DEFAULT_FORM_ID)
        if active_form_id not in seen_ids:
            active_form_id = DEFAULT_FORM_ID

        return {
            "schema_version": 1,
            "active_form_id": active_form_id,
            "forms": normalized_forms,
        }

    def _read_registry_payload(self):
        registry_read_path = self.data_registry.resolve_read_path("form_definitions")
        if not os.path.exists(registry_read_path):
            return self._default_registry_payload()
        with open(registry_read_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_registry_payload(self, payload):
        return write_json_with_backup(
            self.registry_path,
            payload,
            backup_dir=self.registry_backup_dir,
            keep_count=12,
        )

    def get_registry(self):
        raw_payload = self._read_registry_payload()
        normalized_payload = self._normalize_registry_payload(raw_payload)
        if normalized_payload != raw_payload or not os.path.exists(self.registry_path):
            self._write_registry_payload(normalized_payload)
        return normalized_payload

    def resolve_load_path(self, form_record):
        if str(form_record.get("id") or DEFAULT_FORM_ID).strip() == DEFAULT_FORM_ID:
            return self.data_registry.resolve_read_path("layout_config")
        relative_path = form_record.get("layout_relative_path", self.default_layout_relative_path)
        if form_record.get("layout_path_mode") == "local_or_resource":
            return local_or_resource_path(relative_path)
        return external_path(relative_path)

    def resolve_save_path(self, form_record):
        if str(form_record.get("id") or DEFAULT_FORM_ID).strip() == DEFAULT_FORM_ID:
            return self.data_registry.resolve_write_path("layout_config")
        relative_path = form_record.get("layout_relative_path", self.default_layout_relative_path)
        return external_path(relative_path)

    def resolve_backup_dir(self, form_record):
        form_id = str(form_record.get("id") or DEFAULT_FORM_ID).strip() or DEFAULT_FORM_ID
        if form_id == DEFAULT_FORM_ID:
            return self.data_registry.resolve_backup_dir("layout_config")
        return ensure_external_directory(os.path.join("data", "backups", "layouts", form_id))

    def enrich_form_record(self, form_record, active_form_id=None):
        enriched = dict(form_record)
        enriched["load_path"] = self.resolve_load_path(form_record)
        enriched["save_path"] = self.resolve_save_path(form_record)
        enriched["backup_dir"] = self.resolve_backup_dir(form_record)
        enriched["is_active"] = enriched.get("id") == active_form_id
        return enriched

    def list_forms(self):
        registry = self.get_registry()
        active_form_id = registry.get("active_form_id")
        return [self.enrich_form_record(form_record, active_form_id=active_form_id) for form_record in registry.get("forms", [])]

    def get_form(self, form_id=None):
        registry = self.get_registry()
        requested_form_id = self.canonical_form_id(form_id or registry.get("active_form_id") or DEFAULT_FORM_ID)
        for form_record in registry.get("forms", []):
            if form_record.get("id") == requested_form_id:
                return self.enrich_form_record(form_record, active_form_id=registry.get("active_form_id"))
        raise ValueError(f"Form definition '{requested_form_id}' was not found.")

    def _get_form_record_index(self, registry, form_id):
        requested_form_id = self.canonical_form_id(form_id)
        for index, form_record in enumerate(registry.get("forms", [])):
            if form_record.get("id") == requested_form_id:
                return index, form_record
        raise ValueError(f"Form definition '{requested_form_id}' was not found.")

    def get_active_form(self):
        try:
            form_info = self.get_form(None)
            load_path = form_info.get("load_path")
            if not load_path:
                load_path = self.resolve_load_path(form_info)
            if os.path.exists(load_path):
                with open(load_path, "r", encoding="utf-8") as handle:
                    json.load(handle)
                return form_info
        except Exception:
            pass

        try:
            registry = self.get_registry()
            if registry.get("active_form_id") != DEFAULT_FORM_ID:
                registry["active_form_id"] = DEFAULT_FORM_ID
                self._write_registry_payload(registry)
        except Exception:
            pass
        return self.get_form(DEFAULT_FORM_ID)

    def load_form_config(self, form_id=None):
        form_info = self.get_form(form_id)
        load_path = form_info["load_path"]
        if not os.path.exists(load_path):
            raise FileNotFoundError(f"Form layout config was not found: {load_path}")
        with open(load_path, "r", encoding="utf-8") as handle:
            return json.load(handle), form_info, load_path

    def activate_form(self, form_id):
        registry = self.get_registry()
        requested_form_id = self.canonical_form_id(form_id)
        available_ids = {form_record.get("id") for form_record in registry.get("forms", [])}
        if requested_form_id not in available_ids:
            raise ValueError(f"Form definition '{requested_form_id}' was not found.")
        if registry.get("active_form_id") != requested_form_id:
            registry["active_form_id"] = requested_form_id
            self._write_registry_payload(registry)
        return self.get_form(requested_form_id)

    def rename_form(self, form_id, name, description=None):
        registry = self.get_registry()
        index, form_record = self._get_form_record_index(registry, form_id)
        if form_record.get("built_in"):
            raise ValueError("The built-in default form cannot be renamed.")

        form_name = str(name or "").strip()
        if not form_name:
            raise ValueError("Form name is required.")

        registry["forms"][index]["name"] = form_name
        if description is not None:
            registry["forms"][index]["description"] = str(description or "").strip()

        normalized_payload = self._normalize_registry_payload(registry)
        self._write_registry_payload(normalized_payload)
        return self.get_form(form_record.get("id"))

    def _build_unique_form_id(self, name):
        registry = self.get_registry()
        existing_ids = {form_record.get("id") for form_record in registry.get("forms", [])}
        base_id = self.normalize_form_id(name)
        if base_id not in existing_ids:
            return base_id

        index = 2
        while True:
            candidate_id = f"{base_id}_{index}"
            if candidate_id not in existing_ids:
                return candidate_id
            index += 1

    def create_form(self, name, config, description="", activate=False):
        form_name = str(name or "").strip()
        if not form_name:
            raise ValueError("Form name is required.")

        form_id = self._build_unique_form_id(form_name)
        relative_path = self._build_default_relative_path(form_id)
        save_path = external_path(relative_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        normalized_config = self._ensure_calculation_metadata(config, form_id)
        write_json_with_backup(
            save_path,
            normalized_config,
            backup_dir=ensure_external_directory(os.path.join("data", "backups", "layouts", form_id)),
            keep_count=12,
        )

        calculations_relative_path = self._build_default_calculations_relative_path(form_id)
        calculations_path = external_path(calculations_relative_path)
        os.makedirs(os.path.dirname(calculations_path), exist_ok=True)
        if not os.path.exists(calculations_path):
            write_json_with_backup(
                calculations_path,
                self._build_default_calculation_payload(),
                backup_dir=self._build_calculation_backup_dir(form_id),
                keep_count=12,
            )

        registry = self.get_registry()
        registry.setdefault("forms", []).append(
            {
                "id": form_id,
                "name": form_name,
                "description": str(description or "").strip(),
                "layout_relative_path": relative_path,
                "layout_path_mode": "external",
                "built_in": False,
            }
        )
        if activate:
            registry["active_form_id"] = form_id
        self._write_registry_payload(self._normalize_registry_payload(registry))
        return self.get_form(form_id)

    def duplicate_form(self, source_form_id, name, description=None, activate=False):
        source_form = self.get_form(source_form_id)
        config, _form_info, _source_path = self.load_form_config(source_form_id)
        if description is None:
            description = source_form.get("description", "")
        return self.create_form(name, config, description=description, activate=activate)

    def delete_form(self, form_id):
        registry = self.get_registry()
        index, form_record = self._get_form_record_index(registry, form_id)
        if form_record.get("built_in"):
            raise ValueError("The built-in default form cannot be deleted.")

        deleted_form = self.enrich_form_record(form_record, active_form_id=registry.get("active_form_id"))
        del registry["forms"][index]

        active_changed = registry.get("active_form_id") == deleted_form.get("id")
        if active_changed:
            registry["active_form_id"] = DEFAULT_FORM_ID

        normalized_payload = self._normalize_registry_payload(registry)
        self._write_registry_payload(normalized_payload)

        save_path = deleted_form.get("save_path")
        if save_path and os.path.exists(save_path):
            os.remove(save_path)

        calculation_path = external_path(self._build_default_calculations_relative_path(deleted_form.get("id") or ""))
        if calculation_path and os.path.exists(calculation_path):
            os.remove(calculation_path)

        layout_dir = os.path.dirname(str(save_path or ""))
        if layout_dir and os.path.isdir(layout_dir):
            try:
                if not os.listdir(layout_dir):
                    os.rmdir(layout_dir)
            except Exception:
                pass

        return {
            "deleted_form": deleted_form,
            "active_form": self.get_form(normalized_payload.get("active_form_id")),
            "active_changed": active_changed,
        }