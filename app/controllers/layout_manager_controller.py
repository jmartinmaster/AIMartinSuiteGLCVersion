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
from app.models.layout_manager_model import LayoutManagerModel
from app.views.layout_manager_view import LayoutManagerView


class LayoutManagerController:
    def __init__(self, parent, dispatcher):
        self.model = LayoutManagerModel()
        self.view = LayoutManagerView(parent, dispatcher, self, self.model)
        self.load_config(initial=True)

    def __getattr__(self, attribute_name):
        return getattr(self.view, attribute_name)

    def _apply_loaded_config(self, config, source_path):
        self.model.config_path = source_path
        self.view.set_editor_text(config, mark_clean=True)
        self.view.refresh_block_view(config)
        self.view.update_source_label()
        self.view.update_preview()

    def _update_layout(self, config, status_message):
        self.model.validate_config(config)
        self.model.mark_dirty()
        self.view.build_layout_update(config, status_message)

    def load_config(self, initial=False):
        if not initial and not self.view.confirm_discard_changes():
            return
        try:
            config, source_path = self.model.load_current_config()
            self._apply_loaded_config(config, source_path)
        except Exception as exc:
            self.view.show_error("Load Error", f"Failed to load layout config: {exc}")

    def load_default_config(self):
        if not self.view.confirm_discard_changes():
            return
        try:
            config, source_path = self.model.load_default_config()
            self._apply_loaded_config(config, source_path)
        except Exception as exc:
            self.view.show_error("Load Error", f"Failed to load default layout config: {exc}")

    def format_json(self):
        try:
            config = self.view.get_current_config()
            self.view.set_editor_text(config, mark_clean=False)
            self.view.refresh_block_view(config)
            self.view.update_preview()
            self.model.mark_dirty()
            self.view.update_status("JSON formatted", bootstyle="info")
        except Exception as exc:
            self.view.show_error("Format Error", f"Unable to format JSON: {exc}")

    def validate_editor_json(self):
        try:
            self.view.get_current_config()
            self.view.show_validation_success()
        except Exception as exc:
            self.view.update_status(f"Validation error: {exc}", bootstyle="danger")
            self.view.show_error("Validation Error", f"Layout JSON is invalid: {exc}")

    def update_preview(self):
        self.view.update_preview()

    def add_header_field(self):
        try:
            config = self.view.get_current_config()
            updated_config, status_message = self.model.add_header_field(config)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not add header field: {exc}")

    def move_header_field(self, field_id, direction):
        try:
            config = self.view.get_current_config()
            updated_config, status_message = self.model.move_header_field(config, field_id, direction)
            if status_message is not None:
                self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not reorder header field: {exc}")

    def remove_header_field(self, field_id):
        try:
            config = self.view.get_current_config()
            updated_config, status_message = self.model.remove_header_field(config, field_id)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not remove header field: {exc}")

    def update_header_field_from_block(self, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value):
        try:
            config = self.view.get_current_config()
            updated_config, status_message = self.model.update_header_field(
                config,
                field_id,
                row_value,
                col_value,
                cell_value,
                width_value,
                readonly_value,
                default_value,
            )
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Block Edit Error", f"Could not update field from block view: {exc}")

    def update_mapping_from_block(self, mapping_name, start_row_value, column_values):
        try:
            config = self.view.get_current_config()
            updated_config, status_message = self.model.update_mapping(config, mapping_name, start_row_value, column_values)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Mapping Edit Error", f"Could not update mapping from block view: {exc}")

    def save_config(self):
        try:
            config = self.view.get_current_config()
            backup_info = self.model.save_config(config)
            self.view.update_source_label()
            self.view.show_save_success(self.model.save_path, backup_info)
            self.view.update_preview()
        except Exception as exc:
            self.view.show_error("Error", f"Error saving: {exc}")
