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
__module_name__ = "Internal Code Editor"
__version__ = "0.1.0"


def get_ui(parent, dispatcher):
    if dispatcher is not None and getattr(dispatcher, "should_use_qt_in_viewport", None):
        if dispatcher.should_use_qt_in_viewport("internal_code_editor"):
            from app.controllers.internal_code_editor_qt_controller import InternalCodeEditorQtController

            return InternalCodeEditorQtController(parent=parent, dispatcher=dispatcher)
    raise RuntimeError("The Tk Internal Code Editor controller was removed from the live Phase 9 runtime. See shadow/app/controllers/internal_code_editor_controller.py.")
