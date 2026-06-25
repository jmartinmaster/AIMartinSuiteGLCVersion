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
    import json
    import os
    from app.utils import external_data_path, ensure_external_data_directory

    # Try loading from options source directory first
    dir_path = external_data_path("forms/op_source")
    path = os.path.join(dir_path, "downtime_codes.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cleaned = {}
                    for k, v in data.items():
                        cleaned[str(k).strip()] = str(v).strip()
                    return cleaned
        except Exception:
            pass

    # Legacy settings load or default fallback
    code_map = dict(DEFAULT_DT_CODE_MAP)
    try:
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
    except Exception:
        pass

    # Auto-initialize the file so it can be edited
    try:
        ensure_external_data_directory("forms/op_source")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(code_map, f, indent=4)
    except Exception:
        pass

    return code_map


def clear_downtime_code_cache():
    load_code_map.cache_clear()


def get_available_options_sources():
    import os
    from app.utils import external_data_path
    sources = ["", "downtime_codes"]
    dir_path = external_data_path("forms/op_source")
    if os.path.exists(dir_path):
        try:
            for f in os.listdir(dir_path):
                if f.endswith(".json"):
                    name = f[:-5]
                    if name not in sources:
                        sources.append(name)
        except Exception:
            pass
    return sorted(list(set(sources)))


def load_generic_options_source(source_name):
    import json
    import os
    from app.utils import external_data_path

    if not source_name:
        return {}
    if source_name == "downtime_codes":
        return load_code_map()

    path = os.path.join(external_data_path("forms/op_source"), f"{source_name}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cleaned = {}
                    for k, v in data.items():
                        cleaned[str(k).strip()] = str(v).strip()
                    return cleaned
        except Exception:
            pass
    return {}


def save_generic_options_source(source_name, data):
    import json
    import os
    from app.utils import ensure_external_data_directory

    if not source_name:
        return
    dir_path = ensure_external_data_directory("forms/op_source")
    path = os.path.join(dir_path, f"{source_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    if source_name == "downtime_codes":
        clear_downtime_code_cache()


def get_code_lookup():
    ordered = sorted(load_code_map().items(), key=lambda item: (int(item[0]) if str(item[0]).isdigit() else float("inf"), str(item[0])))
    return {code: f"{code} {label}" for code, label in ordered}


def get_code_options():
    return list(get_code_lookup().values())


def get_generic_options(source_name):
    if not source_name:
        return []
    source_map = load_generic_options_source(source_name)
    ordered = sorted(source_map.items(), key=lambda item: (int(item[0]) if str(item[0]).isdigit() else float("inf"), str(item[0])))
    return [f"{code} {label}".strip() for code, label in ordered]


def normalize_code_value(value):
    return normalize_generic_code_value(value, "downtime_codes")


def normalize_generic_code_value(value, source_name):
    text = str(value or "").strip()
    if not text:
        return ""

    code_map = load_generic_options_source(source_name)
    code_lookup = {code: f"{code} {label}" for code, label in code_map.items()}

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


def format_generic_code_for_export(value, source_name, mode):
    if not value:
        return ""
    code_map = load_generic_options_source(source_name)
    text = str(value).strip()
    parts = text.split(" ", 1)
    code = parts[0]
    description = parts[1] if len(parts) > 1 else ""

    if code in code_map:
        description = code_map[code]
    else:
        found = False
        for c, d in code_map.items():
            if text == d:
                code = c
                description = d
                found = True
                break
        if not found:
            pass

    if mode == "code":
        return code
    elif mode == "description":
        return description
    elif mode == "both":
        return f"{code} {description}".strip() if code or description else text
    return code