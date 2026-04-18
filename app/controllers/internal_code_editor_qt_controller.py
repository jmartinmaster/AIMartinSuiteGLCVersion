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
import time

from app.models.internal_code_editor_model import InternalCodeEditorModel
from app.views.internal_code_editor_qt_view import InternalCodeEditorQtView

__module_name__ = "Internal Code Editor Qt Controller"
__version__ = "1.0.0"


class InternalCodeEditorQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        bundled_path = str(self.payload.get("bundled_app_path") or "")
        external_path = str(self.payload.get("external_app_path") or bundled_path)
        self.model = InternalCodeEditorModel(bundled_path, external_path)
        self.current_analysis = {"definitions": [], "parse_error": None}
        self.view = InternalCodeEditorQtView(self, self.payload)
        self.refresh_file_list()
        self.write_state(status="ready", message="Internal Code Editor Qt window ready.", dirty=False)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False):
        if not self.state_path:
            return
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": "internal_code_editor",
            "current_file": self.model.current_file_key,
            "updated_at": time.time(),
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def refresh_file_list(self, selected_key=None, preferred_path=None):
        entries = self.model.refresh_file_entries()
        if not entries:
            self.view.set_file_options([], None)
            self.view.set_editor_text("")
            self.view.update_file_details("No Python files found.", "")
            self.view.update_status("No files available")
            self.write_state(status="ready", message="No files available.", dirty=False)
            return

        target_key = selected_key if selected_key and self.model.get_file_entry(selected_key) else self.model.current_file_key
        if preferred_path:
            preferred_entry = self.model.get_file_entry_by_path(preferred_path) or self.model.get_file_entry_by_save_path(preferred_path)
            if preferred_entry is not None:
                target_key = preferred_entry["key"]
        if target_key is None:
            target_key = entries[0]["key"]
        self.load_file(target_key, refresh_selector=True)

    def on_file_selected(self):
        selected_key = self.view.get_selected_file_key()
        if not selected_key or selected_key == self.model.current_file_key:
            return
        if self.model.is_dirty and not self.view.confirm_discard_changes():
            self.view.select_file_key(self.model.current_file_key)
            return
        self.load_file(selected_key, refresh_selector=False)

    def load_file(self, file_key, refresh_selector):
        previous_key = self.model.current_file_key
        entry = self.model.get_file_entry(file_key)
        if entry is None:
            self.view.update_status("Selected file is no longer available")
            self.view.select_file_key(previous_key)
            return
        try:
            file_text = self.model.load_file_text(file_key)
        except (OSError, ValueError) as exc:
            self.view.show_error("Load Error", f"Failed to load file:\n{exc}")
            self.view.update_status(f"Load failed: {exc}")
            self.view.select_file_key(previous_key)
            return

        self.model.set_current_file(file_key)
        self.model.mark_clean()
        self.view.set_file_options(self.model.file_entries, entry["key"] if refresh_selector else None)
        self.view.select_file_key(entry["key"])
        self.view.set_editor_text(file_text)
        self.refresh_editor_analysis(file_text)
        self.view.update_file_details(self._build_source_text(entry), self._build_save_target_text(entry))
        self.view.update_status(f"Loaded {entry['relative_path']}")
        self.write_state(status="ready", message=f"Loaded {entry['relative_path']}", dirty=False)

    def reload_current_file(self):
        entry = self.model.get_current_file_entry()
        if entry is None:
            return
        if self.model.is_dirty and not self.view.confirm_discard_changes():
            return
        self.load_file(entry["key"], refresh_selector=False)

    def save_current_file(self):
        entry = self.model.get_current_file_entry()
        if entry is None:
            self.view.update_status("No file selected")
            return
        try:
            saved_path = self.model.save_current_file_text(self.view.get_editor_text())
        except (OSError, ValueError) as exc:
            self.view.show_error("Save Error", f"Failed to save file:\n{exc}")
            self.view.update_status(f"Save failed: {exc}")
            self.write_state(status="ready", message=f"Save failed: {exc}", dirty=True)
            return

        selected_entry = self.model.get_file_entry_by_path(saved_path) or self.model.get_file_entry_by_save_path(saved_path)
        self.refresh_file_list(selected_key=selected_entry["key"] if selected_entry else None, preferred_path=saved_path)
        target_entry = self.model.get_current_file_entry()
        if target_entry is not None:
            self.view.update_status(f"Saved {target_entry['relative_path']}")
            self.write_state(status="ready", message=f"Saved {target_entry['relative_path']}", dirty=False)

    def handle_editor_modified(self):
        self.model.mark_dirty()
        entry = self.model.get_current_file_entry()
        if entry is None:
            message = "Unsaved changes"
        else:
            message = f"Editing {entry['relative_path']} | Unsaved changes"
        self.view.update_status(message)
        self.write_state(status="ready", message=message, dirty=True)

    def refresh_editor_analysis(self, source_text=None):
        editor_text = self.view.get_editor_text() if source_text is None else source_text
        self.current_analysis = self.model.build_editor_analysis(editor_text)
        definition_entries = self.current_analysis["definitions"]
        self.view.set_definition_entries(definition_entries)
        self.view.update_definition_summary(len(definition_entries), self.current_analysis["parse_error"])

    def on_definition_selected(self):
        definition_key = self.view.get_selected_definition_key()
        if not definition_key:
            return
        definition_entry = self._get_definition_entry(definition_key)
        if definition_entry is None:
            return
        self.view.show_definition_location(definition_entry)
        self.view.update_status(
            f"Jumped to {definition_entry['kind']} {definition_entry['qualified_name']} at line {definition_entry['line']}"
        )

    def find_next(self):
        self._find_match(backwards=False)

    def find_previous(self):
        self._find_match(backwards=True)

    def _find_match(self, backwards):
        search_text = self.view.get_search_text()
        if not search_text.strip():
            self.view.update_status("Enter search text first")
            self.view.focus_search()
            return
        match_found = self.view.find_text(search_text, backwards=backwards)
        if not match_found:
            self.view.update_status(f"No matches for '{search_text}'")
            return
        direction_text = "Previous" if backwards else "Next"
        self.view.update_status(f"{direction_text} match: {search_text}")

    def _get_definition_entry(self, definition_key):
        for entry in self.current_analysis.get("definitions", []):
            if entry["key"] == definition_key:
                return entry
        return None

    def _build_source_text(self, entry):
        source_label = entry["source_name"].title()
        return f"Viewing: {entry['relative_path']} | Source: {source_label} | Path: {entry['path']}"

    def _build_save_target_text(self, entry):
        if self.model.bundled_app_path != self.model.external_app_path and entry["source_name"] == "bundled":
            return f"Save target: {entry['save_path']} | Bundled files may be read-only in packaged builds."
        return f"Save target: {entry['save_path']}"

    def poll_commands(self):
        if not self.command_path or not os.path.exists(self.command_path):
            return
        try:
            with open(self.command_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            payload = {}
        try:
            os.remove(self.command_path)
        except OSError:
            pass

        action = str(payload.get("action") or "").strip().lower()
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Internal Code Editor Qt window.", dirty=self.model.is_dirty)
        elif action == "save_current_file":
            self.save_current_file()
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="Internal Code Editor Qt window closed.", dirty=self.model.is_dirty)
