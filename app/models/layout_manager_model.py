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
import re
from copy import deepcopy

from app.layout_config_service import LayoutConfigService
from app.models.production_log_model import DEFAULT_DOWNTIME_ROW_FIELDS, DEFAULT_PRODUCTION_ROW_FIELDS
from app.production_log_roles import PROTECTED_HEADER_ROLES, PROTECTED_ROW_ROLES, REQUIRED_MAPPING_ROLES, get_default_row_field_id, normalize_role_name, normalize_row_section_name, resolve_header_field_role, resolve_row_field_role

VALID_IMPORT_TRANSFORMS = ("value", "code_lookup", "stop_from_duration")
VALID_EXPORT_TRANSFORMS = ("value", "code_number", "duration_minutes", "bool_int", "minutes_label")
DEFAULT_MAPPING_MAX_ROWS = 25
DEFAULT_SECTIONS = (
    {
        "id": "header",
        "name": "Header Fields",
        "description": "Single-record header fields",
        "fields_key": "header_fields",
        "section_type": "single",
        "behavior_profile": "header",
    },
    {
        "id": "production",
        "name": "Production Row Fields",
        "description": "Repeating production rows",
        "fields_key": "production_row_fields",
        "mapping_key": "production_mapping",
        "section_type": "repeating",
        "behavior_profile": "production",
        "default_max_rows": 50,
    },
    {
        "id": "downtime",
        "name": "Downtime Row Fields",
        "description": "Repeating downtime rows",
        "fields_key": "downtime_row_fields",
        "mapping_key": "downtime_mapping",
        "section_type": "repeating",
        "behavior_profile": "downtime",
        "default_max_rows": 25,
    },
)


