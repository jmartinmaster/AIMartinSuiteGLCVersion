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
from ttkbootstrap.constants import DANGER, SECONDARY, SUCCESS

from app.models.internal_code_editor_model import InternalCodeEditorModel
from app.views.internal_code_editor_view import InternalCodeEditorView

__module_name__ = "Internal Code Editor"
__version__ = "0.1.0"


class InternalCodeEditorController:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = InternalCodeEditorModel(dispatcher.modules_path, dispatcher.external_modules_path)
        self.view = InternalCodeEditorView(parent, dispatcher, self)
        self.current_analysis = {"definitions": [], "parse_error": None}
        self.apply_theme()
        self.refresh_file_list()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def apply_theme(self):
        self.view.apply_theme()

    def refresh_file_list(self, selected_key=None, preferred_path=None):
        entries = self.model.refresh_file_entries()
        if not entries:
            self.view.set_file_options([], None)
            self.view.set_editor_text("")
            self.view.update_file_details("No Python files found.", "")
            self.view.update_status("No files available", bootstyle=DANGER)
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
            self.view.update_status("Selected file is no longer available", bootstyle=DANGER)
            self.view.select_file_key(previous_key)
            return
        try:
            file_text = self.model.load_file_text(file_key)
        except (OSError, ValueError) as exc:
            self.view.show_error("Load Error", f"Failed to load file:\n{exc}")
            self.view.update_status(f"Load failed: {exc}", bootstyle=DANGER)
            self.view.select_file_key(previous_key)
            return
        self.model.set_current_file(file_key)
        self.model.mark_clean()
        self.view.set_file_options(self.model.file_entries, entry["key"] if refresh_selector else None)
        self.view.select_file_key(entry["key"])
        self.view.set_editor_text(file_text)
        self.refresh_editor_analysis(file_text)
        self.view.update_file_details(self._build_source_text(entry), self._build_save_target_text(entry))
        self.view.update_status(f"Loaded {entry['relative_path']}", bootstyle=SECONDARY)

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
            self.view.update_status("No file selected", bootstyle=DANGER)
            return
        try:
            saved_path = self.model.save_current_file_text(self.view.get_editor_text())
        except (OSError, ValueError) as exc:
            self.view.show_error("Save Error", f"Failed to save file:\n{exc}")
            self.view.update_status(f"Save failed: {exc}", bootstyle=DANGER)
            return
        selected_entry = self.model.get_file_entry_by_path(saved_path) or self.model.get_file_entry_by_save_path(saved_path)
        self.refresh_file_list(selected_key=selected_entry["key"] if selected_entry else None, preferred_path=saved_path)
        target_entry = self.model.get_current_file_entry()
        self.view.update_status(f"Saved {target_entry['relative_path']}", bootstyle=SUCCESS)

    def can_navigate_away(self):
        if not self.model.is_dirty:
            return True
        return self.view.confirm_discard_changes()

    def handle_editor_modified(self):
        self.model.mark_dirty()
        entry = self.model.get_current_file_entry()
        if entry is None:
            self.view.update_status("Unsaved changes", bootstyle=SECONDARY)
            return
        self.view.update_status(f"Editing {entry['relative_path']} | Unsaved changes", bootstyle=SECONDARY)
        self.view.schedule_analysis_refresh()

    def focus_search(self):
        self.view.focus_search()

    def refresh_editor_analysis(self, source_text=None):
        editor_text = self.view.get_editor_text() if source_text is None else source_text
        self.current_analysis = self.model.build_editor_analysis(editor_text)
        definition_entries = self.current_analysis["definitions"]
        self.view.set_definition_entries(definition_entries)
        self.view.update_definition_summary(len(definition_entries), self.current_analysis["parse_error"])
        self.view.refresh_syntax_highlighting(definition_entries)

    def on_definition_selected(self):
        definition_key = self.view.get_selected_definition_key()
        if not definition_key:
            return
        definition_entry = self._get_definition_entry(definition_key)
        if definition_entry is None:
            return
        self.view.show_definition_location(definition_entry)
        self.view.update_status(
            f"Jumped to {definition_entry['kind']} {definition_entry['qualified_name']} at line {definition_entry['line']}",
            bootstyle=SECONDARY,
        )

    def find_next(self):
        self._find_match(backwards=False)

    def find_previous(self):
        self._find_match(backwards=True)

    def on_hide(self):
        return self.view.on_hide()

    def on_unload(self):
        return self.view.on_unload()

    def _find_match(self, backwards):
        search_text = self.view.get_search_text()
        if not search_text.strip():
            self.view.update_status("Enter search text first", bootstyle=DANGER)
            self.view.focus_search()
            return
        match_range = self.view.find_text(search_text, backwards=backwards)
        if match_range is None:
            self.view.update_status(f"No matches for '{search_text}'", bootstyle=DANGER)
            return
        direction_text = "Previous" if backwards else "Next"
        self.view.update_status(f"{direction_text} match: {search_text}", bootstyle=SECONDARY)

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