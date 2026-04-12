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
import webbrowser

import ttkbootstrap as tb
from ttkbootstrap.constants import INFO, SUCCESS, WARNING

from app import recovery_viewer
from app.models.production_log_model import ProductionLogModel
from app.views.production_log_view import ProductionLogView, __version__ as PRODUCTION_LOG_VERSION

__module_name__ = "Production Log"
__version__ = "1.2.7"


class ProductionLogController:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = ProductionLogModel()
        self.view = None
        self.view = ProductionLogView(parent, dispatcher, self, self.model)
        self.update_export_action_state()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def auto_save(self):
        if self.view.has_unsaved_changes:
            self.save_draft(is_auto=True)

    def get_pending_dir(self):
        return self.model.get_pending_dir()

    def get_pending_history_dir(self):
        return self.model.get_pending_history_dir()

    def build_draft_path(self, header_data):
        return self.model.build_draft_path(header_data)

    def list_pending_drafts(self):
        return self.model.list_pending_drafts()

    def list_recovery_snapshots(self):
        return self.model.list_recovery_snapshots()

    def get_latest_pending_draft(self):
        return self.model.get_latest_pending_draft()

    def save_draft(self, is_auto=False, suppress_toast=False):
        try:
            data = self.view.collect_ui_data()
            if is_auto and not self.view.has_unsaved_changes:
                return
            if self.model.is_form_blank(data):
                return

            draft_path, _payload, backup_info = self.model.save_draft_data(
                data,
                PRODUCTION_LOG_VERSION,
                is_auto=is_auto,
            )
            self.view.current_draft_path = draft_path
            self.view.mark_clean(data)

            if not is_auto and not suppress_toast:
                message = f"Draft saved to {os.path.basename(draft_path)}."
                if backup_info.get("versioned_backup_path"):
                    message += " A recovery snapshot of the previous draft was stored in data/pending/history."
                self.view.show_toast("Draft Saved", message, SUCCESS)
        except Exception as exc:
            self.view.show_error("Draft Save Error", f"Could not save draft: {exc}")

    def refresh_view(self):
        latest = self.get_latest_pending_draft()
        if latest:
            self.load_draft_path(latest["path"])
        else:
            self.view.show_toast("Refresh View", "No previous draft found to reload.", INFO)

    def refresh_downtime_codes(self):
        self.view.dt_codes = self.model.refresh_downtime_codes()
        for row in self.view.downtime_rows:
            code_widget = row.get("code")
            if code_widget is None:
                continue
            current_value = code_widget.get().strip()
            code_widget.configure(values=self.view.dt_codes)
            if current_value:
                code_widget.set(current_value)

    def on_hours_changed(self, _event=None):
        self.view.update_target_time_display()
        self.calculate_metrics()

    def on_goal_changed(self, _event=None):
        self.update_row_math()
        self.calculate_metrics()

    def on_header_field_focus_out(self, _event=None):
        self.view.apply_header_data(self.view.get_raw_header_data(), mark_dirty=False)

    def collect_header_data(self):
        header_data = self.model.normalize_header_data(self.view.get_raw_header_data())
        header_data["total_molds"] = str(self.calculate_total_molds())
        return header_data

    def apply_header_data(self, header_data, mark_dirty=False):
        normalized_header = self.model.normalize_header_data(header_data)
        for field_id, value in normalized_header.items():
            self.view.set_entry_value(field_id, value)
        if mark_dirty:
            self.view.mark_dirty()
        return normalized_header

    def get_target_time_value(self):
        hours_entry = self.view.entries.get("hours")
        hours_value = hours_entry.get() if hours_entry is not None else ""
        return self.model.compute_target_time(hours_value)

    def get_global_goal_rate(self):
        goal_entry = self.view.entries.get("goal_mph")
        goal_value = goal_entry.get() if goal_entry is not None else None
        return self.model.get_global_goal_rate(goal_value)

    def calculate_total_molds(self):
        return self.model.calculate_total_molds(row["molds"].get() for row in self.view.production_rows)

    def get_row_rate(self, row, rates_data, global_goal):
        if bool(row["rate_override_enabled_var"].get()):
            try:
                return float(row["rate_lookup"].get().strip())
            except Exception:
                return None
        return self.model.resolve_lookup_rate(row["part_number"].get(), rates_data, global_goal)

    def is_balance_downtime_row(self, row):
        return self.model.is_balance_downtime_cause(row["cause"].get())

    def find_balance_downtime_row(self):
        for row in self.view.downtime_rows:
            if self.is_balance_downtime_row(row):
                return row
        return None

    def get_row_duration_minutes(self, row):
        return self.model.calculate_downtime_minutes(
            row["start"].get(),
            row["stop"].get(),
            fallback_label=self.view.get_widget_value(row["time_calc"]),
        )

    def get_shift_total_minutes(self):
        hours_entry = self.view.entries.get("hours")
        hours_value = hours_entry.get() if hours_entry is not None else ""
        return self.model.calculate_shift_total_minutes(hours_value)

    def get_production_total_minutes(self):
        total_minutes = 0
        for row in self.view.production_rows:
            total_minutes += self.model.parse_minutes_label(self.view.get_widget_value(row["time_calc"]))
        return total_minutes

    def get_total_downtime_minutes(self):
        return sum(self.get_row_duration_minutes(row) for row in self.view.downtime_rows)

    def get_ghost_time_minutes(self):
        return self.model.calculate_ghost_minutes(
            self.get_shift_total_minutes(),
            self.get_production_total_minutes(),
            self.get_total_downtime_minutes(),
        )

    def collect_balance_reference_minutes(self):
        raw_values = []
        for row in self.view.downtime_rows:
            if self.is_balance_downtime_row(row):
                continue
            raw_values.append(row.get("balance_source_minutes"))
        return self.model.normalize_balance_reference_minutes(raw_values)

    def apply_balance_reference_minutes(self, reference_minutes=None):
        normalized_values = self.model.normalize_balance_reference_minutes(reference_minutes)
        rows = [row for row in self.view.downtime_rows if not self.is_balance_downtime_row(row)]
        for index, row in enumerate(rows):
            value = normalized_values[index] if index < len(normalized_values) else None
            if value is None:
                row.pop("balance_source_minutes", None)
            else:
                row["balance_source_minutes"] = value

    def collect_balance_state(self):
        return {
            "displayed_ghost_minutes": int(self.view.displayed_ghost_minutes),
            "balanceable_ghost_minutes": int(self.view.balanceable_ghost_minutes),
            "balance_target_downtime_total_minutes": int(self.view.balance_target_downtime_total_minutes),
            "action_mode": self.view.balance_action_mode,
            "reference_minutes": self.collect_balance_reference_minutes(),
        }

    def apply_balance_state(self, balance_state=None):
        state = self.model.normalize_balance_state(balance_state)
        self.view.displayed_ghost_minutes = state["displayed_ghost_minutes"]
        self.view.balanceable_ghost_minutes = state["balanceable_ghost_minutes"]
        self.view.balance_target_downtime_total_minutes = state["balance_target_downtime_total_minutes"]
        self.view.balance_action_mode = state["action_mode"]
        self.apply_balance_reference_minutes(state["reference_minutes"])
        self.update_balance_downtime_button()

    def reset_balance_state(self):
        self.view.balanceable_ghost_minutes = 0
        self.view.balance_target_downtime_total_minutes = 0
        self.view.balance_action_mode = "balance"
        self.update_balance_downtime_button()

    def invalidate_balance_reference(self, reset_mode=True):
        for row in self.view.downtime_rows:
            row.pop("balance_source_minutes", None)
        if reset_mode:
            self.reset_balance_state()

    def capture_balance_reference(self, weighted_rows):
        if any("balance_source_minutes" in row for row, _duration in weighted_rows):
            return
        for row, duration in weighted_rows:
            row["balance_source_minutes"] = max(0, int(duration))

    def remember_balance_state(self, balanced_ghost_minutes, target_downtime_total):
        carry_forward = self.view.balanceable_ghost_minutes if self.view.balance_action_mode == "rebalance" else 0
        self.view.balanceable_ghost_minutes = max(
            self.model.coerce_minutes_value(balanced_ghost_minutes, 0),
            carry_forward,
        )
        self.view.balance_target_downtime_total_minutes = max(0, self.model.coerce_minutes_value(target_downtime_total, 0))
        self.view.balance_action_mode = "rebalance" if self.view.balance_target_downtime_total_minutes > 0 else "balance"
        self.update_balance_downtime_button()

    def update_balance_downtime_button(self):
        if self.view.balance_downtime_btn is None:
            return
        button_label = "Rebalance Downtime" if self.view.balance_action_mode == "rebalance" else "Balance Downtime"
        self.view.balance_downtime_btn.config(text=button_label)

    def on_balance_mix_changed(self, _value=None):
        self.view.update_balance_mix_display()

    def on_downtime_row_value_changed(self, _event=None):
        self.invalidate_balance_reference(reset_mode=True)

    def get_weighted_downtime_rows(self):
        weighted_rows = []
        for row in self.view.downtime_rows:
            if self.is_balance_downtime_row(row):
                continue
            duration = row.get("balance_source_minutes")
            if duration is None:
                duration = self.get_row_duration_minutes(row)
            duration = max(0, self.model.coerce_minutes_value(duration, 0))
            if duration > 0:
                weighted_rows.append((row, duration))
        return weighted_rows

    def apply_weighted_downtime_balance(self, target_total_minutes):
        weighted_rows = self.get_weighted_downtime_rows()
        if not weighted_rows:
            return False

        self.capture_balance_reference(weighted_rows)
        balance_row = self.find_balance_downtime_row()
        if balance_row is not None:
            balance_row["start"].master.destroy()
            if balance_row in self.view.downtime_rows:
                self.view.downtime_rows.remove(balance_row)

        applied_minutes = self.model.calculate_spillover_allocations(
            [row["start"].get() for row, _duration in weighted_rows],
            [duration for _row, duration in weighted_rows],
            target_total_minutes,
            self.view.get_balance_mix_ratio(),
        )
        if len(applied_minutes) != len(weighted_rows):
            return False

        for (row, _duration), actual_minutes in zip(weighted_rows, applied_minutes):
            self.view.set_downtime_row_duration(row, actual_minutes, set_balance_metadata=False)
        return True

    def on_rate_override_toggled(self, row):
        override_enabled = bool(row["rate_override_enabled_var"].get())
        if override_enabled:
            lookup_rate = self.view.resolve_lookup_rate(
                row["part_number"].get(),
                self.view.load_rates_data(),
                self.get_global_goal_rate(),
            )
            current_value = row["rate_lookup"].get().strip() or self.view.format_rate_value(lookup_rate)
            self.view.set_rate_lookup_value(row, current_value, editable=True)
            row["rate_lookup"].focus_set()
            row["rate_lookup"].selection_range(0, "end")
        else:
            self.view.set_rate_lookup_value(
                row,
                self.view.format_rate_value(
                    self.view.resolve_lookup_rate(
                        row["part_number"].get(),
                        self.view.load_rates_data(),
                        self.get_global_goal_rate(),
                    )
                ),
                editable=False,
            )
        self.view.mark_dirty()
        self.update_row_math()

    def remove_production_row(self, row):
        row["shop_order"].master.destroy()
        if row in self.view.production_rows:
            self.view.production_rows.remove(row)
        self.view.mark_dirty()
        self.update_row_math()

    def remove_downtime_row(self, row):
        row["start"].master.destroy()
        if row in self.view.downtime_rows:
            self.view.downtime_rows.remove(row)
        self.invalidate_balance_reference(reset_mode=True)
        self.view.mark_dirty()
        self.update_row_math()

    def delete_production_row_with_save_reload(self, row):
        self.save_draft(suppress_toast=True)
        if self.view.current_draft_path and os.path.exists(self.view.current_draft_path):
            try:
                self.model.delete_matching_draft_row(
                    self.view.current_draft_path,
                    "production",
                    {
                        "shop_order": self.view.get_widget_value(row["shop_order"]),
                        "part_number": self.view.get_widget_value(row["part_number"]),
                        "rate_lookup": self.view.get_widget_value(row["rate_lookup"]),
                        "molds": self.view.get_widget_value(row["molds"]),
                        "time_calc": self.view.get_widget_value(row["time_calc"]),
                    },
                )
            except Exception as exc:
                self.view.show_error("Draft Update Error", f"Could not update draft after row delete: {exc}")
            self.load_draft_path(self.view.current_draft_path)

    def delete_downtime_row_with_save_reload(self, row):
        self.save_draft(suppress_toast=True)
        if self.view.current_draft_path and os.path.exists(self.view.current_draft_path):
            try:
                self.model.delete_matching_draft_row(
                    self.view.current_draft_path,
                    "downtime",
                    {
                        "start": self.view.get_widget_value(row["start"]),
                        "stop": self.view.get_widget_value(row["stop"]),
                        "code": self.view.get_widget_value(row["code"]),
                        "cause": self.view.get_widget_value(row["cause"]),
                        "time_calc": self.view.get_widget_value(row["time_calc"]),
                    },
                )
            except Exception as exc:
                self.view.show_error("Draft Update Error", f"Could not update draft after row delete: {exc}")
            self.load_draft_path(self.view.current_draft_path)

    def update_row_math(self):
        rates_data = self.view.load_rates_data()
        global_goal = self.get_global_goal_rate()
        total_molds = 0
        for row in self.view.production_rows:
            if not bool(row["rate_override_enabled_var"].get()):
                lookup_rate = self.view.resolve_lookup_rate(row["part_number"].get(), rates_data, global_goal)
                self.view.set_rate_lookup_value(row, self.view.format_rate_value(lookup_rate), editable=False)
            row_molds = self.model.calculate_total_molds([row["molds"].get()])
            total_molds += row_molds
            rate = self.get_row_rate(row, rates_data, global_goal)
            minutes = self.model.calculate_production_minutes(row["molds"].get(), rate)
            row["time_calc"].config(text=f"{minutes} min")

        if "total_molds" in self.view.entries:
            self.view.set_entry_value("total_molds", str(total_molds))

        for row in self.view.downtime_rows:
            difference = self.model.calculate_clock_duration_minutes(row["start"].get(), row["stop"].get())
            if difference is None:
                row["time_calc"].config(text="--")
            else:
                row["time_calc"].config(text=f"{difference} min")

        self.view.ensure_open_production_row()
        self.view.ensure_open_downtime_row()
        self.view.update_target_time_display()
        self.view.update_ghost_total_display()
        self.view.schedule_summary_refresh()

    def calculate_metrics(self):
        total_molds = self.calculate_total_molds()
        hours_entry = self.view.entries.get("hours")
        goal_entry = self.view.entries.get("goal_mph")
        efficiency = self.model.calculate_efficiency(
            total_molds,
            hours_entry.get() if hours_entry is not None else 8.0,
            goal_entry.get() if goal_entry is not None else 240.0,
        )
        self.view.eff_display_lbl.config(text=f"EFF%: {efficiency:.2f}")
        self.view.update_target_time_display()
        self.view.update_ghost_total_display()
        self.view.schedule_summary_refresh()

    def balance_downtime_to_shift(self):
        self.update_row_math()
        displayed_ghost_minutes = abs(self.view.displayed_ghost_minutes)
        shift_total = self.get_shift_total_minutes()
        production_total = self.get_production_total_minutes()
        current_downtime_total = self.get_total_downtime_minutes()
        target_downtime_total = shift_total - production_total
        delta_minutes = target_downtime_total - current_downtime_total
        balance_row = self.find_balance_downtime_row()

        if shift_total <= 0:
            self.view.show_toast("Balance Downtime", "Enter a valid shift hour value before balancing.", WARNING)
            return
        if target_downtime_total < 0:
            self.view.show_toast(
                "Balance Downtime",
                f"Production time alone exceeds the shift total by {abs(target_downtime_total)} minutes. Downtime balancing cannot correct that overrun.",
                WARNING,
            )
            return
        if self.apply_weighted_downtime_balance(target_downtime_total):
            self.remember_balance_state(displayed_ghost_minutes, target_downtime_total)
            self.update_row_math()
            self.view.mark_dirty()
            if delta_minutes > 0:
                message = f"Added {delta_minutes} downtime minutes across the existing downtime rows using the selected balance mix."
            elif delta_minutes < 0:
                message = f"Removed {abs(delta_minutes)} downtime minutes across the existing downtime rows using the selected balance mix."
            else:
                message = "Redistributed downtime across the existing rows using the selected balance mix."
            self.view.show_toast("Balance Downtime", message, SUCCESS)
            return

        if target_downtime_total <= 0:
            if balance_row is not None:
                self.remove_downtime_row(balance_row)
                self.reset_balance_state()
                self.update_row_math()
                self.view.mark_dirty()
                self.view.show_toast(
                    "Balance Downtime",
                    "Removed the balance downtime row because production now fully accounts for the shift.",
                    SUCCESS,
                )
            else:
                self.reset_balance_state()
                self.view.show_toast("Balance Downtime", "Accounted time already matches the shift total.", INFO)
            return

        if balance_row is None:
            balance_row = self.view.add_downtime_row()
        self.view.set_downtime_row_duration(balance_row, target_downtime_total, set_balance_metadata=True)
        self.remember_balance_state(displayed_ghost_minutes, target_downtime_total)
        self.update_row_math()
        self.view.mark_dirty()
        if delta_minutes > 0:
            message = f"Added {delta_minutes} downtime minutes to the balance row because there were no existing downtime durations to distribute."
        elif delta_minutes < 0:
            message = f"Removed {abs(delta_minutes)} downtime minutes from the balance row to match the shift total."
        else:
            message = "Updated the downtime balance row using the selected balance target."
        self.view.show_toast("Balance Downtime", message, SUCCESS)

    def get_last_export_path(self):
        if self.view.last_export_path and os.path.exists(self.view.last_export_path):
            return self.view.last_export_path
        return None

    def update_export_action_state(self):
        if self.view is None:
            return
        state = "normal" if self.get_last_export_path() else "disabled"
        if hasattr(self.view, "open_export_btn"):
            self.view.open_export_btn.config(state=state)
        if hasattr(self.view, "print_export_btn"):
            self.view.print_export_btn.config(state=state)

    def export_to_excel(self):
        ghost_minutes = self.get_ghost_time_minutes()
        if ghost_minutes != 0 and self.view.ask_yes_no(
            "Unbalanced Time",
            f"Your accounted time is off by {abs(ghost_minutes)} minutes. Do you want to Auto-Balance your downtime before exporting?",
        ):
            self.balance_downtime_to_shift()
        try:
            ui_data = self.view.collect_ui_data()
            shift = ui_data["header"].get("shift", "0")
            date = ui_data["header"].get("date", "00-00-00").replace("/", "")
            target_path = self.model.data_handler.export_to_template(ui_data, shift, date)
            self.view.last_export_path = target_path
            self.update_export_action_state()
            self.view.show_toast("Export Complete", f"Excel export completed successfully: {os.path.basename(target_path)}", SUCCESS)
            if self.view.ask_yes_no(
                "Export Complete",
                f"Workbook created successfully.\n\n{target_path}\n\nOpen it in the default application now so you can review it before printing?",
            ):
                self.open_last_exported_file(show_prompt=False)
        except Exception as exc:
            self.view.show_error("Error", f"Export failed: {exc}")

    def open_last_exported_file(self, show_prompt=True):
        export_path = self.get_last_export_path()
        if not export_path:
            if show_prompt:
                self.view.show_error("Open Export", "No exported workbook is available yet.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(export_path)
            else:
                webbrowser.open(export_path)
        except Exception as exc:
            self.view.show_error("Open Export", f"Could not open exported workbook: {exc}")

    def print_last_exported_file(self):
        export_path = self.get_last_export_path()
        if not export_path:
            self.view.show_error("Print Export", "Export a workbook first so there is something to print.")
            return
        if not self.view.ask_yes_no(
            "Print Export",
            f"Print this workbook using the default application print action?\n\n{export_path}\n\nReview it first with 'Open Last Export' if needed.",
        ):
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(export_path, "print")
                self.view.show_toast("Printing", "Sent Excel file to the default printer.", INFO)
            else:
                self.open_last_exported_file(show_prompt=False)
                self.view.show_toast(
                    "Print Review",
                    "Opened the exported workbook for manual printing in the default application.",
                    INFO,
                )
        except Exception as exc:
            self.view.show_error("Print Export", f"Could not print exported workbook: {exc}")

    def resume_latest_draft(self):
        latest = self.get_latest_pending_draft()
        if not latest:
            self.view.show_toast("Resume Latest", "No pending drafts are available.", INFO)
            return
        self.load_draft_path(latest["path"])

    def open_recovery_viewer(self):
        top = tb.Toplevel(title="Backup / Recovery")
        top.geometry("980x620")
        top.minsize(820, 520)
        recovery_viewer.get_ui(top, self.dispatcher)

    def delete_current_draft(self):
        if not self.view.current_draft_path or not os.path.exists(self.view.current_draft_path):
            self.view.show_toast("Delete Draft", "There is no saved draft attached to the current session.", INFO)
            return
        if not self.view.ask_yes_no("Delete Current Draft", f"Delete {os.path.basename(self.view.current_draft_path)}?"):
            return
        self.delete_draft_file(self.view.current_draft_path)
        self.view.current_draft_path = None
        self.view.mark_dirty()

    def delete_draft_file(self, draft_path):
        self.model.delete_file(draft_path)
        if self.view.current_draft_path == draft_path:
            self.view.current_draft_path = None
        self.view.update_recovery_ui()

    def load_draft_path(self, draft_path, window=None):
        if not self.view.confirm_discard_unsaved_changes():
            return
        try:
            data = self.model.load_json(draft_path)
            self.view.populate_from_data(data, source_path=draft_path, mark_dirty_after_load=False)
        except Exception as exc:
            self.view.show_error("Draft Load Error", f"Error loading draft: {exc}")
        if window is not None:
            window.destroy()

    def show_pending(self):
        return self.view.show_pending()

    def import_from_excel_ui(self):
        file_path = self.view.ask_import_file_path()
        if not file_path:
            return
        if not self.view.confirm_discard_unsaved_changes():
            return
        try:
            data = self.model.data_handler.import_from_excel(file_path)
            self.view.populate_from_data(data, source_path=None, mark_dirty_after_load=True)
            self.view.show_toast("Import Complete", "Excel import completed successfully.", SUCCESS)
        except Exception as exc:
            self.view.show_error("Import Error", f"Failed to import Excel: {exc}")
