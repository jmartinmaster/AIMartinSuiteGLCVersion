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

from app.app_identity import DEB_PACKAGE_NAME

__module_name__ = "Path Helpers"
__version__ = "1.1.5"


def source_root_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def bundled_base_path():
    try:
        return sys._MEIPASS
    except Exception:
        return source_root_path()


def external_base_path():
    if getattr(sys, "frozen", False):
        if sys.platform.startswith("linux"):
            xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()
            if xdg_data_home:
                return os.path.join(xdg_data_home, DEB_PACKAGE_NAME)
            return os.path.join(os.path.expanduser("~"), ".local", "share", DEB_PACKAGE_NAME)
        return os.path.dirname(sys.executable)
    return source_root_path()


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
    candidates = [
        os.path.join(root_path, ".venv", "Scripts", "python.exe"),
        os.path.join(root_path, ".venv", "bin", "python"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None