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

from app.layout_config_service import LayoutConfigService


class LayoutManagerModel:
    def __init__(self):
        self.service = LayoutConfigService()
        self.is_dirty = False
        self.current_source_path = self.service.config_path
        self.protected_field_ids = {"date", "cast_date", "shift", "hours", "goal_mph", "total_molds"}

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

    def serialize_config(self, config):
        return json.dumps(config, indent=4)

    def parse_editor_text(self, text):
        config = json.loads(text)
        self.validate_config(config)
        return config

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

    def mark_dirty(self):
        self.is_dirty = True

    def mark_clean(self):
        self.is_dirty = False

    def validate_config(self, config):
        if not isinstance(config, dict):
            raise ValueError("Config must be a JSON object.")

        required_top_level = ["template_path", "header_fields", "production_mapping", "downtime_mapping"]
        missing_keys = [key for key in required_top_level if key not in config]
        if missing_keys:
            raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

        if not isinstance(config["header_fields"], list):
            raise ValueError("header_fields must be a list.")

        for index, field in enumerate(config["header_fields"], start=1):
            if not isinstance(field, dict):
                raise ValueError(f"header_fields item {index} must be an object.")
            field_missing = [key for key in ("id", "label", "row", "col") if key not in field]
            if field_missing:
                raise ValueError(f"header_fields item {index} is missing: {', '.join(field_missing)}")

        self.validate_mapping(config["production_mapping"], "production_mapping", ("shop_order", "part_number", "molds"))
        self.validate_mapping(config["downtime_mapping"], "downtime_mapping", ("start", "stop", "code", "cause"))

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

    def create_unique_field_id(self, config):
        existing_ids = {field.get("id") for field in config.get("header_fields", [])}
        index = 1
        while True:
            field_id = f"new_field_{index}"
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

    def remove_header_field(self, config, field_id):
        if field_id in self.protected_field_ids:
            raise ValueError(f"Field '{field_id}' is protected and cannot be removed.")
        fields = config.get("header_fields", [])
        updated_fields = [field for field in fields if field.get("id") != field_id]
        if len(updated_fields) == len(fields):
            raise ValueError(f"Field '{field_id}' was not found.")
        config["header_fields"] = updated_fields
        return config, f"Removed field '{field_id}'"

    def update_header_field(self, config, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value):
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

        return {
            "field_count": len(fields),
            "max_row": max_row,
            "max_col": max_col,
            "cells": cells,
        }
