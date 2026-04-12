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
from copy import deepcopy
import json
import os

from app.models.production_log_model import DEFAULT_CALCULATION_SETTINGS, ProductionLogModel
from app.persistence import write_json_with_backup
from app.utils import external_path

__module_name__ = "Production Log Calculations"
__version__ = "1.0.0"


class ProductionLogCalculationsModel:
    def __init__(self):
        self.settings_path = external_path("production_log_calculations.json")
        self.production_log_model = ProductionLogModel()
        self.settings = self.production_log_model.get_calculation_settings_copy()

    def get_settings_copy(self):
        return deepcopy(self.settings)

    def get_default_settings(self):
        return deepcopy(DEFAULT_CALCULATION_SETTINGS)

    def reload_settings(self):
        self.settings = self.production_log_model.refresh_calculation_settings()
        return self.get_settings_copy()

    def normalize_settings(self, payload=None):
        return self.production_log_model.normalize_calculation_settings(payload)

    def update_settings(self, payload):
        self.settings = self.normalize_settings(payload)
        return self.get_settings_copy()

    def load_settings_file(self):
        if not os.path.exists(self.settings_path):
            return self.get_default_settings()
        try:
            with open(self.settings_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            payload = {}
        self.settings = self.normalize_settings(payload)
        return self.get_settings_copy()

    def save_settings_with_backup(self):
        backup_info = write_json_with_backup(
            self.settings_path,
            self.settings,
            backup_dir=external_path("data/backups/production_log_calculations"),
            keep_count=12,
        )
        return backup_info