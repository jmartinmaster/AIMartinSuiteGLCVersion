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

from app.external_data_registry import ExternalDataRegistry


class RateManagerModel:
    def __init__(self):
        self.data_registry = ExternalDataRegistry()
        self.data_file = self.data_registry.resolve_read_path("rates")
        self.save_path = self.data_registry.resolve_write_path("rates")
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
        backup_info = self.data_registry.save_json("rates", self.rates, keep_count=12)
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
