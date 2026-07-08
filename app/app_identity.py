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
import re

__module_name__ = "App Identity"
__version__ = "2.5.2"


APP_NAME = "Production Logging Center_GLC"
APP_MAINTAINER = "Jamie Martin"
LEGACY_EXE_NAME = f"{APP_NAME}.exe"
DEB_PACKAGE_NAME = "production-logging-center-glc"
LEGACY_DEB_NAME = f"{DEB_PACKAGE_NAME}.deb"
MAIN_FILE_NAME = "main.py"
DEFAULT_UPDATE_REPOSITORY_URL = "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion.git"
DEFAULT_STABLE_UPDATE_BRANCH = "main"
DEFAULT_DEV_UPDATE_BRANCH = "Development"
PUBLISHER_PUBLIC_KEY = "de7f5ec1c84e76a930b476df44f310c585274a17af4371a23fc9cf3ce9b618f7"
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
VERSIONED_EXE_PATTERN = re.compile(
    rf"^{re.escape(APP_NAME)}_v(?P<version>\d+\.\d+(?:\.\d+)?)\.exe$",
    re.IGNORECASE,
)
VERSIONED_DEB_PATTERN = re.compile(
    rf"^{re.escape(DEB_PACKAGE_NAME)}_(?P<version>\d+\.\d+(?:\.\d+)?)_(?P<architecture>[0-9A-Za-z_-]+)\.deb$",
    re.IGNORECASE,
)


def parse_version(version_text):
    if not version_text:
        return None
    parts = [part.strip() for part in str(version_text).split(".") if part.strip()]
    if len(parts) in (2, 3) and all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return None


def normalize_version(version_parts):
    if version_parts is None:
        return None
    return version_parts + (0,) * (3 - len(version_parts))


def sanitize_version_for_filename(version_text):
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "-", str(version_text).strip())
    return cleaned.strip("-._") or "0.0.0"


def format_versioned_exe_stem(version_text):
    return f"{APP_NAME}_v{sanitize_version_for_filename(version_text)}"


def format_versioned_exe_name(version_text):
    return f"{format_versioned_exe_stem(version_text)}.exe"


def format_versioned_deb_name(version_text, architecture="amd64"):
    return f"{DEB_PACKAGE_NAME}_{sanitize_version_for_filename(version_text)}_{architecture}.deb"


def parse_versioned_exe_name(file_name):
    match = VERSIONED_EXE_PATTERN.match(file_name)
    if not match:
        return None
    return match.group("version")


def parse_versioned_deb_name(file_name):
    match = VERSIONED_DEB_PATTERN.match(file_name)
    if not match:
        return None
    return match.group("version")


def load_version_from_main(main_file_path=None, default="0.0.0"):
    paths_to_try = []
    if main_file_path:
        paths_to_try.append(main_file_path)
        if main_file_path.endswith("main.py"):
            paths_to_try.append(main_file_path[:-7] + "launcher.py")
            
    app_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(app_dir)
    paths_to_try.append(os.path.join(root_dir, "launcher.py"))
    paths_to_try.append(os.path.join(root_dir, "main.py"))
    paths_to_try.append(os.path.join(app_dir, "main.py"))
    
    for path in paths_to_try:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    file_text = handle.read()
                match = VERSION_PATTERN.search(file_text)
                if match:
                    return match.group(1)
            except OSError:
                continue
    return default