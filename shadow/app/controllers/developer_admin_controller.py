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
from app.controllers.settings_manager_controller import SettingsManagerController
from app.views.developer_admin_view_factory import create_developer_admin_view

__module_name__ = "Developer Admin"
__version__ = "1.0.0"


class DeveloperAdminController(SettingsManagerController):
    def __init__(self, parent, dispatcher):
        super().__init__(
            parent,
            dispatcher,
            section_mode="developer_admin",
            module_name="developer_admin",
            module_title="Developer Tools",
            view_factory=create_developer_admin_view,
        )
