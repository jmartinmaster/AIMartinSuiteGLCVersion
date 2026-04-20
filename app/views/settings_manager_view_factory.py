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
from app.tk_runtime_removed import raise_tk_runtime_removed

raise_tk_runtime_removed("app/views/settings_manager_view_factory.py")

__module_name__ = "Settings Manager View Factory"
__version__ = "1.1.0"


def create_settings_manager_view(parent, dispatcher, controller, section_mode="full"):
    module_title = str(getattr(controller, "module_title", "Settings Manager") or "Settings Manager")
    controller.requested_view_backend = "qt" if bool(getattr(dispatcher, "is_pyqt6_shell_requested", lambda: False)()) else "tk"
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = (
        f"{module_title} uses the Tk fallback path because the shared PyQt6 viewport controller was not selected."
        if controller.requested_view_backend == "qt"
        else None
    )
    return SettingsManagerView(parent, dispatcher, controller, section_mode=section_mode)
