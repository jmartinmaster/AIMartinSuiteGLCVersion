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
import time
from pathlib import Path

from app.models.layout_manager_model import LayoutManagerModel
from app.views.layout_manager_qt_view import LayoutManagerQtView

__module_name__ = "Layout Manager Qt Controller"
__version__ = "0.3.1"


class LayoutManagerQtController:
    def __init__(self, session_payload):
        payload = dict(session_payload or {})
        self.payload = payload
        self.model = LayoutManagerModel()
        self.state_path = Path(payload["state_path"])
        self.command_path = Path(payload["command_path"])
        self.change_token = 0
        self.toast_token = 0
        self.dirty = False
        self.current_form_info = dict(payload.get("form_info") or {})
        self.current_config = dict(payload.get("config") or {})
        self.current_source_path = payload.get("source_path") or ""
        self.guardrails = payload.get("guardrails") or {}
        self.protected_row_field_lookup = payload.get("protected_row_field_lookup") or {}
        self.view = LayoutManagerQtView(controller=self, theme_tokens=payload.get("theme_tokens") or {})

        if not self.current_config:
            self.current_config, self.current_source_path, self.current_form_info = self.model.load_current_config()
            self.guardrails = self.model.build_editor_guardrails(self.current_config)
            self.protected_row_field_lookup = self.model.get_protected_row_field_lookup(self.current_config)

        self.forms = []
        self.refresh_forms()
        self.refresh_view(reason="Loaded layout manager session")
        self.write_state(status="running", message="Layout Manager Qt window is ready.")

    def show(self):
        self.view.show()
        self.view.raise_window()
        self.write_state(status="running", message="Layout Manager Qt window is visible.")

    def apply_theme(self, theme_tokens):
        self.payload["theme_tokens"] = dict(theme_tokens or {})
        self.view.set_theme_tokens(self.payload["theme_tokens"])
        self.write_state(message="Applied updated theme tokens.")

    def refresh_forms(self):
        self.forms = list(self.model.list_forms())
        self.view.set_forms(self.forms, self.current_form_info.get("id"))

    def refresh_view(self, reason=""):
        serialized_config = self.model.serialize_config(self.current_config)
        preview_grid = self.model.build_preview_grid(self.current_config)
        self.guardrails = self.model.build_editor_guardrails(self.current_config)
        self.protected_row_field_lookup = self.model.get_protected_row_field_lookup(self.current_config)
        self.view.set_editor_text(serialized_config)
        self.view.render_block_authoring(self.current_config)
        self.view.render_import_export_authoring(self.current_config)
        self.view.render_preview_grid(preview_grid)
        self.view.render_structure(
            self.current_config,
            self.guardrails,
            self.protected_row_field_lookup,
        )
        self.view.update_header(
            form_info=self.current_form_info,
            source_path=self.current_source_path,
            reason=reason,
        )
        self.view.set_dirty(self.dirty)

    def write_state(self, status="running", message="", toast_event=None):
        state = {
            "status": status,
            "dirty": self.dirty,
            "change_token": self.change_token,
            "form_id": self.current_form_info.get("id"),
            "form_name": self.current_form_info.get("name"),
            "source_path": self.current_source_path,
            "message": message,
            "updated_at": time.time(),
        }
        if isinstance(toast_event, dict):
            state["toast_event"] = toast_event
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _emit_host_toast(self, message, bootstyle="info", title="Layout Manager", duration_ms=None):
        self.toast_token += 1
        toast_payload = {
            "token": self.toast_token,
            "title": str(title or "Layout Manager"),
            "message": str(message or ""),
            "bootstyle": str(bootstyle or "info"),
            "duration_ms": duration_ms,
        }
        self.write_state(message=str(message or ""), toast_event=toast_payload)

    def mark_dirty(self):
        if self.dirty:
            return
        self.dirty = True
        self.model.mark_dirty()
        self.view.set_dirty(True)
        self.write_state(message="Unsaved Qt layout changes are present.")

    def mark_clean(self, message):
        self.dirty = False
        self.model.mark_clean()
        self.change_token += 1
        self.view.set_dirty(False)
        self.view.set_status(message)
        self.write_state(message=message)

    def apply_editor_changes(self, message=None):
        config, _payload_details = self.model.resolve_editor_text(
            self.view.editor_text(),
            base_config=self.current_config,
        )
        self.current_config = config
        self.refresh_view(reason=message or "Applied editor changes")
        self.mark_dirty()
        return config

    def _load_editor_config(self):
        return self.model.parse_editor_text(self.view.editor_text(), base_config=self.current_config)

    def _apply_layout_update(self, updated_config, status_message):
        self.current_config = updated_config
        self.refresh_view(reason=status_message)
        self.mark_dirty()
        self.view.set_status(status_message)

    def validate_editor(self):
        self.model.resolve_editor_text(
            self.view.editor_text(),
            base_config=self.current_config,
        )
        self.view.set_status("JSON is valid.")
        self._emit_host_toast("Layout JSON is valid.", bootstyle="success")

    def format_editor(self):
        self.apply_editor_changes(message="Formatted editor JSON")
        self.view.set_status("Editor JSON was normalized and reformatted.")

    def on_row_section_changed(self, *_args):
        self.view.render_row_fields_authoring(self.current_config)

    def on_mapping_section_changed(self, *_args):
        self.view.render_mapping_authoring(self.current_config)

    def add_header_field_from_block(self):
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.add_header_field(config)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def remove_header_field_from_block(self):
        field_id = self.view.selected_header_field_id()
        if not field_id:
            self.view.set_status("Select a header field to remove.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.remove_header_field(config, field_id)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def move_header_field_up_from_block(self):
        self._move_header_field_from_block(-1)

    def move_header_field_down_from_block(self):
        self._move_header_field_from_block(1)

    def _move_header_field_from_block(self, direction):
        field_id = self.view.selected_header_field_id()
        if not field_id:
            self.view.set_status("Select a header field to move.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.move_header_field(config, field_id, direction)
            if status_message is not None:
                self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def apply_header_field_from_block(self):
        field_id = self.view.selected_header_field_id()
        field_values = self.view.selected_header_field_values()
        if not field_id or field_values is None:
            self.view.set_status("Select a header field to apply.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_header_field(
                config,
                field_id,
                field_values["row"],
                field_values["col"],
                field_values["cell"],
                field_values["width"],
                field_values["readonly"],
                field_values["default"],
                field_values["role"],
                field_values["import_enabled"],
                field_values["export_enabled"],
            )
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def add_row_field_from_block(self):
        section_name = self.view.current_row_section_name()
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.add_row_field(config, section_name)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def remove_row_field_from_block(self):
        section_name = self.view.current_row_section_name()
        field_id = self.view.selected_row_field_id()
        if not field_id:
            self.view.set_status("Select a row field to remove.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.remove_row_field(config, section_name, field_id)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def move_row_field_up_from_block(self):
        self._move_row_field_from_block(-1)

    def move_row_field_down_from_block(self):
        self._move_row_field_from_block(1)

    def _move_row_field_from_block(self, direction):
        section_name = self.view.current_row_section_name()
        field_id = self.view.selected_row_field_id()
        if not field_id:
            self.view.set_status("Select a row field to move.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.move_row_field(config, section_name, field_id, direction)
            if status_message is not None:
                self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def apply_row_field_from_block(self):
        section_name = self.view.current_row_section_name()
        field_id = self.view.selected_row_field_id()
        field_values = self.view.selected_row_field_values()
        if not field_id or field_values is None:
            self.view.set_status("Select a row field to apply.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_row_field(config, section_name, field_id, field_values)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def apply_template_path_from_import_export(self):
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_template_path(config, self.view.template_path_value())
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Import/export error: {exc}", error=True)

    def apply_mapping_from_import_export(self):
        mapping_name = self.view.current_mapping_name()
        mapping_values = self.view.mapping_form_values()
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_mapping(
                config,
                mapping_name,
                mapping_values["start_row"],
                mapping_values["max_rows"],
                mapping_values["columns"],
            )
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Import/export error: {exc}", error=True)

    def reload_current(self):
        config, source_path, form_info = self.model.load_current_config()
        self.current_config = config
        self.current_source_path = source_path
        self.current_form_info = dict(form_info)
        self.refresh_forms()
        self.dirty = False
        self.refresh_view(reason="Reloaded active layout from disk")
        self.write_state(message="Reloaded active layout from disk.")

    def load_default(self):
        config, source_path = self.model.load_default_config()
        self.current_config = config
        self.current_source_path = source_path
        self.current_form_info = dict(self.model.get_active_form_info())
        self.refresh_forms()
        self.mark_dirty()
        self.refresh_view(reason="Loaded default layout template")
        self.write_state(message="Loaded default layout template.")

    def save_current(self):
        config = self.apply_editor_changes(message="Prepared layout for save")
        backup_info = self.model.save_config(config, form_info=self.current_form_info)
        self.current_source_path = self.current_form_info.get("save_path", self.current_source_path)
        backup_path = ""
        if isinstance(backup_info, dict):
            backup_path = backup_info.get("backup_path") or ""
        message = "Saved current layout configuration."
        if backup_path:
            message = f"Saved current layout configuration. Backup: {backup_path}"
        self.mark_clean(message)
        self.refresh_forms()
        self.refresh_view(reason="Saved current layout configuration")
        self._emit_host_toast(message, bootstyle="success")

    def activate_selected_form(self):
        form_id = self.view.current_form_id()
        if not form_id:
            self.view.set_status("Select a form to activate.", error=True)
            return
        self.apply_editor_changes(message="Prepared layout before activation")
        form_info = self.model.activate_form(form_id)
        self.current_form_info = dict(form_info)
        self.current_config, self.current_source_path, self.current_form_info = self.model.load_current_config()
        self.refresh_forms()
        action_message = f"Activated form '{self.current_form_info.get('name', form_id)}'."
        self.mark_clean(action_message)
        self.refresh_view(reason="Activated selected form")
        self._emit_host_toast(action_message, bootstyle="success")

    def create_form(self):
        name = self.view.prompt_text("Create Form", "Form name:")
        if not name:
            return
        description = self.view.prompt_text("Create Form", "Description:", default_text="") or ""
        config = self.apply_editor_changes(message="Prepared layout for new form")
        form_info = self.model.create_form_from_config(name, config, description=description, activate=False)
        self.current_form_info = dict(form_info)
        self.refresh_forms()
        action_message = f"Created form '{form_info.get('name', name)}'."
        self.mark_clean(action_message)
        self.refresh_view(reason="Created new form from editor")
        self._emit_host_toast(action_message, bootstyle="success")

    def duplicate_form(self):
        source_form_id = self.view.current_form_id() or self.current_form_info.get("id")
        if not source_form_id:
            self.view.set_status("Select a form to duplicate.", error=True)
            return
        default_name = f"{self.current_form_info.get('name', source_form_id)} Copy"
        name = self.view.prompt_text("Duplicate Form", "Duplicate form name:", default_text=default_name)
        if not name:
            return
        description = self.view.prompt_text("Duplicate Form", "Description:", default_text="") or ""
        form_info = self.model.duplicate_form(source_form_id, name, description=description, activate=False)
        self.current_form_info = dict(form_info)
        self.refresh_forms()
        action_message = f"Duplicated form '{name}'."
        self.mark_clean(action_message)
        self.refresh_view(reason="Duplicated selected form")
        self._emit_host_toast(action_message, bootstyle="success")

    def rename_form(self):
        form_id = self.view.current_form_id() or self.current_form_info.get("id")
        if not form_id:
            self.view.set_status("Select a form to rename.", error=True)
            return
        current_name = self.current_form_info.get("name", form_id)
        name = self.view.prompt_text("Rename Form", "New form name:", default_text=current_name)
        if not name:
            return
        description = self.view.prompt_text(
            "Rename Form",
            "Description:",
            default_text=self.current_form_info.get("description", ""),
        )
        form_info = self.model.rename_form(form_id, name, description=description)
        self.current_form_info = dict(form_info)
        self.refresh_forms()
        self.refresh_view(reason="Renamed selected form")
        action_message = f"Renamed form to '{name}'."
        self.view.set_status(action_message)
        self._emit_host_toast(action_message, bootstyle="success")

    def delete_form(self):
        form_id = self.view.current_form_id() or self.current_form_info.get("id")
        if not form_id:
            self.view.set_status("Select a form to delete.", error=True)
            return
        form_name = self.current_form_info.get("name", form_id)
        if not self.view.confirm(
            "Delete Form",
            f"Delete '{form_name}'? This removes the stored layout form.",
        ):
            return
        result = self.model.delete_form(form_id)
        self.current_config, self.current_source_path, self.current_form_info = self.model.load_current_config()
        self.refresh_forms()
        action_message = result or f"Deleted form '{form_name}'."
        self.mark_clean(action_message)
        self.refresh_view(reason="Deleted selected form")
        self._emit_host_toast(action_message, bootstyle="success")

    def poll_commands(self):
        if not self.command_path.exists():
            return
        try:
            command = json.loads(self.command_path.read_text(encoding="utf-8"))
        except Exception:
            return
        action = str(command.get("action") or "").strip().lower()
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        if not action:
            return
        try:
            self.command_path.unlink(missing_ok=True)
        except Exception:
            pass
        if action == "raise_window":
            self.view.raise_window()
            self.write_state(message="Raised Layout Manager Qt window.")
        elif action == "apply_theme":
            self.apply_theme(payload.get("theme_tokens") or {})
        elif action == "reload_from_disk":
            self.reload_current()
        elif action == "close_window":
            self.view.close()

    def can_close(self):
        if not self.dirty:
            return True
        return self.view.confirm(
            "Unsaved Changes",
            "Close the Qt layout manager and discard unsaved changes?",
        )

    def handle_close(self):
        self.write_state(status="closed", message="Layout Manager Qt window closed.")
