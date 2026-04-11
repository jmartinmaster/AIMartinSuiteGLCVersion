import json
import os

from app.persistence import write_json_with_backup
from app.utils import external_path, local_or_resource_path


class RateManagerModel:
    def __init__(self):
        self.data_file = local_or_resource_path("rates.json")
        self.save_path = external_path("rates.json")
        self.rates = self.load_data()
        self.editing_part = None

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    return {str(part): str(rate) for part, rate in loaded.items()}
            except Exception:
                return {}
        return {}

    def save_data(self):
        backup_info = write_json_with_backup(
            self.save_path,
            self.rates,
            backup_dir=external_path("data/backups/rates"),
            keep_count=12,
        )
        self.data_file = self.save_path
        return backup_info

    def get_filtered_rates(self, search_text):
        search = str(search_text or "").lower()
        filtered = []
        for part, rate in self.rates.items():
            part_str = str(part)
            if search in part_str.lower():
                filtered.append((part_str, str(rate)))
        return filtered

    def begin_edit(self, part_key):
        if part_key not in self.rates:
            raise ValueError("Select a valid rate row before editing.")
        self.editing_part = str(part_key)
        return self.editing_part, str(self.rates[self.editing_part])

    def cancel_edit(self):
        self.editing_part = None

    def save_edit(self, new_rate):
        if not self.editing_part:
            raise ValueError("No rate is currently being edited.")
        cleaned_rate = str(new_rate or "").strip()
        if not cleaned_rate:
            raise ValueError("Rate cannot be empty.")
        self.rates[str(self.editing_part)] = cleaned_rate
        self.save_data()
        self.editing_part = None

    def add_rate(self, part, rate):
        cleaned_part = str(part or "").strip()
        cleaned_rate = str(rate or "").strip()
        if not cleaned_part or not cleaned_rate:
            raise ValueError("Part number and rate are required.")
        self.rates[cleaned_part] = cleaned_rate
        self.save_data()

    def delete_rate(self, part_key):
        if part_key not in self.rates:
            raise ValueError("Select a valid rate row before deleting.")
        del self.rates[part_key]
        self.save_data()
