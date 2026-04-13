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
from app.form_definition_registry import FormDefinitionRegistry
from app.persistence import write_json_with_backup
from app.utils import resource_path


class LayoutConfigService:
    def __init__(self):
        self.data_registry = ExternalDataRegistry()
        self.registry = FormDefinitionRegistry()
        self.local_config = self.data_registry.resolve_write_path("layout_config")
        self.internal_config = resource_path("layout_config.json")
        self.active_form_info = None
        self.config_path = None
        self.save_path = None
        self._refresh_active_form_info()

    def _refresh_active_form_info(self):
        self.active_form_info = self.registry.get_active_form()
        self.config_path = self.active_form_info["load_path"]
        self.save_path = self.active_form_info["save_path"]
        return self.active_form_info

    def get_active_form_info(self):
        return dict(self._refresh_active_form_info())

    def list_forms(self):
        return self.registry.list_forms()

    def activate_form(self, form_id):
        form_info = self.registry.activate_form(form_id)
        self._refresh_active_form_info()
        return form_info

    def create_form(self, name, config, description="", activate=False):
        form_info = self.registry.create_form(name, config, description=description, activate=activate)
        self._refresh_active_form_info()
        return form_info

    def rename_form(self, form_id, name, description=None):
        form_info = self.registry.rename_form(form_id, name, description=description)
        self._refresh_active_form_info()
        return form_info

    def duplicate_form(self, source_form_id, name, description=None, activate=False):
        form_info = self.registry.duplicate_form(source_form_id, name, description=description, activate=activate)
        self._refresh_active_form_info()
        return form_info

    def delete_form(self, form_id):
        result = self.registry.delete_form(form_id)
        self._refresh_active_form_info()
        return result

    def read_config(self, file_path):
        with open(file_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def load_current(self):
        self._refresh_active_form_info()
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Layout config was not found: {self.config_path}")
        return self.read_config(self.config_path), self.config_path

    def load_default(self):
        if not os.path.exists(self.internal_config):
            raise FileNotFoundError(f"Default layout config was not found: {self.internal_config}")
        return self.read_config(self.internal_config), self.internal_config

    def save_config(self, config):
        form_info = self._refresh_active_form_info()
        backup_info = write_json_with_backup(
            self.save_path,
            config,
            backup_dir=form_info["backup_dir"],
            keep_count=12,
        )
        self.config_path = self.save_path
        return backup_info
