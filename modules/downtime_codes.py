import json
import os
from functools import lru_cache


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


def external_path(relative_path):
    return os.path.join(os.path.abspath("."), relative_path)


@lru_cache(maxsize=1)
def load_code_map():
    code_map = dict(DEFAULT_DT_CODE_MAP)
    settings_path = external_path("settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as handle:
                loaded = json.load(handle)
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
    return code_map


def clear_downtime_code_cache():
    load_code_map.cache_clear()


def get_code_lookup():
    ordered = sorted(load_code_map().items(), key=lambda item: (int(item[0]) if str(item[0]).isdigit() else float('inf'), str(item[0])))
    return {code: f"{code} {label}" for code, label in ordered}


def get_code_options():
    return list(get_code_lookup().values())


def normalize_code_value(value):
    text = str(value or "").strip()
    if not text:
        return ""

    code_lookup = get_code_lookup()
    code_map = load_code_map()

    leading = []
    for char in text:
        if char.isdigit():
            leading.append(char)
        else:
            break
    if leading:
        code = "".join(leading)
        return code_lookup.get(code, text)

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