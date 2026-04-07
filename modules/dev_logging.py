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

__module_name__ = "Developer Debug Logging"
__version__ = "1.0.0"

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'martin_debug.log')
LOG_LOCK = threading.Lock()
LOG_ENABLED = True  # Enabled by default for test session

def set_logging_enabled(enabled: bool):
    global LOG_ENABLED
    LOG_ENABLED = enabled
    if enabled:
        log_event('Logging enabled')
    else:
        log_event('Logging disabled')

def log_event(event, details=None):
    if not LOG_ENABLED:
        return
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg = f"[{timestamp}] {event}"
    if details:
        msg += f" | {details}"
    with LOG_LOCK:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(msg + '\n')

def get_log_file_path():
    return os.path.abspath(LOG_FILE)
