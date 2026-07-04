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
from app.views.layout_manager_qt_view import is_layout_manager_qt_runtime_available
from app.views.layout_manager_view_contract import LayoutManagerViewContract

__module_name__ = "Layout Manager View Factory"
__version__ = "1.0.2"


def get_requested_layout_manager_ui_backend(dispatcher):
    runtime_settings = getattr(dispatcher, "runtime_settings", {}) or {}
    requested_backend = str(runtime_settings.get("layout_manager_ui_backend", "qt")).strip().lower()
    return requested_backend or "qt"


def create_layout_manager_view(parent, dispatcher, controller):
    requested_backend = get_requested_layout_manager_ui_backend(dispatcher)
    controller.requested_view_backend = requested_backend
    controller.resolved_view_backend = "qt"
    controller.view_backend_fallback_reason = None

    if requested_backend != "qt":
        controller.view_backend_fallback_reason = (
            f"Ignoring unsupported Layout Manager backend '{requested_backend}'. "
            "The live runtime uses the in-process PyQt6 host viewport."
        )

    if not is_layout_manager_qt_runtime_available():
        controller.view_backend_fallback_reason = "PyQt6 is not installed; the Layout Manager viewport cannot be loaded."
        raise RuntimeError(controller.view_backend_fallback_reason)

    layout_manager_dispatcher = getattr(dispatcher, "layout_manager_dispatcher", None)
    if layout_manager_dispatcher is None:
        controller.view_backend_fallback_reason = "Layout Manager Qt runtime is unavailable in the current dispatcher."
        raise RuntimeError(controller.view_backend_fallback_reason)

    return layout_manager_dispatcher.launch(parent)
