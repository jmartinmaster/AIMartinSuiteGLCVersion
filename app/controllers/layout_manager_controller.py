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
        self.selected_form_id = None
        self.apply_theme()
        self.load_config(initial=True)

    def _apply_loaded_config(self, config, source_path):
        self.model.config_path = source_path
        self.model.mark_clean()
        self._render_config(config, update_editor=True, status_message="Ready", bootstyle=SECONDARY)

    def _refresh_form_selector(self):
        active_form = self.model.get_active_form_info()
        selected_form_id = None
        if getattr(self, "view", None) is not None:
            selected_form_id = self.view.get_selected_form_id() or self.selected_form_id
        self.view.set_form_options(self.model.list_forms(), active_form.get("id"), selected_form_id=selected_form_id)
        self.selected_form_id = self.view.get_selected_form_id() or active_form.get("id")
        return active_form

    def _notify_active_form_changed(self):
        if hasattr(self.dispatcher, "notify_active_form_changed"):
            self.dispatcher.notify_active_form_changed(source_instance=self)

    def _update_layout(self, config, status_message):
        self.model.validate_config(config)
        self.model.mark_dirty()
        self._render_config(config, update_editor=True, status_message=status_message, bootstyle=INFO)

    def _get_source_name(self):
        active_form = self.model.get_active_form_info()
        form_name = active_form.get("name", "Form")
        if self.model.config_path == self.model.internal_config:
            return f"{form_name} (bundled default)"
        return f"{form_name} ({self.model.config_path})"

    def _get_source_label(self):
        active_form = self.model.get_active_form_info()
        form_name = active_form.get("name", "Form")
        form_id = active_form.get("id", "form")
        if self.model.config_path == self.model.internal_config:
            return f"Active form: {form_name} [{form_id}] | Previewing bundled default: {self.model.internal_config}"
        return f"Active form: {form_name} [{form_id}] | Editing source: {self.model.config_path}"

    def _update_status(self, message, bootstyle=SECONDARY):
        self.view.update_status(message, self._get_source_name(), self.model.is_dirty, bootstyle=bootstyle)

    def _render_preview(self, config, bootstyle=SUCCESS):
        self.current_config = config
        self.preview_grid = self.model.build_preview_grid(config)
        self.view.render_preview(self.preview_grid, self.selected_block_item)
        self._update_status(self._build_preview_status_message(config), bootstyle=bootstyle)

    def _build_preview_status_message(self, config, prefix=None):
        field_count = self.preview_grid["field_count"]
        row_count = self.preview_grid["max_row"] + 1
        col_count = self.preview_grid["max_col"] + 1
        production_count = len(config.get("production_row_fields", []))
        downtime_count = len(config.get("downtime_row_fields", []))
        status_message = (
            f"Preview updated: {field_count} header fields on a {row_count}x{col_count} grid, "
            f"{production_count} production row fields, {downtime_count} downtime row fields"
        )
        if prefix:
            return f"{prefix} | {status_message}"
        return status_message

    def _render_config(self, config, update_editor=False, status_message="Ready", bootstyle=SECONDARY):
        self.current_config = config
        self.preview_grid = self.model.build_preview_grid(config)
        if update_editor:
            self.view.set_editor_text(self.model.serialize_config(config))
        self._refresh_form_selector()
        self.view.update_source_label(self._get_source_label())
        self.view.render_block_view(
            config,
            self.model.protected_field_ids,
            self.model.protected_row_field_ids,
            self.selected_block_item,
        )
        self.view.render_preview(self.preview_grid, self.selected_block_item)
        self._update_status(status_message, bootstyle=bootstyle)

    def _parse_editor_config(self):
        return self.model.parse_editor_text(self.view.get_editor_text(), base_config=self.current_config)

    def _resolve_editor_config(self):
        return self.model.resolve_editor_text(self.view.get_editor_text(), base_config=self.current_config)

    def _build_editor_section_message(self, payload_details, action_text):
        applied_sections = payload_details.get("applied_sections", [])
        if payload_details.get("mode") != "section" or not applied_sections:
            return action_text
        section_noun = "section" if len(applied_sections) == 1 else "sections"
        extracted_text = " extracted" if payload_details.get("extracted") else ""
        return f"{action_text} from{extracted_text} {section_noun}: {', '.join(applied_sections)}"

    def get_field_item_key(self, field_id):
        return self.model.get_field_item_key(field_id)

    def get_row_field_item_key(self, section_name, field_id):
        return self.model.get_row_field_item_key(section_name, field_id)

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
            self.view.render_block_view(
                self.current_config,
                self.model.protected_field_ids,
                self.model.protected_row_field_ids,
                self.selected_block_item,
            )
            if self.preview_grid is None:
                self.preview_grid = self.model.build_preview_grid(self.current_config)
            self.view.render_preview(self.preview_grid, self.selected_block_item)

    def on_hide(self):
        return self.view.on_hide()

    def on_active_form_changed(self):
        self._refresh_form_selector()
        if self.model.is_dirty:
            self._update_status("Active form changed elsewhere. Reload to edit the new form.", bootstyle=INFO)
            return
        self.selected_form_id = self.model.get_active_form_info().get("id")
        self.load_config(initial=True)

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
            config, payload_details = self._resolve_editor_config()
            self.model.mark_dirty()
            status_message = self._build_editor_section_message(payload_details, "JSON formatted")
            self._render_config(config, update_editor=True, status_message=status_message, bootstyle=INFO)
        except Exception as exc:
            self.view.show_error("Format Error", f"Unable to format JSON: {exc}")

    def validate_editor_json(self):
        try:
            _config, payload_details = self._resolve_editor_config()
            validation_message = self._build_editor_section_message(payload_details, "Layout JSON is valid")
            self.view.show_validation_success(validation_message)
            self._update_status(validation_message, bootstyle=SUCCESS)
        except Exception as exc:
            self._update_status(f"Validation error: {exc}", bootstyle=DANGER)
            self.view.show_error("Validation Error", f"Layout JSON is invalid: {exc}")

    def update_preview(self):
        try:
            config, payload_details = self._resolve_editor_config()
            preview_message = None
            if payload_details.get("mode") == "section":
                preview_message = self._build_editor_section_message(payload_details, "Preview merged")
            self._render_preview(config)
            if preview_message:
                self._update_status(self._build_preview_status_message(config, prefix=preview_message), bootstyle=SUCCESS)
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

    def add_row_field(self, section_name):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.add_row_field(config, section_name)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not add row field: {exc}")

    def move_header_field(self, field_id, direction):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.move_header_field(config, field_id, direction)
            if status_message is not None:
                self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not reorder header field: {exc}")

    def move_row_field(self, section_name, field_id, direction):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.move_row_field(config, section_name, field_id, direction)
            if status_message is not None:
                self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not reorder row field: {exc}")

    def remove_header_field(self, field_id):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.remove_header_field(config, field_id)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not remove header field: {exc}")

    def remove_row_field(self, section_name, field_id):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.remove_row_field(config, section_name, field_id)
            if self.selected_block_item == self.model.get_row_field_item_key(section_name, field_id):
                self.selected_block_item = None
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Layout Edit Error", f"Could not remove row field: {exc}")

    def update_header_field_from_block(self, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value, role_value):
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
                role_value,
            )
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Block Edit Error", f"Could not update field from block view: {exc}")

    def update_row_field_from_block(self, section_name, field_id, field_values):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.update_row_field(config, section_name, field_id, field_values)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Block Edit Error", f"Could not update row field from block view: {exc}")

    def update_mapping_from_block(self, mapping_name, start_row_value, column_values):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.update_mapping(config, mapping_name, start_row_value, column_values)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Mapping Edit Error", f"Could not update mapping from block view: {exc}")

    def save_config(self):
        try:
            config, payload_details = self._resolve_editor_config()
            backup_info = self.model.save_config(config)
            self.current_config = config
            self.preview_grid = self.model.build_preview_grid(config)
            self.view.update_source_label(self._get_source_label())
            if payload_details.get("mode") == "section":
                self.view.set_editor_text(self.model.serialize_config(config))
            self.view.render_block_view(
                config,
                self.model.protected_field_ids,
                self.model.protected_row_field_ids,
                self.selected_block_item,
            )
            self.view.render_preview(self.preview_grid, self.selected_block_item)
            if payload_details.get("mode") != "section":
                self.view.reset_editor_modified()
            self._update_status(self._build_editor_section_message(payload_details, "Layout saved"), bootstyle=SUCCESS)
            self.view.show_save_success(self.model.save_path, backup_info)
        except Exception as exc:
            self.view.show_error("Error", f"Error saving: {exc}")

    def activate_selected_form(self):
        selected_form_id = self.view.get_selected_form_id()
        if not selected_form_id:
            self.view.show_error("Form Activation", "Select a form definition to activate.")
            return
        if not self.view.confirm_discard_changes(self.model.is_dirty):
            return
        try:
            form_info = self.model.activate_form(selected_form_id)
            self.selected_form_id = form_info.get("id")
            config, source_path = self.model.load_current_config()
            self._apply_loaded_config(config, source_path)
            self._notify_active_form_changed()
            self.view.show_form_activated(form_info)
        except Exception as exc:
            self.view.show_error("Form Activation", f"Could not activate the selected form: {exc}")

    def create_form_from_current(self):
        form_name = self.view.ask_form_name()
        if form_name is None:
            return
        form_name = form_name.strip()
        if not form_name:
            self.view.show_error("Create Form", "Form name is required.")
            return
        try:
            config = self._parse_editor_config()
            form_info = self.model.create_form_from_config(form_name, config, activate=True)
            self.selected_form_id = form_info.get("id")
            config, source_path = self.model.load_current_config()
            self._apply_loaded_config(config, source_path)
            self._notify_active_form_changed()
            self.view.show_form_created(form_info)
        except Exception as exc:
            self.view.show_error("Create Form", f"Could not create a new form: {exc}")

    def rename_selected_form(self):
        selected_form = self.view.get_selected_form_info()
        if not selected_form:
            self.view.show_error("Rename Form", "Select a form definition to rename.")
            return

        new_name = self.view.ask_form_name(
            title="Rename Form",
            prompt="Enter the new name for this form definition:",
            initialvalue=selected_form.get("name", ""),
        )
        if new_name is None:
            return

        new_name = new_name.strip()
        if not new_name:
            self.view.show_error("Rename Form", "Form name is required.")
            return

        try:
            form_info = self.model.rename_form(selected_form.get("id"), new_name, description=selected_form.get("description", ""))
            self.selected_form_id = form_info.get("id")
            self._refresh_form_selector()
            self.view.update_source_label(self._get_source_label())
            self._update_status("Form renamed", bootstyle=SUCCESS)
            if form_info.get("is_active"):
                self._notify_active_form_changed()
            self.view.show_form_renamed(form_info)
        except Exception as exc:
            self.view.show_error("Rename Form", f"Could not rename the selected form: {exc}")

    def duplicate_selected_form(self):
        selected_form = self.view.get_selected_form_info()
        if not selected_form:
            self.view.show_error("Duplicate Form", "Select a form definition to duplicate.")
            return

        duplicate_name = self.view.ask_form_name(
            title="Duplicate Form",
            prompt="Enter a name for the duplicated form definition:",
            initialvalue=f"{selected_form.get('name', 'Form')} Copy",
        )
        if duplicate_name is None:
            return

        duplicate_name = duplicate_name.strip()
        if not duplicate_name:
            self.view.show_error("Duplicate Form", "Form name is required.")
            return

        try:
            form_info = self.model.duplicate_form(
                selected_form.get("id"),
                duplicate_name,
                description=selected_form.get("description", ""),
                activate=True,
            )
            self.selected_form_id = form_info.get("id")
            config, source_path = self.model.load_current_config()
            self._apply_loaded_config(config, source_path)
            self._notify_active_form_changed()
            self.view.show_form_duplicated(form_info)
        except Exception as exc:
            self.view.show_error("Duplicate Form", f"Could not duplicate the selected form: {exc}")

    def delete_selected_form(self):
        selected_form = self.view.get_selected_form_info()
        if not selected_form:
            self.view.show_error("Delete Form", "Select a form definition to delete.")
            return

        if selected_form.get("is_active") and not self.view.confirm_discard_changes(self.model.is_dirty):
            return
        if not self.view.confirm_delete_form(selected_form):
            return

        try:
            result = self.model.delete_form(selected_form.get("id"))
            deleted_form = result.get("deleted_form", {})
            active_form = result.get("active_form", {})
            active_changed = bool(result.get("active_changed"))
            self.selected_form_id = active_form.get("id") or None
            if active_changed:
                config, source_path = self.model.load_current_config()
                self._apply_loaded_config(config, source_path)
                self._notify_active_form_changed()
            else:
                self._refresh_form_selector()
                self.view.update_source_label(self._get_source_label())
                self._update_status("Form deleted", bootstyle=SUCCESS)
            self.view.show_form_deleted(deleted_form, active_form=active_form, active_changed=active_changed)
        except Exception as exc:
            self.view.show_error("Delete Form", f"Could not delete the selected form: {exc}")
