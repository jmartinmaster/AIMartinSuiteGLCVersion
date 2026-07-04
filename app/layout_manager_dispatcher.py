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
import sys
import time

from app.app_logging import log_exception

__module_name__ = "Layout Manager Mini Dispatcher"
__version__ = "1.3.1"


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

    def is_runtime_running(self):
        return False

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
        pass

    def request_reload_from_disk(self):
        pass

    def apply_theme(self):
        theme_tokens = self._current_theme_tokens()
        host = self.host_dispatcher
        with host.model.preload_data_lock:
            cached_payload = host.shared_data.get(self.PRELOAD_KEY)
            if isinstance(cached_payload, dict):
                cached_payload["theme_tokens"] = dict(theme_tokens)

    def forward_runtime_toast(self, toast_event):
        pass

    def forward_runtime_module_open(self, module_open_event):
        pass

    def stop_window(self):
        pass

    def read_runtime_state(self):
        return {"status": "idle"}

    def handle_runtime_state(self, state):
        pass

    def build_host_runtime_state(self):
        return {
            "module": "layout_manager",
            "window_mode": "embedded",
            "host_contract": "layout_manager_dispatcher",
            "status": "idle",
            "message": "Layout Manager runs in-process.",
        }

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
        from app.controllers.layout_manager_qt_controller import LayoutManagerQtController

        return LayoutManagerQtController(parent=parent, dispatcher=self.host_dispatcher)

    def shutdown(self):
        pass
