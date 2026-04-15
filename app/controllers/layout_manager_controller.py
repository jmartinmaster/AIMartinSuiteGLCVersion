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
from app.views.layout_manager_qt_view import launch_layout_manager_qt_probe
from app.views.layout_manager_view_contract import LayoutManagerViewContract
from app.views.layout_manager_view_factory import create_layout_manager_view


class LayoutManagerController:
    def __init__(self, parent, dispatcher, view_factory=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = LayoutManagerModel()
        self.current_config = None
        self.preview_grid = None
        self.selected_block_item = None
        self.selected_form_id = None
        self.loaded_form_info = None
        self.pending_active_form_info = None
        self.requested_view_backend = "tk"
        self.resolved_view_backend = "tk"
        self.view_backend_fallback_reason = None
        self.view_factory = view_factory or create_layout_manager_view
        self.view: LayoutManagerViewContract = self.view_factory(parent, dispatcher, self)
        self.apply_theme()
        self.load_config(initial=True)

    def _get_preloaded_payload(self):
        if not hasattr(self.dispatcher, "consume_layout_manager_preload"):
            return None
        payload = self.dispatcher.consume_layout_manager_preload()
        if not isinstance(payload, dict):
            return None
        active_form = self.model.get_active_form_info()
        if payload.get("form_id") != active_form.get("id"):
            return None
        return payload

    def _get_loaded_form_info(self):
        if isinstance(self.loaded_form_info, dict):
            return dict(self.loaded_form_info)
        return self.model.get_active_form_info()

    def _set_loaded_form_info(self, form_info):
        self.loaded_form_info = dict(form_info) if isinstance(form_info, dict) else None

    def _has_external_active_form_change(self):
        loaded_form_id = self._get_loaded_form_info().get("id")
        active_form_id = self.model.get_active_form_info().get("id")
        return bool(loaded_form_id and active_form_id and loaded_form_id != active_form_id)

    def _apply_loaded_config(
        self,
        config,
        source_path,
        loaded_form_info=None,
        save_path=None,
        preview_grid=None,
        guardrails=None,
        protected_row_field_lookup=None,
    ):
        self.model.config_path = source_path
        if save_path is not None:
            self.model.current_save_path = save_path
        self._set_loaded_form_info(loaded_form_info or self.model.get_active_form_info())
        self.pending_active_form_info = None
        self.selected_form_id = self._get_loaded_form_info().get("id")
        self.model.mark_clean()
        self._render_config(
            config,
            update_editor=True,
            status_message="Ready",
            bootstyle=SECONDARY,
            preview_grid=preview_grid,
            guardrails=guardrails,
            protected_row_field_lookup=protected_row_field_lookup,
        )

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
        loaded_form = self._get_loaded_form_info()
        form_name = loaded_form.get("name", "Form")
        if self.model.config_path == self.model.internal_config:
            return f"{form_name} (bundled default)"
        if self._has_external_active_form_change():
            return f"{form_name} (stale active form)"
        return f"{form_name} ({self.model.config_path})"

    def _get_source_label(self):
        loaded_form = self._get_loaded_form_info()
        active_form = self.model.get_active_form_info()
        form_name = loaded_form.get("name", "Form")
        form_id = loaded_form.get("id", "form")
        if self.model.config_path == self.model.internal_config:
            source_label = f"Loaded form: {form_name} [{form_id}] | Previewing bundled default: {self.model.internal_config}"
        else:
            source_label = f"Loaded form: {form_name} [{form_id}] | Editing source: {self.model.config_path}"
        if active_form.get("id") != form_id:
            active_name = active_form.get("name", "Form")
            active_id = active_form.get("id", "form")
            source_label += f" | Active elsewhere: {active_name} [{active_id}]"
        return source_label

    def _update_status(self, message, bootstyle=SECONDARY):
        self.view.update_status(message, self._get_source_name(), self.model.is_dirty, bootstyle=bootstyle)

    def _render_preview(self, config, bootstyle=SUCCESS):
        self.current_config = config
        self.preview_grid = self.model.build_preview_grid(config)
        self.view.render_preview(self.preview_grid, self.selected_block_item)
        self._update_status(self._build_preview_status_message(config), bootstyle=bootstyle)

    def _render_visible_tabs(self, config, guardrails=None):
        active_tab = self.view.get_active_editor_tab()
        resolved_guardrails = guardrails or self.model.build_editor_guardrails(config)
        if active_tab == "import_export":
            self.view.render_import_export(config, self.selected_block_item, resolved_guardrails)
        elif active_tab == "preview":
            if self.preview_grid is None:
                self.preview_grid = self.model.build_preview_grid(config)
            self.view.render_preview(self.preview_grid, self.selected_block_item)

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

    def _render_config(
        self,
        config,
        update_editor=False,
        status_message="Ready",
        bootstyle=SECONDARY,
        preview_grid=None,
        guardrails=None,
        protected_row_field_lookup=None,
    ):
        self.current_config = config
        self.preview_grid = preview_grid
        resolved_protected_row_field_lookup = protected_row_field_lookup or self.model.get_protected_row_field_lookup(config)
        resolved_guardrails = guardrails or self.model.build_editor_guardrails(config)
        if update_editor:
            self.view.set_editor_text(self.model.serialize_config(config))
        self._refresh_form_selector()
        self.view.update_source_label(self._get_source_label())
        self.view.render_block_view(
            config,
            self.model.protected_field_ids,
            resolved_protected_row_field_lookup,
            self.selected_block_item,
            resolved_guardrails,
        )
        self._render_visible_tabs(config, guardrails=resolved_guardrails)
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

    def update_section_metadata_from_block(self, section_id, section_values):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.update_section_metadata(config, section_id, section_values)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Section Edit Error", f"Could not update section metadata: {exc}")

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
            protected_row_field_lookup = self.model.get_protected_row_field_lookup(self.current_config)
            guardrails = self.model.build_editor_guardrails(self.current_config)
            self.view.render_block_view(
                self.current_config,
                self.model.protected_field_ids,
                protected_row_field_lookup,
                self.selected_block_item,
                guardrails,
            )
            self._render_visible_tabs(self.current_config)

    def handle_editor_tab_changed(self):
        if self.current_config is None:
            return
        active_tab = self.view.get_active_editor_tab()
        if active_tab == "import_export":
            guardrails = self.model.build_editor_guardrails(self.current_config)
            self.view.render_import_export(self.current_config, self.selected_block_item, guardrails)
            return
        if active_tab == "preview":
            self.update_preview()

    def on_hide(self):
        return self.view.on_hide()

    def on_active_form_changed(self):
        active_form = self.model.get_active_form_info()
        loaded_form = self._get_loaded_form_info()
        loaded_form_id = loaded_form.get("id")
        active_form_id = active_form.get("id")
        if self.model.is_dirty and loaded_form_id and active_form_id != loaded_form_id:
            self.pending_active_form_info = dict(active_form)
            self.selected_form_id = loaded_form_id
            self._refresh_form_selector()
            self.view.update_source_label(self._get_source_label())
            self._update_status(
                "Active form changed elsewhere. Current edits stay bound to the loaded form until you save or use Reload Current.",
                bootstyle=INFO,
            )
            return
        self.pending_active_form_info = None
        self.selected_form_id = active_form_id
        self.load_config(initial=True)

    def on_unload(self):
        return self.view.on_unload()

    def load_config(self, initial=False):
        if not initial and not self.view.confirm_discard_changes(self.model.is_dirty):
            return
        try:
            preloaded_payload = self._get_preloaded_payload()
            if preloaded_payload is not None:
                self._apply_loaded_config(
                    preloaded_payload["config"],
                    preloaded_payload["source_path"],
                    loaded_form_info=preloaded_payload.get("form_info"),
                    save_path=preloaded_payload.get("save_path"),
                    preview_grid=preloaded_payload.get("preview_grid"),
                    guardrails=preloaded_payload.get("guardrails"),
                    protected_row_field_lookup=preloaded_payload.get("protected_row_field_lookup"),
                )
                return
            config, source_path, form_info = self.model.load_current_config()
            self._apply_loaded_config(config, source_path, loaded_form_info=form_info)
        except Exception as exc:
            self.view.show_error("Load Error", f"Failed to load layout config: {exc}")

    def load_default_config(self):
        if not self.view.confirm_discard_changes(self.model.is_dirty):
            return
        try:
            config, source_path, form_info = self.model.load_default_config()
            self._apply_loaded_config(config, source_path, loaded_form_info=form_info)
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

    def launch_qt_probe(self):
        try:
            config, _payload_details = self._resolve_editor_config()
            root = self.parent.winfo_toplevel()
            loaded_form = self._get_loaded_form_info()
            launch_layout_manager_qt_probe(
                {
                    "window_title": "Layout Manager PyQt6 Probe",
                    "requested_backend": self.requested_view_backend,
                    "resolved_backend": self.resolved_view_backend,
                    "form_name": loaded_form.get("name", "Form"),
                    "form_id": loaded_form.get("id", "form"),
                    "source_label": self._get_source_label(),
                    "theme_tokens": get_theme_tokens(root=root),
                    "serialized_config": self.model.serialize_config(config),
                }
            )
            self._update_status("Opened PyQt6 probe window", bootstyle=SUCCESS)
        except Exception as exc:
            self.view.show_error("PyQt6 Probe", f"Could not open the PyQt6 probe window: {exc}")

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

    def update_header_field_from_block(self, field_id, row_value, col_value, cell_value, width_value, readonly_value, default_value, role_value, import_enabled_value, export_enabled_value):
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
                import_enabled_value,
                export_enabled_value,
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

    def update_mapping_from_block(self, mapping_name, start_row_value, max_rows_value, column_values):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.update_mapping(config, mapping_name, start_row_value, max_rows_value, column_values)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Mapping Edit Error", f"Could not update import/export mapping: {exc}")

    def update_template_path_from_tab(self, template_path_value):
        try:
            config = self._parse_editor_config()
            updated_config, status_message = self.model.update_template_path(config, template_path_value)
            self._update_layout(updated_config, status_message)
        except Exception as exc:
            self.view.show_error("Template Path Error", f"Could not update the export template path: {exc}")

    def save_config(self):
        try:
            config, payload_details = self._resolve_editor_config()
            loaded_form = self._get_loaded_form_info()
            backup_info = self.model.save_config(config, form_info=loaded_form)
            self.current_config = config
            self.preview_grid = None
            self.selected_form_id = loaded_form.get("id")
            self._refresh_form_selector()
            self.view.update_source_label(self._get_source_label())
            if payload_details.get("mode") == "section":
                self.view.set_editor_text(self.model.serialize_config(config))
            protected_row_field_lookup = self.model.get_protected_row_field_lookup(config)
            guardrails = self.model.build_editor_guardrails(config)
            self.view.render_block_view(
                config,
                self.model.protected_field_ids,
                protected_row_field_lookup,
                self.selected_block_item,
                guardrails,
            )
            self._render_visible_tabs(config)
            if payload_details.get("mode") != "section":
                self.view.reset_editor_modified()
            status_message = self._build_editor_section_message(payload_details, "Layout saved")
            if self._has_external_active_form_change():
                status_message += " | Active form changed elsewhere; use Reload Current to switch the editor"
            self._update_status(status_message, bootstyle=SUCCESS)
            if hasattr(self.dispatcher, "invalidate_layout_manager_preload"):
                self.dispatcher.invalidate_layout_manager_preload()
            if hasattr(self.dispatcher, "schedule_layout_manager_preload"):
                self.dispatcher.schedule_layout_manager_preload(force=True)
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
            if hasattr(self.dispatcher, "invalidate_layout_manager_preload"):
                self.dispatcher.invalidate_layout_manager_preload()
            config, source_path, loaded_form_info = self.model.load_current_config()
            self._apply_loaded_config(config, source_path, loaded_form_info=loaded_form_info)
            self._notify_active_form_changed()
            self.view.show_form_activated(form_info)
        except Exception as exc:
            self.view.show_error("Form Activation", f"Could not activate the selected form: {exc}")

    def create_form_from_current(self):
        form_details = self.view.ask_form_details(
            title="Create Form",
            name_prompt="Enter a name for the new form definition:",
            default_activate=True,
        )
        if form_details is None:
            return
        form_name = form_details.get("name", "").strip()
        if not form_name:
            self.view.show_error("Create Form", "Form name is required.")
            return
        try:
            config = self._parse_editor_config()
            form_info = self.model.create_form_from_config(
                form_name,
                config,
                description=form_details.get("description", ""),
                activate=bool(form_details.get("activate", True)),
            )
            self.selected_form_id = form_info.get("id")
            if hasattr(self.dispatcher, "invalidate_layout_manager_preload"):
                self.dispatcher.invalidate_layout_manager_preload()
            if form_info.get("is_active"):
                config, source_path, loaded_form_info = self.model.load_current_config()
                self._apply_loaded_config(config, source_path, loaded_form_info=loaded_form_info)
                self._notify_active_form_changed()
            else:
                self._refresh_form_selector()
                self.view.update_source_label(self._get_source_label())
                self._update_status("Form created", bootstyle=SUCCESS)
                if hasattr(self.dispatcher, "schedule_layout_manager_preload"):
                    self.dispatcher.schedule_layout_manager_preload(force=True)
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
            if hasattr(self.dispatcher, "invalidate_layout_manager_preload"):
                self.dispatcher.invalidate_layout_manager_preload()
            self._refresh_form_selector()
            self.view.update_source_label(self._get_source_label())
            self._update_status("Form renamed", bootstyle=SUCCESS)
            if hasattr(self.dispatcher, "schedule_layout_manager_preload"):
                self.dispatcher.schedule_layout_manager_preload(force=True)
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

        form_details = self.view.ask_form_details(
            title="Duplicate Form",
            name_prompt="Enter a name for the duplicated form definition:",
            initial_name=f"{selected_form.get('name', 'Form')} Copy",
            initial_description=selected_form.get("description", ""),
            default_activate=True,
        )
        if form_details is None:
            return

        duplicate_name = form_details.get("name", "").strip()
        if not duplicate_name:
            self.view.show_error("Duplicate Form", "Form name is required.")
            return

        try:
            form_info = self.model.duplicate_form(
                selected_form.get("id"),
                duplicate_name,
                description=form_details.get("description", selected_form.get("description", "")),
                activate=bool(form_details.get("activate", True)),
            )
            self.selected_form_id = form_info.get("id")
            if hasattr(self.dispatcher, "invalidate_layout_manager_preload"):
                self.dispatcher.invalidate_layout_manager_preload()
            if form_info.get("is_active"):
                config, source_path, loaded_form_info = self.model.load_current_config()
                self._apply_loaded_config(config, source_path, loaded_form_info=loaded_form_info)
                self._notify_active_form_changed()
            else:
                self._refresh_form_selector()
                self.view.update_source_label(self._get_source_label())
                self._update_status("Form duplicated", bootstyle=SUCCESS)
                if hasattr(self.dispatcher, "schedule_layout_manager_preload"):
                    self.dispatcher.schedule_layout_manager_preload(force=True)
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
            if hasattr(self.dispatcher, "invalidate_layout_manager_preload"):
                self.dispatcher.invalidate_layout_manager_preload()
            if active_changed:
                config, source_path, loaded_form_info = self.model.load_current_config()
                self._apply_loaded_config(config, source_path, loaded_form_info=loaded_form_info)
                self._notify_active_form_changed()
            else:
                self._refresh_form_selector()
                self.view.update_source_label(self._get_source_label())
                self._update_status("Form deleted", bootstyle=SUCCESS)
                if hasattr(self.dispatcher, "schedule_layout_manager_preload"):
                    self.dispatcher.schedule_layout_manager_preload(force=True)
            self.view.show_form_deleted(deleted_form, active_form=active_form, active_changed=active_changed)
        except Exception as exc:
            self.view.show_error("Delete Form", f"Could not delete the selected form: {exc}")
