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
import difflib
from copy import deepcopy
from pathlib import Path
from PyQt6.QtCore import QTimer

from app.models.layout_manager_model import LayoutManagerModel
from app.views.layout_manager_qt_view import LayoutManagerQtView

__module_name__ = "Layout Manager Qt Controller"
__version__ = "2.5.1"


class LayoutManagerQtController:
    def __init__(self, session_payload=None, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.embedded = dispatcher is not None
        self.model = LayoutManagerModel()

        if self.embedded:
            theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
            config, source_path, form_info = self.model.load_current_config()
            payload = {
                "form_info": dict(form_info),
                "config": config,
                "source_path": source_path,
                "guardrails": self.model.build_editor_guardrails(config),
                "protected_row_field_lookup": self.model.get_protected_row_field_lookup(config),
                "theme_tokens": theme_tokens,
            }
        else:
            payload = dict(session_payload or {})
            self.state_path = Path(payload["state_path"])
            self.command_path = Path(payload["command_path"])

        self.payload = payload
        self.change_token = 0
        self.toast_token = 0
        self.module_open_token = 0
        self.dirty = False
        self.current_form_info = dict(payload.get("form_info") or {})
        self.current_config = dict(payload.get("config") or {})
        self.current_source_path = payload.get("source_path") or ""
        self.current_editor_text = None
        self.selected_form_id = str(payload.get("selected_form_id") or self.current_form_info.get("id") or "").strip()
        self.guardrails = payload.get("guardrails") or {}
        self.protected_row_field_lookup = payload.get("protected_row_field_lookup") or {}
        self.last_refresh_ms = 0.0
        self.compare_reference_form_id = ""
        self.view = LayoutManagerQtView(controller=self, theme_tokens=payload.get("theme_tokens") or {}, parent_widget=self.parent)
        self._initial_view_rendered = False
        self._undo_stack = []
        self._redo_stack = []

        if not self.current_config:
            self.current_config, self.current_source_path, self.current_form_info = self.model.load_current_config()
            self.current_editor_text = self.model.load_current_text()
            self.guardrails = self.model.build_editor_guardrails(self.current_config)
            self.protected_row_field_lookup = self.model.get_protected_row_field_lookup(self.current_config)
        else:
            self.current_editor_text = self.model.serialize_config(self.current_config)

        if not self.selected_form_id:
            self.selected_form_id = self.loaded_form_id()

        self._clean_editor_text = self.current_editor_text
        self.forms = []
        self.refresh_forms()
        self.refresh_view(reason="Loaded layout manager session", editor_text_override=self.current_editor_text)
        self.view.set_dirty(self.dirty)
        self.write_state(status="running", message="Layout Manager Qt window is ready.")

    def check_and_prompt_for_missing_fields(self, config, filename=None):
        """
        Detects missing standard fields/roles or metadata in configuration.
        If found, prompts the user via InjectMissingFieldsDialog to inject them.
        Returns (updated_config, form_name, description).
        """
        missing_data = self.model.detect_missing_standard_fields(config)
        
        has_missing_header = len(missing_data.get("header", [])) > 0
        has_missing_prod = len(missing_data.get("production", [])) > 0
        has_missing_down = len(missing_data.get("downtime", [])) > 0
        
        metadata_check = missing_data.get("metadata", {})
        name_missing = metadata_check.get("name_missing")
        desc_missing = metadata_check.get("description_missing")
        
        if not (has_missing_header or has_missing_prod or has_missing_down or name_missing or desc_missing):
            return config, None, None
            
        suggestions = self.model.get_missing_fields_suggestions(config, filename)
        
        from app.views.layout_manager_qt_view import InjectMissingFieldsDialog
        dialog = InjectMissingFieldsDialog(self.view, missing_fields=missing_data, suggestions=suggestions)
        if dialog.exec():
            result = dialog.get_values()
            metadata = result.get("metadata", {})
            fields_to_inject = result.get("fields", [])
            
            # Inject standard fields
            updated_config = self.model.inject_fields_into_config(config, fields_to_inject)
            
            # Make sure export_prefix is updated in the configuration
            if metadata.get("export_prefix"):
                updated_config["export_prefix"] = metadata.get("export_prefix")
                
            return updated_config, metadata.get("name"), metadata.get("description")
            
        return config, None, None

    def check_and_prompt_active_form(self):
        """
        Checks the currently loaded active form for missing fields and prompts if necessary.
        """
        updated_config, name, description = self.check_and_prompt_for_missing_fields(
            self.current_config, filename=self.current_source_path
        )
        if updated_config != self.current_config or name or description:
            form_id = self.loaded_form_id()
            if form_id and (name or description):
                curr_name = self.current_form_info.get("name")
                curr_desc = self.current_form_info.get("description")
                if (name and name != curr_name) or (description is not None and description != curr_desc):
                    self.model.rename_form(form_id, name or curr_name, description=description if description is not None else curr_desc)
                    # Reload the new state
                    self.current_config, self.current_source_path, self.current_form_info = self.model.load_form_config(form_id)
            
            # Save config
            self.current_config = updated_config
            self.model.save_config(self.current_config, form_info=self.current_form_info)
            self.dirty = False
            self.refresh_forms()
            serialized = self.model.serialize_config(self.current_config)
            self.refresh_view(reason="Injected missing fields/metadata on active form", editor_text_override=serialized)

    def show(self):
        self.view.show()
        self.view.raise_window()
        if not self._initial_view_rendered:
            self._initial_view_rendered = True
            
            def _setup_initial():
                self.refresh_view(
                    reason="Loaded layout manager session",
                    editor_text_override=self.current_editor_text,
                )
                self.check_and_prompt_active_form()
                
            QTimer.singleShot(0, _setup_initial)
        self.write_state(status="running", message="Layout Manager Qt window is visible.")

    def _run_busy_action(self, message, callback):
        self.view.set_busy_state(True, message)
        try:
            return callback()
        finally:
            self.view.set_busy_state(False)

    def apply_theme(self, theme_tokens=None):
        if theme_tokens is None:
            if self.dispatcher is not None:
                view = getattr(self.dispatcher, "view", None)
                theme_tokens = getattr(view, "theme_tokens", {}) if view is not None else {}
            else:
                theme_tokens = self.payload.get("theme_tokens") or {}
        self.payload["theme_tokens"] = dict(theme_tokens or {})
        self.view.set_theme_tokens(self.payload["theme_tokens"])
        self.write_state(message="Applied updated theme tokens.")

    def loaded_form_id(self):
        return str(self.current_form_info.get("id") or "").strip()

    def selected_form_name(self):
        form_id = str(self.selected_form_id or "").strip()
        if not form_id:
            return ""
        for form_info in self.forms:
            if str(form_info.get("id") or "").strip() == form_id:
                return str(form_info.get("name") or form_id)
        try:
            return str(self.model.get_form_info(form_id).get("name") or form_id)
        except Exception:
            return form_id

    def set_selected_form_id(self, form_id):
        self.selected_form_id = str(form_id or "").strip()

    def selection_differs_from_loaded(self):
        selected_form_id = str(self.selected_form_id or "").strip()
        loaded_form_id = self.loaded_form_id()
        return bool(selected_form_id and loaded_form_id and selected_form_id != loaded_form_id)

    def set_loaded_form_state(self, config, source_path, form_info):
        self.current_config = dict(config or {})
        self.current_source_path = source_path or ""
        self.current_form_info = dict(form_info or {})
        self.current_editor_text = None
        self.set_selected_form_id(self.loaded_form_id())

    def update_current_form_info_if_loaded(self, form_info):
        if not isinstance(form_info, dict):
            return
        if str(form_info.get("id") or "").strip() == self.loaded_form_id():
            self.current_form_info = dict(form_info)

    def set_status_message(self, message, error=False):
        self.view.set_status(message, error=error)
        self.write_state(message=message)

    def refresh_forms(self):
        self.forms = list(self.model.list_forms())
        available_form_ids = {str(form_info.get("id") or "").strip() for form_info in self.forms}
        selected_form_id = str(self.selected_form_id or "").strip()
        if selected_form_id not in available_form_ids:
            selected_form_id = self.loaded_form_id()
        if selected_form_id not in available_form_ids:
            selected_form_id = next(iter(available_form_ids), "")
        self.selected_form_id = selected_form_id
        self.view.set_forms(self.forms, self.selected_form_id)
        compare_form_id = str(self.compare_reference_form_id or "").strip()
        if compare_form_id not in available_form_ids:
            compare_form_id = self.selected_form_id or next(iter(available_form_ids), "")
        self.compare_reference_form_id = compare_form_id
        self.view.set_compare_forms(self.forms, self.compare_reference_form_id)

    def refresh_view(self, reason="", editor_text_override=None):
        started_at = time.perf_counter()
        if editor_text_override is not None:
            self.current_editor_text = str(editor_text_override)
            serialized_config = self.current_editor_text
        else:
            self.current_editor_text = None
            serialized_config = self.model.serialize_config(self.current_config)
        preview_grid = self.model.build_preview_grid(self.current_config)
        validation_summary = self.model.build_validation_summary(self.current_config)
        import_export_metadata = self.model.build_import_export_metadata(self.current_config)
        dependency_audit = self.model.build_form_dependency_audit(self.current_form_info.get("id"))
        self.guardrails = self.model.build_editor_guardrails(self.current_config)
        self.protected_row_field_lookup = self.model.get_protected_row_field_lookup(self.current_config)
        self.view.set_editor_text(serialized_config)
        self.view.render_block_authoring(self.current_config)
        self.view.set_header_field_presets(self.model.list_available_header_field_templates(self.current_config))
        self.view.set_row_field_presets(
            self.model.list_available_row_field_templates(
                self.current_config,
                self.view.current_row_section_name(),
            )
        )
        self.view.render_import_export_authoring(self.current_config, metadata=import_export_metadata)
        self.view.render_preview_grid(preview_grid)
        self.view.render_validation_summary(validation_summary)
        self.view.render_form_dependency_audit(dependency_audit)
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
        self.last_refresh_ms = round((time.perf_counter() - started_at) * 1000.0, 2)

    def write_state(self, status="running", message="", toast_event=None, module_open_event=None):
        if self.embedded:
            if isinstance(toast_event, dict):
                title = str(toast_event.get("title") or "Layout Manager")
                msg = str(toast_event.get("message") or "")
                bootstyle = str(toast_event.get("bootstyle") or "info")
                duration_ms = toast_event.get("duration_ms")
                if self.dispatcher is not None:
                    self.dispatcher.show_toast(title, msg, bootstyle=bootstyle, duration_ms=duration_ms)
            if isinstance(module_open_event, dict):
                module_name = str(module_open_event.get("module") or "").strip()
                reason = str(module_open_event.get("reason") or "").strip()
                if module_name and self.dispatcher is not None:
                    self.dispatcher.load_module(module_name, use_transition=True, ensure_authorized=True)
                    if reason:
                        self.dispatcher.show_toast("Layout Manager", f"Opened {module_name}: {reason}", bootstyle="info")
            return

        state = {
            "status": status,
            "dirty": self.dirty,
            "change_token": self.change_token,
            "last_refresh_ms": self.last_refresh_ms,
            "form_id": self.current_form_info.get("id"),
            "form_name": self.current_form_info.get("name"),
            "source_path": self.current_source_path,
            "message": message,
            "updated_at": time.time(),
        }
        if isinstance(toast_event, dict):
            state["toast_event"] = toast_event
        if isinstance(module_open_event, dict):
            state["module_open_event"] = module_open_event
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

    def _emit_host_module_open(self, module_name, reason="", payload=None):
        target_module = str(module_name or "").strip()
        if not target_module:
            return
        self.module_open_token += 1
        module_open_payload = {
            "token": self.module_open_token,
            "module": target_module,
            "reason": str(reason or "").strip(),
            "payload": dict(payload or {}),
        }
        self.write_state(
            message=f"Requested host to open module '{target_module}'.",
            module_open_event=module_open_payload,
        )

    def _required_calculation_section_ids(self, config):
        metadata = self.model._normalize_calculations_metadata(config if isinstance(config, dict) else {})
        section_profiles = metadata.get("section_profiles") if isinstance(metadata, dict) else []
        required_sections = set()
        for profile in section_profiles if isinstance(section_profiles, list) else []:
            if not isinstance(profile, dict):
                continue
            section_id = str(profile.get("section_id") or "").strip().lower()
            if not section_id:
                continue
            if bool(profile.get("requires_calculations")):
                required_sections.add(section_id)
        return required_sections

    def _handle_new_calculation_requirements(self, previous_config, updated_config):
        previous_required = self._required_calculation_section_ids(previous_config)
        updated_required = self._required_calculation_section_ids(updated_config)
        newly_required = sorted(updated_required - previous_required)
        if not newly_required:
            return

        section_names = [
            self.model.get_section_name(section_id, config=updated_config, fallback_name=section_id)
            for section_id in newly_required
        ]
        section_lines = "\n".join(f"- {name}" for name in section_names)
        prompt_message = (
            "This save introduced sections that now require calculations setup:\n\n"
            f"{section_lines}\n\n"
            "Open Form Calculations now to configure them?"
        )

        if not self.view.confirm("Open Form Calculations", prompt_message):
            self._emit_host_toast(
                "Skipped opening Form Calculations. You can open it manually later.",
                bootstyle="warning",
            )
            return

        self._emit_host_module_open(
            "production_log_calculations",
            reason="Layout save introduced required calculations metadata.",
            payload={
                "section_ids": newly_required,
                "section_names": section_names,
                "source_form_id": str(self.current_form_info.get("id") or "").strip(),
                "source_form_name": str(self.current_form_info.get("name") or "").strip(),
            },
        )

    def mark_dirty(self):
        if self.dirty:
            return
        self.dirty = True
        self.model.mark_dirty()
        self.view.set_dirty(True)
        self.write_state(message="Unsaved Qt layout changes are present.")

    def mark_clean(self, message):
        self.dirty = False
        try:
            self._clean_editor_text = self.view.editor_text()
        except Exception:
            self._clean_editor_text = self.current_editor_text
        self.model.mark_clean()
        self.change_token += 1
        self.view.set_dirty(False)
        self.view.set_status(message)
        self.write_state(message=message)

    def has_actual_changes(self):
        if not self.dirty:
            return False
        try:
            current_text = self.view.editor_text()
            if current_text == getattr(self, "_clean_editor_text", None):
                self.mark_clean("No changes detected")
                return False
        except Exception:
            pass
        return True

    def apply_editor_changes(self, message=None):
        config, payload_details = self.model.resolve_editor_text(
            self.view.editor_text(),
            base_config=self.current_config,
        )
        self._record_undo_state()
        self.current_config = config
        self.refresh_view(reason=message or "Applied editor changes")
        self.mark_dirty()
        self._redo_stack.clear()
        return config, payload_details

    def _payload_warning_message(self, payload_details):
        details = payload_details if isinstance(payload_details, dict) else {}
        warning_message = str(details.get("warning_message") or "").strip()
        if warning_message:
            return warning_message
        missing_keys = details.get("auto_filled_missing_keys")
        if isinstance(missing_keys, list) and missing_keys:
            return (
                "Saved using auto-repaired JSON. Missing top-level keys were restored from the active form/default: "
                f"{', '.join(str(key) for key in missing_keys)}"
            )
        return ""

    def sync_block_view_to_editor(self):
        try:
            parsed_config, composed_config, _payload_details = self._compose_save_config(self.view.editor_text())
        except Exception:
            return
        if composed_config == self.current_config:
            return
        serialized_config = self.model.serialize_config(composed_config)
        self.current_config = composed_config
        self.refresh_view(reason="Synced block view changes into JSON editor", editor_text_override=serialized_config)
        self.mark_dirty()

    def _load_editor_config(self):
        return self.model.parse_editor_text(self.view.editor_text(), base_config=self.current_config)

    def _mapping_name_for_row_section(self, section_name):
        return self.model._mapping_name_for_section(section_name, config=self.current_config)

    def _current_row_field_rename_map(self, row_fields):
        rename_map = {}
        for field in row_fields if isinstance(row_fields, list) else []:
            original_id = str((field or {}).get("_original_id") or "").strip()
            field_id = str((field or {}).get("id") or "").strip()
            if original_id and field_id and original_id != field_id:
                rename_map[original_id] = field_id
        return rename_map

    def _compose_save_config(self, editor_text):
        parsed_config, payload_details = self.model.resolve_editor_text(
            editor_text,
            base_config=self.current_config,
        )
        if self.view.is_json_editor_active():
            return parsed_config, parsed_config, payload_details

        updated_config = deepcopy(parsed_config)

        updated_config, _status_message = self.model.update_template_path(
            updated_config,
            self.view.template_path_value(),
        )
        updated_config, _status_message = self.model.update_export_prefix(
            updated_config,
            self.view.export_prefix_value(),
        )
        updated_config, _status_message = self.model.replace_header_fields(
            updated_config,
            self.view.header_field_table_values(),
        )

        row_section_name = self.view.current_row_section_name()
        row_field_values = self.view.row_field_table_values()
        rename_map = self._current_row_field_rename_map(row_field_values)
        updated_config, _status_message = self.model.replace_row_fields(
            updated_config,
            row_section_name,
            row_field_values,
        )

        current_section_id = self.view.current_section_id()
        if current_section_id:
            updated_config, _status_message = self.model.update_section_metadata(
                updated_config,
                current_section_id,
                self.view.selected_section_values(),
            )

        mapping_name = self.view.current_mapping_name()
        mapping_values = self.view.mapping_form_values()
        mapping_columns = dict(mapping_values.get("columns") or {})
        if mapping_name == self._mapping_name_for_row_section(row_section_name) and rename_map:
            remapped_columns = {}
            for field_id, value in mapping_columns.items():
                remapped_columns[rename_map.get(field_id, field_id)] = value
            mapping_columns = remapped_columns
        updated_config, _status_message = self.model.update_mapping(
            updated_config,
            mapping_name,
            mapping_values["start_row"],
            mapping_values["max_rows"],
            mapping_columns,
        )
        return parsed_config, updated_config, payload_details

    def _apply_layout_update(self, updated_config, status_message):
        self._record_undo_state()
        self.current_config = updated_config
        self.refresh_view(reason=status_message)
        self.mark_dirty()
        self.view.set_status(status_message)
        self._redo_stack.clear()

    def _record_undo_state(self):
        self._undo_stack.append(self.model.serialize_config(self.current_config))
        if len(self._undo_stack) > 50:
            self._undo_stack = self._undo_stack[-50:]

    def undo_last_change(self):
        if not self._undo_stack:
            self.view.set_status("Nothing to undo.")
            return
        self._redo_stack.append(self.model.serialize_config(self.current_config))
        if len(self._redo_stack) > 50:
            self._redo_stack = self._redo_stack[-50:]
        previous_snapshot = self._undo_stack.pop()
        self.current_config = self.model.parse_editor_text(previous_snapshot, base_config=self.current_config)
        self.refresh_view(reason="Undid last change")
        self.mark_dirty()

    def redo_last_change(self):
        if not self._redo_stack:
            self.view.set_status("Nothing to redo.")
            return
        self._undo_stack.append(self.model.serialize_config(self.current_config))
        if len(self._undo_stack) > 50:
            self._undo_stack = self._undo_stack[-50:]
        next_snapshot = self._redo_stack.pop()
        self.current_config = self.model.parse_editor_text(next_snapshot, base_config=self.current_config)
        self.refresh_view(reason="Redid last change")
        self.mark_dirty()

    def save_version_snapshot(self):
        label = self.view.version_label_value() or "Manual Snapshot"
        try:
            config = self._load_editor_config()
            snapshot_id = self.model.create_form_snapshot(self.current_form_info, config, label=label)
            self.current_config = config
            self.refresh_view(reason="Saved version snapshot")
            self.view.set_status(f"Saved version snapshot: {snapshot_id}")
            self._emit_host_toast("Saved layout version snapshot.", bootstyle="success")
        except Exception as exc:
            self.view.set_status(f"Snapshot error: {exc}", error=True)

    def restore_latest_snapshot(self):
        form_id = str(self.current_form_info.get("id") or "")
        snapshots = self.model.list_form_snapshots(form_id=form_id)
        if not snapshots:
            self.view.set_status("No saved snapshots for this form.", error=True)
            return
        latest_snapshot = snapshots[0]
        snapshot_id = str(latest_snapshot.get("snapshot_id") or "")
        if not snapshot_id:
            self.view.set_status("Latest snapshot was invalid.", error=True)
            return
        if not self.view.confirm("Restore Version", f"Restore latest snapshot '{snapshot_id}'?"):
            return
        try:
            self._record_undo_state()
            restored_config, snapshot = self.model.restore_form_snapshot(snapshot_id)
            self.current_config = restored_config
            self._redo_stack.clear()
            self.refresh_view(reason="Restored version snapshot")
            self.mark_dirty()
            snapshot_label = snapshot.get("label") or snapshot_id
            self.view.set_status(f"Restored snapshot: {snapshot_label}")
            self._emit_host_toast("Restored layout version snapshot.", bootstyle="success")
        except Exception as exc:
            self.view.set_status(f"Snapshot restore error: {exc}", error=True)

    def bulk_rename_row_fields(self):
        section_name = self.view.current_row_section_name()
        find_text = self.view.prompt_text("Bulk Rename", "Find text in labels:")
        if not find_text:
            return
        replace_text = self.view.prompt_text("Bulk Rename", "Replace with:", default_text="")
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.bulk_rename_row_fields(
                config,
                section_name,
                find_text,
                replace_text or "",
            )
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Bulk operation error: {exc}", error=True)

    def bulk_delete_row_fields(self):
        section_name = self.view.current_row_section_name()
        contains_text = self.view.prompt_text("Bulk Delete", "Delete row fields where id/label contains:")
        if not contains_text:
            return
        if not self.view.confirm(
            "Bulk Delete",
            f"Delete non-protected fields in {section_name} containing '{contains_text}'?",
        ):
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.bulk_delete_row_fields(
                config,
                section_name,
                contains_text,
            )
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Bulk operation error: {exc}", error=True)

    def bulk_convert_row_widgets(self):
        section_name = self.view.current_row_section_name()
        from_widget = self.view.prompt_text(
            "Bulk Convert Widget",
            "From widget (entry/display/checkbutton/combobox):",
            default_text="entry",
        )
        if not from_widget:
            return
        to_widget = self.view.prompt_text(
            "Bulk Convert Widget",
            "To widget (entry/display/checkbutton/combobox):",
            default_text="display",
        )
        if not to_widget:
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.bulk_convert_row_widgets(
                config,
                section_name,
                from_widget,
                to_widget,
            )
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Bulk operation error: {exc}", error=True)

    def validate_editor(self):
        try:
            _config, payload_details = self.model.resolve_editor_text(
                self.view.editor_text(),
                base_config=self.current_config,
            )
        except Exception as exc:
            self.view.set_status(f"JSON validation failed: {exc}", error=True)
            return
        warning_message = self._payload_warning_message(payload_details)
        if warning_message:
            self.view.set_status(f"JSON is valid with warnings. {warning_message}")
        else:
            self.view.set_status("JSON is valid.")
        self._emit_host_toast("Layout JSON is valid.", bootstyle="success")

    def load_compare_reference_selected_form(self):
        form_id = str(self.view.current_compare_form_id() or "").strip()
        if not form_id:
            self.view.set_status("Select a reference form first.", error=True)
            return
        try:
            reference_text, missing_keys = self._load_form_text_for_compare(form_id)
            self.compare_reference_form_id = form_id
            self.view.set_compare_reference_text(reference_text)
            self._refresh_compare_diff()
            if missing_keys:
                self.view.set_status(
                    f"Loaded compare reference from '{form_id}' with auto-added keys: {', '.join(missing_keys)}. "
                    "Recommendation: save a refreshed copy to persist full structure."
                )
            else:
                self.view.set_status(f"Loaded compare reference from form '{form_id}'.")
        except Exception as exc:
            self.view.set_status(f"Compare reference load failed: {exc}", error=True)

    def load_compare_selected_form_into_editor(self):
        form_id = str(self.view.current_compare_form_id() or "").strip()
        if not form_id:
            self.view.set_status("Select a form to load into the editor.", error=True)
            return
        if self.has_actual_changes() and not self.view.confirm(
            "Replace Unsaved Changes",
            "Load selected form JSON into editor and replace current unsaved changes?",
        ):
            self.view.set_status("Load into editor cancelled.")
            return
        try:
            source_text, missing_keys = self._load_form_text_for_compare(form_id)
            self.view.set_editor_text(source_text)
            self.apply_editor_changes(message=f"Loaded form '{form_id}' into editor")
            self.view.set_compare_working_text(source_text)
            self._refresh_compare_diff()
            if missing_keys:
                self.view.set_status(
                    f"Loaded form '{form_id}' into editor with auto-added keys: {', '.join(missing_keys)}. "
                    "Recommendation: save to persist full layout structure."
                )
            else:
                self.view.set_status(f"Loaded form '{form_id}' into editor (not activated).")
        except Exception as exc:
            self.view.set_status(f"Load into editor failed: {exc}", error=True)

    def load_compare_reference_default(self):
        try:
            reference_text = self.model.load_default_text()
            self.view.set_compare_reference_text(reference_text)
            self._refresh_compare_diff()
            self.view.set_status("Loaded compare reference from default layout template.")
        except Exception as exc:
            self.view.set_status(f"Default reference load failed: {exc}", error=True)

    def copy_compare_reference_to_working(self):
        self.view.set_compare_working_text(self.view.compare_reference_text())
        self._refresh_compare_diff()
        self.view.set_status("Copied reference JSON into compare working editor.")

    def copy_compare_section_from_reference_to_working(self):
        section_key = str(self.view.current_compare_section_key() or "").strip()
        if not section_key:
            self.view.set_status("Select a section key first.", error=True)
            return
        try:
            reference_payload = self._parse_compare_text_with_fallback(
                self.view.compare_reference_text(),
                label="reference",
            )
        except Exception as exc:
            self.view.set_status(f"Reference JSON is invalid: {exc}", error=True)
            return

        if section_key not in reference_payload:
            self.view.set_status(f"Reference JSON does not include '{section_key}'.", error=True)
            return

        working_text = self.view.compare_working_text().strip()
        if not working_text:
            try:
                working_payload = self._load_editor_config()
            except Exception:
                working_payload = deepcopy(self.current_config)
        else:
            try:
                working_payload = self._parse_compare_text_with_fallback(working_text, label="working")
            except Exception as exc:
                self.view.set_status(f"Working JSON is invalid: {exc}", error=True)
                return

        working_payload[section_key] = deepcopy(reference_payload[section_key])
        self.view.set_compare_working_text(self.model.serialize_config(working_payload))
        self._refresh_compare_diff()
        self.view.set_status(f"Copied '{section_key}' from reference into working JSON.")

    def copy_editor_to_compare_working(self):
        self.view.set_compare_working_text(self.view.editor_text())
        self._refresh_compare_diff()
        self.view.set_status("Copied current JSON editor text into compare working editor.")

    def apply_compare_working_to_editor(self):
        working_text = self.view.compare_working_text()
        if not str(working_text or "").strip():
            self.view.set_status("Compare working editor is empty.", error=True)
            return
        try:
            self.view.set_editor_text(working_text)
            self.apply_editor_changes(message="Applied compare working JSON")
            self._refresh_compare_diff()
            self.view.set_status("Applied compare working JSON to the main editor.")
        except Exception as exc:
            self.view.set_status(f"Apply compare JSON failed: {exc}", error=True)

    def refresh_compare_diff(self):
        self._refresh_compare_diff()

    def _refresh_compare_diff(self):
        reference_lines = self.view.compare_reference_text().splitlines()
        working_lines = self.view.compare_working_text().splitlines()
        diff_lines = list(
            difflib.unified_diff(
                reference_lines,
                working_lines,
                fromfile="reference",
                tofile="working",
                lineterm="",
            )
        )
        self.view.set_compare_diff_text("\n".join(diff_lines) if diff_lines else "No differences.")

    def _load_form_text_for_compare(self, form_id):
        raw_text = self.model.load_form_text(form_id)
        missing_keys = []
        try:
            self.model.resolve_editor_text(raw_text, base_config=self.current_config)
            return raw_text, missing_keys
        except Exception as exc:
            message = str(exc or "")
            if "JSON editor expects the full layout object" not in message:
                raise
            missing_keys = self._extract_missing_keys_from_error(message)
            config, _source_path, _form_info = self.model.load_form_config(form_id)
            return self.model.serialize_config(config), missing_keys

    def _parse_compare_text_with_fallback(self, text, label="json"):
        try:
            return self.model.parse_editor_text(text, base_config=self.current_config)
        except Exception as exc:
            message = str(exc or "")
            if "JSON editor expects the full layout object" not in message:
                raise
            payload = json.loads(str(text or "{}"))
            if not isinstance(payload, dict):
                raise
            missing_keys = self._extract_missing_keys_from_error(message)
            repaired_payload = self.model.build_blank_form_config()
            repaired_payload.update(payload)
            repaired_payload = self.model.normalize_config(repaired_payload)
            self.model.validate_config(repaired_payload)
            if missing_keys:
                self.view.set_status(
                    f"{label.title()} JSON was legacy/incomplete; auto-added: {', '.join(missing_keys)}. "
                    "Recommendation: save an updated copy."
                )
            return repaired_payload

    def _extract_missing_keys_from_error(self, message):
        text = str(message or "")
        marker = "Missing:"
        if marker not in text:
            return []
        missing_text = text.split(marker, 1)[1].strip()
        if not missing_text:
            return []
        return [part.strip() for part in missing_text.split(",") if part.strip()]

    def format_editor(self):
        try:
            _config, payload_details = self.apply_editor_changes(message="Formatted editor JSON")
        except Exception as exc:
            self.view.set_status(f"Format JSON failed: {exc}", error=True)
            return
        warning_message = self._payload_warning_message(payload_details)
        if warning_message:
            self.view.set_status(f"Editor JSON was normalized and reformatted with warnings. {warning_message}")
        else:
            self.view.set_status("Editor JSON was normalized and reformatted.")

    def on_row_section_changed(self, *_args):
        self.view.render_row_fields_authoring(self.current_config)
        self.view.set_row_field_presets(
            self.model.list_available_row_field_templates(
                self.current_config,
                self.view.current_row_section_name(),
            )
        )

    def on_mapping_section_changed(self, *_args):
        self.view.render_mapping_authoring(self.current_config)

    def on_section_changed(self, *_args):
        self.view.render_section_editor(self.current_config)

    def add_section_from_structure(self):
        section_id = self.view.prompt_text("Add Section", "Section ID (snake_case):")
        if not section_id:
            return
        section_name = self.view.prompt_text("Add Section", "Section name:", default_text=section_id.replace("_", " ").title())
        if not section_name:
            return
        section_type = self.view.prompt_text("Add Section", "Section type (single/repeating):", default_text="single") or "single"
        behavior_profile = self.view.prompt_text("Add Section", "Behavior profile:", default_text=section_id) or section_id
        section_values = {
            "id": section_id,
            "name": section_name,
            "section_type": section_type,
            "behavior_profile": behavior_profile,
            "description": "",
            "default_max_rows": "25",
            "default_field_width": "12",
            "show_delete_button": True,
            "delete_button_label": "X",
            "delete_button_tooltip": "Delete this row",
            "require_delete_confirmation": False,
        }
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.add_section(config, section_values)
            self._apply_layout_update(updated_config, status_message)
            self.view.set_section_selection(section_id)
        except Exception as exc:
            self.view.set_status(f"Section edit error: {exc}", error=True)

    def remove_section_from_structure(self):
        section_id = self.view.current_section_id()
        if not section_id:
            self.view.set_status("Select a section to remove.", error=True)
            return
        if not self.view.confirm("Remove Section", f"Remove section '{section_id}'?"):
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.remove_section(config, section_id)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Section edit error: {exc}", error=True)

    def apply_section_from_structure(self):
        section_id = self.view.current_section_id()
        section_values = self.view.selected_section_values()
        if not section_id or section_values is None:
            self.view.set_status("Select a section to apply.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_section_metadata(config, section_id, section_values)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Section edit error: {exc}", error=True)

    def move_section_up_from_structure(self):
        self._move_section_from_structure(-1)

    def move_section_down_from_structure(self):
        self._move_section_from_structure(1)

    def _move_section_from_structure(self, direction):
        section_id = self.view.current_section_id()
        if not section_id:
            self.view.set_status("Select a section to move.", error=True)
            return
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.move_section(config, section_id, direction)
            if status_message is not None:
                self._apply_layout_update(updated_config, status_message)
                self.view.set_section_selection(section_id)
        except Exception as exc:
            self.view.set_status(f"Section edit error: {exc}", error=True)

    def add_header_field_from_block(self):
        try:
            config = self._load_editor_config()
            insert_index = self.view.selected_header_field_row_index()
            if insert_index >= 0:
                insert_index += 1
            else:
                insert_index = None
            updated_config, status_message = self.model.add_header_field(config, insert_index=insert_index)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def add_selected_preset_header_field_from_block(self):
        preset_field_id = self.view.current_header_field_preset_id()
        if not preset_field_id:
            self.view.set_status("Select a preset field to add.", error=True)
            return
        try:
            config = self._load_editor_config()
            insert_index = self.view.selected_header_field_row_index()
            if insert_index >= 0:
                insert_index += 1
            else:
                insert_index = None
            updated_config, status_message = self.model.add_preset_header_field(
                config,
                preset_field_id,
                insert_index=insert_index,
            )
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
                field_values["id"],
                field_values["label"],
                field_values["row"],
                field_values["col"],
                field_values["cell"],
                field_values["width"],
                field_values["readonly"],
                field_values["default"],
                field_values["role"],
                field_values["import_enabled"],
                field_values["export_enabled"],
                field_values["widget"],
                field_values["state"],
                field_values["options_source"],
                field_values["values"],
            )
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def add_row_field_from_block(self):
        section_name = self.view.current_row_section_name()
        try:
            config = self._load_editor_config()
            insert_index = self.view.selected_row_field_row_index()
            if insert_index >= 0:
                insert_index += 1
            else:
                insert_index = None
            updated_config, status_message = self.model.add_row_field(config, section_name, insert_index=insert_index)
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Block edit error: {exc}", error=True)

    def add_selected_preset_row_field_from_block(self):
        section_name = self.view.current_row_section_name()
        preset_field_id = self.view.current_row_field_preset_id()
        if not preset_field_id:
            self.view.set_status("Select a preset column to add.", error=True)
            return
        try:
            config = self._load_editor_config()
            insert_index = self.view.selected_row_field_row_index()
            if insert_index >= 0:
                insert_index += 1
            else:
                insert_index = None
            updated_config, status_message = self.model.add_preset_row_field(
                config,
                section_name,
                preset_field_id,
                insert_index=insert_index,
            )
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
        self.view.set_import_export_progress(True, "Applying template path...")
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_template_path(config, self.view.template_path_value())
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Import/export error: {exc}", error=True)
        finally:
            self.view.set_import_export_progress(False)

    def apply_export_prefix_from_import_export(self):
        self.view.set_import_export_progress(True, "Applying export prefix...")
        try:
            config = self._load_editor_config()
            updated_config, status_message = self.model.update_export_prefix(config, self.view.export_prefix_value())
            self._apply_layout_update(updated_config, status_message)
        except Exception as exc:
            self.view.set_status(f"Import/export error: {exc}", error=True)
        finally:
            self.view.set_import_export_progress(False)

    def browse_template_from_import_export(self):
        selected_file = self.view.choose_template_file(self.view.template_path_value())
        if not selected_file:
            self.view.set_status("Template browse canceled.")
            return
        self.view.set_template_path_value(selected_file)
        self.view.set_status("Template selected. Apply to persist or Store With Form to keep it with this form.")

    def open_template_from_import_export(self):
        template_path = self.view.template_path_value()
        resolved_template_path = self.model.resolve_template_path(template_path)
        if not resolved_template_path:
            self.view.set_status("Template path is not set or does not exist.", error=True)
            return
        if not self.view.open_local_file(resolved_template_path):
            self.view.set_status("Could not open the template with a local app.", error=True)
            return
        self.view.set_status(f"Opened template: {resolved_template_path}")

    def store_template_with_active_form_from_import_export(self):
        self.view.set_import_export_progress(True, "Storing template with active form...")
        try:
            stored_template = self.model.copy_template_to_active_form(
                self.view.template_path_value(),
                form_info=self.current_form_info,
            )
            config = self._load_editor_config()
            updated_config, _status_message = self.model.update_template_path(
                config,
                stored_template["relative_path"],
            )
            self._apply_layout_update(
                updated_config,
                f"Stored template with active form: {stored_template['relative_path']}",
            )
            self._emit_host_toast("Stored export template with the active form.", bootstyle="success")
        except Exception as exc:
            self.view.set_status(f"Import/export error: {exc}", error=True)
        finally:
            self.view.set_import_export_progress(False)

    def apply_mapping_from_import_export(self):
        mapping_name = self.view.current_mapping_name()
        mapping_values = self.view.mapping_form_values()
        self.view.set_import_export_progress(True, f"Applying {mapping_name} mapping...")
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
        finally:
            self.view.set_import_export_progress(False)

    def assign_selected_mapping_column_from_import_export(self):
        mapping_name = self.view.current_mapping_name()
        field_id = self.view.selected_mapping_field_id()
        column_name = self.view.current_mapping_column_choice()
        if not field_id:
            self.view.set_status("Select a mapping row to assign a column.", error=True)
            return
        if not column_name:
            self.view.set_status("Select a column value to assign.", error=True)
            return
        self.view.set_import_export_progress(True, f"Assigning column '{column_name}'...")
        try:
            config = self._load_editor_config()
            mapping_values = self.view.mapping_form_values()
            row_mapping = mapping_values["columns"].setdefault(
                field_id,
                {
                    "column": "",
                    "import_enabled": "true",
                    "export_enabled": "true",
                    "import_transform": "value",
                    "export_transform": "value",
                },
            )
            row_mapping["column"] = column_name
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
        finally:
            self.view.set_import_export_progress(False)

    def clear_selected_mapping_column_from_import_export(self):
        mapping_name = self.view.current_mapping_name()
        field_id = self.view.selected_mapping_field_id()
        if not field_id:
            self.view.set_status("Select a mapping row to clear.", error=True)
            return
        self.view.set_import_export_progress(True, f"Clearing mapping for '{field_id}'...")
        try:
            config = self._load_editor_config()
            mapping_values = self.view.mapping_form_values()
            row_mapping = mapping_values["columns"].setdefault(
                field_id,
                {
                    "column": "",
                    "import_enabled": "true",
                    "export_enabled": "true",
                    "import_transform": "value",
                    "export_transform": "value",
                },
            )
            row_mapping["column"] = ""
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
        finally:
            self.view.set_import_export_progress(False)

    def reload_current(self):
        def _execute():
            config, source_path, form_info = self.model.load_current_config()
            editor_text = self.model.load_current_text()
            self.set_loaded_form_state(config, source_path, form_info)
            self.refresh_forms()
            self.dirty = False
            self.refresh_view(reason="Reloaded active layout from disk", editor_text_override=editor_text)
            self.write_state(message="Reloaded active layout from disk.")
            self.check_and_prompt_active_form()

        self._run_busy_action("Reloading active layout...", _execute)

    def load_default(self):
        def _execute():
            config, source_path, active_form_info = self.model.load_default_config()
            editor_text = self.model.load_default_text()
            self.set_loaded_form_state(config, source_path, active_form_info)
            self.refresh_forms()
            self.mark_dirty()
            self.refresh_view(reason="Loaded default layout template", editor_text_override=editor_text)
            self.write_state(message="Loaded default layout template.")

        self._run_busy_action("Loading default layout template...", _execute)

    def save_current(self):
        def _execute():
            try:
                previous_config = deepcopy(self.current_config)
                self.view.finalize_block_table_edits()
                editor_text = self.view.editor_text()
                parsed_config, composed_config, payload_details = self._compose_save_config(editor_text)
                serialized_config = self.model.serialize_config(composed_config)
                try:
                    raw_parsed = json.loads(editor_text)
                except Exception:
                    raw_parsed = None
                save_text = editor_text if (composed_config == parsed_config and raw_parsed is not None and composed_config == raw_parsed) else serialized_config
                self.current_config = composed_config
                self.refresh_view(reason="Prepared layout for save", editor_text_override=save_text)
                backup_info = self.model.save_config_text(save_text, config=composed_config, form_info=self.current_form_info)
                self.current_source_path = self.current_form_info.get("save_path", self.current_source_path)
                backup_path = ""
                if isinstance(backup_info, dict):
                    backup_path = backup_info.get("backup_path") or ""
                    if not backup_path:
                        backup_path = backup_info.get("versioned_backup_path") or backup_info.get("adjacent_backup_path") or ""
                message = f"Saved current layout configuration for '{self.current_form_info.get('name', self.loaded_form_id() or 'active form')}'."
                if backup_path:
                    message = f"{message} Backup: {backup_path}"
                if self.selection_differs_from_loaded():
                    message = (
                        f"{message} '{self.selected_form_name()}' is selected in Stored Forms but is not active. "
                        "Click Activate before editing or saving that form."
                    )
                warning_message = self._payload_warning_message(payload_details)
                if warning_message:
                    message = f"{message} Warning: {warning_message}"
                self.mark_clean(message)
                self.refresh_forms()
                self.refresh_view(reason="Saved current layout configuration", editor_text_override=save_text)
                self._emit_host_toast(message, bootstyle="success")
                self._handle_new_calculation_requirements(previous_config, composed_config)
                if self.embedded and self.dispatcher is not None:
                    if self.loaded_form_id() == self.selected_form_id:
                        self.dispatcher.notify_active_form_changed(source_instance=self, active_form_info=self.current_form_info)
            except Exception as exc:
                self.set_status_message(f"Save failed: {exc}", error=True)

        self._run_busy_action("Saving layout configuration...", _execute)

    def activate_selected_form(self):
        form_id = self.view.current_form_id()
        if not form_id:
            self.view.set_status("Select a form to activate.", error=True)
            return
        if str(form_id or "").strip() == self.loaded_form_id():
            self.set_selected_form_id(form_id)
            self.refresh_forms()
            self.set_status_message("Selected form is already active.")
            return
        if self.has_actual_changes() and not self.view.confirm(
            "Unsaved Changes",
            "Activate the selected form and discard unsaved layout changes?",
        ):
            self.refresh_forms()
            self.set_status_message("Activation cancelled.")
            return

        def _execute():
            self.model.activate_form(form_id)
            config, source_path, loaded_form_info = self.model.load_current_config()
            editor_text = self.model.load_current_text()
            self.set_loaded_form_state(config, source_path, loaded_form_info)
            self.refresh_forms()
            action_message = f"Activated form '{self.current_form_info.get('name', form_id)}'."
            self.mark_clean(action_message)
            self.refresh_view(reason="Activated selected form", editor_text_override=editor_text)
            self._emit_host_toast(action_message, bootstyle="success")
            if self.embedded and self.dispatcher is not None:
                self.dispatcher.notify_active_form_changed(source_instance=self, active_form_info=self.current_form_info)
            self.check_and_prompt_active_form()

        self._run_busy_action(f"Activating form '{form_id}'...", _execute)

    def create_form(self):
        name = self.view.prompt_text("Create Form", "Form name:")
        if not name:
            return
        description = self.view.prompt_text("Create Form", "Description:", default_text="") or ""

        def _execute():
            try:
                config = self._load_editor_config()
                form_info = self.model.create_form_from_config(name, config, description=description, activate=False)
                self.set_selected_form_id(form_info.get("id"))
                self.refresh_forms()
                action_message = (
                    f"Created form '{form_info.get('name', name)}'. Click Activate before editing or saving that form."
                )
                self.refresh_view(reason="Created new stored form from current editor")
                self.set_status_message(action_message)
                self._emit_host_toast(action_message, bootstyle="success")
            except Exception as exc:
                self.set_status_message(f"Create form failed: {exc}", error=True)

        self._run_busy_action(f"Creating form '{name}'...", _execute)

    def create_blank_form(self):
        from app.controllers.form_wizard_qt_controller import FormWizardQtController
        
        wizard = FormWizardQtController(parent_view=self.view)
        if not wizard.exec():
            return
            
        form_id = wizard.created_form_id
        if not form_id:
            return
            
        self.set_selected_form_id(form_id)
        self.refresh_forms()
        action_message = (
            f"Created form '{wizard.created_form_name}'. Click Activate before editing or saving that form."
        )
        self.refresh_view(reason="Created blank stored form")
        self.set_status_message(action_message)
        self._emit_host_toast(action_message, bootstyle="success")
        
        # Check for missing standard fields and prompt to inject
        try:
            config, source_path, form_info = self.model.load_form_config(form_id)
            updated_config, name, description = self.check_and_prompt_for_missing_fields(config, filename=source_path)
            if updated_config != config or name or description:
                if name or description:
                    curr_name = form_info.get("name")
                    curr_desc = form_info.get("description")
                    if (name and name != curr_name) or (description is not None and description != curr_desc):
                        form_info = self.model.rename_form(form_id, name or curr_name, description=description if description is not None else curr_desc)
                self.model.save_config(updated_config, form_info=form_info)
                self.set_selected_form_id(form_info.get("id"))
                self.refresh_forms()
                self.refresh_view(reason="Created blank stored form with injected fields")
        except Exception as exc:
            self.set_status_message(f"Check for missing fields failed on blank creation: {exc}", error=True)

    def import_form(self):
        selected_file = self.view.choose_import_json_file()
        if not selected_file:
            return

        def _execute():
            try:
                import os
                with open(selected_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as exc:
                self.view.show_error("Import Error", f"Failed to parse JSON file:\n{exc}")
                return

            try:
                # Detect missing fields and metadata
                updated_config, name, description = self.check_and_prompt_for_missing_fields(config, filename=selected_file)
                
                # Ensure we have a form name
                if not name:
                    base_name = os.path.splitext(os.path.basename(selected_file))[0]
                    clean_name = base_name.replace("_", " ").replace("-", " ").title()
                    name = self.view.prompt_text("Import Form", "Form name:", default_text=clean_name)
                    if not name:
                        return
                    description = self.view.prompt_text("Import Form", "Description:", default_text=f"Imported from {os.path.basename(selected_file)}") or ""
                
                if not updated_config.get("export_prefix"):
                    updated_config["export_prefix"] = name

                # Create/register the new form from config
                form_info = self.model.create_form_from_config(name, updated_config, description=description, activate=False)
                
                form_id = form_info.get("id")
                self.set_selected_form_id(form_id)
                self.refresh_forms()
                
                action_message = f"Imported form '{name}'. Click Activate before editing or saving that form."
                self.refresh_view(reason="Imported form layout configuration")
                self.set_status_message(action_message)
                self._emit_host_toast(action_message, bootstyle="success")
            except Exception as exc:
                self.set_status_message(f"Import form failed: {exc}", error=True)
                self.view.show_error("Import Form Failed", f"An error occurred during import:\n{exc}")

        self._run_busy_action(f"Importing form from '{os.path.basename(selected_file)}'...", _execute)

    def duplicate_form(self):
        source_form_id = self.view.current_form_id() or self.current_form_info.get("id")
        if not source_form_id:
            self.view.set_status("Select a form to duplicate.", error=True)
            return
        source_form_name = self.selected_form_name() or self.current_form_info.get("name", source_form_id)
        default_name = f"{source_form_name} Copy"
        name = self.view.prompt_text("Duplicate Form", "Duplicate form name:", default_text=default_name)
        if not name:
            return
        description = self.view.prompt_text("Duplicate Form", "Description:", default_text="") or ""

        def _execute():
            form_info = self.model.duplicate_form(source_form_id, name, description=description, activate=False)
            self.set_selected_form_id(form_info.get("id"))
            self.refresh_forms()
            action_message = f"Duplicated form '{name}'. Click Activate before editing or saving that form."
            self.refresh_view(reason="Duplicated selected stored form")
            self.set_status_message(action_message)
            self._emit_host_toast(action_message, bootstyle="success")

        self._run_busy_action(f"Duplicating form '{source_form_id}'...", _execute)

    def rename_form(self):
        form_id = self.view.current_form_id() or self.current_form_info.get("id")
        if not form_id:
            self.view.set_status("Select a form to rename.", error=True)
            return
        selected_form_info = self.model.get_form_info(form_id)
        current_name = selected_form_info.get("name", form_id)
        name = self.view.prompt_text("Rename Form", "New form name:", default_text=current_name)
        if not name:
            return
        description = self.view.prompt_text(
            "Rename Form",
            "Description:",
            default_text=selected_form_info.get("description", ""),
        )
        def _execute():
            form_info = self.model.rename_form(form_id, name, description=description)
            self.set_selected_form_id(form_info.get("id"))
            self.update_current_form_info_if_loaded(form_info)
            self.refresh_forms()
            self.refresh_view(reason="Renamed selected form")
            action_message = f"Renamed form to '{name}'."
            if self.selection_differs_from_loaded():
                action_message = f"{action_message} '{self.selected_form_name()}' remains stored only until you activate it."
            self.set_status_message(action_message)
            self._emit_host_toast(action_message, bootstyle="success")

        self._run_busy_action(f"Renaming form '{form_id}'...", _execute)

    def delete_form(self):
        form_id = self.view.current_form_id() or self.current_form_info.get("id")
        if not form_id:
            self.view.set_status("Select a form to delete.", error=True)
            return
        form_info = self.model.get_form_info(form_id)
        form_name = form_info.get("name", form_id)
        dependency_audit = self.model.build_form_dependency_audit(form_id)
        dependent_drafts = dependency_audit.get("dependent_drafts") or []
        if dependent_drafts:
            draft_lines = [f"- {draft.get('filename')} ({draft.get('saved_at')})" for draft in dependent_drafts[:8]]
            if len(dependent_drafts) > 8:
                draft_lines.append(f"- ... and {len(dependent_drafts) - 8} more")
            warning_message = "\n".join(
                [
                    f"Cannot delete '{form_name}' while pending Form Loader drafts still depend on it.",
                    "",
                    dependency_audit.get("summary") or "",
                    "",
                    *draft_lines,
                    "",
                    "Clear or migrate those drafts first, then retry the delete.",
                ]
            )
            self.view.set_status(f"Delete blocked for '{form_name}' because pending drafts still depend on it.", error=True)
            self.view.show_warning("Delete Form Blocked", warning_message)
            return
        if not self.view.confirm(
            "Delete Form",
            f"Delete '{form_name}'? This removes the stored layout form.",
        ):
            return
        def _execute():
            result = self.model.delete_form(form_id)
            active_changed = bool((result or {}).get("active_changed"))
            deleted_form = (result or {}).get("deleted_form") or {}
            active_form = (result or {}).get("active_form") or {}
            deleted_form_id = str(deleted_form.get("id") or form_id).strip()
            load_error = None
            if deleted_form_id == self.loaded_form_id() or active_changed:
                try:
                    config, source_path, loaded_form_info = self.model.load_current_config()
                    editor_text = self.model.load_current_text()
                    self.set_loaded_form_state(config, source_path, loaded_form_info)
                except ValueError as exc:
                    load_error = str(exc)
                    try:
                        editor_text = self.model.load_current_text()
                    except Exception:
                        editor_text = None
            elif active_form:
                self.set_selected_form_id(active_form.get("id"))
                editor_text = None
            elif deleted_form_id == str(self.selected_form_id or "").strip():
                self.set_selected_form_id(self.loaded_form_id())
                editor_text = None
            else:
                editor_text = None
            self.refresh_forms()
            action_message = f"Deleted form '{form_name}'."
            if load_error:
                self.refresh_view(reason="Deleted form; active form has invalid config", editor_text_override=editor_text)
                self.set_status_message(
                    f"{action_message} Warning: active form config is invalid — {load_error}",
                    error=True,
                )
                self._emit_host_toast(action_message, bootstyle="warning")
            elif deleted_form_id == self.loaded_form_id() or active_changed:
                self.mark_clean(action_message)
                if self.embedded and self.dispatcher is not None:
                    self.dispatcher.notify_active_form_changed(source_instance=self, active_form_info=self.current_form_info)
                self._emit_host_toast(action_message, bootstyle="success")
            else:
                self.refresh_view(reason="Deleted selected stored form", editor_text_override=editor_text)
                self.set_status_message(action_message)
                self._emit_host_toast(action_message, bootstyle="success")

        self._run_busy_action(f"Deleting form '{form_name}'...", _execute)

    def migrate_forms_storage(self):
        if not self.view.confirm(
            "Migrate Forms",
            "Migrate stored forms to per-form folders and ensure companion calculation JSON metadata is present?\n\n"
            "This rewrites form layout paths in the form registry.",
        ):
            return

        def _execute():
            try:
                import os
                # Check and prompt for missing standard fields before migrating
                registry = self.model.service.registry
                registry_payload = registry.get_registry()
                forms = registry_payload.get("forms") if isinstance(registry_payload.get("forms"), list) else []
                
                for form_record in forms:
                    if not isinstance(form_record, dict) or form_record.get("built_in"):
                        continue
                    form_id = form_record.get("id")
                    if not form_id:
                        continue
                        
                    try:
                        config, source_path, form_info = self.model.load_form_config(form_id)
                        updated_config, name, description = self.check_and_prompt_for_missing_fields(config, filename=source_path)
                        if updated_config != config or name or description:
                            if name or description:
                                curr_name = form_info.get("name")
                                curr_desc = form_info.get("description")
                                if (name and name != curr_name) or (description is not None and description != curr_desc):
                                    form_info = self.model.rename_form(form_id, name or curr_name, description=description if description is not None else curr_desc)
                            self.model.save_config(updated_config, form_info=form_info)
                    except Exception as exc:
                        print(f"Error checking form '{form_id}' during migration: {exc}")

                result = self.model.migrate_forms_to_scoped_storage()
                migrated = list(result.get("migrated") or [])
                skipped = list(result.get("skipped") or [])
                config, source_path, loaded_form_info = self.model.load_current_config()
                editor_text = self.model.load_current_text()
                self.set_loaded_form_state(config, source_path, loaded_form_info)
                self.refresh_forms()
                self.refresh_view(reason="Migrated stored forms to scoped storage", editor_text_override=editor_text)
                message = f"Migrated {len(migrated)} forms to scoped folders."
                if skipped:
                    message = f"{message} Skipped {len(skipped)} forms."
                self.set_status_message(message)
                self._emit_host_toast(message, bootstyle="success")
                details = [
                    message,
                    "",
                    f"Migrated: {', '.join(migrated) if migrated else 'None'}",
                    f"Skipped: {', '.join(skipped) if skipped else 'None'}",
                ]
                self.view.show_info("Migration Complete", "\n".join(details))
            except Exception as exc:
                self.set_status_message(f"Migration failed: {exc}", error=True)

        self._run_busy_action("Migrating forms and companion calculations...", _execute)

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
        if not self.has_actual_changes():
            return True
        return self.view.confirm(
            "Unsaved Changes",
            "Close the Qt layout manager and discard unsaved changes?",
        )

    def handle_close(self):
        self.write_state(status="closed", message="Layout Manager Qt window closed.")
