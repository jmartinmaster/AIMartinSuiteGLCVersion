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
__module_name__ = "Tk Runtime Removal Guard"
__version__ = "9.0.0"


def raise_tk_runtime_removed(live_path):
    live_path = str(live_path or "app")
    shadow_path = f"shadow/{live_path}"
    raise RuntimeError(
        f"{live_path} was removed from the live Phase 9 runtime. Use the PyQt6 implementation or inspect {shadow_path}."
    )