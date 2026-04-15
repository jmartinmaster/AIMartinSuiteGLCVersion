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
from app.views.about_qt_view import is_about_qt_runtime_available
from app.views.about_view import AboutView
from app.views.qt_module_bridge_view import QtModuleBridgeView

__module_name__ = "About View Factory"
__version__ = "1.0.0"


def get_requested_about_ui_backend(dispatcher):
    if dispatcher is None:
        return "tk"
    if bool(getattr(dispatcher, "is_pyqt6_shell_requested", lambda: False)()):
        return "qt"
    return "tk"


def create_about_view(parent, dispatcher, controller):
    controller.requested_view_backend = get_requested_about_ui_backend(dispatcher)
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = None

    if controller.requested_view_backend == "qt" and is_about_qt_runtime_available():
        controller.resolved_view_backend = "qt"
        return QtModuleBridgeView(
            parent,
            dispatcher,
            controller,
            {
                "title": "About Qt Runtime",
                "subtitle": (
                    "The About module is running in a dedicated PyQt6 window while the main shell remains on Tk. "
                    "Use the controls below to raise or restart the sidecar window."
                ),
                "initial_status": "Launching About Qt window...",
            },
        )
    if controller.requested_view_backend == "qt":
        controller.view_backend_fallback_reason = "PyQt6 is not installed; using the Tk About view."

    return AboutView(parent, dispatcher, controller)