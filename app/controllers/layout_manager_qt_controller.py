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
__version__ = "0.2.0"


class LayoutManagerQtController:
    def __init__(self, session_payload):
        payload = dict(session_payload or {})
        self.payload = payload
        self.model = LayoutManagerModel()
        self.state_path = Path(payload["state_path"])
        self.command_path = Path(payload["command_path"])
        self.change_token = 0
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

    def refresh_forms(self):
        self.forms = list(self.model.list_forms())
        self.view.set_forms(self.forms, self.current_form_info.get("id"))

    def refresh_view(self, reason=""):
        serialized_config = self.model.serialize_config(self.current_config)
        preview_grid = self.model.build_preview_grid(self.current_config)
        self.guardrails = self.model.build_editor_guardrails(self.current_config)
        self.protected_row_field_lookup = self.model.get_protected_row_field_lookup(self.current_config)
        self.view.set_editor_text(serialized_config)
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

    def write_state(self, status="running", message=""):
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
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

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

    def validate_editor(self):
        self.model.resolve_editor_text(
            self.view.editor_text(),
            base_config=self.current_config,
        )
        self.view.set_status("JSON is valid.")
        self.write_state(message="JSON validation passed.")

    def format_editor(self):
        self.apply_editor_changes(message="Formatted editor JSON")
        self.view.set_status("Editor JSON was normalized and reformatted.")

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
        self.mark_clean(f"Activated form '{self.current_form_info.get('name', form_id)}'.")
        self.refresh_view(reason="Activated selected form")

    def create_form(self):
        name = self.view.prompt_text("Create Form", "Form name:")
        if not name:
            return
        description = self.view.prompt_text("Create Form", "Description:", default_text="") or ""
        config = self.apply_editor_changes(message="Prepared layout for new form")
        form_info = self.model.create_form_from_config(name, config, description=description, activate=False)
        self.current_form_info = dict(form_info)
        self.refresh_forms()
        self.mark_clean(f"Created form '{form_info.get('name', name)}'.")
        self.refresh_view(reason="Created new form from editor")

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
        self.mark_clean(f"Duplicated form '{name}'.")
        self.refresh_view(reason="Duplicated selected form")

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
        self.write_state(message=f"Renamed form '{name}'.")
        self.view.set_status(f"Renamed form to '{name}'.")

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
        self.mark_clean(result or f"Deleted form '{form_name}'.")
        self.refresh_view(reason="Deleted selected form")

    def poll_commands(self):
        if not self.command_path.exists():
            return
        try:
            command = json.loads(self.command_path.read_text(encoding="utf-8"))
        except Exception:
            return
        action = str(command.get("action") or "").strip().lower()
        if not action:
            return
        try:
            self.command_path.unlink(missing_ok=True)
        except Exception:
            pass
        if action == "raise_window":
            self.view.raise_window()
            self.write_state(message="Raised Layout Manager Qt window.")
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
