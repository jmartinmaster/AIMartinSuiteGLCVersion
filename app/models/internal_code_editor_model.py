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
import ast
import os
import tempfile

__module_name__ = "Internal Code Editor"
__version__ = "0.1.0"


class InternalCodeEditorModel:
    SOURCE_SORT_ORDER = {"external": 0, "workspace": 0, "bundled": 1}

    def __init__(self, bundled_app_path, external_app_path):
        self.bundled_app_path = os.path.abspath(bundled_app_path)
        self.external_app_path = os.path.abspath(external_app_path)
        self.file_entries = []
        self.current_file_key = None
        self.is_dirty = False

    def refresh_file_entries(self):
        entries = []
        seen_paths = set()

        for source_name, browse_path in self._iter_sources():
            if not os.path.isdir(browse_path):
                continue
            for root_path, dir_names, file_names in os.walk(browse_path):
                dir_names[:] = [name for name in dir_names if name != "__pycache__"]
                for file_name in sorted(file_names):
                    if not file_name.endswith(".py"):
                        continue
                    absolute_path = os.path.abspath(os.path.join(root_path, file_name))
                    normalized_path = os.path.normcase(absolute_path)
                    if normalized_path in seen_paths:
                        continue
                    seen_paths.add(normalized_path)
                    relative_path = os.path.relpath(absolute_path, browse_path).replace(os.sep, "/")
                    label_prefix = "Workspace" if source_name == "workspace" else source_name.title()
                    entry_key = f"{source_name}:{relative_path}"
                    entries.append(
                        {
                            "key": entry_key,
                            "label": f"{label_prefix} | {relative_path}",
                            "relative_path": relative_path,
                            "path": absolute_path,
                            "save_path": absolute_path,
                            "source_name": source_name,
                        }
                    )

        entries.sort(
            key=lambda item: (
                item["relative_path"].lower(),
                self.SOURCE_SORT_ORDER.get(item["source_name"], 99),
                item["source_name"].lower(),
            )
        )
        self.file_entries = entries
        if self.current_file_key not in {entry["key"] for entry in entries}:
            self.current_file_key = entries[0]["key"] if entries else None
        return list(self.file_entries)

    def get_file_entry(self, file_key):
        for entry in self.file_entries:
            if entry["key"] == file_key:
                return entry
        return None

    def get_file_entry_by_path(self, file_path):
        normalized_target = os.path.normcase(os.path.abspath(file_path))
        for entry in self.file_entries:
            if os.path.normcase(entry["path"]) == normalized_target:
                return entry
        return None

    def get_file_entry_by_save_path(self, file_path):
        normalized_target = os.path.normcase(os.path.abspath(file_path))
        for entry in self.file_entries:
            if os.path.normcase(entry["save_path"]) == normalized_target:
                return entry
        return None

    def set_current_file(self, file_key):
        if self.get_file_entry(file_key) is None:
            raise ValueError(f"Unknown file selection: {file_key}")
        self.current_file_key = file_key

    def load_current_file_text(self):
        entry = self.get_current_file_entry()
        if entry is None:
            raise ValueError("No file is selected.")
        text = self.load_file_text(entry["key"])
        self.is_dirty = False
        return text

    def load_file_text(self, file_key):
        entry = self.get_file_entry(file_key)
        if entry is None:
            raise ValueError(f"Unknown file selection: {file_key}")
        with open(entry["path"], "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def save_current_file_text(self, text):
        entry = self.get_current_file_entry()
        if entry is None:
            raise ValueError("No file is selected.")
        target_path = entry["save_path"]
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        file_descriptor, temporary_path = tempfile.mkstemp(prefix="internal_code_editor_", suffix=".tmp", dir=os.path.dirname(target_path))
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
            os.replace(temporary_path, target_path)
        except Exception:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise
        self.is_dirty = False
        return target_path

    def build_editor_analysis(self, source_text):
        definitions, parse_error = self.build_definition_index(source_text)
        return {
            "definitions": definitions,
            "parse_error": parse_error,
        }

    def build_definition_index(self, source_text):
        try:
            syntax_tree = ast.parse(source_text)
        except SyntaxError as exc:
            if exc.lineno:
                return [], f"Syntax error at line {exc.lineno}: {exc.msg}"
            return [], f"Syntax error: {exc.msg}"

        source_lines = source_text.splitlines()
        definition_entries = []
        self._collect_definition_entries(syntax_tree.body, definition_entries, source_lines, owner_class=None)
        return definition_entries, None

    def get_current_file_entry(self):
        if self.current_file_key is None:
            return None
        return self.get_file_entry(self.current_file_key)

    def mark_dirty(self):
        self.is_dirty = True

    def mark_clean(self):
        self.is_dirty = False

    def _collect_definition_entries(self, nodes, definition_entries, source_lines, owner_class=None):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                definition_entries.append(self._build_definition_entry(node, "class", source_lines, owner_class=owner_class))
                self._collect_definition_entries(node.body, definition_entries, source_lines, owner_class=node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definition_kind = "method" if owner_class else "function"
                definition_entries.append(self._build_definition_entry(node, definition_kind, source_lines, owner_class=owner_class))

    def _build_definition_entry(self, node, definition_kind, source_lines, owner_class=None):
        line_number = int(getattr(node, "lineno", 1) or 1)
        line_text = source_lines[line_number - 1] if 0 < line_number <= len(source_lines) else ""
        name_column = self._find_name_column(line_text, node.name, int(getattr(node, "col_offset", 0) or 0))
        end_column = name_column + len(node.name)
        qualified_name = f"{owner_class}.{node.name}" if owner_class and definition_kind == "method" else node.name
        return {
            "key": f"{definition_kind}:{qualified_name}:{line_number}",
            "name": node.name,
            "qualified_name": qualified_name,
            "kind": definition_kind,
            "line": line_number,
            "target_index": f"{line_number}.0",
            "name_start_index": f"{line_number}.{name_column}",
            "name_end_index": f"{line_number}.{end_column}",
        }

    def _find_name_column(self, line_text, symbol_name, minimum_column):
        if not line_text:
            return max(0, minimum_column)
        symbol_index = line_text.find(symbol_name, minimum_column)
        if symbol_index >= 0:
            return symbol_index
        fallback_index = line_text.find(symbol_name)
        if fallback_index >= 0:
            return fallback_index
        return max(0, minimum_column)

    def _iter_sources(self):
        if self.bundled_app_path == self.external_app_path:
            yield "workspace", self.bundled_app_path
            return
        if os.path.isdir(self.external_app_path):
            yield "external", self.external_app_path
        yield "bundled", self.bundled_app_path