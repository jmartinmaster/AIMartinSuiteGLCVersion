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
from app.views.rate_manager_view import RateManagerView


class RateManagerController:
    def __init__(self, parent, dispatcher):
        self.dispatcher = dispatcher
        self.model = RateManagerModel()
        self.view = None
        self.view = RateManagerView(parent, dispatcher, self, self.model)
        self.refresh_table()
        self._sync_shared_data()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

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
