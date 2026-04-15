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
from app.views.qt_module_bridge_view import QtModuleBridgeView
from app.views.settings_manager_qt_view import is_settings_manager_qt_runtime_available
from app.views.settings_manager_view import SettingsManagerView

__module_name__ = "Settings Manager View Factory"
__version__ = "1.0.0"


def create_settings_manager_view(parent, dispatcher, controller, section_mode="full"):
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = None
    if is_settings_manager_qt_runtime_available():
        controller.resolved_view_backend = "qt"
        return QtModuleBridgeView(
            parent,
            dispatcher,
            controller,
            {
                "title": "Settings Manager Qt Runtime",
                "subtitle": (
                    "Settings Manager is now running in a dedicated PyQt6 window using staged migration slices. "
                    "Use the controls below to raise or restart the sidecar window."
                ),
                "initial_status": "Launching Settings Manager Qt window...",
            },
        )

    controller.view_backend_fallback_reason = "PyQt6 is not installed; using the Tk Settings Manager."
    return SettingsManagerView(parent, dispatcher, controller, section_mode=section_mode)
