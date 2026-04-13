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
from functools import lru_cache

from app.external_data_registry import ExternalDataRegistry

__module_name__ = "Downtime Codes"
__version__ = "1.1.4"

DEFAULT_DT_CODE_MAP = {
    "1": "Misc Reason",
    "2": "Machine Repairs",
    "3": "Auto Pour",
    "4": "Inoculator",
    "5": "Pattern Repair",
    "6": "No Iron (Cupola)",
    "7": "No Iron (Transfer)",
    "8": "AMC, SBC, Shakeout",
    "9": "Pattern Change",
    "10": "No Sand",
}


@lru_cache(maxsize=1)
def load_code_map():
    code_map = dict(DEFAULT_DT_CODE_MAP)
    loaded = ExternalDataRegistry().load_json("settings", default_factory=dict)
    overrides = loaded.get("downtime_codes", {}) if isinstance(loaded, dict) else {}
    if isinstance(overrides, dict):
        for raw_code, raw_label in overrides.items():
            code = str(raw_code).strip()
            if not code:
                continue
            label = str(raw_label or "").strip()
            if not label:
                continue
            code_map[code] = label
    return code_map


def clear_downtime_code_cache():
    load_code_map.cache_clear()


def get_code_lookup():
    ordered = sorted(load_code_map().items(), key=lambda item: (int(item[0]) if str(item[0]).isdigit() else float("inf"), str(item[0])))
    return {code: f"{code} {label}" for code, label in ordered}


def get_code_options():
    return list(get_code_lookup().values())


def normalize_code_value(value):
    text = str(value or "").strip()
    if not text:
        return ""

    code_lookup = get_code_lookup()
    code_map = load_code_map()

    def iter_code_candidates(raw_text):
        candidates = []

        def add_candidate(candidate):
            normalized = str(candidate or "").strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        add_candidate(raw_text)

        leading = []
        for char in raw_text:
            if char.isdigit():
                leading.append(char)
            else:
                break
        if leading:
            leading_text = "".join(leading)
            add_candidate(leading_text)
            add_candidate(leading_text.lstrip("0") or "0")

        try:
            numeric_value = float(raw_text)
        except (TypeError, ValueError):
            numeric_value = None

        if numeric_value is not None and numeric_value.is_integer():
            integer_text = str(int(numeric_value))
            add_candidate(integer_text)
            add_candidate(integer_text.lstrip("0") or "0")

        return candidates

    for code in iter_code_candidates(text):
        if code in code_lookup:
            return code_lookup[code]

    lowered = text.lower()
    for code, label in code_map.items():
        if lowered == label.lower():
            return f"{code} {label}"
    return text


def get_code_number(value):
    normalized = normalize_code_value(value)
    if not normalized:
        return ""
    return normalized.split(" ", 1)[0]