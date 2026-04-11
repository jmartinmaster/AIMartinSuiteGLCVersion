import json
import os
import re
from datetime import datetime

from app.downtime_codes import get_code_options
from app.utils import external_path, local_or_resource_path
from app.data_handler_service import DataHandlerService

BALANCE_DOWNTIME_CAUSE = "Time Balance Adjustment"
DEFAULT_GHOST_LABEL = "Ghost Time: 0 min"


class ProductionLogModel:
    def __init__(self):
        self.config_path = local_or_resource_path("layout_config.json")
        self.dt_codes = get_code_options()
        self.data_handler = DataHandlerService()
        self.settings = self.load_settings()
        self.default_hours = str(self.settings.get("default_shift_hours", 8.0))
        self.default_goal = str(self.settings.get("default_goal_mph", 240))
        self.auto_save_interval = int(self.settings.get("auto_save_interval_min", 5)) * 60000

    def load_settings(self):
        settings_path = external_path("settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    return loaded
            except Exception:
                pass
        return {}

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
        raw_date = str(header_data.get("date", "unsaved") or "unsaved").replace("/", "-")
        shift_str = str(header_data.get("shift", "0") or "0")
        filename = f"draft_{raw_date}_shift{shift_str}.json"
        return os.path.join(self.get_pending_dir(), filename)

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
                saved_at = meta.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
                header = data.get("header", {})
                drafts.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": saved_at,
                    "date": header.get("date", ""),
                    "shift": header.get("shift", ""),
                })
            except Exception:
                drafts.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
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
                saved_at = meta.get("saved_at") or datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
                header = data.get("header", {})
                snapshots.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": saved_at,
                    "date": header.get("date", ""),
                    "shift": header.get("shift", ""),
                    "source": "Recovery Snapshot",
                })
            except Exception:
                snapshots.append({
                    "path": path,
                    "filename": filename,
                    "saved_at": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
                    "date": "",
                    "shift": "",
                    "source": "Recovery Snapshot",
                })
        snapshots.sort(key=lambda item: item["saved_at"], reverse=True)
        return snapshots

    def get_latest_pending_draft(self):
        drafts = self.list_pending_drafts()
        return drafts[0] if drafts else None

    def load_rates_data(self):
        rates_data = {}
        rates_path = local_or_resource_path("rates.json")
        if os.path.exists(rates_path):
            try:
                with open(rates_path, "r", encoding="utf-8") as rate_file:
                    loaded_rates = json.load(rate_file)
                if isinstance(loaded_rates, dict):
                    for part_number, rate in loaded_rates.items():
                        for lookup_key in self.build_part_lookup_keys(part_number):
                            if lookup_key not in rates_data:
                                rates_data[lookup_key] = rate
            except Exception:
                pass
        return rates_data

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

    def strip_leading_zeros_from_segments(self, value):
        def replace_match(match):
            digits = match.group(0)
            stripped = digits.lstrip("0")
            return stripped or "0"

        return re.sub(r"\d+", replace_match, value)

    def build_part_lookup_keys(self, value):
        normalized = self.normalize_part_number(value)
        if not normalized:
            return []

        candidates = []
        compact = normalized.replace(" ", "")
        zero_normalized = self.strip_leading_zeros_from_segments(normalized)
        zero_compact = self.strip_leading_zeros_from_segments(compact)

        for candidate in (normalized, compact, zero_normalized, zero_compact):
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
            raw_rate = global_goal
        try:
            return float(raw_rate)
        except Exception:
            return None

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

    def format_clock_value(self, total_minutes):
        normalized = int(total_minutes) % (24 * 60)
        return f"{normalized // 60:02}{normalized % 60:02}"
