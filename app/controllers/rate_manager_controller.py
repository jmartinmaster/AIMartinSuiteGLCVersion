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
from ttkbootstrap.constants import INFO, SUCCESS

from app.models.rate_manager_model import RateManagerModel
from app.qt_module_runtime import QtModuleRuntimeManager
from app.views.rate_manager_view_factory import create_rate_manager_view

__module_name__ = "Rate Manager"
__version__ = "1.1.0"


class RateManagerController:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.requested_view_backend = "qt"
        self.resolved_view_backend = "tk"
        self.view_backend_fallback_reason = None
        self.model = RateManagerModel()
        self.view = None
        self.runtime_manager = QtModuleRuntimeManager("rate_manager", self.build_qt_session_payload)
        self.view = create_rate_manager_view(parent, dispatcher, self, self.model)
        if self.resolved_view_backend == "tk":
            self.refresh_table()
        self._sync_shared_data()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def build_qt_session_payload(self):
        root = self.parent.winfo_toplevel()
        return {
            "window_title": "Rate Manager - Production Logging Center",
            "title": "Rate Manager",
            "subtitle": "Manage per-part target rate entries in a dedicated PyQt6 sidecar.",
            "theme_tokens": dict(getattr(root, "_martin_theme_tokens", {}) or {}),
        }

    def open_or_raise_qt_window(self):
        self.runtime_manager.ensure_running(force_restart=False)

    def restart_qt_window(self):
        self.runtime_manager.ensure_running(force_restart=True)

    def stop_qt_window(self):
        self.runtime_manager.stop_runtime(force=False)

    def read_runtime_state(self):
        return self.runtime_manager.read_state()

    def _sync_shared_data(self):
        if hasattr(self.dispatcher, "shared_data"):
            self.dispatcher.shared_data["rates_count"] = len(self.model.rates)

    def refresh_table(self):
        self.view.refresh_table(self.model.get_filtered_rates(self.view.get_search_text()))

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
            self._sync_shared_data()
            self.view.show_toast("Rate Saved", "Updated target rate.", INFO)
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
            self._sync_shared_data()
            self.view.show_toast("Rate Added", "Added target rate entry.", SUCCESS)
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
            self._sync_shared_data()
            self.view.show_toast("Rate Deleted", "Removed target rate entry.", SUCCESS)
        except Exception as exc:
            self.view.show_error("Rate Manager", str(exc))

    def on_hide(self):
        return None

    def on_unload(self):
        if self.resolved_view_backend == "qt":
            self.stop_qt_window()
