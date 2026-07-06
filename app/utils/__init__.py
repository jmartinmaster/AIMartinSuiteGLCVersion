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
import shutil
import sys

from app.app_identity import DEB_PACKAGE_NAME

__module_name__ = "Path Helpers"
__version__ = "1.1.5"

DATA_ROOT_RELATIVE_PATH = "data"
_LEGACY_EXTERNAL_ROOT_FILES = {
    "settings.json",
    "layout_config.json",
    "form_definitions.json",
    "rates.json",
    "production_log_calculations.json",
}


def source_root_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def bundled_base_path():
    try:
        return sys._MEIPASS
    except Exception:
        return source_root_path()


def app_data_home_path():
    if sys.platform.startswith("win"):
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return local_app_data
        app_data = os.environ.get("APPDATA", "").strip()
        if app_data:
            roaming_parent = os.path.dirname(app_data)
            if roaming_parent:
                return os.path.join(roaming_parent, "Local")
            return app_data
        return os.path.join(os.path.expanduser("~"), "AppData", "Local")
    if sys.platform.startswith("linux"):
        xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()
        if xdg_data_home:
            return xdg_data_home
        return os.path.join(os.path.expanduser("~"), ".local", "share")
    return source_root_path()


def external_base_path():
    return os.path.join(app_data_home_path(), DEB_PACKAGE_NAME)


def legacy_external_base_paths():
    current_base = os.path.abspath(external_base_path())
    legacy_bases = []
    for candidate in (
        source_root_path(),
        os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else None,
    ):
        if not candidate:
            continue
        normalized_candidate = os.path.abspath(candidate)
        if normalized_candidate == current_base or normalized_candidate in legacy_bases:
            continue
        legacy_bases.append(normalized_candidate)
    return legacy_bases


def legacy_external_path_candidates(relative_path):
    normalized_relative_path = str(relative_path or "").strip().replace("/", os.sep).replace("\\", os.sep)
    return [
        os.path.join(base_path, normalized_relative_path)
        for base_path in legacy_external_base_paths()
    ]


def _is_runtime_external_path(relative_path):
    normalized_relative_path = str(relative_path or "").strip().replace("\\", "/").lstrip("/")
    if not normalized_relative_path:
        return False
    return normalized_relative_path == DATA_ROOT_RELATIVE_PATH or normalized_relative_path.startswith(f"{DATA_ROOT_RELATIVE_PATH}/") or normalized_relative_path in _LEGACY_EXTERNAL_ROOT_FILES


def _migrate_legacy_external_path(relative_path):
    if not _is_runtime_external_path(relative_path):
        return

    target_path = os.path.abspath(os.path.join(external_base_path(), str(relative_path or "").strip()))
    if os.path.exists(target_path):
        return

    for legacy_path in legacy_external_path_candidates(relative_path):
        normalized_legacy_path = os.path.abspath(legacy_path)
        if normalized_legacy_path == target_path or not os.path.exists(normalized_legacy_path):
            continue
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.move(normalized_legacy_path, target_path)
            legacy_backup_path = f"{normalized_legacy_path}.bak"
            target_backup_path = f"{target_path}.bak"
            if os.path.exists(legacy_backup_path) and not os.path.exists(target_backup_path):
                shutil.move(legacy_backup_path, target_backup_path)
            return
        except OSError:
            continue


def resource_path(relative_path):
    return os.path.join(bundled_base_path(), relative_path)


def external_path(relative_path):
    _migrate_legacy_external_path(relative_path)
    return os.path.join(external_base_path(), relative_path)


def external_data_path(relative_path=""):
    normalized_relative_path = str(relative_path or "").strip().replace("\\", "/").lstrip("/")
    if not normalized_relative_path:
        return external_path(DATA_ROOT_RELATIVE_PATH)
    return external_path(os.path.join(DATA_ROOT_RELATIVE_PATH, normalized_relative_path))


def local_or_resource_path(relative_path):
    local_path = external_path(relative_path)
    if os.path.exists(local_path):
        return local_path
    return resource_path(relative_path)


def ensure_external_directory(relative_path):
    directory_path = external_path(relative_path)
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def ensure_external_data_directory(relative_path=""):
    directory_path = external_data_path(relative_path)
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def resolve_local_venv_python(base_path=None):
    root_path = os.path.abspath(base_path or source_root_path())
    candidates = [
        os.path.join(root_path, ".venv", "Scripts", "python.exe"),
        os.path.join(root_path, ".venv", "bin", "python"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None
