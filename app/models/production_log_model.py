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
from datetime import datetime

from app.downtime_codes import get_code_options
from app.external_data_registry import ExternalDataRegistry
from app.form_definition_registry import DEFAULT_FORM_ID, DEFAULT_FORM_NAME, FormDefinitionRegistry
from app.persistence import write_json_with_backup
from app.production_log_roles import HEADER_BLANK_IGNORE_ROLES, HEADER_DERIVED_ROLES, resolve_header_field_role, resolve_row_field_role, normalize_role_name
from app.utils import ensure_external_directory, external_path
from app.data_handler_service import DEFAULT_SHIFT_TIME_SETTINGS, DEFAULT_PRODUCTION_ROW_FIELDS, DEFAULT_DOWNTIME_ROW_FIELDS, DataHandlerService

__module_name__ = "Form Loader"
__version__ = "1.2.11"

BALANCE_DOWNTIME_CAUSE = "Time Balance Adjustment"
DEFAULT_GHOST_LABEL = "Ghost Time: 0 min"
DEFAULT_CALCULATION_FORMULAS = {
    "production_minutes": "round_minutes((molds / rate) * 60, production_minutes_rounding)",
    "shift_total_minutes": "round_minutes(hours * 60, shift_total_rounding)",
    "shift_start_time": "format_clock(default_start_minutes)",
    "shift_end_time": "format_clock(default_end_minutes)",
    "downtime_minutes": "if_value(stop_minutes < start_minutes, if_value(allow_overnight_downtime, (stop_minutes + day_minutes) - start_minutes, invalid_value), stop_minutes - start_minutes)",
    "downtime_stop_clock": "format_clock(default_stop_minutes)",
    "ghost_minutes": "shift_total_minutes - production_total_minutes - downtime_total_minutes",
    "efficiency_pct": "if_value((hours <= 0) or (goal_rate <= 0), 0, (total_molds / (hours * goal_rate)) * 100)",
}
DEFAULT_CALCULATION_SETTINGS = {
    **DEFAULT_SHIFT_TIME_SETTINGS,
    "production_minutes_rounding": "floor",
    "missing_rate_fallback_mode": "header_goal",
    "missing_rate_fallback_value": 240.0,
    "allow_overnight_downtime": True,
    "negative_ghost_mode": "allow_negative",
    "default_balance_mix_pct": 100.0,
    "downtime_code_export_mode": "both",
    "display_targets": {
        "production_minutes_role": "duration_minutes",
        "downtime_minutes_role": "duration_minutes",
        "efficiency_header_role": "efficiency_pct",
        "ghost_display_mode": "metrics_only",
        "ghost_header_role": "target_time",
    },
    "formulas": deepcopy(DEFAULT_CALCULATION_FORMULAS),
}
# Constants moved to data_handler_service.py to prevent circular imports.
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
        "delete_row_policy": {
            "show_delete_button": True,
            "delete_button_label": "X",
            "delete_button_tooltip": "Delete this row",
            "require_delete_confirmation": False,
        },
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
        "delete_row_policy": {
            "show_delete_button": True,
            "delete_button_label": "X",
            "delete_button_tooltip": "Delete this row",
            "require_delete_confirmation": False,
        },
    },
)
SUPPORTED_BEHAVIOR_PROFILES = ("header", "production", "downtime")


