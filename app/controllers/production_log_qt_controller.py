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
import time
import webbrowser

from app.models.production_log_model import ProductionLogModel
from app.views.production_log_qt_view import ProductionLogQtView

__module_name__ = "Production Log Qt Controller"
__version__ = "1.2.0"


class ProductionLogQtController:
    def __init__(self, payload=None, parent=None, dispatcher=None):
        payload = dict(payload or {}) if isinstance(payload, dict) else {}
        self.parent = parent
        self.dispatcher = dispatcher
        self.embedded = dispatcher is not None
        self.payload = dict(payload)
        self.model = ProductionLogModel(data_registry=getattr(dispatcher, "external_data_registry", None))
        self.layout_config = self.model.load_layout_config()
        self.header_fields = self.model.get_section_field_configs("header", config=self.layout_config)
        self.production_fields = self.model.get_section_field_configs("production", config=self.layout_config)
        self.downtime_fields = self.model.get_section_field_configs("downtime", config=self.layout_config)
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
            "window_title": "Production Log - Production Logging Center",
            "title": "Production Log",
            "subtitle": "Primary Production Log editor for the shared PyQt6 workspace.",
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
            self.header_fields,
            self.production_fields,
            self.downtime_fields,
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
        self.header_fields = self.model.get_section_field_configs("header", config=self.layout_config)
        self.production_fields = self.model.get_section_field_configs("production", config=self.layout_config)
        self.downtime_fields = self.model.get_section_field_configs("downtime", config=self.layout_config)

    def _rebuild_view_payload(self):
        if self.embedded:
            self.payload = self._build_view_payload()
            return
        self.payload["theme_tokens"] = dict(self.payload.get("theme_tokens") or {})

    def get_active_form_info(self):
        return dict(self.model.form_registry.get_active_form())

    def serialize_ui_data(self, data=None):
        payload = dict(data or self.collect_ui_data())
        if "balance_state" not in payload:
            payload["balance_state"] = dict(self.balance_state or {})
        return self.model.serialize_ui_data(payload)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def _initialize_form(self):
        self.view.set_form_name(self.model.get_active_form_name())
        self.balance_state = self.model.normalize_balance_state()
        self.current_draft_path = None
        self.view.set_form_data(self._default_header_payload(), [{}], [{}])
        self.view.mark_clean(self.collect_ui_data())
        self.view.set_status("Production Log Qt editor ready.")

    def _default_header_payload(self):
        payload = {}
        for field in self.header_fields:
            field_id = str(field.get("id") or "").strip()
            if not field_id:
                continue
            payload[field_id] = str(field.get("default") or "")
        return payload

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
            message = "Production Log viewport ready." if self.embedded else "Production Log Qt editor ready."
        else:
            message = "Draft and recovery lists refreshed."
            self.view.set_status(message)
        self.write_state(status="ready", message=message)

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
            return
        if self.model.is_form_blank(data):
            if not is_auto:
                self.view.show_info("Production Log", "Enter data before saving a draft.")
            return
        try:
            draft_path, _payload, _backup_info = self.model.save_draft_data(data, __version__, is_auto=is_auto)
        except Exception as exc:
            if not is_auto:
                self.view.show_error("Draft Save Error", f"Could not save draft:\n{exc}")
            return

        self.current_draft_path = draft_path
        self.refresh_draft_lists(initial=False)
        self.view.mark_clean(data)
        if is_auto:
            self.write_state(status="ready", message=f"Auto-saved draft {os.path.basename(draft_path)}.")
            return
        self.view.show_toast("Draft Saved", f"Saved draft {os.path.basename(draft_path)}.")
        self.write_state(status="ready", message=f"Saved draft {os.path.basename(draft_path)}.")

    def auto_save(self):
        if self.view.has_unsaved_changes:
            self.save_draft(is_auto=True)

    def _apply_loaded_payload(self, payload, draft_path=None, mark_dirty_after_load=False):
        payload = dict(payload or {})
        self.balance_state = self.model.normalize_balance_state(payload.get("balance_state"))
        self.current_draft_path = draft_path
        production_rows = list(payload.get("production") or []) or [{}]
        downtime_rows = list(payload.get("downtime") or []) or [{}]
        self.view.set_form_name(self.model.get_active_form_name())
        self.view.set_form_data(payload.get("header") or {}, production_rows, downtime_rows)
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
            self.view.show_info("Production Log", "No draft path was provided.")
            return False
        if not os.path.exists(draft_path):
            self.view.show_error("Production Log", f"Draft not found:\n{draft_path}")
            return False
        if prompt_discard and not self.view.confirm_discard_unsaved_changes():
            return False

        try:
            payload = self.model.load_json(draft_path)
        except Exception as exc:
            self.view.show_error("Production Log", f"Could not load draft:\n{exc}")
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
        self.resume_latest_draft()

    def resume_latest_draft(self):
        latest = self.model.get_latest_pending_draft()
        if not latest:
            self.view.show_info("Resume Latest", "No pending drafts are available.")
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

    def open_recovery_viewer(self):
        if self.dispatcher is None:
            return None
        self.dispatcher.load_module("recovery_viewer", use_transition=False, ensure_authorized=False)
        recovery_instance = getattr(self.dispatcher, "active_module_instance", None)
        if recovery_instance is not None and hasattr(recovery_instance, "refresh_records"):
            try:
                recovery_instance.refresh_records()
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
            self.view.show_error("Production Log", f"Could not open path:\n{exc}")

    def open_pending_folder(self):
        self._open_path(self.model.get_pending_dir())

    def open_recovery_folder(self):
        self._open_path(self.model.get_pending_history_dir())

    def delete_current_draft(self):
        draft_path = str(self.current_draft_path or "").strip()
        if not draft_path:
            self.view.show_info("Delete Current Draft", "There is no saved draft attached to the current session.")
            return
        if not os.path.exists(draft_path):
            self.current_draft_path = None
            self.refresh_draft_lists(initial=False)
            self.view.show_info("Delete Current Draft", "The current draft file no longer exists.")
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
        _ = snapshot_path
        self.open_recovery_viewer()
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
        if total_molds_field_id in self.view.header_widgets:
            self.view.header_widgets[total_molds_field_id].setText(str(total_molds))

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
            self.view.show_info("Production Log", "Enter data before exporting.")
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
            self.view.set_status(f"Exported workbook: {os.path.basename(target_path)}")
            self._show_data_handler_warnings("export")
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
            self.view.show_toast("Import Complete", "Imported workbook into Production Log.")
            self._show_data_handler_warnings("import")
        except Exception as exc:
            self.view.show_error("Import Error", f"Failed to import Excel:\n{exc}")

    def poll_commands(self):
        return None

    def handle_close(self):
        if self.embedded:
            return None
        self.write_state(status="closed", message="Production Log Qt window closed.")

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})

    def on_active_form_changed(self, active_form_info=None, form_id=None):
        _ = active_form_info
        _ = form_id
        try:
            if self.view.has_unsaved_changes and not self.model.is_form_blank(self.collect_ui_data()):
                self.save_draft(is_auto=True)
        except Exception:
            pass
        self.reload_active_form()

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
