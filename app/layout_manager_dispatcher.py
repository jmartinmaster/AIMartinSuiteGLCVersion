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
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.app_logging import log_exception

__module_name__ = "Layout Manager Mini Dispatcher"
__version__ = "1.1.1"
LAYOUT_MANAGER_QT_SESSION_ENV = "AIMARTIN_LAYOUT_MANAGER_QT_SESSION"

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


class LayoutManagerQtRuntimeManager:
    def __init__(self, mini_dispatcher):
        self.mini_dispatcher = mini_dispatcher
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
            name="LayoutManagerQtRuntime",
            daemon=True,
        )
        self.launch_thread.start()

    def _launch_runtime(self):
        payload = self.mini_dispatcher.consume_preload() or self.mini_dispatcher._build_preload_payload()
        self._prepare_session(payload)
        command = self._build_command()
        env = os.environ.copy()
        env[LAYOUT_MANAGER_QT_SESSION_ENV] = str(self.session_path)
        process = subprocess.Popen(command, cwd=str(REPO_ROOT), env=env, close_fds=True)
        with self.process_lock:
            self.process = process

    def _prepare_session(self, payload):
        self._cleanup_session_dir()
        session_dir = Path(tempfile.mkdtemp(prefix="aimartin_layout_manager_qt_"))
        session_path = session_dir / "session.json"
        state_path = session_dir / "state.json"
        command_path = session_dir / "command.json"
        state_path.write_text(
            json.dumps(
                {
                    "status": "launching",
                    "dirty": False,
                    "change_token": 0,
                    "message": "Launching Layout Manager Qt window.",
                    "updated_at": time.time(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        session_payload = _to_json_compatible(dict(payload or {}))
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
        except Exception:
            return {}

    def send_command(self, action, payload=None):
        command_path = self.command_path
        if command_path is None:
            return
        try:
            command_path.write_text(
                json.dumps(
                    {
                        "action": action,
                        "requested_at": time.time(),
                        "payload": _to_json_compatible(payload or {}),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            log_exception("layout_manager_qt_runtime.send_command", exc)

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
        except Exception:
            pass


class LayoutManagerQtBridge(QWidget):
    def __init__(self, parent, mini_dispatcher):
        super().__init__(parent)
        self.mini_dispatcher = mini_dispatcher
        self.runtime_manager = mini_dispatcher.runtime_manager
        self._poll_timer = QTimer(self)
        self._build_ui()
        self._poll_timer.setInterval(900)
        self._poll_timer.timeout.connect(self._poll_state)
        self._poll_timer.start()
        self._poll_state()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        header = QLabel("Layout Manager Qt Runtime", self)
        header.setObjectName("pageTitle")
        root_layout.addWidget(header)

        subtitle = QLabel(
            "Layout Manager now runs in a dedicated Qt window. Use the controls below to open, raise, or resync the dedicated runtime.",
            self,
        )
        subtitle.setObjectName("subtitleLabel")
        subtitle.setWordWrap(True)
        root_layout.addWidget(subtitle)

        controls_layout = QHBoxLayout()
        open_button = QPushButton("Open / Raise Qt Window", self)
        open_button.clicked.connect(self.open_or_raise)
        controls_layout.addWidget(open_button)

        reload_button = QPushButton("Reload From Disk", self)
        reload_button.clicked.connect(self.reload_from_disk)
        controls_layout.addWidget(reload_button)

        restart_button = QPushButton("Restart Qt Runtime", self)
        restart_button.clicked.connect(self.restart_runtime)
        controls_layout.addWidget(restart_button)
        controls_layout.addStretch(1)
        root_layout.addLayout(controls_layout)

        status_group = QGroupBox("Qt Runtime Status", self)
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("Launching Qt runtime...", status_group)
        self.form_label = QLabel("Form: --", status_group)
        self.form_label.setObjectName("mutedLabel")
        self.path_label = QLabel("Source: --", status_group)
        self.path_label.setObjectName("mutedLabel")
        self.path_label.setWordWrap(True)
        self.message_label = QLabel("Waiting for state...", status_group)
        self.message_label.setObjectName("mutedLabel")
        self.message_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.form_label)
        status_layout.addWidget(self.path_label)
        status_layout.addWidget(self.message_label)
        root_layout.addWidget(status_group)
        root_layout.addStretch(1)

    def _poll_state(self):
        state = self.runtime_manager.read_state()
        status = str(state.get("status") or "launching").title()
        dirty = bool(state.get("dirty"))
        dirty_suffix = " (Unsaved changes)" if dirty else ""
        self.status_label.setText(f"Status: {status}{dirty_suffix}")
        form_name = state.get("form_name") or state.get("form_id") or "--"
        self.form_label.setText(f"Form: {form_name}")
        self.path_label.setText(f"Source: {state.get('source_path') or '--'}")
        self.message_label.setText(str(state.get("message") or "Waiting for state..."))
        if status.lower() == "closed":
            self.mini_dispatcher.schedule_preload(force=True)

    def open_or_raise(self):
        self.mini_dispatcher.open_or_raise_window(restart=False)

    def reload_from_disk(self):
        self.mini_dispatcher.request_reload_from_disk()

    def restart_runtime(self):
        self.mini_dispatcher.open_or_raise_window(restart=True)

    def can_navigate_away(self):
        return True

    def on_hide(self):
        return None

    def on_unload(self):
        self._poll_timer.stop()
        return None

    def apply_theme(self):
        self.mini_dispatcher.apply_theme()
        return None


class LayoutManagerMiniDispatcher:
    PRELOAD_KEY = "layout_manager_preload"
    PRELOAD_PENDING_KEY = "layout_manager_preload_pending"
    MODULE_BUNDLE = (
        "app.layout_manager",
        "app.controllers.layout_manager_controller",
        "app.controllers.layout_manager_qt_controller",
        "app.models.layout_manager_model",
        "app.views.layout_manager_qt_view",
    )

    def __init__(self, host_dispatcher):
        self.host_dispatcher = host_dispatcher
        self.runtime_manager = LayoutManagerQtRuntimeManager(self)

    def is_runtime_running(self):
        return self.runtime_manager.is_running()

    def _current_theme_tokens(self):
        view = getattr(self.host_dispatcher, "view", None)
        if view is not None:
            theme_tokens = getattr(view, "theme_tokens", None)
            if isinstance(theme_tokens, dict) and theme_tokens:
                return dict(theme_tokens)
        root_tokens = getattr(self.host_dispatcher.root, "_martin_theme_tokens", None)
        if isinstance(root_tokens, dict) and root_tokens:
            return dict(root_tokens)
        return {}

    def open_or_raise_window(self, restart=False):
        self.schedule_preload(force=bool(restart))
        self.runtime_manager.ensure_running(force_restart=bool(restart))

    def request_reload_from_disk(self):
        if self.runtime_manager.is_running():
            self.runtime_manager.send_command("reload_from_disk")
            return
        self.open_or_raise_window(restart=False)

    def apply_theme(self):
        theme_tokens = self._current_theme_tokens()
        host = self.host_dispatcher
        with host.model.preload_data_lock:
            cached_payload = host.shared_data.get(self.PRELOAD_KEY)
            if isinstance(cached_payload, dict):
                cached_payload["theme_tokens"] = dict(theme_tokens)
        if self.runtime_manager.is_running():
            self.runtime_manager.send_command("apply_theme", {"theme_tokens": theme_tokens})
            return
        self.schedule_preload(force=True)

    def stop_window(self):
        self.runtime_manager.stop_runtime(force=False)

    def read_runtime_state(self):
        return dict(self.runtime_manager.read_state() or {})

    def handle_runtime_state(self, state):
        if not isinstance(state, dict):
            return
        status = str(state.get("status") or "").strip().lower()
        if status == "closed":
            self.schedule_preload(force=True)

    def build_host_runtime_state(self):
        state = self.read_runtime_state()
        self.handle_runtime_state(state)
        status = str(state.get("status") or ("running" if self.is_runtime_running() else "idle")).strip().lower() or "idle"
        message = str(state.get("message") or "").strip()
        if not message:
            if status == "running":
                message = "Layout Manager dedicated window is running."
            elif status == "launching":
                message = "Launching Layout Manager dedicated window."
            elif status == "closed":
                message = "Layout Manager dedicated window is closed."
            else:
                message = "Layout Manager dedicated window is idle."
        state["module"] = "layout_manager"
        state["window_mode"] = "dedicated_window"
        state["host_contract"] = "layout_manager_dispatcher"
        state["status"] = status
        state["message"] = message
        return state

    def preload_module_bundle(self, force_fresh=False):
        host = self.host_dispatcher
        with host.model.module_import_lock:
            host._configure_module_import_paths()
            if force_fresh:
                for module_path in self.MODULE_BUNDLE:
                    sys.modules.pop(module_path, None)
            importlib.invalidate_caches()
            host.import_managed_module("layout_manager", force_fresh=force_fresh, track_loaded=False)
            for module_path in self.MODULE_BUNDLE[1:]:
                importlib.import_module(module_path)

    def _build_preload_payload(self):
        self.preload_module_bundle(force_fresh=False)
        layout_model_module = importlib.import_module("app.models.layout_manager_model")
        model_class = getattr(layout_model_module, "LayoutManagerModel")
        model = model_class()
        config, source_path, form_info = model.load_current_config()
        return {
            "managed_source_generation": self.host_dispatcher.model.managed_source_generation,
            "form_id": form_info.get("id"),
            "source_path": source_path,
            "save_path": form_info.get("save_path", source_path),
            "form_info": dict(form_info),
            "config": config,
            "preview_grid": model.build_preview_grid(config),
            "guardrails": model.build_editor_guardrails(config),
            "protected_row_field_lookup": model.get_protected_row_field_lookup(config),
            "theme_tokens": self._current_theme_tokens(),
            "loaded_at": time.time(),
        }

    def _store_preload_payload(self, payload):
        host = self.host_dispatcher
        with host.model.preload_data_lock:
            host.shared_data[self.PRELOAD_KEY] = payload
            host.shared_data[self.PRELOAD_PENDING_KEY] = False

    def invalidate_preload(self):
        host = self.host_dispatcher
        with host.model.preload_data_lock:
            host.shared_data.pop(self.PRELOAD_KEY, None)
            host.shared_data[self.PRELOAD_PENDING_KEY] = False

    def schedule_preload(self, force=False):
        host = self.host_dispatcher
        if host.data_request_worker is None:
            return

        with host.model.preload_data_lock:
            if not force:
                cached_payload = host.shared_data.get(self.PRELOAD_KEY)
                if isinstance(cached_payload, dict):
                    if cached_payload.get("managed_source_generation") == host.model.managed_source_generation:
                        return
                if host.shared_data.get(self.PRELOAD_PENDING_KEY):
                    return
            host.shared_data[self.PRELOAD_PENDING_KEY] = True

        def on_success(payload):
            self._store_preload_payload(payload)

        def on_error(exc):
            with host.model.preload_data_lock:
                host.shared_data[self.PRELOAD_PENDING_KEY] = False
            log_exception("layout_manager_mini_dispatcher.schedule_preload", exc)

        host.data_request_worker.submit(
            self._build_preload_payload,
            on_success=on_success,
            on_error=on_error,
            description="layout_manager_preload",
        )

    def consume_preload(self):
        host = self.host_dispatcher
        with host.model.preload_data_lock:
            payload = host.shared_data.pop(self.PRELOAD_KEY, None)
            if not isinstance(payload, dict):
                return None
            if payload.get("managed_source_generation") != host.model.managed_source_generation:
                return None
            host.shared_data[self.PRELOAD_PENDING_KEY] = False
            return payload

    def launch(self, parent):
        # Layout Manager intentionally keeps its heavy editor in a dedicated Qt
        # window while the shell surface exposes status and lifecycle controls.
        self.schedule_preload(force=False)
        self.open_or_raise_window(restart=False)
        return LayoutManagerQtBridge(parent, self)

    def shutdown(self):
        self.stop_window()
