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
import re

__module_name__ = "Production Log Roles"
__version__ = "1.0.0"

HEADER_FIELD_ROLE_DEFAULTS = {
    "date": "log_date",
    "cast_date": "cast_date",
    "bond": "bond",
    "eff_pct": "efficiency_pct",
    "shift": "shift_number",
    "hours": "shift_hours",
    "target_time": "target_time",
    "mtd_pct": "mtd_percentage",
    "goal_mph": "goal_rate",
    "total_molds": "total_molds",
    "ret_north": "ret_north",
    "start_time": "shift_start_time",
    "end_time": "shift_end_time",
    "ret_south": "ret_south",
}

ROW_FIELD_ROLE_DEFAULTS = {
    "production": {
        "shop_order": "job_order",
        "part_number": "part_number",
        "rate_lookup": "rate_value",
        "rate_override_enabled": "rate_override_toggle",
        "molds": "mold_count",
        "time_calc": "duration_minutes",
    },
    "downtime": {
        "start": "start_clock",
        "stop": "stop_clock",
        "code": "downtime_code",
        "cause": "cause_text",
        "time_calc": "duration_minutes",
    },
}

HEADER_FIELD_ID_BY_ROLE = {
    role_name: field_id
    for field_id, role_name in HEADER_FIELD_ROLE_DEFAULTS.items()
}

ROW_FIELD_ID_BY_ROLE = {
    section_name: {
        role_name: field_id
        for field_id, role_name in field_roles.items()
    }
    for section_name, field_roles in ROW_FIELD_ROLE_DEFAULTS.items()
}

PROTECTED_HEADER_ROLES = {
    HEADER_FIELD_ROLE_DEFAULTS[field_id]
    for field_id in ("date", "cast_date", "shift", "hours", "goal_mph", "total_molds", "start_time", "end_time", "target_time")
}

PROTECTED_ROW_ROLES = {
    "production_row_fields": set(ROW_FIELD_ROLE_DEFAULTS["production"].values()),
    "downtime_row_fields": set(ROW_FIELD_ROLE_DEFAULTS["downtime"].values()),
}

HEADER_DERIVED_ROLES = {"cast_date", "shift_start_time", "shift_end_time", "target_time"}
HEADER_BLANK_IGNORE_ROLES = {"shift_hours", "goal_rate", "cast_date", "target_time", "total_molds"}
REQUIRED_MAPPING_ROLES = {
    "production": ("job_order", "part_number", "mold_count"),
    "downtime": ("start_clock", "stop_clock", "downtime_code", "cause_text"),
}
PRODUCTION_IMPORT_LABEL_ROLES = {
    "shop order": "job_order",
    "part number": "part_number",
    "molds": "mold_count",
}

_ROLE_SEPARATOR_PATTERN = re.compile(r"[\s\-]+")
_ROLE_INVALID_PATTERN = re.compile(r"[^a-z0-9_]+")


def normalize_role_name(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = _ROLE_SEPARATOR_PATTERN.sub("_", text)
    text = _ROLE_INVALID_PATTERN.sub("", text)
    return re.sub(r"_+", "_", text).strip("_")


def normalize_row_section_name(section_name):
    normalized = normalize_role_name(section_name)
    if normalized.endswith("_row_fields"):
        normalized = normalized[: -len("_row_fields")]
    return normalized


def resolve_header_field_role(field_id, explicit_role=None):
    role_name = normalize_role_name(explicit_role)
    if role_name:
        return role_name
    return HEADER_FIELD_ROLE_DEFAULTS.get(str(field_id or "").strip(), "")


def resolve_row_field_role(section_name, field_id, explicit_role=None):
    role_name = normalize_role_name(explicit_role)
    if role_name:
        return role_name
    normalized_section = normalize_row_section_name(section_name)
    return ROW_FIELD_ROLE_DEFAULTS.get(normalized_section, {}).get(str(field_id or "").strip(), "")


def get_default_header_field_id(role_name):
    return HEADER_FIELD_ID_BY_ROLE.get(normalize_role_name(role_name))


def get_default_row_field_id(section_name, role_name):
    normalized_section = normalize_row_section_name(section_name)
    return ROW_FIELD_ID_BY_ROLE.get(normalized_section, {}).get(normalize_role_name(role_name))