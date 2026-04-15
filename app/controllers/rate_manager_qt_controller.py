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

from app.models.rate_manager_model import RateManagerModel
from app.views.rate_manager_qt_view import RateManagerQtView

__module_name__ = "Rate Manager Qt Controller"
__version__ = "1.0.0"


class RateManagerQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.model = RateManagerModel()
        self.view = RateManagerQtView(self, self.payload)
        self.refresh_table(initial=True)

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
            "module": "rate_manager",
            "rate_count": len(self.model.rates),
            "updated_at": time.time(),
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def refresh_table(self, initial=False):
        rows = self.model.get_filtered_rates(self.view.get_search_text())
        self.view.refresh_table(rows)
        self.write_state(status="ready", message="Rate Manager Qt window ready." if initial else "Rate table refreshed.")

    def on_search_changed(self):
        self.refresh_table()

    def enter_edit_mode(self):
        try:
            part_key = self.view.get_selected_part()
            if not part_key:
                raise ValueError("Select a rate row before editing.")
            edit_part, edit_rate = self.model.begin_edit(part_key)
            self.view.populate_edit_form(edit_part, edit_rate)
        except Exception as exc:
            self.view.show_error("Rate Manager", str(exc))

    def save_edit(self):
        try:
            _part, new_rate = self.view.get_form_values()
            self.model.save_edit(new_rate)
            self.view.reset_form()
            self.refresh_table()
            self.view.show_info("Rate Saved", "Updated target rate.")
        except Exception as exc:
            self.view.show_error("Rate Manager", str(exc))

    def cancel_edit(self):
        self.model.cancel_edit()
        self.view.reset_form()

    def add_rate(self):
        try:
            part, rate = self.view.get_form_values()
            self.model.add_rate(part, rate)
            self.view.reset_form()
            self.refresh_table()
            self.view.show_info("Rate Added", "Added target rate entry.")
        except Exception as exc:
            self.view.show_error("Rate Manager", str(exc))

    def delete_rate(self):
        try:
            part_key = self.view.get_selected_part()
            if not part_key:
                raise ValueError("Select a rate row before deleting.")
            self.model.delete_rate(part_key)
            self.view.reset_form()
            self.refresh_table()
            self.view.show_info("Rate Deleted", "Removed target rate entry.")
        except Exception as exc:
            self.view.show_error("Rate Manager", str(exc))

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
            self.write_state(status="ready", message="Raised Rate Manager Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="Rate Manager Qt window closed.")
