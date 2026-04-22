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

__module_name__ = "Update Manager"
__version__ = "2.4.0"


class UpdateManagerController:
    def __init__(self, parent, dispatcher):
        _ = parent
        _ = dispatcher
        raise_tk_runtime_removed("app/controllers/update_manager_controller.py")


def get_ui(parent, dispatcher):
    return UpdateManagerController(parent, dispatcher)