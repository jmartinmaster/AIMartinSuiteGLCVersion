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
from app.views.rate_manager_qt_view import RateManagerQtView

__module_name__ = "Rate Manager Qt Controller"
__version__ = "1.1.0"


class RateManagerQtController:
    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = RateManagerModel()
        self.payload = self._build_view_payload()
        self.view = RateManagerQtView(self, self.payload, parent_widget=parent)
        self.refresh_table(initial=True)
        self.view.show()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "Rate Manager - Production Logging Center",
            "title": "Rate Manager",
            "subtitle": "Manage per-part target rate entries in the shared PyQt6 workspace.",
            "theme_tokens": theme_tokens,
        }

    def _sync_shared_data(self):
        if hasattr(self.dispatcher, "shared_data"):
            self.dispatcher.shared_data["rates_count"] = len(self.model.rates)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def refresh_table(self, initial=False):
        rows = self.model.get_filtered_rates(self.view.get_search_text())
        self.view.refresh_table(rows)
        self._sync_shared_data()
        if initial:
            self.view.set_status("Rate Manager ready.")

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
            self.view.show_toast("Rate Deleted", "Removed target rate entry.", SUCCESS)
        except Exception as exc:
            self.view.show_error("Rate Manager", str(exc))

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})

    def handle_close(self):
        return None

    def on_hide(self):
        return None

    def on_unload(self):
        try:
            self.view.close()
        except Exception:
            pass
