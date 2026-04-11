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
from ttkbootstrap.constants import DANGER, INFO, SECONDARY, SUCCESS

from app.models.layout_manager_model import LayoutManagerModel
from app.theme_manager import get_theme_tokens
from app.views.layout_manager_view import LayoutManagerView


class LayoutManagerController:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = LayoutManagerModel()
        self.view = LayoutManagerView(parent, dispatcher, self)
        self.current_config = None
        self.preview_grid = None
        self.selected_block_item = None
        self.apply_theme()
        self.load_config(initial=True)

    def _apply_loaded_config(self, config, source_path):
        self.model.config_path = source_path
        self.model.mark_clean()
        self._render_config(config, update_editor=True, status_message="Ready", bootstyle=SECONDARY)

    def _update_layout(self, config, status_message):
        self.model.validate_config(config)
        self.model.mark_dirty()
        self._render_config(config, update_editor=True, status_message=status_message, bootstyle=INFO)

    def _get_source_name(self):
        if self.model.config_path == self.model.local_config:
            return self.model.local_config
        return self.model.internal_config.rsplit("/", 1)[-1]

    def _get_source_label(self):
        if self.model.config_path == self.model.local_config:
            return f"Editing local config: {self.model.local_config}"
        return f"Editing packaged default: {self.model.internal_config}"

    def _update_status(self, message, bootstyle=SECONDARY):
        self.view.update_status(message, self._get_source_name(), self.model.is_dirty, bootstyle=bootstyle)

    def _render_preview(self, config, bootstyle=SUCCESS):
        self.current_config = config
        self.preview_grid = self.model.build_preview_grid(config)
        self.view.render_preview(self.preview_grid, self.selected_block_item)
        field_count = self.preview_grid["field_count"]
        row_count = self.preview_grid["max_row"] + 1
        col_count = self.preview_grid["max_col"] + 1
        self._update_status(f"Preview updated: {field_count} header fields on a {row_count}x{col_count} grid", bootstyle=bootstyle)

    def _render_config(self, config, update_editor=False, status_message="Ready", bootstyle=SECONDARY):
        self.current_config = config
        self.preview_grid = self.model.build_preview_grid(config)
        if update_editor:
            self.view.set_editor_text(self.model.serialize_config(config))
        self.view.update_source_label(self._get_source_label())
        self.view.render_block_view(config, self.model.protected_field_ids, self.selected_block_item)
        self.view.render_preview(self.preview_grid, self.selected_block_item)
        self._update_status(status_message, bootstyle=bootstyle)

    def _parse_editor_config(self):
        return self.model.parse_editor_text(self.view.get_editor_text())

    def get_field_item_key(self, field_id):
        return self.model.get_field_item_key(field_id)

    def get_mapping_item_key(self, mapping_name):
        return self.model.get_mapping_item_key(mapping_name)

    def handle_editor_modified(self):
        self.model.mark_dirty()
        self._update_status("Unsaved changes", bootstyle=SECONDARY)

    def select_block_item(self, item_key, scroll=False):
        self.selected_block_item = item_key
        self.view.apply_selection(item_key, scroll=scroll)

    def apply_theme(self):
        root = self.parent.winfo_toplevel()
        self.view.apply_theme(get_theme_tokens(root=root))
        if self.current_config is not None:
            self.view.render_block_view(self.current_config, self.model.protected_field_ids, self.selected_block_item)
            if self.preview_grid is None:
                self.preview_grid = self.model.build_preview_grid(self.current_config)
            self.view.render_preview(self.preview_grid, self.selected_block_item)

    def on_hide(self):
        return self.view.on_hide()

    def on_unload(self):
        return self.view.on_unload()

    def load_config(self, initial=False):
        if not initial and not self.view.confirm_discard_changes(self.model.is_dirty):
            return
        try:
            config, source_path = self.model.load_current_config()
            self._apply_loaded_config(config, source_path)
        except Exception as exc:
            self.view.show_error("Load Error", f"Failed to load layout config: {exc}")

    def load_default_config(self):
        if not self.view.confirm_discard_changes(self.model.is_dirty):
            return
        try:
            config, source_path = self.model.load_default_config()
            self._apply_loaded_config(config, source_path)
        except Exception as exc:
            self.view.show_error("Load Error", f"Failed to load default layout config: {exc}")

    def format_json(self):
        try:
            config = self._parse_editor_config()
            self.model.mark_dirty()
            self._render_config(config, update_editor=True, status_message="JSON formatted", bootstyle=INFO)
        except Exception as exc:
            self.view.show_error("Format Error", f"Unable to format JSON: {exc}")

    def validate_editor_json(self):
        try:
            self._parse_editor_config()
            self.view.show_validation_success()
            self._update_status("Layout JSON is valid", bootstyle=SUCCESS)
        except Exception as exc:
            self._update_status(f"Validation error: {exc}", bootstyle=DANGER)
            self.view.show_error("Validation Error", f"Layout JSON is invalid: {exc}")

    def update_preview(self):
        try:
            config = self._parse_editor_config()
            self._render_preview(config)
        except Exception as exc:
            self.view.show_preview_error(str(exc))
            self._update_status(f"Preview error: {exc}", bootstyle=DANGER)

    def add_header_field(self):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.add_header_field(config)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not add header field: {exc}")

    def move_header_field(self, field_id, direction):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.move_header_field(config, field_id, direction)
            if status_message is not None:
                self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not reorder header field: {exc}")

    def remove_header_field(self, field_id):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.remove_header_field(config, field_id)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not remove header field: {exc}")

    def update_header_field_from_block(self, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value):
        try:
            config = self._parse_editor_config()
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
            config = self._parse_editor_config()
            updated_config, status_message = self.model.update_mapping(config, mapping_name, start_row_value, column_values)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Mapping Edit Error", f"Could not update mapping from block view: {exc}")

    def save_config(self):
        try:
            config = self._parse_editor_config()
            backup_info = self.model.save_config(config)
            self.current_config = config
            self.preview_grid = self.model.build_preview_grid(config)
            self.view.update_source_label(self._get_source_label())
            self.view.render_block_view(config, self.model.protected_field_ids, self.selected_block_item)
            self.view.render_preview(self.preview_grid, self.selected_block_item)
            self.view.reset_editor_modified()
            self._update_status("Layout saved", bootstyle=SUCCESS)
            self.view.show_save_success(self.model.save_path, backup_info)
        except Exception as exc:
            self.view.show_error("Error", f"Error saving: {exc}")
