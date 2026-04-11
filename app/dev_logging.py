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