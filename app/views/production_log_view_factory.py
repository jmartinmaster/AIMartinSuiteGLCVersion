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

from app.views.production_log_qt_view import is_production_log_qt_runtime_available
from app.views.production_log_view import ProductionLogView
from app.views.qt_module_bridge_view import QtModuleBridgeView

__module_name__ = "Production Log View Factory"
__version__ = "1.1.0"

EMERGENCY_TK_FALLBACK_ENV = "AIMARTIN_PRODUCTION_LOG_EMERGENCY_TK_FALLBACK"


def _is_truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def is_emergency_tk_fallback_enabled(dispatcher):
    runtime_settings = getattr(dispatcher, "runtime_settings", {}) or {}
    runtime_flag = runtime_settings.get("production_log_emergency_tk_fallback", False)
    return bool(runtime_flag) or _is_truthy(os.environ.get(EMERGENCY_TK_FALLBACK_ENV, ""))


def get_requested_production_log_ui_backend(dispatcher):
    runtime_settings = getattr(dispatcher, "runtime_settings", {}) or {}
    default_backend = "qt"
    requested_backend = runtime_settings.get(
        "production_log_ui_backend",
        os.environ.get("AIMARTIN_PRODUCTION_LOG_UI_BACKEND", default_backend),
    )
    requested_backend = str(requested_backend).strip().lower()
    if requested_backend not in {"tk", "qt"}:
        return "qt"
    if requested_backend == "tk" and not is_emergency_tk_fallback_enabled(dispatcher):
        return "qt"
    return requested_backend


def create_production_log_view(parent, dispatcher, controller, model):
    requested_backend = get_requested_production_log_ui_backend(dispatcher)
    controller.requested_view_backend = requested_backend
    controller.resolved_view_backend = "tk"
    controller.view_backend_fallback_reason = None
    controller.view_backend_fallback_code = None

    emergency_tk_fallback_enabled = is_emergency_tk_fallback_enabled(dispatcher)

    if requested_backend == "tk" and emergency_tk_fallback_enabled:
        controller.view_backend_fallback_code = "emergency_tk_fallback_enabled"
        controller.view_backend_fallback_reason = (
            "Production Log emergency Tk fallback is enabled by runtime setting or environment override."
        )
        return ProductionLogView(parent, dispatcher, controller, model)

    if not is_production_log_qt_runtime_available():
        controller.view_backend_fallback_code = "pyqt6_runtime_unavailable"
        controller.view_backend_fallback_reason = "PyQt6 is not installed; using the Tk Production Log view."
        return ProductionLogView(parent, dispatcher, controller, model)

    controller.resolved_view_backend = "qt"
    return QtModuleBridgeView(
        parent,
        dispatcher,
        controller,
        {
            "title": "Production Log (PyQt6)",
            "subtitle": (
                "Production Log is running in the dedicated PyQt6 runtime window. "
                "Use the controls below to raise or restart the window if needed."
            ),
            "initial_status": "Launching Production Log PyQt6 window...",
        },
    )
