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

__module_name__ = "Path Helpers"
__version__ = "1.1.5"


def bundled_base_path():
    try:
        return sys._MEIPASS
    except Exception:
        return os.path.abspath(".")


def external_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def resource_path(relative_path):
    return os.path.join(bundled_base_path(), relative_path)


def external_path(relative_path):
    return os.path.join(external_base_path(), relative_path)


def local_or_resource_path(relative_path):
    local_path = external_path(relative_path)
    if os.path.exists(local_path):
        return local_path
    return resource_path(relative_path)


def ensure_external_directory(relative_path):
    directory_path = external_path(relative_path)
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def resolve_local_venv_python(base_path=None):
    root_path = os.path.abspath(base_path or external_base_path())
    candidate = os.path.join(root_path, ".venv", "Scripts", "python.exe")
    return candidate if os.path.exists(candidate) else None