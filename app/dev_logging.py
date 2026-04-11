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
import threading
from datetime import datetime

from app.utils import ensure_external_directory

__module_name__ = "Developer Debug Logging"
__version__ = "1.0.0"

LOG_DIRECTORY = ensure_external_directory("logs")
LOG_FILE = os.path.join(LOG_DIRECTORY, "martin_debug.log")
LOG_LOCK = threading.Lock()
LOG_ENABLED = True


def set_logging_enabled(enabled: bool):
    global LOG_ENABLED
    LOG_ENABLED = bool(enabled)
    status_message = "Logging enabled" if LOG_ENABLED else "Logging disabled"
    _write_log_line(status_message)


def log_event(event, details=None):
    if not LOG_ENABLED:
        return

    message = str(event or "Event")
    if details:
        message = f"{message} | {details}"
    _write_log_line(message)


def get_log_file_path():
    return os.path.abspath(LOG_FILE)


def _write_log_line(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    with LOG_LOCK:
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")