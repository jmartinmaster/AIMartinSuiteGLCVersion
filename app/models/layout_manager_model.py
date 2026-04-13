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
from app.production_log_roles import PROTECTED_HEADER_ROLES, PROTECTED_ROW_ROLES, REQUIRED_MAPPING_ROLES, get_default_row_field_id, normalize_role_name, normalize_row_section_name, resolve_header_field_role, resolve_row_field_role


class LayoutManagerModel:
    REQUIRED_TOP_LEVEL_KEYS = (
        "template_path",
        "header_fields",
        "production_row_fields",
        "downtime_row_fields",
        "production_mapping",
        "downtime_mapping",
    )

    def __init__(self):
        self.service = LayoutConfigService()
        self.is_dirty = False
        self.current_source_path = self.service.config_path
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
        return self.service.save_path

    def get_active_form_info(self):
        return self.service.get_active_form_info()

    def list_forms(self):
        return self.service.list_forms()

    def serialize_config(self, config):
        return json.dumps(config, indent=4)

    def parse_editor_text(self, text, base_config=None):
        config, _payload_details = self.resolve_editor_text(text, base_config=base_config)
        return config

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
            self.validate_config(normalized_payload)
            return normalized_payload, payload_details

        if base_config is None:
            raise ValueError("Section payloads require a loaded layout before they can be merged.")

        merged_config = deepcopy(base_config)
        for section_name, section_value in normalized_payload.items():
            merged_config[section_name] = deepcopy(section_value)
        self.validate_config(merged_config)

        payload_details = dict(payload_details)
        payload_details["extracted"] = extracted
        return merged_config, payload_details

    def load_current_config(self):
        config, source_path = self.service.load_current()
        self.validate_config(config)
        self.current_source_path = source_path
        self.is_dirty = False
        return config, source_path

    def load_default_config(self):
        config, source_path = self.service.load_default()
        self.validate_config(config)
        self.current_source_path = source_path
        self.is_dirty = False
        return config, source_path

    def save_config(self, config):
        self.validate_config(config)
        backup_info = self.service.save_config(config)
        self.current_source_path = self.service.save_path
        self.is_dirty = False
        return backup_info

    def activate_form(self, form_id):
        form_info = self.service.activate_form(form_id)
        self.current_source_path = self.service.config_path
        self.is_dirty = False
        return form_info

    def create_form_from_config(self, name, config, description="", activate=False):
        self.validate_config(config)
        form_info = self.service.create_form(name, config, description=description, activate=activate)
        self.current_source_path = self.service.config_path
        self.is_dirty = False
        return form_info

    def rename_form(self, form_id, name, description=None):
        form_info = self.service.rename_form(form_id, name, description=description)
        self.current_source_path = self.service.config_path
        return form_info

    def duplicate_form(self, source_form_id, name, description=None, activate=False):
        form_info = self.service.duplicate_form(source_form_id, name, description=description, activate=activate)
        self.current_source_path = self.service.config_path
        self.is_dirty = False
        return form_info

    def delete_form(self, form_id):
        result = self.service.delete_form(form_id)
        self.current_source_path = self.service.config_path
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
        )
        self.validate_mapping(
            config["downtime_mapping"],
            "downtime_mapping",
            self.get_required_mapping_field_ids(config.get("downtime_row_fields", []), "downtime_row_fields"),
        )

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
            role_name = resolve_row_field_role(section_name, field_id, field.get("role"))
            if role_name:
                if role_name in seen_roles:
                    raise ValueError(f"{section_name} contains duplicate role '{role_name}'.")
                seen_roles.add(role_name)

    def validate_mapping(self, mapping, mapping_name, required_columns):
        if not isinstance(mapping, dict):
            raise ValueError(f"{mapping_name} must be an object.")
        if "start_row" not in mapping or "columns" not in mapping:
            raise ValueError(f"{mapping_name} must contain start_row and columns.")
        if not isinstance(mapping["columns"], dict):
            raise ValueError(f"{mapping_name}.columns must be an object.")
        missing_columns = [column for column in required_columns if column not in mapping["columns"]]
        if missing_columns:
            raise ValueError(f"{mapping_name}.columns is missing: {', '.join(missing_columns)}")

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

    def update_header_field(self, config, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value, role_value):
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
        self._set_bool_field(target_field, "open_row_trigger", field_values.get("open_row_trigger"), default=False)
        self._set_bool_field(target_field, "user_input", field_values.get("user_input"), default=False)
        self._set_bool_field(target_field, "expand", field_values.get("expand"), default=False)
        self._set_bool_field(target_field, "bold", field_values.get("bold"), default=False)

        self._set_optional_text_field(target_field, "default", field_values.get("default"))
        self._set_optional_text_field(target_field, "sticky", field_values.get("sticky"))
        self._set_optional_text_field(target_field, "state", field_values.get("state"))
        self._set_optional_text_field(target_field, "options_source", field_values.get("options_source"))
        self._set_optional_text_field(target_field, "bootstyle", field_values.get("bootstyle"))

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

    def update_mapping(self, config, mapping_name, start_row_value, column_values):
        start_row = int(str(start_row_value).strip())
        mapping = config.get(mapping_name)
        if not isinstance(mapping, dict):
            raise ValueError(f"Mapping '{mapping_name}' was not found.")
        mapping["start_row"] = start_row
        for key, value in column_values.items():
            cleaned_value = str(value).strip()
            if not cleaned_value:
                raise ValueError(f"Column '{key}' cannot be empty.")
            mapping.setdefault("columns", {})[key] = cleaned_value
        return config, f"Updated mapping '{mapping_name}'"

    def get_field_item_key(self, field_id):
        return f"field:{field_id}"

    def get_row_field_item_key(self, section_name, field_id):
        return f"row_field:{section_name}:{field_id}"

    def get_mapping_item_key(self, mapping_name):
        return f"mapping:{mapping_name}"

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
        title_map = {
            "production_row_fields": "Production Row Fields",
            "downtime_row_fields": "Downtime Row Fields",
        }
        for section_name in self.row_field_sections:
            preview_fields = []
            for field in config.get(section_name, []):
                preview_field = dict(field)
                preview_field["item_key"] = self.get_row_field_item_key(section_name, field.get("id", ""))
                preview_fields.append(preview_field)
            row_sections.append(
                {
                    "section_name": section_name,
                    "title": title_map.get(section_name, section_name),
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
            recognized_keys = [key for key in self.REQUIRED_TOP_LEVEL_KEYS if key in payload]
            if all(key in payload for key in self.REQUIRED_TOP_LEVEL_KEYS):
                return payload, {"mode": "full", "applied_sections": list(self.REQUIRED_TOP_LEVEL_KEYS)}
            if recognized_keys:
                unknown_keys = [key for key in payload.keys() if key not in self.REQUIRED_TOP_LEVEL_KEYS]
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