class ProductionLogModel:
    def __init__(self, data_registry=None):
        self.data_registry = data_registry or ExternalDataRegistry()
        self.form_registry = FormDefinitionRegistry()
        self.active_form_info = self.form_registry.get_active_form()
        self.form_id = self.active_form_info.get("id", DEFAULT_FORM_ID)
        self.form_name = self.active_form_info.get("name", DEFAULT_FORM_NAME)
        self.config_path = self.active_form_info["load_path"]
        self.dt_codes = get_code_options()
        self.data_handler = DataHandlerService(form_id=self.form_id, data_registry=self.data_registry)
        self.settings = self.load_settings()
        self.layout_config = self.load_layout_config()
        self.calculation_settings = self.load_calculation_settings(config=self.layout_config)
        self.default_hours = self._format_number(self.settings.get("default_shift_hours", 8.0))
        self.default_goal = self._format_number(self.settings.get("default_goal_mph", 240.0))
        backup_policy = self.settings.get("backup_policy", {}) if isinstance(self.settings, dict) else {}
        auto_save_minutes = self._coerce_positive_int(
            backup_policy.get("draft_auto_save_interval_min", self.settings.get("auto_save_interval_min", 5)),
            5,
        )
        self.auto_save_interval = auto_save_minutes * 60000

    def get_active_form_info(self):
        return dict(self.active_form_info)

    def get_active_form_name(self):
        return str(self.active_form_info.get("name") or self.form_name or DEFAULT_FORM_NAME)

    def get_form_section_title(self, suffix_text):
        suffix = str(suffix_text or "").strip()
        section_id = {
            "Header": "header",
            "Jobs": "production",
            "Downtime Issues": "downtime",
        }.get(suffix)
        if section_id:
            config = getattr(self, "layout_config", None)
            if not isinstance(config, dict):
                config = self.load_layout_config()
            section_name = self.get_section_name(section_id, config=config, fallback_name=suffix)
            return f"{self.get_active_form_name()} {section_name}".strip()
        if not suffix:
            return self.get_active_form_name()
        return f"{self.get_active_form_name()} {suffix}".strip()

    def load_layout_config_for_form(self, form_id=None):
        try:
            form_info = self.form_registry.get_form(form_id)
            with open(form_info["load_path"], "r", encoding="utf-8") as handle:
                return self._normalize_layout_config(json.load(handle))
        except Exception:
            return self.load_layout_config()

    def get_form_name_for_id(self, form_id=None):
        try:
            form_info = self.form_registry.get_form(form_id)
            return str(form_info.get("name") or form_info.get("id") or "Form")
        except Exception:
            return self.get_active_form_name()

    def resolve_draft_form_id(self, meta):
        raw_form_id = ""
        if isinstance(meta, dict):
            raw_form_id = str(meta.get("form_id") or "").strip()
        return self.form_registry.canonical_form_id(raw_form_id or DEFAULT_FORM_ID)

    def load_layout_config(self):
        with open(self.config_path, "r", encoding="utf-8") as handle:
            self.layout_config = self._normalize_layout_config(json.load(handle))
        return deepcopy(self.layout_config)

    def _normalize_layout_config(self, config):
        normalized = dict(config) if isinstance(config, dict) else {}
        normalized["sections"] = self._normalize_sections(normalized)
        if "header_fields" in normalized:
            normalized["header_fields"] = self._normalize_header_field_configs(normalized.get("header_fields"))
        
        if "production_row_fields" not in normalized or not normalized["production_row_fields"]:
            normalized["production_row_fields"] = deepcopy(DEFAULT_PRODUCTION_ROW_FIELDS)
        else:
            normalized["production_row_fields"] = self._merge_row_field_configs(
                normalized.get("production_row_fields"),
                DEFAULT_PRODUCTION_ROW_FIELDS,
                "production",
            )
        if "downtime_row_fields" not in normalized or not normalized["downtime_row_fields"]:
            normalized["downtime_row_fields"] = deepcopy(DEFAULT_DOWNTIME_ROW_FIELDS)
        else:
            normalized["downtime_row_fields"] = self._merge_row_field_configs(
                normalized.get("downtime_row_fields"),
                DEFAULT_DOWNTIME_ROW_FIELDS,
                "downtime",
            )
        return normalized

    def _normalize_sections(self, config):
        raw_sections = config.get("sections") if isinstance(config, dict) else None
        if not isinstance(raw_sections, list):
            raw_sections = []
        if not raw_sections:
            raw_sections = deepcopy(DEFAULT_SECTIONS)

        normalized_sections = []
        seen_ids = set()

        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                continue
            section_id = str(raw_section.get("id", "")).strip().lower()
            if not section_id or section_id in seen_ids:
                continue
            normalized_section = deepcopy(raw_section)
            normalized_section["id"] = section_id
            normalized_section["name"] = str(
                raw_section.get("name", normalized_section.get("name", section_id.replace("_", " ").title()))
            ).strip() or section_id.replace("_", " ").title()

            description_text = str(raw_section.get("description", normalized_section.get("description", ""))).strip()
            if description_text:
                normalized_section["description"] = description_text
            else:
                normalized_section.pop("description", None)

            fields_key = str(raw_section.get("fields_key", normalized_section.get("fields_key", ""))).strip()
            if fields_key:
                normalized_section["fields_key"] = fields_key
            else:
                normalized_section.pop("fields_key", None)

            mapping_key = str(raw_section.get("mapping_key", normalized_section.get("mapping_key", ""))).strip()
            if mapping_key:
                normalized_section["mapping_key"] = mapping_key
            else:
                normalized_section.pop("mapping_key", None)

            section_type = str(raw_section.get("section_type", normalized_section.get("section_type", "single"))).strip().lower()
            normalized_section["section_type"] = section_type or "single"

            behavior_profile = str(raw_section.get("behavior_profile", normalized_section.get("behavior_profile", section_id))).strip().lower()
            if behavior_profile:
                normalized_section["behavior_profile"] = behavior_profile
            else:
                normalized_section.pop("behavior_profile", None)

            if normalized_section["section_type"] == "repeating":
                default_max_rows = raw_section.get("default_max_rows", normalized_section.get("default_max_rows"))
                if default_max_rows not in (None, ""):
                    try:
                        normalized_section["default_max_rows"] = max(1, int(default_max_rows))
                    except (TypeError, ValueError):
                        normalized_section["default_max_rows"] = default_max_rows
                else:
                    normalized_section.pop("default_max_rows", None)
                raw_policy = raw_section.get("delete_row_policy", normalized_section.get("delete_row_policy"))
                if isinstance(raw_policy, dict):
                    normalized_section["delete_row_policy"] = self._normalize_delete_row_policy(
                        raw_policy,
                        default_policy=normalized_section.get("delete_row_policy"),
                    )
                else:
                    normalized_section.pop("delete_row_policy", None)
            else:
                normalized_section.pop("default_max_rows", None)
                normalized_section.pop("delete_row_policy", None)

            normalized_sections.append(normalized_section)
            seen_ids.add(section_id)

        return normalized_sections

    def _normalize_delete_row_policy(self, policy, default_policy=None):
        base_policy = dict(default_policy or {})
        raw_policy = policy if isinstance(policy, dict) else {}
        show_delete_button = bool(raw_policy.get("show_delete_button", base_policy.get("show_delete_button", True)))
        delete_button_label = str(
            raw_policy.get("delete_button_label", base_policy.get("delete_button_label", "X")) or "X"
        ).strip() or "X"
        delete_button_tooltip = str(
            raw_policy.get("delete_button_tooltip", base_policy.get("delete_button_tooltip", "Delete this row"))
            or "Delete this row"
        ).strip() or "Delete this row"
        require_delete_confirmation = bool(
            raw_policy.get(
                "require_delete_confirmation",
                base_policy.get("require_delete_confirmation", False),
            )
        )
        return {
            "show_delete_button": show_delete_button,
            "delete_button_label": delete_button_label,
            "delete_button_tooltip": delete_button_tooltip,
            "require_delete_confirmation": require_delete_confirmation,
        }

    def get_sections(self, config=None):
        config_data = config or self.layout_config
        return [deepcopy(section) for section in config_data.get("sections", []) if isinstance(section, dict)]

    def get_section_info(self, section_id, config=None):
        normalized_section_id = str(section_id or "").strip().lower()
        for section in self.get_sections(config=config):
            if section.get("id") == normalized_section_id:
                return section
        routed_section = self.get_routed_section_by_profile(normalized_section_id, config=config)
        if isinstance(routed_section, dict) and routed_section:
            return routed_section
        return {}

    def get_section_name(self, section_id, config=None, fallback_name=None):
        section_info = self.get_section_info(section_id, config=config)
        if section_info:
            return section_info.get("name") or fallback_name or str(section_id or "").replace("_", " ").title()
        return fallback_name or str(section_id or "").replace("_", " ").title()

    def get_delete_row_policy(self, section_id, config=None):
        section_info = self.get_section_info(section_id, config=config)
        section_type = str(section_info.get("section_type", "")).strip().lower()
        if section_type != "repeating":
            return {
                "show_delete_button": False,
                "delete_button_label": "X",
                "delete_button_tooltip": "Delete this row",
                "require_delete_confirmation": False,
            }
        policy = section_info.get("delete_row_policy") if isinstance(section_info.get("delete_row_policy"), dict) else {}
        return self._normalize_delete_row_policy(policy)

    def _resolve_section_profile_from_structure(self, section, config=None):
        if not isinstance(section, dict):
            return ""
        section_type = str(section.get("section_type") or "single").strip().lower()
        section_id = normalize_role_name(section.get("id"))
        behavior_profile = normalize_role_name(section.get("behavior_profile"))
        if behavior_profile in SUPPORTED_BEHAVIOR_PROFILES:
            return behavior_profile
        if section_id in SUPPORTED_BEHAVIOR_PROFILES:
            return section_id

        config_data = config if isinstance(config, dict) else self.layout_config
        fields_key = str(section.get("fields_key") or "").strip()
        if not fields_key:
            return ""
        field_configs = config_data.get(fields_key, []) if isinstance(config_data.get(fields_key), list) else []
        if not field_configs:
            return ""

        if section_type == "single":
            header_roles = {
                resolve_header_field_role(str(field.get("id") or "").strip(), field.get("role"))
                for field in field_configs
                if isinstance(field, dict)
            }
            if any(role_name in header_roles for role_name in ("log_date", "shift_number", "shift_hours", "goal_rate")):
                return "header"
            return ""

        if section_type != "repeating":
            return ""

        resolved_roles = {
            resolve_row_field_role(section_id or behavior_profile, str(field.get("id") or "").strip(), field.get("role"))
            for field in field_configs
            if isinstance(field, dict)
        }
        production_roles = set(REQUIRED_MAPPING_ROLES.get("production") or ())
        downtime_roles = set(REQUIRED_MAPPING_ROLES.get("downtime") or ())
        if production_roles and production_roles.issubset(resolved_roles):
            return "production"
        if downtime_roles and downtime_roles.issubset(resolved_roles):
            return "downtime"
        return ""

    def get_routed_section_by_profile(self, behavior_profile, config=None, expected_type=None):
        normalized_profile = normalize_role_name(behavior_profile)
        if not normalized_profile:
            return {}

        declared_sections = self.get_sections(config=config)
        if expected_type:
            declared_sections = [
                section
                for section in declared_sections
                if str(section.get("section_type") or "").strip().lower() == expected_type
            ]

        id_matches = [
            section
            for section in declared_sections
            if normalize_role_name(section.get("id")) == normalized_profile
        ]
        if len(id_matches) == 1:
            return id_matches[0]
        if len(id_matches) > 1:
            return {}

        explicit_profile_matches = [
            section
            for section in declared_sections
            if normalize_role_name(section.get("behavior_profile")) == normalized_profile
        ]
        if len(explicit_profile_matches) == 1:
            return explicit_profile_matches[0]
        if len(explicit_profile_matches) > 1:
            return {}

        inferred_profile_matches = []
        for section in declared_sections:
            inferred_profile = self._resolve_section_profile_from_structure(section, config=config)
            if inferred_profile != normalized_profile:
                continue
            inferred_profile_matches.append(section)

        if len(inferred_profile_matches) != 1:
            return {}
        return inferred_profile_matches[0]

    def get_active_repeating_profiles(self, config=None):
        active_profiles = []
        for profile_name in ("production", "downtime"):
            if self.get_routed_section_by_profile(profile_name, config=config, expected_type="repeating"):
                active_profiles.append(profile_name)
        return active_profiles

    def _normalize_header_field_configs(self, configured_fields):
        if not isinstance(configured_fields, list):
            return []

        normalized_fields = []
        seen_ids = set()
        for field in configured_fields:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("id", "")).strip()
            if not field_id or field_id in seen_ids:
                continue
            normalized_field = dict(field)
            role_name = resolve_header_field_role(field_id, normalized_field.get("role"))
            if role_name:
                normalized_field["role"] = role_name
            else:
                normalized_field.pop("role", None)

            if "readonly" in normalized_field:
                readonly_val = self._coerce_bool(normalized_field.get("readonly"), default=False)
                if readonly_val:
                    normalized_field["readonly"] = True
                else:
                    normalized_field.pop("readonly", None)

            normalized_fields.append(normalized_field)
            seen_ids.add(field_id)
        return normalized_fields

    def _merge_row_field_configs(self, configured_fields, default_fields, section_name):
        if not isinstance(configured_fields, list):
            return []

        merged_fields = []
        seen_ids = set()
        for field in configured_fields:
            if not isinstance(field, dict):
                continue
            field_id = str(field.get("id", "")).strip()
            if not field_id or field_id in seen_ids:
                continue
            merged_field = dict(field)
            role_name = resolve_row_field_role(section_name, field_id, merged_field.get("role"))
            if role_name:
                merged_field["role"] = role_name
            else:
                merged_field.pop("role", None)

            for key in ("readonly", "derived", "math_trigger", "open_row_trigger", "user_input", "expand", "bold"):
                if key in merged_field:
                    val = self._coerce_bool(merged_field.get(key), default=False)
                    if val:
                        merged_field[key] = True
                    else:
                        merged_field.pop(key, None)

            if merged_field.get("user_input"):
                merged_field.pop("derived", None)

            merged_fields.append(merged_field)
            seen_ids.add(field_id)

        return merged_fields

    def get_section_field_configs(self, section_name, config=None):
        config_data = config or self.load_layout_config()
        section_info = self.get_section_info(section_name, config=config_data)
        config_key = section_info.get("fields_key")
        if not config_key:
            return []
        field_configs = config_data.get(config_key, [])
        return [dict(field) for field in field_configs if isinstance(field, dict) and field.get("id")]

    def _resolve_field_role(self, section_name, field_config, config=None):
        field_id = str(field_config.get("id", "")).strip()
        header_sec = self.get_routed_section_by_profile("header", config=config)
        header_id = header_sec.get("id") or "header"
        if section_name == header_id:
            return resolve_header_field_role(field_id, field_config.get("role"))
        return resolve_row_field_role(section_name, field_id, field_config.get("role"))

    def get_header_field_id_by_role(self, role_name, config=None, fallback_id=None):
        normalized_role = normalize_role_name(role_name)
        header_sec = self.get_routed_section_by_profile("header", config=config)
        header_id = header_sec.get("id") or "header"
        for field in self.get_section_field_configs(header_id, config=config):
            if self._resolve_field_role(header_id, field, config=config) == normalized_role:
                return field["id"]
        return fallback_id

    def get_section_field_id_by_role(self, section_name, role_name, config=None, fallback_id=None):
        normalized_role = normalize_role_name(role_name)
        for field in self.get_section_field_configs(section_name, config=config):
            if self._resolve_field_role(section_name, field, config=config) == normalized_role:
                return field["id"]
        return fallback_id

    def get_section_field_config_by_role(self, section_name, role_name, config=None):
        field_id = self.get_section_field_id_by_role(section_name, role_name, config=config)
        if not field_id:
            return {}
        for field in self.get_section_field_configs(section_name, config=config):
            if field.get("id") == field_id:
                return field
        return {}

    def get_first_section_field_config_by_key(self, section_name, key_name, expected_value=None, config=None):
        expected_text = str(expected_value).strip().lower() if expected_value is not None else None
        for field in self.get_section_field_configs(section_name, config=config):
            if key_name not in field:
                continue
            if expected_text is None:
                return field
            candidate = str(field.get(key_name, "")).strip().lower()
            if candidate == expected_text:
                return field
        return {}

    def get_rate_value_field_config(self, config=None):
        field_config = self.get_first_section_field_config_by_key("production", "lookup_source", "part_number_rate", config=config)
        if field_config:
            return field_config
        return self.get_section_field_config_by_role("production", "rate_value", config=config)

    def get_rate_override_field_config(self, config=None):
        rate_field = self.get_rate_value_field_config(config=config)
        target_role = normalize_role_name(rate_field.get("override_toggle_role")) if rate_field else ""
        if target_role:
            field_config = self.get_section_field_config_by_role("production", target_role, config=config)
            if field_config:
                return field_config
        field_config = self.get_first_section_field_config_by_key("production", "toggle_target_role", "rate_value", config=config)
        if field_config:
            return field_config
        return self.get_section_field_config_by_role("production", "rate_override_toggle", config=config)

    def get_rate_value_role(self, config=None):
        field_config = self.get_rate_value_field_config(config=config)
        if field_config:
            production_sec = self.get_routed_section_by_profile("production", config=config)
            production_id = production_sec.get("id") or "production"
            return self._resolve_field_role(production_id, field_config, config=config)
        return "rate_value"

    def get_rate_override_role(self, config=None):
        field_config = self.get_rate_override_field_config(config=config)
        if field_config:
            production_sec = self.get_routed_section_by_profile("production", config=config)
            production_id = production_sec.get("id") or "production"
            return self._resolve_field_role(production_id, field_config, config=config)
        return "rate_override_toggle"

    def get_rate_lookup_key_role(self, config=None):
        field_config = self.get_rate_value_field_config(config=config)
        lookup_key_role = normalize_role_name(field_config.get("lookup_key_role")) if field_config else ""
        return lookup_key_role or "part_number"

    def get_header_field_role(self, field_id, config=None):
        header_sec = self.get_routed_section_by_profile("header", config=config)
        header_id = header_sec.get("id") or "header"
        for field in self.get_section_field_configs(header_id, config=config):
            if field.get("id") == field_id:
                return self._resolve_field_role(header_id, field, config=config)
        return resolve_header_field_role(field_id)

    def get_section_field_role(self, section_name, field_id, config=None):
        for field in self.get_section_field_configs(section_name, config=config):
            if field.get("id") == field_id:
                return self._resolve_field_role(section_name, field, config=config)
        return resolve_row_field_role(section_name, field_id)

    def get_header_value_by_role(self, header_data, role_name, config=None, fallback_id=None, default=""):
        if not isinstance(header_data, dict):
            return default
        field_id = self.get_header_field_id_by_role(role_name, config=config, fallback_id=fallback_id)
        if field_id and field_id in header_data:
            return header_data.get(field_id, default)
        if fallback_id and fallback_id in header_data:
            return header_data.get(fallback_id, default)
        return default

    def get_section_field_ids(self, section_name, config=None):
        return [field["id"] for field in self.get_section_field_configs(section_name, config=config)]

    def get_open_row_field_ids(self, section_name, config=None):
        return [
            field["id"]
            for field in self.get_section_field_configs(section_name, config=config)
            if field.get("open_row_trigger")
        ]

    def get_default_row_math_trigger_roles(self, section_name):
        if section_name == "production":
            return {"part_number", "rate_value", "mold_count"}
        if section_name == "downtime":
            return {"start_clock", "stop_clock"}
        return set()

    def normalize_header_data(self, header_data):
        return self.data_handler.normalize_header_data(
            header_data,
            calculation_settings=self.calculation_settings,
        )

    def compute_target_time(self, raw_hours):
        return self.data_handler.compute_target_time(
            raw_hours,
            calculation_settings=self.calculation_settings,
        )

    def get_default_calculation_settings(self):
        return deepcopy(DEFAULT_CALCULATION_SETTINGS)

    def get_default_calculation_formulas(self):
        return deepcopy(DEFAULT_CALCULATION_FORMULAS)

    def _get_calculations_metadata(self, config=None):
        config_data = config if isinstance(config, dict) else self.layout_config
        calculations = config_data.get("calculations") if isinstance(config_data.get("calculations"), dict) else {}
        companion_relative_path = str(calculations.get("companion_relative_path") or "").strip().replace("\\", "/")
        if not companion_relative_path:
            companion_relative_path = os.path.join("data", "forms", self.form_id, "calculations.json").replace("\\", "/")
        section_profiles = calculations.get("section_profiles") if isinstance(calculations.get("section_profiles"), list) else []
        return {
            "companion_relative_path": companion_relative_path,
            "section_profiles": [dict(profile) for profile in section_profiles if isinstance(profile, dict)],
        }

    def _resolve_calculation_companion_paths(self, config=None):
        metadata = self._get_calculations_metadata(config=config)
        companion_relative_path = str(metadata.get("companion_relative_path") or "").strip().replace("\\", "/")
        companion_path = external_path(companion_relative_path)
        backup_dir = ensure_external_directory(os.path.join("data", "backups", "form_calculations", self.form_id))
        return {
            "relative_path": companion_relative_path,
            "path": companion_path,
            "backup_dir": backup_dir,
            "section_profiles": metadata.get("section_profiles") or [],
        }

    def load_calculation_settings(self, config=None):
        companion_info = self._resolve_calculation_companion_paths(config=config)
        companion_path = companion_info["path"]
        payload = None
        if os.path.exists(companion_path):
            try:
                with open(companion_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except Exception:
                payload = None

        if not isinstance(payload, dict):
            if self.form_id == DEFAULT_FORM_ID:
                payload = self.data_registry.load_json(
                    "production_log_calculations",
                    default_factory=self.get_default_calculation_settings,
                )
            else:
                payload = self.get_default_calculation_settings()

        normalized_settings = self.normalize_calculation_settings(payload)
        if not os.path.exists(companion_path):
            os.makedirs(os.path.dirname(companion_path), exist_ok=True)
            write_json_with_backup(
                companion_path,
                normalized_settings,
                backup_dir=companion_info["backup_dir"],
                keep_count=12,
            )
        return normalized_settings

    def get_calculation_settings_copy(self):
        return deepcopy(self.calculation_settings)

    def refresh_calculation_settings(self):
        self.calculation_settings = self.load_calculation_settings(config=self.layout_config)
        return self.get_calculation_settings_copy()

    def save_calculation_settings(self, payload=None):
        normalized_settings = self.normalize_calculation_settings(payload if isinstance(payload, dict) else self.calculation_settings)
        companion_info = self._resolve_calculation_companion_paths(config=self.layout_config)
        backup_info = write_json_with_backup(
            companion_info["path"],
            normalized_settings,
            backup_dir=companion_info["backup_dir"],
            keep_count=12,
        )
        self.calculation_settings = normalized_settings
        return backup_info

    def normalize_calculation_settings(self, payload=None):
        raw_settings = payload if isinstance(payload, dict) else {}
        defaults = self.get_default_calculation_settings()
        normalized_settings = dict(defaults)

        normalized_settings["production_minutes_rounding"] = self._normalize_choice(
            raw_settings.get("production_minutes_rounding"),
            {"floor", "nearest", "ceil"},
            defaults["production_minutes_rounding"],
        )
        normalized_settings["shift_total_rounding"] = self._normalize_choice(
            raw_settings.get("shift_total_rounding"),
            {"floor", "nearest", "ceil"},
            defaults["shift_total_rounding"],
        )
        normalized_settings["missing_rate_fallback_mode"] = self._normalize_choice(
            raw_settings.get("missing_rate_fallback_mode"),
            {"header_goal", "fixed_value", "no_fallback"},
            defaults["missing_rate_fallback_mode"],
        )
        normalized_settings["missing_rate_fallback_value"] = self._coerce_float(
            raw_settings.get("missing_rate_fallback_value", defaults["missing_rate_fallback_value"]),
            defaults["missing_rate_fallback_value"],
        )
        for shift_index in (1, 2, 3):
            anchor_key = f"shift_{shift_index}_anchor_mode"
            time_key = f"shift_{shift_index}_reference_time"
            normalized_settings[anchor_key] = self._normalize_choice(
                raw_settings.get(anchor_key),
                {"start", "midpoint", "end"},
                defaults[anchor_key],
            )
            normalized_settings[time_key] = self._normalize_compact_time_value(
                raw_settings.get(time_key),
                defaults[time_key],
            )
        normalized_settings["allow_overnight_downtime"] = self._coerce_bool(
            raw_settings.get("allow_overnight_downtime", defaults["allow_overnight_downtime"]),
            defaults["allow_overnight_downtime"],
        )
        normalized_settings["negative_ghost_mode"] = self._normalize_choice(
            raw_settings.get("negative_ghost_mode"),
            {"allow_negative", "clamp_zero"},
            defaults["negative_ghost_mode"],
        )
        normalized_settings["downtime_code_export_mode"] = self._normalize_choice(
            raw_settings.get("downtime_code_export_mode"),
            {"both", "code", "description"},
            defaults["downtime_code_export_mode"],
        )
        normalized_settings["default_balance_mix_pct"] = max(
            0.0,
            min(
                100.0,
                self._coerce_float(
                    raw_settings.get("default_balance_mix_pct", defaults["default_balance_mix_pct"]),
                    defaults["default_balance_mix_pct"],
                ),
            ),
        )
        raw_display_targets = raw_settings.get("display_targets") if isinstance(raw_settings.get("display_targets"), dict) else {}
        default_display_targets = defaults.get("display_targets") if isinstance(defaults.get("display_targets"), dict) else {}
        normalized_settings["display_targets"] = {
            "production_minutes_role": self._normalize_choice(
                raw_display_targets.get("production_minutes_role"),
                {"duration_minutes", "mold_count", "part_number", "job_order"},
                default_display_targets.get("production_minutes_role", "duration_minutes"),
            ),
            "downtime_minutes_role": self._normalize_choice(
                raw_display_targets.get("downtime_minutes_role"),
                {"duration_minutes", "cause_text", "downtime_code", "start_clock", "stop_clock"},
                default_display_targets.get("downtime_minutes_role", "duration_minutes"),
            ),
            "efficiency_header_role": self._normalize_choice(
                raw_display_targets.get("efficiency_header_role"),
                {"efficiency_pct", "mtd_percentage", "total_molds", "goal_rate"},
                default_display_targets.get("efficiency_header_role", "efficiency_pct"),
            ),
            "ghost_display_mode": self._normalize_choice(
                raw_display_targets.get("ghost_display_mode"),
                {"metrics_only", "header_only", "metrics_and_header"},
                default_display_targets.get("ghost_display_mode", "metrics_only"),
            ),
            "ghost_header_role": self._normalize_choice(
                raw_display_targets.get("ghost_header_role"),
                {"target_time", "cast_date", "mtd_percentage", "efficiency_pct"},
                default_display_targets.get("ghost_header_role", "target_time"),
            ),
        }
        raw_formulas = raw_settings.get("formulas") if isinstance(raw_settings.get("formulas"), dict) else {}
        normalized_formulas = self.get_default_calculation_formulas()
        for formula_name, default_formula in list(normalized_formulas.items()):
            formula_text = str(raw_formulas.get(formula_name, default_formula) or "").strip()
            normalized_formulas[formula_name] = formula_text or default_formula
        for formula_name, custom_formula in raw_formulas.items():
            if formula_name not in normalized_formulas:
                normalized_formulas[formula_name] = str(custom_formula or "").strip()
        normalized_settings["formulas"] = normalized_formulas
        return normalized_settings

    def get_display_target(self, key_name, default_value=""):
        display_targets = self.calculation_settings.get("display_targets") if isinstance(self.calculation_settings, dict) else {}
        if not isinstance(display_targets, dict):
            return default_value
        value = str(display_targets.get(key_name) or "").strip()
        return value or str(default_value or "")

    def get_calculation_formula(self, formula_name):
        formulas = self.calculation_settings.get("formulas", {}) if isinstance(self.calculation_settings, dict) else {}
        return str(formulas.get(formula_name, DEFAULT_CALCULATION_FORMULAS.get(formula_name, "")) or "").strip()

    def evaluate_runtime_formula(self, formula_name, context=None, default=None):
        formula_text = self.get_calculation_formula(formula_name)
        formula_context = {
            key: value
            for key, value in self.calculation_settings.items()
            if key != "formulas"
        }
        formula_context.update(
            {
                "day_minutes": 24 * 60,
                "invalid_value": -1,
            }
        )
        if isinstance(context, dict):
            formula_context.update(context)
        return self.data_handler.evaluate_expression_formula(formula_text, formula_context, default=default)

    def serialize_ui_data(self, data):
        return json.dumps(data, sort_keys=True, default=str)

    def is_form_blank(self, data):
        layout_config = self.load_layout_config()
        header_sec = self.get_routed_section_by_profile("header", config=layout_config)
        header_id = header_sec.get("id") or "header"
        header = data.get(header_id, data.get("header", {}))
        significant_header_values = [
            value for key, value in header.items()
            if self.get_header_field_role(key, config=layout_config) not in HEADER_BLANK_IGNORE_ROLES and str(value).strip()
        ]
        repeating_has_data = False
        for section in self.get_sections(config=layout_config):
            if not isinstance(section, dict):
                continue
            section_type = str(section.get("section_type") or "single").strip().lower()
            if section_type != "repeating":
                continue
            section_id = str(section.get("id") or "").strip().lower()
            if not section_id:
                continue
            open_row_fields = self.get_open_row_field_ids(section_id, config=layout_config)
            section_rows = list(data.get(section_id) or [])
            if not section_rows and section_id == "production":
                section_rows = list(data.get("production") or [])
            if not section_rows and section_id == "downtime":
                section_rows = list(data.get("downtime") or [])
            if any(any(str(row.get(key, "")).strip() for key in open_row_fields) for row in section_rows):
                repeating_has_data = True
                break

        return not significant_header_values and not repeating_has_data

    def load_settings(self):
        default_settings = {
            "auto_save_interval_min": 5,
            "default_shift_hours": 8.0,
            "default_goal_mph": 240.0,
        }
        settings = self.data_registry.load_json("settings", default_factory=lambda: dict(default_settings))
        if not isinstance(settings, dict):
            settings = dict(default_settings)
        settings["auto_save_interval_min"] = self._coerce_positive_int(settings.get("auto_save_interval_min", 5), 5)
        settings["default_shift_hours"] = self._coerce_float(settings.get("default_shift_hours", 8.0), 8.0)
        settings["default_goal_mph"] = self._coerce_float(settings.get("default_goal_mph", 240.0), 240.0)
        return settings

    def _coerce_positive_int(self, value, default):
        try:
            normalized = int(float(str(value).strip()))
        except Exception:
            return default
        return max(1, normalized)

    def _coerce_float(self, value, default):
        try:
            return float(str(value).strip())
        except Exception:
            return default

    def _coerce_bool(self, value, default=False):
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return bool(default)

    def _normalize_choice(self, value, allowed_values, default):
        normalized_value = str(value or "").strip().lower()
        if normalized_value in allowed_values:
            return normalized_value
        return default

    def _normalize_compact_time_value(self, value, default):
        digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
        if not digits:
            return default
        digits = digits.zfill(4)[-4:]
        try:
            hours = int(digits[:2])
            minutes = int(digits[2:])
        except Exception:
            return default
        if hours > 23 or minutes > 59:
            return default
        return digits

    def _format_number(self, value):
        try:
            numeric_value = float(value)
        except Exception:
            return str(value)
        if numeric_value.is_integer():
            return str(int(numeric_value))
        return str(numeric_value)

    def refresh_downtime_codes(self):
        self.dt_codes = get_code_options()
        return self.dt_codes

    def get_pending_dir(self):
        pending_dir = external_path("data/pending")
        os.makedirs(pending_dir, exist_ok=True)
        return pending_dir

    def get_pending_history_dir(self):
        history_dir = os.path.join(self.get_pending_dir(), "history")
        os.makedirs(history_dir, exist_ok=True)
        return history_dir

    def build_draft_path(self, header_data):
        layout_config = self.load_layout_config()
        raw_date = str(self.get_header_value_by_role(header_data, "log_date", config=layout_config, fallback_id="date", default="unsaved") or "unsaved").replace("/", "-")
        shift_str = str(self.get_header_value_by_role(header_data, "shift_number", config=layout_config, fallback_id="shift", default="0") or "0")
        filename = f"draft_{self.form_id}_{raw_date}_shift{shift_str}.json"
        return os.path.join(self.get_pending_dir(), filename)

    def build_draft_payload(self, data, version, draft_path, is_auto=False):
        return {
            "meta": {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "auto_save": is_auto,
                "version": version,
                "draft_name": os.path.basename(draft_path),
                "form_id": self.form_id,
                "form_name": self.get_active_form_name(),
            },
            **data,
        }

    def save_draft_data(self, data, version, is_auto=False):
        header_sec = self.get_routed_section_by_profile("header")
        header_id = header_sec.get("id") or "header"
        draft_path = self.build_draft_path(data.get(header_id, data.get("header", {})))
        payload = self.build_draft_payload(data, version, draft_path, is_auto=is_auto)
        backup_policy = self.settings.get("backup_policy", {}) if isinstance(self.settings, dict) else {}
        backup_info = write_json_with_backup(
            draft_path,
            payload,
            backup_dir=self.get_pending_history_dir(),
            keep_count=self._coerce_positive_int(backup_policy.get("draft_history_keep_count", 20), 20),
        )
        return draft_path, payload, backup_info

    def load_json(self, path):
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def write_json(self, path, payload):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def delete_matching_draft_row(self, draft_path, section_name, match_values):
        if not draft_path or not os.path.exists(draft_path):
            return False

        data = self.load_json(draft_path)
        rows = data.get(section_name, [])
        if not isinstance(rows, list):
            return False

        def row_matches(record):
            return all(
                str(record.get(field_name, "")) == str(match_values.get(field_name, ""))
                for field_name in match_values
            )

        index = next((row_index for row_index, record in enumerate(rows) if row_matches(record)), None)
        if index is None:
            return False

        del rows[index]
        data[section_name] = rows
        self.write_json(draft_path, data)
        return True

    def delete_file(self, path):
        if os.path.exists(path):
            os.remove(path)

    def list_pending_drafts(self):
        drafts = []
        pending_dir = self.get_pending_dir()
        for filename in os.listdir(pending_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(pending_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                meta = data.get("meta", {})
                form_id = self.resolve_draft_form_id(meta)
                layout_config = self.load_layout_config_for_form(form_id)
                saved_at = meta.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
                header_sec = self.get_routed_section_by_profile("header", config=layout_config)
                header_id = header_sec.get("id") or "header"
                header = data.get(header_id, data.get("header", {}))
                drafts.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": saved_at,
                    "form_id": form_id,
                    "form_name": meta.get("form_name") or self.get_form_name_for_id(form_id),
                    "date": self.get_header_value_by_role(header, "log_date", config=layout_config, fallback_id="date", default=""),
                    "shift": self.get_header_value_by_role(header, "shift_number", config=layout_config, fallback_id="shift", default=""),
                })
            except Exception:
                drafts.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
                    "form_id": DEFAULT_FORM_ID,
                    "form_name": self.get_form_name_for_id(DEFAULT_FORM_ID),
                    "date": "",
                    "shift": "",
                })
        drafts.sort(key=lambda item: item["saved_at"], reverse=True)
        return drafts

    def list_recovery_snapshots(self):
        snapshots = []
        history_dir = self.get_pending_history_dir()
        for filename in os.listdir(history_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(history_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                meta = data.get("meta", {})
                form_id = self.resolve_draft_form_id(meta)
                layout_config = self.load_layout_config_for_form(form_id)
                saved_at = meta.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
                header_sec = self.get_routed_section_by_profile("header", config=layout_config)
                header_id = header_sec.get("id") or "header"
                header = data.get(header_id, data.get("header", {}))
                snapshots.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": saved_at,
                    "form_id": form_id,
                    "form_name": meta.get("form_name") or self.get_form_name_for_id(form_id),
                    "date": self.get_header_value_by_role(header, "log_date", config=layout_config, fallback_id="date", default=""),
                    "shift": self.get_header_value_by_role(header, "shift_number", config=layout_config, fallback_id="shift", default=""),
                    "source": "Recovery Snapshot",
                })
            except Exception:
                snapshots.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
                    "form_id": DEFAULT_FORM_ID,
                    "form_name": self.get_form_name_for_id(DEFAULT_FORM_ID),
                    "date": "",
                    "shift": "",
                    "source": "Recovery Snapshot",
                })
        snapshots.sort(key=lambda item: item["saved_at"], reverse=True)
        return snapshots

    def get_latest_pending_draft(self):
        drafts = self.list_pending_drafts()
        for draft in drafts:
            if draft.get("form_id") == self.form_id:
                return draft
        return None

    def load_rates_data(self):
        rates_data = {}
        loaded_rates = self.data_registry.load_json("rates", default_factory=dict)
        if isinstance(loaded_rates, dict):
            for part_number, rate in loaded_rates.items():
                for lookup_key in self.build_part_lookup_keys(part_number):
                    if lookup_key not in rates_data:
                        rates_data[lookup_key] = rate
        return rates_data

    def coerce_minutes_value(self, value, default=0):
        try:
            return int(float(value))
        except Exception:
            return default

    def get_global_goal_rate(self, value, default=240.0):
        try:
            return float(value if value not in (None, "") else default)
        except Exception:
            return default

    def calculate_total_molds(self, mold_values):
        total_molds = 0
        for value in mold_values:
            try:
                total_molds += int(float(value or 0))
            except Exception:
                continue
        return total_molds

    def calculate_production_minutes(self, molds_value, rate):
        try:
            molds = float(molds_value or 0)
        except Exception:
            return 0
        if rate is None or rate <= 0:
            return 0
        result = self.evaluate_runtime_formula(
            "production_minutes",
            {
                "molds": molds,
                "rate": float(rate),
                "mold_count": molds,
                "rate_value": float(rate),
            },
            default=0,
        )
        return max(0, self.coerce_minutes_value(result, 0))

    def calculate_shift_total_minutes(self, hours_value):
        result = self.evaluate_runtime_formula(
            "shift_total_minutes",
            {
                "hours": self._coerce_float(hours_value, 0.0),
                "shift_hours": self._coerce_float(hours_value, 0.0),
            },
            default=0,
        )
        return max(0, self.coerce_minutes_value(result, 0))

    def get_default_balance_mix_pct(self):
        return self._coerce_float(
            self.calculation_settings.get("default_balance_mix_pct", DEFAULT_CALCULATION_SETTINGS["default_balance_mix_pct"]),
            DEFAULT_CALCULATION_SETTINGS["default_balance_mix_pct"],
        )

    def calculate_efficiency(self, total_molds, hours_value, goal_value):
        try:
            hours = float(hours_value or 8.0)
            goal = float(goal_value or 240.0)
        except Exception:
            return 0.0
        result = self.evaluate_runtime_formula(
            "efficiency_pct",
            {
                "total_molds": float(total_molds or 0),
                "hours": hours,
                "shift_hours": hours,
                "goal_rate": goal,
            },
            default=0.0,
        )
        return max(0.0, self._coerce_float(result, 0.0))

    def format_rate_value(self, value):
        try:
            numeric_value = float(value)
        except Exception:
            return ""
        if numeric_value.is_integer():
            return str(int(numeric_value))
        return f"{numeric_value:.2f}".rstrip("0").rstrip(".")

    def normalize_part_number(self, value):
        part_text = str(value or "").strip().upper()
        return " ".join(part_text.split())

    def strip_lookup_separators(self, value):
        return str(value or "").replace(" ", "").replace("-", "")

    def build_part_lookup_keys(self, value):
        normalized = self.normalize_part_number(value)
        if not normalized:
            return []

        candidates = []
        compact = normalized.replace(" ", "")
        separator_compact = self.strip_lookup_separators(normalized)

        for candidate in (normalized, compact, separator_compact):
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        return candidates

    def resolve_lookup_rate(self, part_number, rates_data, global_goal):
        part_keys = self.build_part_lookup_keys(part_number)
        if not part_keys:
            return None

        raw_rate = None
        for part_key in part_keys:
            if part_key in rates_data:
                raw_rate = rates_data[part_key]
                break
        if raw_rate is None:
            fallback_mode = self.calculation_settings.get("missing_rate_fallback_mode", "header_goal")
            if fallback_mode == "no_fallback":
                return None
            if fallback_mode == "fixed_value":
                raw_rate = self.calculation_settings.get("missing_rate_fallback_value", 240.0)
            else:
                raw_rate = global_goal
        try:
            return float(raw_rate)
        except Exception:
            return None

    def is_balance_downtime_cause(self, cause_value):
        return str(cause_value or "").strip() == BALANCE_DOWNTIME_CAUSE

    def parse_minutes_label(self, value):
        text = str(value or "").strip().lower().replace(" min", "")
        try:
            return int(float(text))
        except Exception:
            return 0

    def parse_clock_value(self, value):
        text = str(value or "").strip()
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        digits = digits.zfill(4)[-4:]
        hours = int(digits[:2])
        minutes = int(digits[2:])
        if hours > 23 or minutes > 59:
            return None
        return hours * 60 + minutes

    def calculate_clock_duration_minutes(self, start_value, stop_value):
        start_minutes = self.parse_clock_value(start_value)
        stop_minutes = self.parse_clock_value(stop_value)
        if start_minutes is None or stop_minutes is None:
            return None
        result = self.evaluate_runtime_formula(
            "downtime_minutes",
            {
                "start_minutes": start_minutes,
                "stop_minutes": stop_minutes,
            },
            default=-1,
        )
        duration = self.coerce_minutes_value(result, -1)
        return None if duration < 0 else duration

    def calculate_downtime_minutes(self, start_value, stop_value, fallback_label=None):
        duration = self.calculate_clock_duration_minutes(start_value, stop_value)
        if duration is not None:
            return duration
        if fallback_label is not None:
            return self.parse_minutes_label(fallback_label)
        return 0

    def calculate_ghost_minutes(self, shift_total_minutes, production_total_minutes, downtime_total_minutes):
        if shift_total_minutes <= 0:
            return 0
        ghost_minutes = self.coerce_minutes_value(
            self.evaluate_runtime_formula(
                "ghost_minutes",
                {
                    "shift_total_minutes": shift_total_minutes,
                    "production_total_minutes": production_total_minutes,
                    "downtime_total_minutes": downtime_total_minutes,
                },
                default=0,
            ),
            0,
        )
        if self.calculation_settings.get("negative_ghost_mode") == "clamp_zero":
            return max(0, ghost_minutes)
        return ghost_minutes

    def normalize_balance_mix_ratio(self, value):
        try:
            percentage = float(value)
        except Exception:
            percentage = 100.0
        return max(0.0, min(1.0, percentage / 100.0))

    def format_balance_mix_message(self, mix_ratio):
        weighted_percentage = int(round(self.normalize_balance_mix_ratio(mix_ratio) * 100))
        if weighted_percentage <= 0:
            return "100% even"
        if weighted_percentage >= 100:
            return "100% weighted"
        return f"{weighted_percentage}% weighted"

    def normalize_balance_reference_minutes(self, reference_minutes):
        if not isinstance(reference_minutes, list):
            return []

        normalized_values = []
        has_reference = False
        for value in reference_minutes:
            if value is None:
                normalized_values.append(None)
                continue
            normalized = max(0, self.coerce_minutes_value(value, 0))
            if normalized > 0:
                normalized_values.append(normalized)
                has_reference = True
            else:
                normalized_values.append(None)
        return normalized_values if has_reference else []

    def normalize_balance_state(self, balance_state=None):
        state = balance_state if isinstance(balance_state, dict) else {}
        target_total = max(0, self.coerce_minutes_value(state.get("balance_target_downtime_total_minutes"), 0))
        requested_mode = str(state.get("action_mode", "balance") or "balance").strip().lower()
        action_mode = "rebalance" if requested_mode == "rebalance" and target_total > 0 else "balance"
        return {
            "displayed_ghost_minutes": self.coerce_minutes_value(state.get("displayed_ghost_minutes"), 0),
            "balanceable_ghost_minutes": self.coerce_minutes_value(state.get("balanceable_ghost_minutes"), 0),
            "balance_target_downtime_total_minutes": target_total,
            "action_mode": action_mode,
            "reference_minutes": self.normalize_balance_reference_minutes(state.get("reference_minutes", [])),
        }

    def get_balance_distribution_weights(self, reference_minutes, mix_ratio):
        if not reference_minutes:
            return []

        row_count = len(reference_minutes)
        even_weight = 1 / row_count
        total_duration = sum(reference_minutes)
        normalized_mix = self.normalize_balance_mix_ratio(mix_ratio)
        weights = []
        for duration in reference_minutes:
            duration_weight = (duration / total_duration) if total_duration > 0 else even_weight
            blended_weight = ((1.0 - normalized_mix) * even_weight) + (normalized_mix * duration_weight)
            weights.append(blended_weight)
        return weights

    def allocate_weighted_minutes(self, reference_minutes, target_total_minutes, mix_ratio):
        target_total_minutes = max(0, int(target_total_minutes))
        weights = self.get_balance_distribution_weights(reference_minutes, mix_ratio)
        total_weight = sum(weights)
        if total_weight <= 0:
            return []

        allocations = []
        used_minutes = 0
        for weight in weights:
            exact = target_total_minutes * (weight / total_weight)
            allocated = int(exact)
            allocations.append({"allocated": allocated, "remainder": exact - allocated})
            used_minutes += allocated

        leftover = target_total_minutes - used_minutes
        for item in sorted(allocations, key=lambda entry: entry["remainder"], reverse=True):
            if leftover <= 0:
                break
            item["allocated"] += 1
            leftover -= 1
        return [item["allocated"] for item in allocations]

    def build_downtime_timeline(self, start_values):
        timeline = []
        day_offset = 0
        previous_start = None
        for value in start_values:
            start_minutes = self.parse_clock_value(value)
            absolute_start = None
            if start_minutes is not None:
                if previous_start is not None and start_minutes < previous_start:
                    day_offset += 24 * 60
                absolute_start = day_offset + start_minutes
                previous_start = start_minutes
            timeline.append(absolute_start)
        return timeline

    def calculate_spillover_allocations(self, start_values, reference_minutes, target_total_minutes, mix_ratio):
        allocations = self.allocate_weighted_minutes(reference_minutes, target_total_minutes, mix_ratio)
        timeline = self.build_downtime_timeline(start_values)
        if not allocations or len(allocations) != len(timeline):
            return []

        applied_minutes = []
        spill_minutes = 0
        for index, allocated in enumerate(allocations):
            desired_minutes = allocated + spill_minutes
            spill_minutes = 0
            actual_minutes = desired_minutes
            current_start = timeline[index]
            next_start = timeline[index + 1] if index + 1 < len(timeline) else None
            if current_start is not None and next_start is not None:
                max_minutes = max(0, next_start - current_start)
                if actual_minutes > max_minutes:
                    spill_minutes = actual_minutes - max_minutes
                    actual_minutes = max_minutes
            applied_minutes.append(actual_minutes)

        if spill_minutes > 0 and applied_minutes:
            applied_minutes[-1] += spill_minutes
        return applied_minutes

    def format_clock_value(self, total_minutes):
        normalized = int(total_minutes) % (24 * 60)
        return f"{normalized // 60:02}{normalized % 60:02}"
