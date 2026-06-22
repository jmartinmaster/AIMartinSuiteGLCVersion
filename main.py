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
import sys

from app.controllers.app_controller import Dispatcher
from launcher import __module_name__, __version__, main as launcher_main, run_application, run_special_mode_from_environment
from app.app_platform import apply_app_icon, apply_windows_app_id, apply_windows_window_icons, convert_png_to_ico, get_obsolete_local_executables, get_work_area_insets
from app.crash_handler import run_monitor_loop, install_child_crash_handler


if __name__ == "__main__":
    if os.environ.get("AIMARTIN_CHILD_PROCESS") != "1":
        run_monitor_loop()
    else:
        install_child_crash_handler()
        raise SystemExit(launcher_main())

