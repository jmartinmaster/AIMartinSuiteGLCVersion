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
import webbrowser

from app.models.production_log_model import ProductionLogModel
from app.views.production_log_qt_view import ProductionLogQtView

__module_name__ = "Production Log Qt Controller"
__version__ = "1.1.0"


class ProductionLogQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.model = ProductionLogModel()
        self.layout_config = self.model.load_layout_config()
        self.header_fields = self.model.get_section_field_configs("header", config=self.layout_config)
        self.production_fields = self.model.get_section_field_configs("production", config=self.layout_config)
        self.downtime_fields = self.model.get_section_field_configs("downtime", config=self.layout_config)
        self.pending_drafts = []
        self.recovery_snapshots = []
        self.current_draft_path = None
        self.auto_save_interval_ms = max(60000, int(getattr(self.model, "auto_save_interval", 300000) or 300000))
        self.view = ProductionLogQtView(
            self,
            self.payload,
            self.header_fields,
            self.production_fields,
            self.downtime_fields,
        )
        self._initialize_form()
        self.refresh_draft_lists(initial=True)
        self.calculate_metrics()

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def _initialize_form(self):
        self.view.set_form_name(self.model.get_active_form_name())
        self.view.set_form_data(self._default_header_payload(), [], [])
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
        if not self.state_path:
            return
        latest_name = "None"
        if self.pending_drafts:
            latest_name = str(self.pending_drafts[0].get("filename") or "None")
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": "production_log",
            "pending_draft_count": len(self.pending_drafts),
            "recovery_snapshot_count": len(self.recovery_snapshots),
            "latest_draft_name": latest_name,
            "dt_code_count": len(self.model.dt_codes or []),
            "form_name": self.model.get_active_form_name(),
            "updated_at": time.time(),
        }
        if runtime_event:
            payload["runtime_event"] = str(runtime_event)
        if isinstance(metadata, dict):
            payload.update(metadata)
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def refresh_draft_lists(self, initial=False):
        self.pending_drafts = self.model.list_pending_drafts()
        self.recovery_snapshots = self.model.list_recovery_snapshots()
        latest_name = self.pending_drafts[0].get("filename") if self.pending_drafts else "None"
        self.view.set_draft_status(len(self.pending_drafts), len(self.recovery_snapshots), latest_name)
        if initial:
            message = "Production Log Qt editor ready."
        else:
            message = "Draft and recovery lists refreshed."
            self.view.set_status(message)
        self.write_state(status="ready", message=message)

    def collect_ui_data(self):
        return self.view.collect_form_data()

    def save_draft(self, is_auto=False):
        self.calculate_metrics(silent=is_auto)
        data = self.collect_ui_data()
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

        self.refresh_draft_lists(initial=False)
        if is_auto:
            self.write_state(status="ready", message=f"Auto-saved draft {os.path.basename(draft_path)}.")
            return
        self.view.set_status(f"Draft saved: {os.path.basename(draft_path)}")
        self.write_state(status="ready", message=f"Saved draft {os.path.basename(draft_path)}.")

    def auto_save(self):
        self.save_draft(is_auto=True)

    def load_draft_path(self, draft_path):
        draft_path = str(draft_path or "").strip()
        if not draft_path:
            self.view.show_info("Production Log", "No draft path was provided.")
            return False
        if not os.path.exists(draft_path):
            self.view.show_error("Production Log", f"Draft not found:\n{draft_path}")
            return False

        try:
            payload = self.model.load_json(draft_path)
        except Exception as exc:
            self.view.show_error("Production Log", f"Could not load draft:\n{exc}")
            return False

        self.view.set_form_data(
            payload.get("header") or {},
            payload.get("production") or [],
            payload.get("downtime") or [],
        )
        self.current_draft_path = draft_path
        self.calculate_metrics()
        self.refresh_draft_lists(initial=False)
        self.view.set_status(f"Loaded {os.path.basename(draft_path)}")
        self.write_state(status="ready", message=f"Loaded draft {os.path.basename(draft_path)}.")
        return True

    def refresh_view(self):
        self.resume_latest_draft()

    def resume_latest_draft(self):
        latest = self.model.get_latest_pending_draft()
        if not latest:
            self.view.show_info("Resume Latest", "No pending drafts are available.")
            return
        self.load_draft_path(str(latest.get("path") or ""))

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

    def open_pending_dialog(self):
        self.refresh_draft_lists(initial=False)
        self.view.show_pending_dialog(self.pending_drafts)

    def show_pending(self):
        self.open_pending_dialog()

    def open_recovery_dialog(self):
        self.refresh_draft_lists(initial=False)
        self.view.show_recovery_dialog(self.recovery_snapshots)

    def open_recovery_viewer(self):
        self.request_open_recovery(snapshot_path=None)

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

    def request_open_recovery(self, snapshot_path=None):
        metadata = {}
        snapshot_path = str(snapshot_path or "").strip()
        if snapshot_path:
            metadata["snapshot_path"] = snapshot_path
        self.write_state(
            status="ready",
            message="Requested host recovery viewer.",
            dirty=True,
            runtime_event="open_recovery_requested",
            metadata=metadata,
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
        try:
            data = self.model.data_handler.import_from_excel(
                file_path,
                calculation_settings=self.model.get_calculation_settings_copy(),
            )
            self.view.set_form_data(
                data.get("header") or {},
                data.get("production") or [],
                data.get("downtime") or [],
            )
            self.calculate_metrics()
            self.view.set_status("Imported workbook into Production Log.")
            self._show_data_handler_warnings("import")
        except Exception as exc:
            self.view.show_error("Import Error", f"Failed to import Excel:\n{exc}")

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
        command_payload = payload if isinstance(payload, dict) else {}

        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Production Log Qt window.")
            return

        if action == "close_window":
            self.handle_close()
            self.view.close()
            return

        if action == "refresh_snapshot":
            self.refresh_draft_lists(initial=False)
            return

        if action == "show_pending":
            self.show()
            self.open_pending_dialog()
            self.write_state(status="ready", message="Opened pending draft dialog.")
            return

        if action == "load_draft_path":
            draft_path = str(command_payload.get("draft_path") or "").strip()
            self.show()
            if not draft_path:
                self.view.show_info("Production Log", "No draft path was provided.")
                return
            if self.load_draft_path(draft_path):
                self.write_state(status="ready", message=f"Loaded draft {os.path.basename(draft_path)} from host request.")
            return

        if action == "save_draft":
            self.save_draft()
            return

        if action == "calculate_all":
            self.calculate_metrics()
            return

        if action == "export_to_excel":
            self.export_to_excel()
            return

        if action == "import_from_excel_ui":
            self.import_from_excel_ui()
            return

        if action == "host_action_completed":
            action_name = str(command_payload.get("action_name") or "host_action").strip()
            message = str(command_payload.get("message") or "Host action completed.")
            self.view.set_status(f"{action_name}: {message}")
            self.write_state(status="ready", message=f"Received host completion for {action_name}.")

    def handle_close(self):
        self.write_state(status="closed", message="Production Log Qt window closed.")