class LayoutManagerModel:
    REQUIRED_TOP_LEVEL_KEYS = (
        "template_path",
        "header_fields",
        "production_row_fields",
        "downtime_row_fields",
        "production_mapping",
        "downtime_mapping",
    )
    EDITOR_TOP_LEVEL_KEYS = REQUIRED_TOP_LEVEL_KEYS + ("sections",)

    def __init__(self):
        self.service = LayoutConfigService()
        self.is_dirty = False
        self.current_source_path = self.service.config_path
        self.current_save_path = self.service.save_path
        self._default_config_template = None
        self.protected_field_ids = {"date", "cast_date", "shift", "hours", "goal_mph", "total_molds"}
        self.protected_header_roles = set(PROTECTED_HEADER_ROLES)
        self.row_field_sections = ("production_row_fields", "downtime_row_fields")
        self.protected_row_field_ids = {
            "production_row_fields": {"shop_order", "part_number", "rate_lookup", "rate_override_enabled", "molds", "time_calc"},
            "downtime_row_fields": {"start", "stop", "code", "cause", "time_calc"},
        }
        self.protected_row_roles = {section_name: set(PROTECTED_ROW_ROLES.get(section_name, set())) for section_name in self.row_field_sections}

    @property
    def local_config(self):
        return self.service.local_config

    @property
    def internal_config(self):
        return self.service.internal_config

    @property
    def config_path(self):
        return self.current_source_path

    @config_path.setter
    def config_path(self, value):
        self.current_source_path = value

    @property
    def save_path(self):
        return self.current_save_path

    def get_active_form_info(self):
        return self.service.get_active_form_info()

    def get_form_info(self, form_id):
        return self.service.get_form_info(form_id)

    def list_forms(self):
        return self.service.list_forms()

    def serialize_config(self, config):
        return json.dumps(config, indent=4)

    def parse_editor_text(self, text, base_config=None):
        config, _payload_details = self.resolve_editor_text(text, base_config=base_config)
        return config

    def _get_default_config_template(self):
        if self._default_config_template is None:
            try:
                default_config, _source_path = self.service.load_default()
            except Exception:
                default_config = {}
            normalized_default = dict(default_config) if isinstance(default_config, dict) else {}
            normalized_default["production_row_fields"] = self._merge_row_fields_with_defaults(
                normalized_default.get("production_row_fields"),
                DEFAULT_PRODUCTION_ROW_FIELDS,
            )
            normalized_default["downtime_row_fields"] = self._merge_row_fields_with_defaults(
                normalized_default.get("downtime_row_fields"),
                DEFAULT_DOWNTIME_ROW_FIELDS,
            )
            normalized_default.setdefault(
                "production_mapping",
                self._build_default_mapping("production_mapping", DEFAULT_PRODUCTION_ROW_FIELDS),
            )
            normalized_default.setdefault(
                "downtime_mapping",
                self._build_default_mapping("downtime_mapping", DEFAULT_DOWNTIME_ROW_FIELDS),
            )
            normalized_default.setdefault("header_fields", [])
            normalized_default["sections"] = self._normalize_sections(normalized_default)
            normalized_default.setdefault("template_path", "")
            self._default_config_template = normalized_default
        return deepcopy(self._default_config_template)

    def _normalize_sections(self, config):
        raw_sections = config.get("sections") if isinstance(config, dict) else None
        if not isinstance(raw_sections, list):
            raw_sections = []

        normalized_sections = []
        seen_ids = set()
        default_by_id = {section["id"]: deepcopy(section) for section in DEFAULT_SECTIONS}

        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                continue
            section_id = str(raw_section.get("id", "")).strip().lower()
            if not section_id or section_id in seen_ids:
                continue
            normalized_section = default_by_id.get(section_id, {"id": section_id})
            normalized_section["id"] = section_id
            normalized_section["name"] = str(raw_section.get("name", normalized_section.get("name", section_id.replace("_", " ").title()))).strip() or normalized_section.get("name", section_id)

            description_text = str(raw_section.get("description", normalized_section.get("description", ""))).strip()
            if description_text:
                normalized_section["description"] = description_text
            else:
                normalized_section.pop("description", None)

            fields_key = str(raw_section.get("fields_key", normalized_section.get("fields_key", ""))).strip()
            if section_id == "header":
                fields_key = "header_fields"
            elif section_id == "production":
                fields_key = "production_row_fields"
            elif section_id == "downtime":
                fields_key = "downtime_row_fields"
            if not fields_key:
                continue
            normalized_section["fields_key"] = fields_key

            mapping_key = str(raw_section.get("mapping_key", normalized_section.get("mapping_key", ""))).strip()
            if section_id == "production":
                mapping_key = "production_mapping"
            elif section_id == "downtime":
                mapping_key = "downtime_mapping"
            if mapping_key:
                normalized_section["mapping_key"] = mapping_key
            else:
                normalized_section.pop("mapping_key", None)

            section_type = str(raw_section.get("section_type", normalized_section.get("section_type", "single"))).strip().lower()
            normalized_section["section_type"] = section_type if section_type in {"single", "repeating"} else normalized_section.get("section_type", "single")

            behavior_profile = str(raw_section.get("behavior_profile", normalized_section.get("behavior_profile", section_id))).strip().lower()
            normalized_section["behavior_profile"] = behavior_profile or normalized_section.get("behavior_profile", section_id)

            if normalized_section["section_type"] == "repeating":
                default_max_rows = raw_section.get("default_max_rows", normalized_section.get("default_max_rows", DEFAULT_MAPPING_MAX_ROWS))
                try:
                    normalized_section["default_max_rows"] = max(1, int(default_max_rows or DEFAULT_MAPPING_MAX_ROWS))
                except (TypeError, ValueError):
                    normalized_section["default_max_rows"] = DEFAULT_MAPPING_MAX_ROWS
            else:
                normalized_section.pop("default_max_rows", None)

            normalized_sections.append(normalized_section)
            seen_ids.add(section_id)

        for default_section in DEFAULT_SECTIONS:
            section_id = default_section["id"]
            if section_id not in seen_ids:
                normalized_sections.append(deepcopy(default_section))

        return normalized_sections

    def get_sections(self, config=None):
        config_data = self.normalize_config(config) if isinstance(config, dict) else self._get_default_config_template()
        return [deepcopy(section) for section in config_data.get("sections", []) if isinstance(section, dict)]

    def get_section_info(self, section_id, config=None):
        normalized_section_id = str(section_id or "").strip().lower()
        for section in self.get_sections(config=config):
            if section.get("id") == normalized_section_id:
                return section
        return {}

    def get_section_name(self, section_id, config=None, fallback_name=None):
        section_info = self.get_section_info(section_id, config=config)
        if section_info:
            return section_info.get("name") or fallback_name or str(section_id or "").replace("_", " ").title()
        return fallback_name or str(section_id or "").replace("_", " ").title()

    def build_editor_guardrails(self, config=None):
        config_data = self.normalize_config(config) if isinstance(config, dict) else self._get_default_config_template()
        sections = [section for section in config_data.get("sections", []) if isinstance(section, dict)]
        profile_matches = {profile_name: [] for profile_name in ("header", "production", "downtime")}
        for section in sections:
            profile_name = normalize_role_name(section.get("behavior_profile"))
            if profile_name in profile_matches:
                profile_matches[profile_name].append(section)

        routed_sections = []
        warnings = []
        for profile_name, matches in profile_matches.items():
            if len(matches) == 1:
                section = matches[0]
                routed_sections.append(
                    {
                        "profile": profile_name,
                        "name": section.get("name") or section.get("id", profile_name).replace("_", " ").title(),
                        "section_type": section.get("section_type", "single"),
                        "fields_key": section.get("fields_key", ""),
                        "mapping_key": section.get("mapping_key", ""),
                    }
                )
                continue
            if not matches:
                warnings.append(f"No section currently routes the supported '{profile_name}' profile.")
                continue
            warnings.append(f"Multiple sections claim the supported '{profile_name}' profile. Keep supported profiles unique.")

        notes = [
            "Import and export only move fields that are both listed in the active section schema and enabled in the mapping or header toggle.",
            "Supported routing profiles are bounded to header, production, and downtime. Unsupported profiles fail closed.",
            "Stale mapping columns that no longer match the row schema are removed during normalization, and manual JSON edits still validate against the current field ids.",
        ]
        return {
            "routed_sections": routed_sections,
            "warnings": warnings,
            "notes": notes,
        }

    def update_section_metadata(self, config, section_id, section_values):
        normalized_section_id = str(section_id or "").strip().lower()
        if not normalized_section_id:
            raise ValueError("Section ID is missing.")

        config["sections"] = self._normalize_sections(config)
        target_section = None
        for section in config["sections"]:
            if section.get("id") == normalized_section_id:
                target_section = section
                break
        if target_section is None:
            raise ValueError(f"Section '{normalized_section_id}' was not found.")

        name_text = str(section_values.get("name", target_section.get("name", ""))).strip()
        if not name_text:
            raise ValueError("Section name cannot be empty.")
        target_section["name"] = name_text

        description_text = str(section_values.get("description", target_section.get("description", ""))).strip()
        if description_text:
            target_section["description"] = description_text
        else:
            target_section.pop("description", None)

        section_type = str(section_values.get("section_type", target_section.get("section_type", "single"))).strip().lower()
        if section_type not in {"single", "repeating"}:
            raise ValueError("Section type must be 'single' or 'repeating'.")
        target_section["section_type"] = section_type

        behavior_profile = str(section_values.get("behavior_profile", target_section.get("behavior_profile", normalized_section_id))).strip().lower()
        if not behavior_profile:
            raise ValueError("Behavior profile cannot be empty.")
        target_section["behavior_profile"] = behavior_profile

        return config, f"Updated section '{normalized_section_id}' metadata"

    def _get_mapping_section_name(self, mapping_name):
        if mapping_name == "production_mapping":
            return "production"
        if mapping_name == "downtime_mapping":
            return "downtime"
        return ""

    def _get_default_mapping_transform(self, mapping_name, field_id, direction, row_fields=None):
        section_name = self._get_mapping_section_name(mapping_name)
        role_name = ""
        for field in row_fields if isinstance(row_fields, list) else []:
            if not isinstance(field, dict):
                continue
            if str(field.get("id", "")).strip() == str(field_id or "").strip():
                role_name = resolve_row_field_role(section_name, field_id, field.get("role"))
                break
        if section_name == "downtime" and role_name == "downtime_code":
            return "code_number" if direction == "export" else "code_lookup"
        if section_name == "downtime" and role_name == "stop_clock":
            return "duration_minutes" if direction == "export" else "stop_from_duration"
        return "value"

    def _normalize_mapping_column_config(self, mapping_name, field_id, raw_value, row_fields=None):
        default_export_transform = self._get_default_mapping_transform(mapping_name, field_id, "export", row_fields=row_fields)
        default_import_transform = self._get_default_mapping_transform(mapping_name, field_id, "import", row_fields=row_fields)
        if isinstance(raw_value, dict):
            return {
                "column": str(raw_value.get("column", "")).strip(),
                "import_enabled": self._normalize_bool_value(raw_value.get("import_enabled"), default=True),
                "export_enabled": self._normalize_bool_value(raw_value.get("export_enabled"), default=True),
                "import_transform": str(raw_value.get("import_transform", default_import_transform) or default_import_transform).strip() or default_import_transform,
                "export_transform": str(raw_value.get("export_transform", default_export_transform) or default_export_transform).strip() or default_export_transform,
            }
        return {
            "column": str(raw_value or "").strip(),
            "import_enabled": True,
            "export_enabled": True,
            "import_transform": default_import_transform,
            "export_transform": default_export_transform,
        }

    def _build_default_mapping(self, mapping_name, row_fields):
        return {
            "start_row": 1,
            "max_rows": DEFAULT_MAPPING_MAX_ROWS,
            "columns": {
                field["id"]: self._normalize_mapping_column_config(mapping_name, field["id"], "", row_fields=row_fields)
                for field in row_fields
                if isinstance(field, dict) and field.get("id")
            },
        }

    def _normalize_header_fields(self, header_fields):
        if not isinstance(header_fields, list):
            return []

        normalized_fields = []
        for field in header_fields:
            if not isinstance(field, dict):
                continue
            normalized_field = deepcopy(field)
            normalized_field["import_enabled"] = self._normalize_bool_value(normalized_field.get("import_enabled"), default=True)
            normalized_field["export_enabled"] = self._normalize_bool_value(normalized_field.get("export_enabled"), default=True)
            normalized_fields.append(normalized_field)
        return normalized_fields

    def _merge_row_fields_with_defaults(self, row_fields, default_row_fields):
        if not isinstance(default_row_fields, list):
            return list(row_fields) if isinstance(row_fields, list) else []
        if not isinstance(row_fields, list):
            return deepcopy(default_row_fields)

        default_map = {}
        for default_field in default_row_fields:
            if isinstance(default_field, dict):
                field_id = str(default_field.get("id", "")).strip()
                if field_id:
                    default_map[field_id] = default_field

        merged_fields = []
        seen_ids = set()
        for field in row_fields:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("id", "")).strip()
            if not field_id or field_id in seen_ids:
                continue
            merged_field = deepcopy(default_map.get(field_id, {}))
            merged_field.update(field)
            merged_fields.append(merged_field)
            seen_ids.add(field_id)

        for default_field in default_row_fields:
            if not isinstance(default_field, dict):
                continue
            field_id = str(default_field.get("id", "")).strip()
            if field_id and field_id not in seen_ids:
                merged_fields.append(deepcopy(default_field))
        return merged_fields

    def _merge_mapping_with_defaults(self, mapping_name, mapping, default_mapping, row_fields=None):
        if not isinstance(default_mapping, dict):
            return dict(mapping) if isinstance(mapping, dict) else {}
        merged_mapping = deepcopy(default_mapping)
        if not isinstance(mapping, dict):
            return merged_mapping
        allowed_field_ids = {
            str(field.get("id", "")).strip()
            for field in row_fields if isinstance(row_fields, list) and isinstance(field, dict) and field.get("id")
        }
        default_columns = default_mapping.get("columns", {}) if isinstance(default_mapping.get("columns"), dict) else {}
        for key_name, value in mapping.items():
            if key_name == "columns" and isinstance(value, dict):
                for field_id, raw_column_value in value.items():
                    if allowed_field_ids and field_id not in allowed_field_ids:
                        continue
                    base_value = default_columns.get(field_id, "")
                    normalized_value = self._normalize_mapping_column_config(
                        mapping_name,
                        field_id,
                        raw_column_value if raw_column_value is not None else base_value,
                        row_fields=row_fields,
                    )
                    merged_mapping.setdefault("columns", {})[field_id] = normalized_value
            else:
                merged_mapping[key_name] = deepcopy(value)
        if isinstance(merged_mapping.get("columns"), dict):
            for field_id, raw_column_value in list(merged_mapping["columns"].items()):
                if allowed_field_ids and field_id not in allowed_field_ids:
                    merged_mapping["columns"].pop(field_id, None)
                    continue
                merged_mapping["columns"][field_id] = self._normalize_mapping_column_config(
                    mapping_name,
                    field_id,
                    raw_column_value,
                    row_fields=row_fields,
                )
        merged_mapping.setdefault("max_rows", DEFAULT_MAPPING_MAX_ROWS)
        return merged_mapping

    def normalize_config(self, config):
        normalized = dict(config) if isinstance(config, dict) else {}
        default_config = self._get_default_config_template()

        for key_name in self.REQUIRED_TOP_LEVEL_KEYS:
            if key_name not in normalized and key_name in default_config:
                normalized[key_name] = deepcopy(default_config[key_name])

        normalized["sections"] = self._normalize_sections(normalized)

        normalized["header_fields"] = self._normalize_header_fields(
            deepcopy(normalized.get("header_fields", default_config.get("header_fields", [])))
        )
        normalized["production_row_fields"] = self._merge_row_fields_with_defaults(
            normalized.get("production_row_fields"),
            default_config.get("production_row_fields", []),
        )
        normalized["downtime_row_fields"] = self._merge_row_fields_with_defaults(
            normalized.get("downtime_row_fields"),
            default_config.get("downtime_row_fields", []),
        )
        normalized["production_mapping"] = self._merge_mapping_with_defaults(
            "production_mapping",
            normalized.get("production_mapping"),
            default_config.get("production_mapping", {}),
            row_fields=normalized["production_row_fields"],
        )
        normalized["downtime_mapping"] = self._merge_mapping_with_defaults(
            "downtime_mapping",
            normalized.get("downtime_mapping"),
            default_config.get("downtime_mapping", {}),
            row_fields=normalized["downtime_row_fields"],
        )
        if "template_path" not in normalized and "template_path" in default_config:
            normalized["template_path"] = default_config.get("template_path")
        return normalized

    def resolve_editor_text(self, text, base_config=None):
        raw_text = str(text or "").strip()
        if not raw_text:
            raise ValueError("Editor is empty.")

        try:
            payload = json.loads(raw_text)
            extracted = False
        except json.JSONDecodeError as exc:
            payload = self._extract_partial_sections(raw_text)
            extracted = True
            if not payload:
                raise ValueError(f"Syntax error at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc

        normalized_payload, payload_details = self._normalize_editor_payload(payload)
        if payload_details["mode"] == "full":
            normalized_config = self.normalize_config(normalized_payload)
            self.validate_config(normalized_config)
            return normalized_config, payload_details

        if base_config is None:
            raise ValueError("Section payloads require a loaded layout before they can be merged.")

        merged_config = self.normalize_config(base_config)
        for section_name, section_value in normalized_payload.items():
            merged_config[section_name] = deepcopy(section_value)
        merged_config = self.normalize_config(merged_config)
        self.validate_config(merged_config)

        payload_details = dict(payload_details)
        payload_details["extracted"] = extracted
        return merged_config, payload_details

    def load_current_config(self):
        form_info = self.service.get_active_form_info()
        config, source_path = self.service.load_form(form_info=form_info)
        config = self.normalize_config(config)
        self.validate_config(config)
        self.current_source_path = source_path
        self.current_save_path = form_info.get("save_path", source_path)
        self.is_dirty = False
        return config, source_path, form_info

    def load_form_config(self, form_id):
        form_info = self.service.get_form_info(form_id)
        config, source_path = self.service.load_form(form_info=form_info)
        config = self.normalize_config(config)
        self.validate_config(config)
        self.current_source_path = source_path
        self.current_save_path = form_info.get("save_path", source_path)
        self.is_dirty = False
        return config, source_path, form_info

    def load_default_config(self):
        config, source_path = self.service.load_default()
        active_form_info = self.service.get_active_form_info()
        config = self.normalize_config(config)
        self.validate_config(config)
        self.current_source_path = source_path
        self.current_save_path = active_form_info.get("save_path", source_path)
        self.is_dirty = False
        return config, source_path, active_form_info

    def save_config(self, config, form_info=None):
        config = self.normalize_config(config)
        self.validate_config(config)
        resolved_form_info = dict(form_info) if isinstance(form_info, dict) else self.service.get_active_form_info()
        backup_info = self.service.save_config(config, form_info=resolved_form_info)
        self.current_source_path = resolved_form_info.get("save_path", self.current_source_path)
        self.current_save_path = resolved_form_info.get("save_path", self.current_save_path)
        self.is_dirty = False
        return backup_info

    def activate_form(self, form_id):
        form_info = self.service.activate_form(form_id)
        self.current_source_path = self.service.config_path
        self.current_save_path = self.service.save_path
        self.is_dirty = False
        return form_info

    def create_form_from_config(self, name, config, description="", activate=False):
        config = self.normalize_config(config)
        self.validate_config(config)
        form_info = self.service.create_form(name, config, description=description, activate=activate)
        self.current_source_path = self.service.config_path
        self.current_save_path = self.service.save_path
        self.is_dirty = False
        return form_info

    def rename_form(self, form_id, name, description=None):
        form_info = self.service.rename_form(form_id, name, description=description)
        self.current_source_path = self.service.config_path
        self.current_save_path = self.service.save_path
        return form_info

    def duplicate_form(self, source_form_id, name, description=None, activate=False):
        form_info = self.service.duplicate_form(source_form_id, name, description=description, activate=activate)
        self.current_source_path = self.service.config_path
        self.current_save_path = self.service.save_path
        self.is_dirty = False
        return form_info

    def delete_form(self, form_id):
        result = self.service.delete_form(form_id)
        self.current_source_path = self.service.config_path
        self.current_save_path = self.service.save_path
        self.is_dirty = False
        return result

    def mark_dirty(self):
        self.is_dirty = True

    def mark_clean(self):
        self.is_dirty = False

    def validate_config(self, config):
        if not isinstance(config, dict):
            raise ValueError("Config must be a JSON object.")

        required_top_level = list(self.REQUIRED_TOP_LEVEL_KEYS)
        missing_keys = [key for key in required_top_level if key not in config]
        if missing_keys:
            raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

        if "sections" in config and not isinstance(config.get("sections"), list):
            raise ValueError("sections must be a list.")

        seen_section_ids = set()
        seen_supported_profiles = {}
        for index, section in enumerate(config.get("sections", []), start=1):
            if not isinstance(section, dict):
                raise ValueError(f"sections item {index} must be an object.")
            missing_section_keys = [key for key in ("id", "name", "fields_key", "section_type", "behavior_profile") if key not in section]
            if missing_section_keys:
                raise ValueError(f"sections item {index} is missing: {', '.join(missing_section_keys)}")
            section_id = str(section.get("id", "")).strip().lower()
            if not section_id:
                raise ValueError(f"sections item {index} has an empty id.")
            if section_id in seen_section_ids:
                raise ValueError(f"sections contains duplicate id '{section_id}'.")
            seen_section_ids.add(section_id)
            section_type = str(section.get("section_type", "")).strip().lower()
            if section_type not in {"single", "repeating"}:
                raise ValueError(f"sections item {index} uses unsupported section_type '{section.get('section_type')}'.")
            behavior_profile = str(section.get("behavior_profile", "")).strip().lower()
            if not behavior_profile:
                raise ValueError(f"sections item {index} has an empty behavior_profile.")
            if behavior_profile in {"header", "production", "downtime"}:
                existing_section = seen_supported_profiles.get(behavior_profile)
                if existing_section is not None:
                    raise ValueError(
                        f"sections contains duplicate supported behavior_profile '{behavior_profile}' in '{existing_section}' and '{section_id}'."
                    )
                seen_supported_profiles[behavior_profile] = section_id

        if not isinstance(config["header_fields"], list):
            raise ValueError("header_fields must be a list.")

        seen_header_roles = set()
        for index, field in enumerate(config["header_fields"], start=1):
            if not isinstance(field, dict):
                raise ValueError(f"header_fields item {index} must be an object.")
            field_missing = [key for key in ("id", "label", "row", "col") if key not in field]
            if field_missing:
                raise ValueError(f"header_fields item {index} is missing: {', '.join(field_missing)}")
            field_id = str(field.get("id", "")).strip()
            role_name = resolve_header_field_role(field_id, field.get("role"))
            if role_name:
                if role_name in seen_header_roles:
                    raise ValueError(f"header_fields contains duplicate role '{role_name}'.")
                seen_header_roles.add(role_name)

        for section_name in self.row_field_sections:
            self.validate_row_fields(config.get(section_name), section_name)

        self.validate_mapping(
            config["production_mapping"],
            "production_mapping",
            self.get_required_mapping_field_ids(config.get("production_row_fields", []), "production_row_fields"),
            self.get_mapping_field_ids(config.get("production_row_fields", [])),
        )
        self.validate_mapping(
            config["downtime_mapping"],
            "downtime_mapping",
            self.get_required_mapping_field_ids(config.get("downtime_row_fields", []), "downtime_row_fields"),
            self.get_mapping_field_ids(config.get("downtime_row_fields", [])),
        )

    def get_mapping_field_ids(self, row_fields):
        field_ids = []
        for field in row_fields if isinstance(row_fields, list) else []:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("id", "")).strip()
            if field_id:
                field_ids.append(field_id)
        return field_ids

    def get_required_mapping_field_ids(self, row_fields, section_name):
        normalized_section = normalize_row_section_name(section_name)
        required_roles = REQUIRED_MAPPING_ROLES.get(normalized_section, ())
        role_to_field_id = {}
        for field in row_fields if isinstance(row_fields, list) else []:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("id", "")).strip()
            if not field_id:
                continue
            role_name = resolve_row_field_role(section_name, field_id, field.get("role"))
            if role_name and role_name not in role_to_field_id:
                role_to_field_id[role_name] = field_id

        required_field_ids = []
        missing_roles = []
        for role_name in required_roles:
            field_id = role_to_field_id.get(role_name)
            if field_id:
                required_field_ids.append(field_id)
            else:
                missing_roles.append(role_name)

        if missing_roles:
            missing_text = ", ".join(missing_roles)
            raise ValueError(f"{section_name} is missing required semantic roles: {missing_text}")
        return required_field_ids

    def validate_row_fields(self, row_fields, section_name):
        if not isinstance(row_fields, list):
            raise ValueError(f"{section_name} must be a list.")

        allowed_widgets = {"entry", "display", "checkbutton", "combobox"}
        seen_ids = set()
        seen_roles = set()
        for index, field in enumerate(row_fields, start=1):
            if not isinstance(field, dict):
                raise ValueError(f"{section_name} item {index} must be an object.")
            field_missing = [key for key in ("id", "label", "widget") if key not in field]
            if field_missing:
                raise ValueError(f"{section_name} item {index} is missing: {', '.join(field_missing)}")
            field_id = str(field.get("id", "")).strip()
            if not field_id:
                raise ValueError(f"{section_name} item {index} has an empty id.")
            if field_id in seen_ids:
                raise ValueError(f"{section_name} contains duplicate field id '{field_id}'.")
            seen_ids.add(field_id)
            widget_name = str(field.get("widget", "")).strip().lower()
            if widget_name not in allowed_widgets:
                raise ValueError(
                    f"{section_name} field '{field_id}' uses unsupported widget '{field.get('widget')}'."
                )
            raw_values = field.get("values")
            if raw_values is not None and not isinstance(raw_values, list):
                raise ValueError(f"{section_name} field '{field_id}' values must be a list.")
            role_name = resolve_row_field_role(section_name, field_id, field.get("role"))
            if role_name:
                if role_name in seen_roles:
                    raise ValueError(f"{section_name} contains duplicate role '{role_name}'.")
                seen_roles.add(role_name)

    def validate_mapping(self, mapping, mapping_name, required_columns, allowed_columns=None):
        if not isinstance(mapping, dict):
            raise ValueError(f"{mapping_name} must be an object.")
        if "start_row" not in mapping or "columns" not in mapping:
            raise ValueError(f"{mapping_name} must contain start_row and columns.")
        try:
            start_row = int(mapping.get("start_row", 0))
        except (TypeError, ValueError):
            raise ValueError(f"{mapping_name}.start_row must be an integer.")
        if start_row < 1:
            raise ValueError(f"{mapping_name}.start_row must be 1 or greater.")
        if "max_rows" in mapping:
            try:
                max_rows = int(mapping.get("max_rows", 0))
            except (TypeError, ValueError):
                raise ValueError(f"{mapping_name}.max_rows must be an integer.")
            if max_rows < 1:
                raise ValueError(f"{mapping_name}.max_rows must be 1 or greater.")
        if not isinstance(mapping["columns"], dict):
            raise ValueError(f"{mapping_name}.columns must be an object.")
        allowed_column_set = set(allowed_columns or required_columns)
        unknown_columns = [column_name for column_name in mapping["columns"] if column_name not in allowed_column_set]
        if unknown_columns:
            raise ValueError(f"{mapping_name}.columns contains unknown fields: {', '.join(sorted(unknown_columns))}")
        missing_columns = [column for column in required_columns if column not in mapping["columns"]]
        if missing_columns:
            raise ValueError(f"{mapping_name}.columns is missing: {', '.join(missing_columns)}")
        for field_id, column_config in mapping["columns"].items():
            if isinstance(column_config, dict):
                column_name = str(column_config.get("column", "")).strip()
                if not column_name:
                    raise ValueError(f"{mapping_name}.columns.{field_id} must include a column value.")
                import_transform = str(column_config.get("import_transform", "value") or "value").strip()
                export_transform = str(column_config.get("export_transform", "value") or "value").strip()
                if import_transform not in VALID_IMPORT_TRANSFORMS:
                    raise ValueError(
                        f"{mapping_name}.columns.{field_id} uses unsupported import_transform '{import_transform}'."
                    )
                if export_transform not in VALID_EXPORT_TRANSFORMS:
                    raise ValueError(
                        f"{mapping_name}.columns.{field_id} uses unsupported export_transform '{export_transform}'."
                    )
                continue
            if not str(column_config or "").strip():
                raise ValueError(f"{mapping_name}.columns.{field_id} cannot be empty.")

    def create_unique_field_id(self, config, section_name="header_fields"):
        existing_ids = {field.get("id") for field in config.get(section_name, [])}
        prefix_map = {
            "header_fields": "new_field",
            "production_row_fields": "new_production_field",
            "downtime_row_fields": "new_downtime_field",
        }
        prefix = prefix_map.get(section_name, "new_field")
        index = 1
        while True:
            field_id = f"{prefix}_{index}"
            if field_id not in existing_ids:
                return field_id
            index += 1

    def add_header_field(self, config):
        field_id = self.create_unique_field_id(config)
        next_row = max((int(field.get("row", 0)) for field in config.get("header_fields", [])), default=-1) + 1
        config.setdefault("header_fields", []).append(
            {
                "id": field_id,
                "label": field_id.replace("_", " ").title(),
                "row": next_row,
                "col": 0,
                "width": 10,
                "cell": "",
            }
        )
        return config, f"Added header field '{field_id}'"

    def add_row_field(self, config, section_name):
        section_title = section_name.replace("_", " ").replace(" fields", "").title()
        field_id = self.create_unique_field_id(config, section_name)
        config.setdefault(section_name, []).append(
            {
                "id": field_id,
                "label": field_id.replace("_", " ").title(),
                "widget": "entry",
                "width": 12,
                "open_row_trigger": True,
                "user_input": True,
            }
        )
        return config, f"Added {section_title} field '{field_id}'"

    def move_header_field(self, config, field_id, direction):
        fields = config.get("header_fields", [])
        current_index = next((index for index, field in enumerate(fields) if field.get("id") == field_id), None)
        if current_index is None:
            raise ValueError(f"Field '{field_id}' was not found.")
        target_index = current_index + direction
        if target_index < 0 or target_index >= len(fields):
            return config, None
        fields[current_index], fields[target_index] = fields[target_index], fields[current_index]
        return config, f"Reordered field '{field_id}'"

    def move_row_field(self, config, section_name, field_id, direction):
        fields = config.get(section_name, [])
        current_index = next((index for index, field in enumerate(fields) if field.get("id") == field_id), None)
        if current_index is None:
            raise ValueError(f"Field '{field_id}' was not found in {section_name}.")
        target_index = current_index + direction
        if target_index < 0 or target_index >= len(fields):
            return config, None
        fields[current_index], fields[target_index] = fields[target_index], fields[current_index]
        return config, f"Reordered field '{field_id}' in {section_name}"

    def remove_header_field(self, config, field_id):
        if field_id in self.protected_field_ids:
            raise ValueError(f"Field '{field_id}' is protected and cannot be removed.")
        fields = config.get("header_fields", [])
        updated_fields = [field for field in fields if field.get("id") != field_id]
        if len(updated_fields) == len(fields):
            raise ValueError(f"Field '{field_id}' was not found.")
        config["header_fields"] = updated_fields
        return config, f"Removed field '{field_id}'"

    def remove_row_field(self, config, section_name, field_id):
        field_role = ""
        for field in config.get(section_name, []):
            if field.get("id") == field_id:
                field_role = resolve_row_field_role(section_name, field_id, field.get("role"))
                break
        if field_id in self.protected_row_field_ids.get(section_name, set()) or field_role in self.protected_row_roles.get(section_name, set()):
            raise ValueError(f"Field '{field_id}' is protected and cannot be removed.")
        fields = config.get(section_name, [])
        updated_fields = [field for field in fields if field.get("id") != field_id]
        if len(updated_fields) == len(fields):
            raise ValueError(f"Field '{field_id}' was not found in {section_name}.")
        config[section_name] = updated_fields
        return config, f"Removed field '{field_id}' from {section_name}"

    def update_header_field(self, config, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value, role_value, import_enabled_value, export_enabled_value):
        if not field_id:
            raise ValueError("Field ID is missing.")
        row = int(str(row_value).strip())
        col = int(str(col_value).strip())
        width = int(str(width_value).strip())
        cell = str(cell_value).strip()
        default_text = str(default_value)
        target_field = None
        for field in config.get("header_fields", []):
            if field.get("id") == field_id:
                target_field = field
                break
        if target_field is None:
            raise ValueError(f"Field '{field_id}' was not found.")
        target_field["row"] = row
        target_field["col"] = col
        target_field["import_enabled"] = self._normalize_bool_value(import_enabled_value, default=True)
        target_field["export_enabled"] = self._normalize_bool_value(export_enabled_value, default=True)
        if field_id in self.protected_field_ids:
            target_field["role"] = resolve_header_field_role(field_id, target_field.get("role"))
        else:
            normalized_role = normalize_role_name(role_value)
            if normalized_role:
                target_field["role"] = normalized_role
            else:
                target_field.pop("role", None)
        if target_field.get("id") == "cast_date":
            target_field["readonly"] = True
            target_field.pop("default", None)
        elif readonly_value:
            target_field["width"] = width
            target_field["readonly"] = True
        else:
            target_field["width"] = width
            target_field.pop("readonly", None)
        if target_field.get("id") != "cast_date":
            if cell:
                target_field["cell"] = cell
            else:
                target_field.pop("cell", None)
            if default_text.strip():
                target_field["default"] = default_text
            else:
                target_field.pop("default", None)
        return config, f"Updated field '{field_id}'"

    def update_row_field(self, config, section_name, field_id, field_values):
        if not field_id:
            raise ValueError("Field ID is missing.")
        target_field = None
        for field in config.get(section_name, []):
            if field.get("id") == field_id:
                target_field = field
                break
        if target_field is None:
            raise ValueError(f"Field '{field_id}' was not found in {section_name}.")

        widget_name = str(field_values.get("widget", target_field.get("widget", "entry"))).strip().lower()
        if widget_name not in {"entry", "display", "checkbutton", "combobox"}:
            raise ValueError(f"Unsupported widget type '{widget_name}'.")

        label_text = str(field_values.get("label", target_field.get("label", field_id))).strip()
        if not label_text:
            raise ValueError("Label cannot be empty.")

        width_text = str(field_values.get("width", target_field.get("width", ""))).strip()
        width_value = int(width_text) if width_text else 0
        if width_value < 0:
            raise ValueError("Width cannot be negative.")

        target_field["label"] = label_text
        target_field["widget"] = widget_name
        if width_value > 0:
            target_field["width"] = width_value
        else:
            target_field.pop("width", None)

        normalized_role = resolve_row_field_role(section_name, field_id, field_values.get("role"))
        if field_id in self.protected_row_field_ids.get(section_name, set()) or normalized_role in self.protected_row_roles.get(section_name, set()):
            target_field["role"] = resolve_row_field_role(section_name, field_id, target_field.get("role"))
        else:
            explicit_role = normalize_role_name(field_values.get("role"))
            if explicit_role:
                target_field["role"] = explicit_role
            else:
                target_field.pop("role", None)

        self._set_bool_field(target_field, "readonly", field_values.get("readonly"), default=False)
        self._set_bool_field(target_field, "derived", field_values.get("derived"), default=False)
        self._set_bool_field(target_field, "math_trigger", field_values.get("math_trigger"), default=False)
        self._set_bool_field(target_field, "open_row_trigger", field_values.get("open_row_trigger"), default=False)
        self._set_bool_field(target_field, "user_input", field_values.get("user_input"), default=False)
        self._set_bool_field(target_field, "expand", field_values.get("expand"), default=False)
        self._set_bool_field(target_field, "bold", field_values.get("bold"), default=False)

        self._set_optional_text_field(target_field, "default", field_values.get("default"))
        self._set_optional_text_field(target_field, "sticky", field_values.get("sticky"))
        self._set_optional_text_field(target_field, "state", field_values.get("state"))
        self._set_optional_text_field(target_field, "options_source", field_values.get("options_source"))
        self._set_optional_text_field(target_field, "bootstyle", field_values.get("bootstyle"))
        if widget_name == "combobox":
            self._set_optional_list_field(target_field, "values", field_values.get("values", target_field.get("values")))
        else:
            target_field.pop("values", None)

        return config, f"Updated field '{field_id}' in {section_name}"

    def _normalize_bool_value(self, value, default=False):
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return bool(default)

    def _set_bool_field(self, target_field, key_name, value, default=False):
        if self._normalize_bool_value(value, default=default):
            target_field[key_name] = True
        else:
            target_field.pop(key_name, None)

    def _set_optional_text_field(self, target_field, key_name, value):
        text_value = str(value or "").strip()
        if text_value:
            target_field[key_name] = text_value
        else:
            target_field.pop(key_name, None)

    def _normalize_text_list(self, value):
        if isinstance(value, list):
            return [text for text in (str(item).strip() for item in value) if text]

        raw_text = str(value or "").strip()
        if not raw_text:
            return []

        try:
            parsed_value = json.loads(raw_text)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed_value = None

        if isinstance(parsed_value, list):
            return [text for text in (str(item).strip() for item in parsed_value) if text]

        return [text for text in (item.strip() for item in re.split(r"[,\n]+", raw_text)) if text]

    def _set_optional_list_field(self, target_field, key_name, value):
        normalized_values = self._normalize_text_list(value)
        if normalized_values:
            target_field[key_name] = normalized_values
        else:
            target_field.pop(key_name, None)

    def update_mapping(self, config, mapping_name, start_row_value, max_rows_value, column_values):
        start_row = int(str(start_row_value).strip())
        max_rows = int(str(max_rows_value).strip())
        mapping = config.get(mapping_name)
        if not isinstance(mapping, dict):
            raise ValueError(f"Mapping '{mapping_name}' was not found.")
        mapping["start_row"] = start_row
        mapping["max_rows"] = max_rows
        for key, value in column_values.items():
            if isinstance(value, dict):
                cleaned_value = str(value.get("column", "")).strip()
                if not cleaned_value:
                    raise ValueError(f"Column '{key}' cannot be empty.")
                import_transform = str(value.get("import_transform", "value") or "value").strip() or "value"
                export_transform = str(value.get("export_transform", "value") or "value").strip() or "value"
                if import_transform not in VALID_IMPORT_TRANSFORMS:
                    raise ValueError(f"Column '{key}' uses unsupported import transform '{import_transform}'.")
                if export_transform not in VALID_EXPORT_TRANSFORMS:
                    raise ValueError(f"Column '{key}' uses unsupported export transform '{export_transform}'.")
                mapping.setdefault("columns", {})[key] = {
                    "column": cleaned_value,
                    "import_enabled": self._normalize_bool_value(value.get("import_enabled"), default=True),
                    "export_enabled": self._normalize_bool_value(value.get("export_enabled"), default=True),
                    "import_transform": import_transform,
                    "export_transform": export_transform,
                }
                continue

            cleaned_value = str(value).strip()
            if not cleaned_value:
                raise ValueError(f"Column '{key}' cannot be empty.")
            mapping.setdefault("columns", {})[key] = cleaned_value
        return config, f"Updated mapping '{mapping_name}'"

    def update_template_path(self, config, template_path_value):
        config["template_path"] = str(template_path_value or "").strip()
        return config, "Updated export template path"

    def get_field_item_key(self, field_id):
        return f"field:{field_id}"

    def get_row_field_item_key(self, section_name, field_id):
        return f"row_field:{section_name}:{field_id}"

    def get_mapping_item_key(self, mapping_name):
        return f"mapping:{mapping_name}"

    def get_protected_row_field_lookup(self, config):
        protected_lookup = {}
        for section_name in self.row_field_sections:
            protected_ids = set(self.protected_row_field_ids.get(section_name, set()))
            for field in config.get(section_name, []) if isinstance(config.get(section_name), list) else []:
                if not isinstance(field, dict):
                    continue
                field_id = str(field.get("id", "")).strip()
                if not field_id:
                    continue
                role_name = resolve_row_field_role(section_name, field_id, field.get("role"))
                if role_name in self.protected_row_roles.get(section_name, set()):
                    protected_ids.add(field_id)
            protected_lookup[section_name] = protected_ids
        return protected_lookup

    def build_preview_grid(self, config):
        fields = config.get("header_fields", [])
        max_row = max((int(field.get("row", 0)) for field in fields), default=0)
        max_col = max((int(field.get("col", 0)) for field in fields), default=0)
        field_positions = {}

        for field in fields:
            row = int(field.get("row", 0))
            col = int(field.get("col", 0))
            preview_field = dict(field)
            preview_field["item_key"] = self.get_field_item_key(field.get("id", ""))
            field_positions.setdefault((row, col), []).append(preview_field)

        cells = []
        for row in range(max_row + 1):
            for col in range(max_col + 1):
                fields_here = field_positions.get((row, col), [])
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "fields": fields_here,
                        "item_keys": [field["item_key"] for field in fields_here if field.get("item_key")],
                    }
                )

        row_sections = []
        for section_name in self.row_field_sections:
            protected_ids = self.get_protected_row_field_lookup(config).get(section_name, set())
            preview_fields = []
            for field in config.get(section_name, []):
                preview_field = dict(field)
                preview_field["item_key"] = self.get_row_field_item_key(section_name, field.get("id", ""))
                preview_field["protected"] = str(field.get("id", "")).strip() in protected_ids
                preview_fields.append(preview_field)
            section_id = "production" if section_name == "production_row_fields" else "downtime"
            row_sections.append(
                {
                    "section_id": section_id,
                    "section_name": section_name,
                    "title": self.get_section_name(section_id, config=config, fallback_name=section_name),
                    "description": self.get_section_info(section_id, config=config).get("description", ""),
                    "fields": preview_fields,
                }
            )

        return {
            "field_count": len(fields),
            "max_row": max_row,
            "max_col": max_col,
            "cells": cells,
            "row_sections": row_sections,
        }

    def _normalize_editor_payload(self, payload):
        if isinstance(payload, dict):
            recognized_keys = [key for key in self.EDITOR_TOP_LEVEL_KEYS if key in payload]
            if all(key in payload for key in self.REQUIRED_TOP_LEVEL_KEYS):
                applied_sections = [key for key in self.EDITOR_TOP_LEVEL_KEYS if key in payload]
                return payload, {"mode": "full", "applied_sections": applied_sections}
            if recognized_keys:
                unknown_keys = [key for key in payload.keys() if key not in self.EDITOR_TOP_LEVEL_KEYS]
                if unknown_keys:
                    raise ValueError(
                        f"Unknown top-level keys for section editor: {', '.join(sorted(str(key) for key in unknown_keys))}"
                    )
                return {key: payload[key] for key in recognized_keys}, {"mode": "section", "applied_sections": recognized_keys}

            inferred_mapping_key = self._infer_mapping_key(payload)
            if inferred_mapping_key is not None:
                return {inferred_mapping_key: payload}, {"mode": "section", "applied_sections": [inferred_mapping_key]}

            raise ValueError(
                "JSON editor content must be a full layout config or a recognized top-level section payload."
            )

        if isinstance(payload, list):
            inferred_section = self._infer_list_section(payload)
            if inferred_section is None:
                raise ValueError(
                    "Could not infer which section this array belongs to. Wrap it in a key like header_fields or production_row_fields."
                )
            return {inferred_section: payload}, {"mode": "section", "applied_sections": [inferred_section]}

        if isinstance(payload, str):
            return {"template_path": payload}, {"mode": "section", "applied_sections": ["template_path"]}

        raise ValueError("JSON editor content must be an object, array, or template_path string.")

    def _infer_list_section(self, payload):
        if not payload:
            return None
        if not all(isinstance(item, dict) for item in payload):
            return None

        if any("row" in item or "col" in item or "cell" in item for item in payload):
            return "header_fields"

        if any("widget" in item or "open_row_trigger" in item or "options_source" in item for item in payload):
            return self._infer_row_field_section(payload)
        return None

    def _infer_row_field_section(self, payload):
        section_scores = {}
        for section_name in self.row_field_sections:
            score = 0
            protected_ids = self.protected_row_field_ids.get(section_name, set())
            protected_roles = self.protected_row_roles.get(section_name, set())
            required_roles = set(REQUIRED_MAPPING_ROLES.get(section_name, ()))
            for field in payload:
                field_id = str(field.get("id", "")).strip()
                role_name = resolve_row_field_role(section_name, field_id, field.get("role"))
                if field_id in protected_ids:
                    score += 3
                if role_name in protected_roles:
                    score += 2
                if role_name in required_roles:
                    score += 1
            section_scores[section_name] = score

        highest_score = max(section_scores.values(), default=0)
        if highest_score <= 0:
            return None
        matching_sections = [section_name for section_name, score in section_scores.items() if score == highest_score]
        if len(matching_sections) != 1:
            return None
        return matching_sections[0]

    def _infer_mapping_key(self, payload):
        if not isinstance(payload, dict):
            return None
        if "start_row" not in payload or "columns" not in payload or not isinstance(payload.get("columns"), dict):
            return None

        column_names = {str(column_name).strip() for column_name in payload.get("columns", {}).keys()}
        mapping_scores = {
            "production_mapping": len(column_names & self.protected_row_field_ids.get("production_row_fields", set())),
            "downtime_mapping": len(column_names & self.protected_row_field_ids.get("downtime_row_fields", set())),
        }
        highest_score = max(mapping_scores.values(), default=0)
        if highest_score <= 0:
            return None
        matching_mappings = [mapping_name for mapping_name, score in mapping_scores.items() if score == highest_score]
        if len(matching_mappings) != 1:
            return None
        return matching_mappings[0]

    def _extract_partial_sections(self, raw_text):
        extracted_sections = {}
        for section_name in self.REQUIRED_TOP_LEVEL_KEYS:
            extracted_value = self._extract_named_json_value(raw_text, section_name)
            if extracted_value is not None:
                extracted_sections[section_name] = extracted_value
        return extracted_sections

    def _extract_named_json_value(self, raw_text, key_name):
        pattern = re.compile(rf'"{re.escape(key_name)}"\s*:')
        decoder = json.JSONDecoder()
        for match in pattern.finditer(raw_text):
            value_index = match.end()
            while value_index < len(raw_text) and raw_text[value_index].isspace():
                value_index += 1
            try:
                value, _end_index = decoder.raw_decode(raw_text, idx=value_index)
            except json.JSONDecodeError:
                continue
            return value
        return None
