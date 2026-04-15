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
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from app.app_logging import log_exception

__module_name__ = "Qt Module Runtime"
__version__ = "1.0.0"

QT_MODULE_SESSION_ENV = "AIMARTIN_QT_MODULE_SESSION"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _to_json_compatible(value):
    if isinstance(value, dict):
        return {str(key): _to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, set):
        return [_to_json_compatible(item) for item in sorted(value, key=lambda item: repr(item))]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class QtModuleRuntimeManager:
    def __init__(self, module_name, payload_builder):
        self.module_name = str(module_name)
        self.payload_builder = payload_builder
        self.process = None
        self.launch_thread = None
        self.process_lock = threading.Lock()
        self.session_dir = None
        self.session_path = None
        self.state_path = None
        self.command_path = None

    def is_running(self):
        with self.process_lock:
            return self.process is not None and self.process.poll() is None

    def ensure_running(self, force_restart=False):
        if force_restart:
            self.stop_runtime(force=True)
        if self.is_running():
            self.send_command("raise_window")
            return
        if self.launch_thread is not None and self.launch_thread.is_alive():
            return
        self.launch_thread = threading.Thread(
            target=self._launch_runtime,
            name=f"{self.module_name.title()}QtRuntime",
            daemon=True,
        )
        self.launch_thread.start()

    def _launch_runtime(self):
        payload = self.payload_builder() or {}
        self._prepare_session(payload)
        env = os.environ.copy()
        env[QT_MODULE_SESSION_ENV] = str(self.session_path)
        process = subprocess.Popen(self._build_command(), cwd=str(REPO_ROOT), env=env, close_fds=True)
        with self.process_lock:
            self.process = process

    def _prepare_session(self, payload):
        self._cleanup_session_dir()
        session_dir = Path(tempfile.mkdtemp(prefix=f"aimartin_{self.module_name}_qt_"))
        session_path = session_dir / "session.json"
        state_path = session_dir / "state.json"
        command_path = session_dir / "command.json"
        state_path.write_text(
            json.dumps(
                {
                    "status": "launching",
                    "dirty": False,
                    "message": f"Launching {self.module_name.replace('_', ' ').title()} Qt window.",
                    "updated_at": time.time(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        session_payload = _to_json_compatible(dict(payload or {}))
        session_payload["module"] = self.module_name
        session_payload["state_path"] = str(state_path)
        session_payload["command_path"] = str(command_path)
        session_path.write_text(json.dumps(session_payload, indent=2), encoding="utf-8")
        self.session_dir = session_dir
        self.session_path = session_path
        self.state_path = state_path
        self.command_path = command_path

    def _build_command(self):
        if getattr(sys, "frozen", False):
            return [sys.executable]
        return [sys.executable, str(REPO_ROOT / "main.py")]

    def read_state(self):
        state_path = self.state_path
        if state_path is None or not state_path.exists():
            return {}
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log_exception(f"qt_module_runtime.read_state.{self.module_name}", exc)
            return {}

    def send_command(self, action):
        command_path = self.command_path
        if command_path is None:
            return
        try:
            command_path.write_text(
                json.dumps({"action": action, "requested_at": time.time()}, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            log_exception(f"qt_module_runtime.send_command.{self.module_name}", exc)

    def stop_runtime(self, force=False):
        process = self.process
        if process is None:
            self._cleanup_session_dir()
            return
        if process.poll() is not None:
            with self.process_lock:
                self.process = None
            self._cleanup_session_dir()
            return
        if not force:
            self.send_command("close_window")
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
        with self.process_lock:
            self.process = None
        self._cleanup_session_dir()

    def _cleanup_session_dir(self):
        session_dir = self.session_dir
        self.session_dir = None
        self.session_path = None
        self.state_path = None
        self.command_path = None
        if session_dir is None:
            return
        try:
            shutil.rmtree(session_dir, ignore_errors=True)
        except Exception as exc:
            log_exception(f"qt_module_runtime.cleanup.{self.module_name}", exc)