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
import os
import sys
import time
import webbrowser

from app.models.production_log_model import BALANCE_DOWNTIME_CAUSE, ProductionLogModel
from app.views.production_log_qt_view import ProductionLogQtView

__module_name__ = "Form Loader Qt Controller"
__version__ = "1.3.0"


class ProductionLogQtController:
    def __init__(self, payload=None, parent=None, dispatcher=None):
        payload = dict(payload or {}) if isinstance(payload, dict) else {}
        self.parent = parent
        self.dispatcher = dispatcher
        self.embedded = dispatcher is not None
        self.payload = dict(payload)
        self.model = ProductionLogModel(data_registry=getattr(dispatcher, "external_data_registry", None))
        self.layout_config = self.model.load_layout_config()
        self.sections = self.model.get_sections(config=self.layout_config)
        self.header_fields = self.model.get_section_field_configs("header", config=self.layout_config)
        self.production_fields = self.model.get_section_field_configs("production", config=self.layout_config)
        self.downtime_fields = self.model.get_section_field_configs("downtime", config=self.layout_config)
        self.row_delete_policies = self._build_row_delete_policies()
        self.pending_drafts = []
        self.recovery_snapshots = []
        self.current_draft_path = None
        self.balance_state = self.model.normalize_balance_state()
        self.auto_save_interval_ms = max(60000, int(getattr(self.model, "auto_save_interval", 300000) or 300000))
        if self.embedded:
            self.payload = self._build_view_payload()
        self._create_view()
        self._initialize_form()
        self.refresh_draft_lists(initial=True)
        self.calculate_metrics()
        if self.embedded:
            self.view.show()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        pending_drafts = self.model.list_pending_drafts()
        recovery_snapshots = self.model.list_recovery_snapshots()
        latest_draft_name = str(pending_drafts[0].get("filename") or "None") if pending_drafts else "None"
        return {
            "window_title": "Form Loader - Production Logging Center",
            "title": "Form Loader",
            "subtitle": "Primary form loader editor for the shared PyQt6 workspace.",
            "pending_draft_count": len(pending_drafts),
            "recovery_snapshot_count": len(recovery_snapshots),
            "latest_draft_name": latest_draft_name,
            "dt_code_count": len(self.model.dt_codes or []),
            "updated_at": time.time(),
            "theme_tokens": theme_tokens,
        }

    def _create_view(self):
        self.view = ProductionLogQtView(
            self,
            self.payload,
            self.sections,
            self.header_fields,
            self.production_fields,
            self.downtime_fields,
            row_delete_policies=self.row_delete_policies,
            parent_widget=self.parent,
        )

    def _dispose_view(self):
        view = self.__dict__.get("view")
        if view is None:
            return
        try:
            view.hide()
        except Exception:
            pass
        try:
            if self.embedded:
                view.setParent(None)
        except Exception:
            pass
        try:
            view.deleteLater()
        except Exception:
            pass

    def _reload_layout_fields(self):
        self.layout_config = self.model.load_layout_config()
        self.sections = self.model.get_sections(config=self.layout_config)
        self.header_fields = self.model.get_section_field_configs("header", config=self.layout_config)
        self.production_fields = self.model.get_section_field_configs("production", config=self.layout_config)
        self.downtime_fields = self.model.get_section_field_configs("downtime", config=self.layout_config)
        self.row_delete_policies = self._build_row_delete_policies()

    def _build_row_delete_policies(self):
        return {
            "production": self.model.get_delete_row_policy("production", config=self.layout_config),
            "downtime": self.model.get_delete_row_policy("downtime", config=self.layout_config),
        }

    def _rebuild_view_payload(self):
        if self.embedded:
            self.payload = self._build_view_payload()
            return
        self.payload["theme_tokens"] = dict(self.payload.get("theme_tokens") or {})

    def get_active_form_info(self):
        return dict(self.model.form_registry.get_active_form())

    def list_available_forms(self):
        return [dict(form_info) for form_info in self.model.form_registry.list_forms()]

    def _refresh_form_selector(self, selected_form_id=None):
        target_form_id = str(selected_form_id or self.model.form_id or "").strip()
        self.view.set_form_options(self.list_available_forms(), target_form_id)

    def _has_entered_form_data(self):
        try:
            return not self.model.is_form_blank(self.collect_ui_data())
        except Exception:
            return bool(self.view.has_unsaved_changes)

    def _prompt_for_form_switch(self, target_form_id):
        normalized_target_form_id = self.model.form_registry.canonical_form_id(target_form_id)
        if normalized_target_form_id == self.model.form_id:
            return "cancel"
        if not self._has_entered_form_data():
            return "discard"
        current_form_name = self.model.get_active_form_name()
        target_form_name = self.model.get_form_name_for_id(normalized_target_form_id)
        return self.view.ask_form_switch_action(current_form_name, target_form_name)

    def _resolve_notified_form_id(self, active_form_info=None, form_id=None):
        raw_form_id = ""
        if isinstance(active_form_info, dict):
            raw_form_id = str(active_form_info.get("id") or "").strip()
        if not raw_form_id:
            raw_form_id = str(form_id or "").strip()
        if not raw_form_id:
            raw_form_id = str(self.model.form_registry.get_active_form().get("id") or self.model.form_id or "").strip()
        return self.model.form_registry.canonical_form_id(raw_form_id or self.model.form_id)

    def _cancel_external_form_switch(self, current_form_id):
        normalized_current_form_id = self.model.form_registry.canonical_form_id(current_form_id or self.model.form_id)
        self.model.form_registry.activate_form(normalized_current_form_id)
        self._refresh_form_selector(normalized_current_form_id)
        self.view.set_status("Form switch cancelled.")
        self.write_state(status="ready", message="Form switch cancelled.")
        if hasattr(self.dispatcher, "notify_active_form_changed"):
            self.dispatcher.notify_active_form_changed(source_instance=self, active_form_info=self.get_active_form_info())
        return False

    def _switch_active_form(self, target_form_id, notify_others=True):
        normalized_target_form_id = self.model.form_registry.canonical_form_id(target_form_id)
        self.model.form_registry.activate_form(normalized_target_form_id)
        self.reload_active_form()
        self.view.set_status(f"Activated form {self.model.get_active_form_name()}.")
        self.write_state(status="ready", message=f"Activated form {self.model.get_active_form_name()}.")
        if notify_others and hasattr(self.dispatcher, "notify_active_form_changed"):
            self.dispatcher.notify_active_form_changed(source_instance=self, active_form_info=self.get_active_form_info())
        return True

    def activate_selected_form(self):
        target_form_id = str(self.view.current_form_id() or "").strip()
        if not target_form_id:
            self.view.show_info("Form Loader", "Select a stored form first.")
            self._refresh_form_selector()
            return False

        normalized_target_form_id = self.model.form_registry.canonical_form_id(target_form_id)
        if normalized_target_form_id == self.model.form_id:
            self.view.set_status("Selected form is already active.")
            self._refresh_form_selector()
            return False

        switch_action = self._prompt_for_form_switch(normalized_target_form_id)
        if switch_action == "cancel":
            self.view.set_status("Form switch cancelled.")
            self._refresh_form_selector()
            return False

        if switch_action == "save" and not self.save_draft(is_auto=False):
            self._refresh_form_selector()
            return False

        return self._switch_active_form(normalized_target_form_id, notify_others=True)

    def serialize_ui_data(self, data=None):
        payload = dict(data or self.collect_ui_data())
        if "balance_state" not in payload:
            payload["balance_state"] = dict(self.balance_state or {})
        return self.model.serialize_ui_data(payload)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def show_toast(self, title, message, bootstyle=None):
        dispatcher = self.dispatcher
        show_toast = getattr(dispatcher, "show_toast", None)
        if callable(show_toast):
            show_toast(title, message, bootstyle)
            self.view.set_status(message)
            return
        self.view.show_info(title, message)

    def _initialize_form(self):
        self.view.set_form_name(self.model.get_active_form_name())
        self._refresh_form_selector()
        self.balance_state = self.model.normalize_balance_state()
        self.current_draft_path = None
        self.view.set_form_data(self._default_header_payload(), [{}], [{}])
        self.view.mark_clean(self.collect_ui_data())
        self.view.set_status("Form Loader ready.")

    def _default_header_payload(self):
        payload = {}
        for field in self.header_fields:
            field_id = str(field.get("id") or "").strip()
            if not field_id:
                continue
            payload[field_id] = str(field.get("default") or "")
        return self.model.normalize_header_data(payload)

    def apply_header_data(self, header_data, mark_dirty=False):
        normalized_header = self.model.normalize_header_data(header_data)
        for field_id, value in normalized_header.items():
            self.view.set_header_field_value(field_id, value)
        if mark_dirty:
            self.view.mark_dirty()
        return normalized_header

    def on_header_field_focus_out(self, _event=None):
        header_payload = self.collect_ui_data().get("header") or {}
        self.apply_header_data(header_payload, mark_dirty=False)

    def write_state(self, status="ready", message="", dirty=False, runtime_event=None, metadata=None):
        _ = status
        _ = message
        _ = dirty
        _ = runtime_event
        _ = metadata
        return None

    def refresh_draft_lists(self, initial=False):
        self.pending_drafts = self.model.list_pending_drafts()
        self.recovery_snapshots = self.model.list_recovery_snapshots()
        latest_name = self.pending_drafts[0].get("filename") if self.pending_drafts else "None"
        self.view.set_draft_status(len(self.pending_drafts), len(self.recovery_snapshots), latest_name)
        if initial:
            message = "Form Loader viewport ready." if self.embedded else "Form Loader ready."
        else:
            message = "Draft and recovery lists refreshed."
            self.view.set_status(message)
        self.write_state(status="ready", message=message)
        self.update_export_action_state()

    def collect_ui_data(self):
        data = self.view.collect_form_data()
        data["balance_state"] = dict(self.balance_state or {})
        return data

    def can_navigate_away(self):
        return self.view.confirm_discard_unsaved_changes()

    def save_draft(self, is_auto=False):
        self.calculate_metrics(silent=is_auto)
        data = self.collect_ui_data()
        if is_auto and not self.view.has_unsaved_changes:
            return False
        if self.model.is_form_blank(data):
            if not is_auto:
                self.view.show_info("Form Loader", "Enter data before saving a draft.")
            return False
        try:
            draft_path, _payload, _backup_info = self.model.save_draft_data(data, __version__, is_auto=is_auto)
        except Exception as exc:
            if not is_auto:
                self.view.show_error("Draft Save Error", f"Could not save draft:\n{exc}")
            return False

        self.current_draft_path = draft_path
        self.refresh_draft_lists(initial=False)
        self.view.mark_clean(data)
        if is_auto:
            self.write_state(status="ready", message=f"Auto-saved draft {os.path.basename(draft_path)}.")
            return True
        self.show_toast("Draft Saved", f"Saved draft {os.path.basename(draft_path)}.")
        self.write_state(status="ready", message=f"Saved draft {os.path.basename(draft_path)}.")
        return True

    def auto_save(self):
        if self.view.has_unsaved_changes:
            self.save_draft(is_auto=True)

    def _apply_loaded_payload(self, payload, draft_path=None, mark_dirty_after_load=False):
        payload = dict(payload or {})
        self.balance_state = self.model.normalize_balance_state(payload.get("balance_state"))
        self.current_draft_path = draft_path
        normalized_header = self.model.normalize_header_data(payload.get("header") or {})
        production_rows = list(payload.get("production") or []) or [{}]
        downtime_rows = list(payload.get("downtime") or []) or [{}]
        self.view.set_form_name(self.model.get_active_form_name())
        self._refresh_form_selector()
        self.view.set_form_data(normalized_header, production_rows, downtime_rows)
        if mark_dirty_after_load:
            self.view.mark_dirty()
        else:
            self.view.mark_clean(self.collect_ui_data())

    def reload_active_form(self, data=None, draft_path=None, mark_dirty_after_load=False):
        self.model = ProductionLogModel(data_registry=getattr(self.dispatcher, "external_data_registry", None))
        self._reload_layout_fields()
        self._rebuild_view_payload()
        self._dispose_view()
        self._create_view()
        if data is None:
            self._initialize_form()
        else:
            self._apply_loaded_payload(data, draft_path=draft_path, mark_dirty_after_load=mark_dirty_after_load)
        self.refresh_draft_lists(initial=True)
        self.calculate_metrics(silent=True)

    def load_draft_path(self, draft_path, prompt_discard=True):
        draft_path = str(draft_path or "").strip()
        if not draft_path:
            self.view.show_info("Form Loader", "No draft path was provided.")
            return False
        if not os.path.exists(draft_path):
            self.view.show_error("Form Loader", f"Draft not found:\n{draft_path}")
            return False
        if prompt_discard and not self.view.confirm_discard_unsaved_changes():
            return False

        try:
            payload = self.model.load_json(draft_path)
        except Exception as exc:
            self.view.show_error("Form Loader", f"Could not load draft:\n{exc}")
            return False

        draft_form_id = self.model.resolve_draft_form_id(payload.get("meta", {}))
        if draft_form_id != self.model.form_id:
            self.model.form_registry.activate_form(draft_form_id)
            if hasattr(self.dispatcher, "notify_active_form_changed"):
                self.dispatcher.notify_active_form_changed(source_instance=self, active_form_info=self.get_active_form_info())
            self.reload_active_form(data=payload, draft_path=draft_path, mark_dirty_after_load=False)
            self.view.set_status(f"Loaded {os.path.basename(draft_path)}")
            self.write_state(status="ready", message=f"Loaded draft {os.path.basename(draft_path)}.")
            return True

        self._apply_loaded_payload(payload, draft_path=draft_path, mark_dirty_after_load=False)
        self.calculate_metrics()
        self.refresh_draft_lists(initial=False)
        self.view.set_status(f"Loaded {os.path.basename(draft_path)}")
        self.write_state(status="ready", message=f"Loaded draft {os.path.basename(draft_path)}.")
        return True

    def delete_draft_file(self, draft_path):
        draft_path = str(draft_path or "").strip()
        if not draft_path:
            return False
        if not os.path.exists(draft_path):
            self.refresh_draft_lists(initial=False)
            if self.current_draft_path == draft_path:
                self.current_draft_path = None
            return False
        try:
            self.model.delete_file(draft_path)
        except Exception as exc:
            self.view.show_error("Delete Draft", f"Could not delete draft:\n{exc}")
            return False

        if self.current_draft_path == draft_path:
            self.current_draft_path = None
        self.refresh_draft_lists(initial=False)
        self.view.set_status(f"Deleted draft {os.path.basename(draft_path)}")
        self.write_state(status="ready", message=f"Deleted draft {os.path.basename(draft_path)}.")
        return True

    def refresh_view(self):
        latest = self.model.get_latest_pending_draft()
        if not latest:
            self.show_toast("Refresh View", "No previous draft found to reload.", "info")
            return
        self.load_draft_path(str(latest.get("path") or ""))

    def resume_latest_draft(self):
        latest = self.model.get_latest_pending_draft()
        if not latest:
            self.show_toast("Resume Latest", "No pending drafts are available.", "info")
            return
        self.load_draft_path(str(latest.get("path") or ""))

    def open_pending_dialog(self):
        self.refresh_draft_lists(initial=False)
        self.view.show_pending_dialog(self.pending_drafts)

    def show_pending(self):
        self.open_pending_dialog()

    def open_recovery_dialog(self):
        self.refresh_draft_lists(initial=False)
        self.view.show_recovery_dialog(self.recovery_snapshots)

    def open_recovery_viewer(self, snapshot_path=None):
        if self.dispatcher is None:
            return None
        self.dispatcher.load_module("recovery_viewer", use_transition=False, ensure_authorized=False)
        recovery_instance = getattr(self.dispatcher, "active_module_instance", None)
        selected_record_path = str(snapshot_path or "").strip() or None
        if recovery_instance is not None and hasattr(recovery_instance, "refresh_records"):
            try:
                recovery_instance.refresh_records()
            except Exception:
                pass
        if selected_record_path and recovery_instance is not None and hasattr(recovery_instance, "focus_record_path"):
            try:
                recovery_instance.focus_record_path(selected_record_path)
            except Exception:
                pass
        return None

    def _open_path(self, path):
        if not path:
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)
            else:
                webbrowser.open(f"file://{path}")
            self.view.set_status(f"Opened {os.path.basename(path)}")
        except Exception as exc:
            self.view.show_error("Form Loader", f"Could not open path:\n{exc}")

    def open_pending_folder(self):
        self._open_path(self.model.get_pending_dir())

    def open_recovery_folder(self):
        self._open_path(self.model.get_pending_history_dir())

    def delete_current_draft(self):
        draft_path = str(self.current_draft_path or "").strip()
        if not draft_path:
            self.show_toast("Delete Draft", "There is no saved draft attached to the current session.", "info")
            return
        if not os.path.exists(draft_path):
            self.current_draft_path = None
            self.refresh_draft_lists(initial=False)
            self.show_toast("Delete Draft", "There is no saved draft attached to the current session.", "info")
            return
        if not self.view.ask_yes_no("Delete Current Draft", f"Delete {os.path.basename(draft_path)}?"):
            return
        self.delete_draft_file(draft_path)

    def restore_snapshot_to_form(self, snapshot_path):
        if self.load_draft_path(snapshot_path):
            self.write_state(
                status="ready",
                message=f"Restored snapshot to form: {os.path.basename(str(snapshot_path or ''))}",
            )

    def request_open_recovery(self, snapshot_path=None):
        self.open_recovery_viewer(snapshot_path=snapshot_path)
        return None

    def _header_value_by_role(self, header_payload, role_name, fallback_id=None, default=""):
        return self.model.get_header_value_by_role(
            header_payload,
            role_name,
            config=self.layout_config,
            fallback_id=fallback_id,
            default=default,
        )

    def _row_value_by_role(self, row_payload, section_name, role_name, fallback_id=None):
        field_id = self.model.get_section_field_id_by_role(
            section_name,
            role_name,
            config=self.layout_config,
            fallback_id=fallback_id,
        )
        if field_id and field_id in row_payload:
            return row_payload.get(field_id)
        if fallback_id and fallback_id in row_payload:
            return row_payload.get(fallback_id)
        return ""

    def _show_data_handler_warnings(self, operation_name):
        warnings = self.model.data_handler.get_last_operation_warnings()
        if not warnings:
            return
        message = self.model.data_handler.format_operation_warnings(warnings)
        if not message:
            return
        self.view.show_info(f"{operation_name.title()} Warnings", message)
        self.show_toast(
            f"{operation_name.title()} Warnings",
            "Some declared profiles were skipped because runtime support is not implemented yet.",
            "warning",
        )

    def _header_value_by_role(self, header_payload, role_name, fallback_id=None, default=""):
        return self.model.get_header_value_by_role(
            header_payload,
            role_name,
            config=self.layout_config,
            fallback_id=fallback_id,
            default=default,
        )

    def _row_value_by_role(self, row_payload, section_name, role_name, fallback_id=None):
        field_id = self.model.get_section_field_id_by_role(
            section_name,
            role_name,
            config=self.layout_config,
            fallback_id=fallback_id,
        )
        if field_id and field_id in row_payload:
            return row_payload.get(field_id)
        if fallback_id and fallback_id in row_payload:
            return row_payload.get(fallback_id)
        return ""

    def _set_row_value_by_role(self, row_payload, section_name, role_name, value, fallback_id=None):
        field_id = self.model.get_section_field_id_by_role(
            section_name,
            role_name,
            config=self.layout_config,
            fallback_id=fallback_id,
        )
        if field_id:
            row_payload[field_id] = value
        elif fallback_id:
            row_payload[fallback_id] = value

    def _is_balance_downtime_row(self, row_payload):
        return self.model.is_balance_downtime_cause(
            self._row_value_by_role(row_payload, "downtime", "cause_text", fallback_id="cause")
        )

    def _find_balance_downtime_index(self, downtime_rows):
        for row_index, row_payload in enumerate(downtime_rows):
            if self._is_balance_downtime_row(row_payload):
                return row_index
        return None

    def _get_last_export_path(self):
        export_path = str(getattr(self.view, "last_export_path", "") or "").strip()
        return export_path if export_path and os.path.exists(export_path) else None

    def update_export_action_state(self):
        export_available = self._get_last_export_path() is not None
        if hasattr(self.view, "open_export_button"):
            self.view.open_export_button.setEnabled(export_available)
        if hasattr(self.view, "print_export_button"):
            self.view.print_export_button.setEnabled(export_available)

    def open_last_exported_file(self, show_prompt=True):
        export_path = self._get_last_export_path()
        if not export_path:
            if show_prompt:
                self.view.show_error("Open Export", "No exported workbook is available yet.")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(export_path)
            else:
                webbrowser.open(f"file://{export_path}")
            self.show_toast("Open Export", f"Opened {os.path.basename(export_path)}", "info")
        except Exception as exc:
            self.view.show_error("Open Export", f"Could not open exported workbook:\n{exc}")

    def print_last_exported_file(self):
        export_path = self._get_last_export_path()
        if not export_path:
            self.view.show_error("Print Export", "Export a workbook first so there is something to print.")
            return
        if not self.view.ask_yes_no(
            "Print Export",
            f"Print this workbook using the default application print action?\n\n{export_path}\n\n"
            "Review it first with Open Last Export if needed.",
        ):
            return
        try:
            if sys.platform.startswith("win") and hasattr(os, "startfile"):
                os.startfile(export_path, "print")
                self.show_toast("Print Export", "Sent exported workbook to the default printer.", "info")
            else:
                self.open_last_exported_file(show_prompt=False)
                self.show_toast("Print Export", "Opened exported workbook for manual printing.", "info")
        except Exception as exc:
            self.view.show_error("Print Export", f"Could not print exported workbook:\n{exc}")

    def balance_downtime_to_shift(self):
        self.calculate_metrics(silent=True)
        data = self.collect_ui_data()
        header_payload = dict(data.get("header") or {})
        production_rows = list(data.get("production") or [])
        downtime_rows = list(data.get("downtime") or [])

        shift_total_minutes = self.model.calculate_shift_total_minutes(
            self._header_value_by_role(header_payload, "shift_hours", fallback_id="hours", default="8")
        )
        if shift_total_minutes <= 0:
            self.show_toast("Balance Downtime", "Enter a valid shift hour value before balancing.", "warning")
            return

        production_total_minutes = 0
        for row_payload in production_rows:
            production_total_minutes += self.model.parse_minutes_label(
                self._row_value_by_role(row_payload, "production", "duration_minutes", fallback_id="time_calc")
            )

        target_downtime_total = shift_total_minutes - production_total_minutes
        if target_downtime_total < 0:
            self.show_toast(
                "Balance Downtime",
                f"Production time exceeds shift total by {abs(target_downtime_total)} minutes. Downtime balance cannot correct that overrun.",
                "warning",
            )
            return

        balance_index = self._find_balance_downtime_index(downtime_rows)
        non_balance_total = 0
        for row_index, row_payload in enumerate(downtime_rows):
            if balance_index is not None and row_index == balance_index:
                continue
            non_balance_total += self.model.calculate_downtime_minutes(
                self._row_value_by_role(row_payload, "downtime", "start_clock", fallback_id="start"),
                self._row_value_by_role(row_payload, "downtime", "stop_clock", fallback_id="stop"),
                fallback_label=self._row_value_by_role(row_payload, "downtime", "duration_minutes", fallback_id="time_calc"),
            )

        balance_minutes = max(0, target_downtime_total - non_balance_total)

        if balance_minutes <= 0:
            if balance_index is not None:
                downtime_rows.pop(balance_index)
                self._apply_loaded_payload(
                    {"header": header_payload, "production": production_rows, "downtime": downtime_rows},
                    draft_path=self.current_draft_path,
                    mark_dirty_after_load=True,
                )
                self.calculate_metrics(silent=True)
                self.show_toast(
                    "Balance Downtime",
                    "Removed balance downtime row because existing downtime now covers the shift target.",
                    "success",
                )
                return
            self.show_toast("Balance Downtime", "Accounted time already matches the shift total.", "info")
            return

        if balance_index is None:
            downtime_rows.append({})
            balance_index = len(downtime_rows) - 1

        balance_row = downtime_rows[balance_index]
        self._set_row_value_by_role(balance_row, "downtime", "cause_text", BALANCE_DOWNTIME_CAUSE, fallback_id="cause")
        self._set_row_value_by_role(balance_row, "downtime", "duration_minutes", f"{balance_minutes} min", fallback_id="time_calc")

        self._apply_loaded_payload(
            {"header": header_payload, "production": production_rows, "downtime": downtime_rows},
            draft_path=self.current_draft_path,
            mark_dirty_after_load=True,
        )
        self.calculate_metrics(silent=True)
        self.show_toast(
            "Balance Downtime",
            f"Updated balance downtime row to {balance_minutes} minutes so accounted time matches the shift target.",
            "success",
        )

    def calculate_metrics(self, silent=False):
        data = self.collect_ui_data()
        header_payload = dict(data.get("header") or {})
        production_rows = list(data.get("production") or [])
        downtime_rows = list(data.get("downtime") or [])

        rates_data = self.model.load_rates_data()
        goal_value = self.model.get_global_goal_rate(
            self._header_value_by_role(header_payload, "goal_rate", fallback_id="goal_mph", default="240")
        )

        total_molds = 0
        production_total_minutes = 0
        for row_index, row_payload in enumerate(production_rows):
            part_number = self._row_value_by_role(row_payload, "production", "part_number", fallback_id="part_number")
            molds_value = self._row_value_by_role(row_payload, "production", "mold_count", fallback_id="molds")

            rate_value = self._row_value_by_role(row_payload, "production", "rate_value", fallback_id="rate_lookup")
            try:
                rate = float(str(rate_value).strip()) if str(rate_value).strip() else None
            except Exception:
                rate = None

            if rate is None:
                rate = self.model.resolve_lookup_rate(part_number, rates_data, goal_value)
                rate_field_id = self.model.get_section_field_id_by_role(
                    "production",
                    "rate_value",
                    config=self.layout_config,
                    fallback_id="rate_lookup",
                )
                self.view.set_table_field_value(
                    "production",
                    row_index,
                    rate_field_id,
                    self.model.format_rate_value(rate) if rate is not None else "",
                )

            minutes = self.model.calculate_production_minutes(molds_value, rate)
            production_total_minutes += minutes
            duration_field_id = self.model.get_section_field_id_by_role(
                "production",
                "duration_minutes",
                config=self.layout_config,
                fallback_id="time_calc",
            )
            self.view.set_table_field_value("production", row_index, duration_field_id, f"{minutes} min")
            total_molds += self.model.calculate_total_molds([molds_value])

        downtime_total_minutes = 0
        for row_index, row_payload in enumerate(downtime_rows):
            start_value = self._row_value_by_role(row_payload, "downtime", "start_clock", fallback_id="start")
            stop_value = self._row_value_by_role(row_payload, "downtime", "stop_clock", fallback_id="stop")
            duration_minutes = self.model.calculate_clock_duration_minutes(start_value, stop_value)
            duration_text = "--" if duration_minutes is None else f"{duration_minutes} min"
            if duration_minutes is not None:
                downtime_total_minutes += duration_minutes
            duration_field_id = self.model.get_section_field_id_by_role(
                "downtime",
                "duration_minutes",
                config=self.layout_config,
                fallback_id="time_calc",
            )
            self.view.set_table_field_value("downtime", row_index, duration_field_id, duration_text)

        total_molds_field_id = self.model.get_header_field_id_by_role(
            "total_molds",
            config=self.layout_config,
            fallback_id="total_molds",
        )
        self.view.set_header_field_value(total_molds_field_id, str(total_molds))

        hours_value = self._header_value_by_role(header_payload, "shift_hours", fallback_id="hours", default="8")
        shift_total_minutes = self.model.calculate_shift_total_minutes(hours_value)
        ghost_minutes = self.model.calculate_ghost_minutes(
            shift_total_minutes,
            production_total_minutes,
            downtime_total_minutes,
        )
        self.balance_state["displayed_ghost_minutes"] = int(ghost_minutes)
        efficiency = self.model.calculate_efficiency(total_molds, hours_value, goal_value)
        self.view.set_metrics(efficiency, ghost_minutes)
        if not silent:
            self.view.set_status("Calculated production metrics.")

    def export_to_excel(self):
        self.calculate_metrics()
        ui_data = self.collect_ui_data()
        if self.model.is_form_blank(ui_data):
            self.view.show_info("Form Loader", "Enter data before exporting.")
            return
        shift = str(self._header_value_by_role(ui_data.get("header", {}), "shift_number", fallback_id="shift", default="0"))
        date_text = str(self._header_value_by_role(ui_data.get("header", {}), "log_date", fallback_id="date", default="00-00-00")).replace("/", "")
        try:
            target_path = self.model.data_handler.export_to_template(
                ui_data,
                shift,
                date_text,
                calculation_settings=self.model.get_calculation_settings_copy(),
            )
            self.view.last_export_path = target_path
            self.update_export_action_state()
            self.show_toast("Export Complete", f"Excel export completed successfully: {os.path.basename(target_path)}", "success")
            self._show_data_handler_warnings("export")
            if self.view.ask_yes_no(
                "Export Complete",
                f"Workbook created successfully.\n\n{target_path}\n\nOpen it now so you can review it before printing?",
            ):
                self.open_last_exported_file(show_prompt=False)
        except Exception as exc:
            self.view.show_error("Export Error", f"Export failed:\n{exc}")

    def import_from_excel_ui(self):
        file_path = self.view.ask_import_file_path()
        if not file_path:
            return
        if not self.view.confirm_discard_unsaved_changes():
            return
        try:
            data = self.model.data_handler.import_from_excel(
                file_path,
                calculation_settings=self.model.get_calculation_settings_copy(),
            )
            self.balance_state = self.model.normalize_balance_state()
            self.current_draft_path = None
            self._apply_loaded_payload(data, draft_path=None, mark_dirty_after_load=True)
            self.calculate_metrics()
            self.show_toast("Import Complete", "Imported workbook into Form Loader.")
            self._show_data_handler_warnings("import")
        except Exception as exc:
            self.view.show_error("Import Error", f"Failed to import Excel:\n{exc}")

    def poll_commands(self):
        return None

    def handle_close(self):
        if self.embedded:
            return None
        self.write_state(status="closed", message="Form Loader window closed.")

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})

    def on_active_form_changed(self, active_form_info=None, form_id=None):
        target_form_id = self._resolve_notified_form_id(active_form_info=active_form_info, form_id=form_id)
        current_form_id = self.model.form_registry.canonical_form_id(self.model.form_id)

        if target_form_id == current_form_id:
            self._refresh_form_selector(current_form_id)
            return False

        switch_action = self._prompt_for_form_switch(target_form_id)
        if switch_action == "cancel":
            return self._cancel_external_form_switch(current_form_id)

        if switch_action == "save" and not self.save_draft(is_auto=False):
            return self._cancel_external_form_switch(current_form_id)

        return self._switch_active_form(target_form_id, notify_others=False)

    def on_calculation_settings_changed(self):
        self.model.refresh_calculation_settings()
        self.calculate_metrics(silent=True)
        self.view.set_status("Calculation settings refreshed.")

    def on_hide(self):
        return None

    def on_unload(self):
        try:
            self.view.close()
        except Exception:
            pass
