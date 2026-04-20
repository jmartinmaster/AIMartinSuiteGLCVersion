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
from app.views.settings_manager_view_factory import create_settings_manager_view

__module_name__ = "Security Admin View Factory"
__version__ = "1.0.0"


def create_security_admin_view(parent, dispatcher, controller, section_mode="security_admin"):
    return create_settings_manager_view(parent, dispatcher, controller, section_mode=section_mode)
