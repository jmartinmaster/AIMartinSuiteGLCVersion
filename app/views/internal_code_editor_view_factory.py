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
from app.views.internal_code_editor_qt_view import is_internal_code_editor_qt_runtime_available
from app.views.internal_code_editor_view import InternalCodeEditorView
from app.views.qt_module_bridge_view import QtModuleBridgeView

__module_name__ = "Internal Code Editor View Factory"
__version__ = "1.0.0"


def create_internal_code_editor_view(parent, dispatcher, controller):
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = None
    if is_internal_code_editor_qt_runtime_available():
        controller.resolved_view_backend = "qt"
        return QtModuleBridgeView(
            parent,
            dispatcher,
            controller,
            {
                "title": "Internal Code Editor Qt Runtime",
                "subtitle": (
                    "The Internal Code Editor now runs in a dedicated PyQt6 window while the host shell remains on Tk. "
                    "Use the controls below to raise or restart the sidecar window."
                ),
                "initial_status": "Launching Internal Code Editor Qt window...",
            },
        )

    controller.view_backend_fallback_reason = "PyQt6 is not installed; using the Tk Internal Code Editor."
    return InternalCodeEditorView(parent, dispatcher, controller)
