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

from app.persistence import write_json_with_backup
from app.utils import external_path, local_or_resource_path, resource_path


class LayoutConfigService:
    def __init__(self):
        self.local_config = external_path("layout_config.json")
        self.internal_config = resource_path("layout_config.json")
        self.config_path = local_or_resource_path("layout_config.json")
        self.save_path = self.local_config

    def read_config(self, file_path):
        with open(file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def load_current(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Layout config was not found: {self.config_path}")
        return self.read_config(self.config_path), self.config_path

    def load_default(self):
        if not os.path.exists(self.internal_config):
            raise FileNotFoundError(f"Default layout config was not found: {self.internal_config}")
        return self.read_config(self.internal_config), self.internal_config

    def save_config(self, config):
        backup_info = write_json_with_backup(
            self.save_path,
            config,
            backup_dir=external_path("data/backups/layouts"),
            keep_count=12,
        )
        self.config_path = self.save_path
        return backup_info
