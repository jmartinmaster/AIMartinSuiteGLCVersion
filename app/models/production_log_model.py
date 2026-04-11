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
from datetime import datetime

from app.downtime_codes import get_code_options
from app.persistence import write_json_with_backup
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

    def load_layout_config(self):
        with open(self.config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def normalize_header_data(self, header_data):
        return self.data_handler.normalize_header_data(header_data)

    def compute_target_time(self, raw_hours):
        return self.data_handler.compute_target_time(raw_hours)

    def serialize_ui_data(self, data):
        return json.dumps(data, sort_keys=True, default=str)

    def is_form_blank(self, data):
        header = data.get("header", {})
        significant_header_values = [
            value for key, value in header.items()
            if key not in {"hours", "goal_mph", "cast_date", "target_time", "total_molds"} and str(value).strip()
        ]
        production_has_data = any(
            any(str(row.get(key, "")).strip() for key in ("shop_order", "part_number", "molds"))
            for row in data.get("production", [])
        )
        downtime_has_data = any(
            any(str(row.get(key, "")).strip() for key in ("start", "stop", "code", "cause"))
            for row in data.get("downtime", [])
        )
        return not significant_header_values and not production_has_data and not downtime_has_data

    def load_settings(self):
        settings = {
            "auto_save_interval_min": 5,
            "default_shift_hours": 8.0,
            "default_goal_mph": 240.0,
        }
        settings_path = external_path("settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass

        try:
            settings["auto_save_interval_min"] = max(1, int(settings.get("auto_save_interval_min", 5)))
        except Exception:
            settings["auto_save_interval_min"] = 5

        try:
            settings["default_shift_hours"] = float(settings.get("default_shift_hours", 8.0))
        except Exception:
            settings["default_shift_hours"] = 8.0

        try:
            settings["default_goal_mph"] = float(settings.get("default_goal_mph", 240.0))
        except Exception:
            settings["default_goal_mph"] = 240.0

        return settings

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

    def build_draft_payload(self, data, version, draft_path, is_auto=False):
        return {
            "meta": {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "auto_save": is_auto,
                "version": version,
                "draft_name": os.path.basename(draft_path),
            },
            **data,
        }

    def save_draft_data(self, data, version, is_auto=False):
        draft_path = self.build_draft_path(data.get("header", {}))
        payload = self.build_draft_payload(data, version, draft_path, is_auto=is_auto)
        backup_info = write_json_with_backup(
            draft_path,
            payload,
            backup_dir=self.get_pending_history_dir(),
            keep_count=20,
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
        return max(0, int((molds / rate) * 60))

    def calculate_shift_total_minutes(self, hours_value):
        try:
            return int(round(float(hours_value or 0) * 60))
        except Exception:
            return 0

    def calculate_efficiency(self, total_molds, hours_value, goal_value):
        try:
            hours = float(hours_value or 8.0)
            goal = float(goal_value or 240.0)
        except Exception:
            return 0.0
        if not hours or not goal:
            return 0.0
        return (float(total_molds) / (hours * goal)) * 100

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
        if stop_minutes < start_minutes:
            stop_minutes += 24 * 60
        return stop_minutes - start_minutes

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
        return shift_total_minutes - production_total_minutes - downtime_total_minutes

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
