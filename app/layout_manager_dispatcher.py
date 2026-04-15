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

import ttkbootstrap as tb

from app.app_logging import log_exception

__module_name__ = "Layout Manager Mini Dispatcher"
__version__ = "1.1.0"
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


class LayoutManagerQtBridge:
    def __init__(self, parent, mini_dispatcher):
        self.parent = parent
        self.mini_dispatcher = mini_dispatcher
        self.runtime_manager = mini_dispatcher.runtime_manager
        self.main_frame = tb.Frame(parent, style="Martin.Content.TFrame", padding=20)
        self.main_frame.pack(fill="both", expand=True)
        self._build_ui()
        self._poll_state()

    def _build_ui(self):
        header = tb.Label(self.main_frame, text="Layout Manager Qt Runtime", style="Martin.PageTitle.TLabel")
        header.pack(anchor="w")
        subtitle = tb.Label(
            self.main_frame,
            text=(
                "Layout Manager now runs in a dedicated Qt window. "
                "Use the controls below to open, raise, or resync the sidecar runtime."
            ),
            style="Martin.Subtitle.TLabel",
            wraplength=720,
            justify="left",
        )
        subtitle.pack(anchor="w", pady=(4, 14))

        controls = tb.Frame(self.main_frame, style="Martin.Content.TFrame")
        controls.pack(fill="x", pady=(0, 12))
        tb.Button(controls, text="Open / Raise Qt Window", bootstyle="primary", command=self.open_or_raise).pack(side="left")
        tb.Button(controls, text="Reload From Disk", bootstyle="secondary", command=self.reload_from_disk).pack(side="left", padx=(8, 0))
        tb.Button(controls, text="Restart Qt Runtime", bootstyle="warning", command=self.restart_runtime).pack(side="left", padx=(8, 0))

        status_card = tb.Labelframe(self.main_frame, text="Qt Runtime Status", style="Martin.Card.TLabelframe", padding=(14, 10))
        status_card.pack(fill="x")
        self.status_label = tb.Label(status_card, text="Launching Qt runtime...", style="Martin.Section.TLabel")
        self.status_label.pack(anchor="w")
        self.form_label = tb.Label(status_card, text="Form: --", style="Martin.Muted.TLabel")
        self.form_label.pack(anchor="w", pady=(6, 0))
        self.path_label = tb.Label(status_card, text="Source: --", style="Martin.Muted.TLabel", wraplength=900, justify="left")
        self.path_label.pack(anchor="w", pady=(4, 0))
        self.message_label = tb.Label(status_card, text="Waiting for state...", style="Martin.Muted.TLabel", wraplength=900, justify="left")
        self.message_label.pack(anchor="w", pady=(4, 0))

    def _poll_state(self):
        state = self.runtime_manager.read_state()
        status = str(state.get("status") or "launching").title()
        dirty = bool(state.get("dirty"))
        dirty_suffix = " (Unsaved changes)" if dirty else ""
        self.status_label.configure(text=f"Status: {status}{dirty_suffix}")
        form_name = state.get("form_name") or state.get("form_id") or "--"
        self.form_label.configure(text=f"Form: {form_name}")
        self.path_label.configure(text=f"Source: {state.get('source_path') or '--'}")
        self.message_label.configure(text=str(state.get("message") or "Waiting for state..."))
        if status.lower() == "closed":
            self.mini_dispatcher.schedule_preload(force=True)
        try:
            self.main_frame.after(900, self._poll_state)
        except Exception:
            pass

    def open_or_raise(self):
        self.runtime_manager.ensure_running(force_restart=False)

    def reload_from_disk(self):
        if self.runtime_manager.is_running():
            self.runtime_manager.send_command("reload_from_disk")
            return
        self.runtime_manager.ensure_running(force_restart=False)

    def restart_runtime(self):
        self.runtime_manager.ensure_running(force_restart=True)

    def can_navigate_away(self):
        return True

    def on_hide(self):
        return None

    def on_unload(self):
        return None

    def apply_theme(self):
        return None


class LayoutManagerMiniDispatcher:
    PRELOAD_KEY = "layout_manager_preload"
    PRELOAD_PENDING_KEY = "layout_manager_preload_pending"
    MODULE_BUNDLE = (
        "app.layout_manager",
        "app.controllers.layout_manager_controller",
        "app.controllers.layout_manager_qt_controller",
        "app.models.layout_manager_model",
        "app.views.layout_manager_view",
        "app.views.layout_manager_qt_view",
    )

    def __init__(self, host_dispatcher):
        self.host_dispatcher = host_dispatcher
        self.runtime_manager = LayoutManagerQtRuntimeManager(self)

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
            "theme_tokens": dict(getattr(self.host_dispatcher.root, "_martin_theme_tokens", {}) or {}),
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
        self.schedule_preload(force=False)
        self.runtime_manager.ensure_running(force_restart=False)
        return LayoutManagerQtBridge(parent, self)

    def shutdown(self):
        self.runtime_manager.stop_runtime(force=False)
