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
from copy import deepcopy

from app.layout_config_service import LayoutConfigService
from app.models.layout_manager_model import LayoutManagerModel, DEFAULT_MAPPING_MAX_ROWS

__module_name__ = "Form Wizard Model"
__version__ = "1.0.1"


class FormWizardModel:
    def __init__(self):
        self.service = LayoutConfigService()
        self.layout_manager = LayoutManagerModel()
        
        # State of the form being configured
        self.form_name = ""
        self.description = ""
        self.template_path = ""
        
        self.sections = []
        self.single_sections = {}     # maps fields_key to list of fields
        self.repeating_sections = {}  # maps section_id/fields_key to list of columns

        # Load standard defaults initially
        self.load_defaults()

    def load_defaults(self):
        default_config = self.layout_manager._get_default_config_template()
        self.template_path = str(default_config.get("template_path", ""))
        self.sections = deepcopy(default_config.get("sections", []))
        
        for section in self.sections:
            section_type = section.get("section_type") or "single"
            fields_key = section.get("fields_key")
            if not fields_key and section.get("id") == "header":
                fields_key = "header_fields"
                section["fields_key"] = fields_key
                
            if section_type == "repeating":
                if fields_key in default_config:
                    self.repeating_sections[fields_key] = deepcopy(default_config[fields_key])
            elif section_type == "single":
                if fields_key in default_config:
                    self.single_sections[fields_key] = deepcopy(default_config[fields_key])

    def get_sections(self):
        return self.sections

    def set_sections(self, sections):
        self.sections = sections

    def get_single_fields(self, fields_key):
        return self.single_sections.get(fields_key, [])

    def set_single_fields(self, fields_key, fields):
        self.single_sections[fields_key] = fields

    def get_repeating_fields(self, fields_key):
        return self.repeating_sections.get(fields_key, [])

    def set_repeating_fields(self, fields_key, fields):
        self.repeating_sections[fields_key] = fields

    def build_config(self):
        config = {
            "template_path": self.template_path,
            "sections": self.sections,
            "editor_presets": {},
            "calculations": {},
        }
        
        for section in self.sections:
            section_type = section.get("section_type") or "single"
            fields_key = section.get("fields_key")
            
            if section_type == "repeating":
                mapping_key = section.get("mapping_key") or f"{section.get('id')}_mapping"
                
                # Fetch fields
                row_fields = self.repeating_sections.get(fields_key, [])
                config[fields_key] = row_fields
                
                # Generate mapping automatically
                config[mapping_key] = self.layout_manager._build_blank_mapping(mapping_key, row_fields)
            elif section_type == "single":
                single_fields = self.single_sections.get(fields_key, [])
                config[fields_key] = single_fields
                
        return config

    def create_form(self, name, description="", activate=False):
        self.form_name = name
        self.description = description
        config = self.build_config()
        
        # Prepopulate calculations metadata
        form_id = self.service.registry.canonical_form_id(name) or self.service.registry.normalize_form_id(name)
        config = self.service.registry._ensure_calculation_metadata(config, form_id)
        
        self.layout_manager.validate_config(config)
        form_info = self.service.create_form(name, config, description=description, activate=activate)
        return form_info
