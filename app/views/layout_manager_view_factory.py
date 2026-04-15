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
import os
from typing import Callable

from app.views.layout_manager_qt_view import is_layout_manager_qt_runtime_available
from app.views.layout_manager_view import LayoutManagerView
from app.views.layout_manager_view_contract import LayoutManagerViewContract
from app.views.qt_module_bridge_view import QtModuleBridgeView

__module_name__ = "Layout Manager View Factory"
__version__ = "1.0.0"

LayoutManagerViewFactory = Callable[[object, object, object], LayoutManagerViewContract]


def get_requested_layout_manager_ui_backend(dispatcher):
    runtime_settings = getattr(dispatcher, "runtime_settings", {}) or {}
    default_backend = "qt" if bool(getattr(dispatcher, "is_pyqt6_shell_requested", lambda: False)()) else "tk"
    requested_backend = runtime_settings.get(
        "layout_manager_ui_backend",
        os.environ.get("AIMARTIN_LAYOUT_MANAGER_UI_BACKEND", default_backend),
    )
    requested_backend = str(requested_backend).strip().lower()
    if requested_backend not in {"tk", "qt"}:
        return "tk"
    return requested_backend


def create_layout_manager_view(parent, dispatcher, controller):
    requested_backend = get_requested_layout_manager_ui_backend(dispatcher)
    controller.requested_view_backend = requested_backend
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = None

    if requested_backend == "qt":
        if not is_layout_manager_qt_runtime_available():
            controller.view_backend_fallback_reason = "PyQt6 is not installed; using the Tk layout manager view."
        else:
            controller.resolved_view_backend = "qt"
            return QtModuleBridgeView(
                parent,
                dispatcher,
                controller,
                {
                    "title": "Layout Manager Qt Runtime",
                    "subtitle": (
                        "Layout Manager now runs in a dedicated PyQt6 window using the same session contract "
                        "as other migrated modules. Use the controls below to raise or restart the sidecar window."
                    ),
                    "initial_status": "Launching Layout Manager Qt window...",
                },
            )

    return LayoutManagerView(parent, dispatcher, controller)