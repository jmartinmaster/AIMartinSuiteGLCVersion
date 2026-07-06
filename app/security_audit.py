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
import json
import hashlib
from datetime import datetime
from app.app_logging import log_error
from app.utils import external_path

AUDIT_LOG_PATH = external_path("data/security_audit.log")


def _now_utc_iso():
    try:
        from datetime import timezone
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except Exception:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _entry_hash(entry):
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _read_last_entry_hash():
    if not os.path.exists(AUDIT_LOG_PATH):
        return ""
    try:
        with open(AUDIT_LOG_PATH, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            file_size = handle.tell()
            if file_size <= 0:
                return ""
            cursor = file_size - 1
            line_bytes = b""
            while cursor >= 0:
                handle.seek(cursor)
                byte = handle.read(1)
                if byte == b"\n" and line_bytes:
                    break
                if byte != b"\n":
                    line_bytes = byte + line_bytes
                cursor -= 1
            if not line_bytes:
                return ""
            payload = json.loads(line_bytes.decode("utf-8", errors="replace"))
            return str(payload.get("entry_hash") or "").strip()
    except Exception as exc:
        log_error("security_audit.read_last_entry_hash", f"{exc}")
        return ""

def log_security_event(event_type: str, description: str, status: str = "success", metadata: dict = None):
    """
    Appends a structured security event entry to the audit log file.
    """
    entry = {
        "timestamp": _now_utc_iso(),
        "event_type": str(event_type).strip(),
        "description": str(description).strip(),
        "status": str(status).strip().lower(),
        "metadata": dict(metadata or {}),
        "prev_hash": _read_last_entry_hash(),
    }
    entry["entry_hash"] = _entry_hash(entry)

    log_dir = os.path.dirname(AUDIT_LOG_PATH)
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as exc:
            log_error("security_audit.makedirs", f"{exc}")
            return None

    try:
        line = (json.dumps(entry, sort_keys=True) + "\n").encode("utf-8")
        handle = os.open(AUDIT_LOG_PATH, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            os.write(handle, line)
        finally:
            os.close(handle)
    except OSError as exc:
        log_error("security_audit.append", f"{exc}")
        return None
    return dict(entry)

def get_recent_security_events(limit: int = 150) -> list:
    """
    Reads the append-only JSONL log file and returns the most recent entries up to the limit.
    """
    if not os.path.exists(AUDIT_LOG_PATH):
        return []
        
    entries = []
    malformed_count = 0
    try:
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as handle:
            for line in handle:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    entries.append(json.loads(line_str))
                except Exception:
                    malformed_count += 1
    except OSError as exc:
        log_error("security_audit.read", f"{exc}")
        return []

    if malformed_count:
        log_error("security_audit.read", f"Skipped {malformed_count} malformed log entr{('y' if malformed_count == 1 else 'ies')}.")

    # Return newest entries first
    return list(reversed(entries))[:limit]
