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
import inspect
import os
import sys
import threading
import webbrowser

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTTOM, DANGER, INFO, LEFT, RIGHT, SUCCESS, WARNING, X
from ttkbootstrap.widgets import ToastNotification

from app.app_logging import log_exception
from app.data_request_worker import DataRequestWorker
from app.external_data_registry import ExternalDataRegistry
from app.module_registry import ModuleRegistry
from app.security import gatekeeper
from app.theme_manager import apply_readability_overrides, normalize_theme, resolve_base_theme
from app.utils import external_path, local_or_resource_path, resource_path
from app.layout_manager_dispatcher import LayoutManagerMiniDispatcher
from app.models.app_model import AppModel
from app.views.app_view import AppShellView
from app.security_service import SecurityService
from app.update_state import UpdateCoordinator
from app.host_ui_adapter import TkHostUiAdapter

__module_name__ = "Dispatcher Core"
__version__ = "2.1.5"

ISSUE_REPORT_URL = "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion/issues/new/choose"
MODULE_PRELOAD_POLL_SECONDS = 1.0
QT_IN_VIEWPORT_PILOT_MODULES = {"about", "help_viewer", "recovery_viewer", "rate_manager", "production_log_calculations"}

SEVERITY_TO_BOOTSTYLE = {
    "info": INFO,
    "success": SUCCESS,
    "warning": WARNING,
    "danger": DANGER,
    "error": DANGER,
}

MODULE_API_SURFACE = {
    "navigation": (
        "load_module",
        "secure_load",
        "refresh_navigation",
        "get_navigation_modules",
        "get_user_facing_modules",
        "get_persistable_modules",
    ),
    "notifications_and_status": (
        "show_toast",
        "notify_user",
        "set_update_status",
        "set_status_banner",
        "clear_update_status",
        "clear_update_status_after",
    ),
    "settings_and_theme": (
        "get_setting",
        "get_ui_shell_backend",
        "is_pyqt6_shell_requested",
        "get_active_shell_backend",
        "get_shell_backend_fallback_reason",
        "refresh_runtime_settings",
        "register_runtime_settings_listener",
        "unregister_runtime_settings_listener",
        "apply_theme",
    ),
    "module_runtime": (
        "open_module_window",
        "open_help_document",
        "send_module_runtime_command",
        "open_production_log_draft",
        "import_managed_module",
        "get_active_form_info",
        "register_active_form_listener",
        "unregister_active_form_listener",
        "notify_active_form_changed",
        "notify_production_log_calculation_settings_changed",
    ),
    "security": (
        "add_security_session_listener",
        "remove_security_session_listener",
        "has_external_modules_directory",
        "get_external_module_override_names",
        "is_external_module_override_trust_enabled",
        "apply_external_override_policy_change",
    ),
    "ui_thread_and_shell": (
        "run_on_main_thread",
        "call_later",
        "request_shutdown",
        "bind_mousewheel_to_widget_tree",
        "bind_shell_viewport_resize",
        "get_shell_viewport_size",
    ),
    "layout_preload": (
        "invalidate_layout_manager_preload",
        "schedule_layout_manager_preload",
        "consume_layout_manager_preload",
    ),
    "transitional_properties": (
        "active_module_instance",
        "modules_path",
        "external_modules_path",
        "loaded_modules",
        "shared_data",
        "update_coordinator",
    ),
}


class Dispatcher:
    def __init__(
        self,
        root,
        main_module=None,
        initial_module_name=None,
        runtime_settings_override=None,
        host_ui_adapter_factory=None,
        shell_view_factory=None,
    ):
        self.root = root
        self.main_module = main_module or sys.modules.get("main") or sys.modules.get("__main__")
        self.dispatcher_version = getattr(self.main_module, "__version__", None) or "0.0.0"
        window_version = self.dispatcher_version if self.dispatcher_version != "0.0.0" else "Unknown"
        self.root.title(f"Production Logging Center - {window_version}")
        self.root.geometry("1000x600")
        self._update_status_clear_after_id = None
        self.security_session_listeners = []
        self.external_data_registry = ExternalDataRegistry()
        self.data_request_worker = None

        modules_path = resource_path("app")
        external_modules_path = external_path("app")
        layout_config = self.external_data_registry.resolve_read_path("layout_config")
        rate_config = self.external_data_registry.resolve_read_path("rates")
        settings_path = self.external_data_registry.resolve_read_path("settings")

        self.model = AppModel(
            modules_path=modules_path,
            external_modules_path=external_modules_path,
            layout_config=layout_config,
            rate_config=rate_config,
            settings_path=settings_path,
        )
        self.module_registry = ModuleRegistry()
        self.security = SecurityService(
            self.get_protected_module_names(),
            module_allowed_roles=self.get_module_allowed_roles(),
            hidden_modules=self.get_hidden_security_module_names(),
        )
        self.model.loaded_modules = {"main": self.main_module}
        self._configure_module_import_paths()
        self.model.runtime_settings = self.load_runtime_settings()
        if isinstance(runtime_settings_override, dict):
            self.model.runtime_settings.update(runtime_settings_override)
        self.requested_shell_backend = "pyqt6"
        self.active_shell_backend = "tk"
        self.shell_backend_fallback_reason = None
        self.host_ui_adapter_factory = host_ui_adapter_factory
        self.shell_view_factory = shell_view_factory
        self._refresh_shell_backend_state()
        self.model.module_preload_poll_seconds = MODULE_PRELOAD_POLL_SECONDS
        self.update_coordinator = UpdateCoordinator(self.root)
        self.layout_manager_dispatcher = LayoutManagerMiniDispatcher(self)
        self.refresh_animation_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.data_request_worker = DataRequestWorker(self._enqueue_on_main_thread, exception_logger=self._log_data_request_error)
        self.data_request_worker.start()

        self.view = self._create_shell_view()
        self._sync_view_aliases()
        self.host_ui_adapter = None
        self._switch_active_host_ui_adapter()
        gatekeeper.add_session_listener(self._handle_gatekeeper_session_change)
        self._setup_menu()
        self.pre_load_manifest()
        self._load_modules_list()
        self._bind_mousewheel()
        self.refresh_update_status_visibility()
        self.load_module(self._resolve_initial_module_name(initial_module_name), use_transition=False)
        self._resolve_active_form_info(source_instance=self.active_module_instance)
        self.call_later(1200, self.notify_non_secure_mode_state)
        self.call_later(1500, self.notify_external_override_policy_state)
        self.call_later(900, self.prompt_old_executable_cleanup)
        self.call_later(1800, self.check_for_available_module_updates)
        self.data_request_worker.submit(self.external_data_registry.warm_cache, description="external_data_registry.warm_cache")
        self.call_later(2500, self.schedule_layout_manager_preload)

    def _create_shell_view(self):
        if callable(self.shell_view_factory):
            view = self.shell_view_factory(self.root, self.update_coordinator, self)
        else:
            view = AppShellView(self.root, self.update_coordinator)

        build = getattr(view, "build", None)
        if callable(build):
            build()

        attach_dispatcher = getattr(view, "attach_dispatcher", None)
        if callable(attach_dispatcher):
            attach_dispatcher(self)

        return view

    def _sync_view_aliases(self):
        self.main_container = getattr(self.view, "main_container", None)
        self.sidebar = getattr(self.view, "sidebar", None)
        self.nav_container = getattr(self.view, "nav_container", None)
        self.right_container = getattr(self.view, "right_container", None)
        self.update_status_frame = getattr(self.view, "update_status_frame", None)
        self.update_status_label = getattr(self.view, "update_status_label", None)
        self.canvas = getattr(self.view, "canvas", None)
        self.scrollbar = getattr(self.view, "scrollbar", None)
        self.x_scrollbar = getattr(self.view, "x_scrollbar", None)
        self.content_area = getattr(self.view, "content_area", None)
        self.canvas_window = getattr(self.view, "canvas_window", None)

    @property
    def modules_path(self):
        return self.model.modules_path

    @property
    def external_modules_path(self):
        return self.model.external_modules_path

    @property
    def layout_config(self):
        return self.model.layout_config

    @property
    def rate_config(self):
        return self.model.rate_config

    @property
    def shared_data(self):
        return self.model.shared_data

    @property
    def loaded_modules(self):
        return self.model.loaded_modules

    @property
    def persistent_module_instances(self):
        return self.model.persistent_module_instances

    @property
    def active_module_instance(self):
        return self.model.active_module_instance

    @active_module_instance.setter
    def active_module_instance(self, value):
        self.model.active_module_instance = value

    @property
    def active_module_name(self):
        return self.model.active_module_name

    @active_module_name.setter
    def active_module_name(self, value):
        self.model.active_module_name = value

    @property
    def active_module_container(self):
        return self.model.active_module_frame

    @active_module_container.setter
    def active_module_container(self, value):
        self.model.active_module_frame = value

    @property
    def active_module_frame(self):
        return self.active_module_container

    @active_module_frame.setter
    def active_module_frame(self, value):
        self.active_module_container = value

    @property
    def active_form_info(self):
        return self.model.active_form_info

    @active_form_info.setter
    def active_form_info(self, value):
        self.model.active_form_info = dict(value) if isinstance(value, dict) else {}

    @property
    def runtime_settings(self):
        return self.model.runtime_settings

    @runtime_settings.setter
    def runtime_settings(self, value):
        self.model.runtime_settings = value

    @property
    def runtime_settings_listeners(self):
        return self.model.runtime_settings_listeners

    @property
    def active_form_listeners(self):
        return self.model.active_form_listeners

    def get_managed_module_names(self):
        return self.module_registry.get_managed_module_names()

    def get_module_api_surface(self):
        return MODULE_API_SURFACE

    def get_navigation_module_names(self):
        return self.module_registry.get_navigation_module_names()

    def get_preload_module_names(self):
        return self.module_registry.get_preload_module_names()

    def get_protected_module_names(self):
        return self.module_registry.get_protected_module_names()

    def get_hidden_security_module_names(self):
        return self.module_registry.get_hidden_security_module_names()

    def get_module_allowed_roles(self):
        return self.module_registry.get_module_allowed_roles()

    @property
    def module_update_check_in_progress(self):
        return self.model.module_update_check_in_progress

    @module_update_check_in_progress.setter
    def module_update_check_in_progress(self, value):
        self.model.module_update_check_in_progress = bool(value)

    @property
    def last_module_update_notification_signature(self):
        return self.model.last_module_update_notification_signature

    @last_module_update_notification_signature.setter
    def last_module_update_notification_signature(self, value):
        self.model.last_module_update_notification_signature = value

    def _configure_module_import_paths(self):
        bundled_base_dir = os.path.abspath(os.path.dirname(self.modules_path))
        external_base_dir = os.path.abspath(os.path.dirname(self.external_modules_path))

        if external_base_dir not in sys.path:
            sys.path.insert(0, external_base_dir)
        if bundled_base_dir not in sys.path:
            sys.path.append(bundled_base_dir)

        importlib.invalidate_caches()

        try:
            app_package = importlib.import_module("app")
            self._configure_package_search_path(app_package, self.external_modules_path, self.modules_path)
            package_specs = [
                ("app.controllers", os.path.join(self.external_modules_path, "controllers"), os.path.join(self.modules_path, "controllers")),
                ("app.models", os.path.join(self.external_modules_path, "models"), os.path.join(self.modules_path, "models")),
                ("app.views", os.path.join(self.external_modules_path, "views"), os.path.join(self.modules_path, "views")),
            ]
            for package_name, external_dir, bundled_dir in package_specs:
                package_module = importlib.import_module(package_name)
                self._configure_package_search_path(package_module, external_dir, bundled_dir)
        except Exception:
            pass

    def _configure_package_search_path(self, package_module, external_dir, bundled_dir):
        package_path = getattr(package_module, "__path__", None)
        if package_path is None:
            return

        normalized_paths = []
        for candidate in (external_dir, bundled_dir):
            if not candidate or not os.path.isdir(candidate):
                continue
            normalized_candidate = os.path.abspath(candidate)
            if normalized_candidate not in normalized_paths:
                normalized_paths.append(normalized_candidate)

        for existing_path in list(package_path):
            normalized_existing_path = os.path.abspath(existing_path)
            if normalized_existing_path not in normalized_paths:
                normalized_paths.append(normalized_existing_path)

        package_path[:] = normalized_paths

    def _relative_python_path_to_module_name(self, relative_path):
        normalized_relative_path = str(relative_path or "").replace("\\", "/").lstrip("/")
        if not normalized_relative_path.endswith(".py"):
            return None
        return normalized_relative_path[:-3].replace("/", ".")

    def _evict_imported_module_paths(self, relative_paths):
        for relative_path in relative_paths:
            module_path = self._relative_python_path_to_module_name(relative_path)
            if not module_path:
                continue
            self.loaded_modules.pop(module_path.removeprefix("app."), None)
            if module_path in sys.modules:
                del sys.modules[module_path]
        importlib.invalidate_caches()

    def ensure_external_modules_package(self):
        self.model.ensure_external_modules_directory()
        self._configure_module_import_paths()

    def import_managed_module(self, module_name, force_fresh=True, track_loaded=True):
        module_path = self._resolve_managed_module_path(module_name)
        with self.model.module_import_lock:
            self._configure_module_import_paths()
            if force_fresh and module_path in sys.modules:
                del sys.modules[module_path]
            importlib.invalidate_caches()
            module = importlib.import_module(module_path)
        if track_loaded:
            self.loaded_modules[module_name] = module
        return module

    def _resolve_managed_module_path(self, module_name):
        return self.module_registry.get_module_path(module_name)

    def _resolve_initial_module_name(self, module_name):
        available_module_names = {name for _display_name, name in self.get_navigation_modules()}
        if module_name in available_module_names:
            return module_name
        default_module_name = self.module_registry.get_default_initial_module_name()
        if default_module_name in available_module_names:
            return default_module_name
        return next(iter(sorted(available_module_names)), default_module_name)

    def _iter_managed_source_files(self):
        source_roots = [("bundled", self.modules_path)]
        if self.has_external_modules_directory():
            source_roots.append(("external", self.external_modules_path))

        for root_kind, root_path in source_roots:
            if not os.path.isdir(root_path):
                continue
            for current_root, dir_names, file_names in os.walk(root_path):
                dir_names[:] = [directory for directory in dir_names if directory != "__pycache__"]
                for file_name in file_names:
                    if not file_name.endswith(".py"):
                        continue
                    absolute_path = os.path.join(current_root, file_name)
                    try:
                        file_stat = os.stat(absolute_path)
                    except OSError:
                        continue
                    relative_path = os.path.relpath(absolute_path, root_path).replace("\\", "/")
                    yield (root_kind, relative_path, file_stat.st_mtime_ns, file_stat.st_size)

    def _build_managed_source_signature(self):
        return tuple(sorted(self._iter_managed_source_files()))

    def _invalidate_managed_module_cache_locked(self, new_signature=None):
        self.model.managed_source_signature = tuple(new_signature or ())
        self.model.managed_source_generation += 1
        self.model.preloaded_module_names.clear()
        if self.layout_manager_dispatcher is not None:
            self.layout_manager_dispatcher.invalidate_preload()
        for module_name in list(self.loaded_modules):
            if module_name == "main":
                continue
            self.loaded_modules.pop(module_name, None)
        for module_key in [key for key in sys.modules if key.startswith("app.")]:
            sys.modules.pop(module_key, None)
        importlib.invalidate_caches()

    def invalidate_managed_module_cache(self, new_signature=None):
        signature = new_signature or self._build_managed_source_signature()
        with self.model.module_import_lock:
            self._invalidate_managed_module_cache_locked(signature)

    def _sync_managed_source_signature(self, force=False):
        current_signature = self._build_managed_source_signature()
        with self.model.module_import_lock:
            if force or current_signature != self.model.managed_source_signature:
                self._invalidate_managed_module_cache_locked(current_signature)
                return True
        return False

    def _get_module_preload_targets(self):
        targets = []
        if self.active_module_name:
            targets.append(self.active_module_name)
        for module_name in self.get_preload_module_names():
            if module_name not in targets:
                targets.append(module_name)
        return targets

    def _run_module_preload_cycle(self):
        self._sync_managed_source_signature(force=False)
        for module_name in self._get_module_preload_targets():
            if self.model.module_preload_stop_event.is_set():
                return
            module_path = self._resolve_managed_module_path(module_name)
            with self.model.module_import_lock:
                if module_path in sys.modules:
                    self.model.preloaded_module_names.add(module_name)
                    continue
            try:
                self.import_managed_module(module_name, force_fresh=False, track_loaded=False)
                self.model.preloaded_module_names.add(module_name)
            except Exception as exc:
                log_exception(f"module_preload.{module_name}", exc)

    def _module_preloader_worker(self):
        while not self.model.module_preload_stop_event.is_set():
            try:
                self._run_module_preload_cycle()
            except Exception as exc:
                log_exception("module_preloader.worker", exc)
            if self.model.module_preload_stop_event.wait(self.model.module_preload_poll_seconds):
                break

    def start_module_preloader(self):
        thread = self.model.module_preload_thread
        if thread is not None and thread.is_alive():
            return
        self.model.module_preload_stop_event.clear()
        self.model.module_preload_thread = threading.Thread(
            target=self._module_preloader_worker,
            name="ModulePreloader",
            daemon=True,
        )
        self.model.module_preload_thread.start()

    def stop_module_preloader(self):
        thread = self.model.module_preload_thread
        if thread is None:
            return
        self.model.module_preload_stop_event.set()
        if thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        self.model.module_preload_thread = None

    def shutdown(self):
        if self.active_module_instance is not None and hasattr(self.active_module_instance, "can_navigate_away"):
            if not self.active_module_instance.can_navigate_away():
                return
        if self.data_request_worker is not None:
            self.data_request_worker.stop()
        self.stop_module_preloader()
        self.layout_manager_dispatcher.shutdown()
        gatekeeper.remove_session_listener(self._handle_gatekeeper_session_change)
        try:
            self.root.destroy()
        except Exception:
            pass

    def get_external_module_override_path(self, module_name):
        return self.model.get_external_module_override_path(module_name, self.get_managed_module_names())

    def has_external_modules_directory(self):
        return self.model.has_external_modules_directory()

    def get_external_module_override_names(self):
        return self.model.get_external_module_override_names(self.get_managed_module_names())

    def get_bundled_module_names(self):
        return self.model.get_bundled_module_names(self.get_managed_module_names())

    def has_external_module_overrides(self):
        return bool(self.get_external_module_override_names())

    def are_external_module_overrides_enabled(self):
        return self.has_external_module_overrides() and self.is_external_module_override_trust_enabled()

    def is_external_module_override_trust_enabled(self):
        return self.security.is_external_module_override_trust_enabled()

    def is_module_loaded_from_external(self, module_name, module_obj=None):
        if module_name == "main":
            return False
        if not self.are_external_module_overrides_enabled():
            return False
        candidate_module = module_obj or self.loaded_modules.get(module_name)
        module_file = getattr(candidate_module, "__file__", "") if candidate_module is not None else ""
        if not module_file:
            return False
        normalized_file = os.path.abspath(module_file)
        normalized_external_root = os.path.abspath(self.external_modules_path)
        try:
            return os.path.commonpath([normalized_file, normalized_external_root]) == normalized_external_root
        except Exception:
            return False

    def reset_module_import_state(self, keep_active=True):
        active_name = self.active_module_name if keep_active else None
        for module_name, session in list(self.persistent_module_instances.items()):
            if keep_active and module_name == active_name:
                continue
            instance = session.get("instance")
            container = self._get_session_container(session)
            if hasattr(instance, "on_unload"):
                try:
                    instance.on_unload()
                except Exception as exc:
                    log_exception(f"reset_module_import_state.{module_name}", exc)
            if self._module_container_exists(container):
                self._destroy_module_container(container)
            self.persistent_module_instances.pop(module_name, None)
        if not keep_active:
            self.invalidate_managed_module_cache()

    def install_module_override(self, module_name, module_text):
        self.ensure_external_modules_package()
        if isinstance(module_text, dict):
            target_path, _written_paths = self.model.write_module_override_files(
                module_text,
                primary_relative_path=f"app/{module_name}.py",
            )
            self._evict_imported_module_paths(module_text.keys())
        else:
            target_path = self.model.write_module_override(module_name, module_text)
            self._evict_imported_module_paths([f"app/{module_name}.py"])
        module = self.import_managed_module(module_name, force_fresh=True) if self.is_external_module_override_trust_enabled() else None
        return target_path, module

    def apply_external_override_policy_change(self):
        current_module_name = self.active_module_name or "settings_manager"
        self.reset_module_import_state(keep_active=False)
        self._configure_module_import_paths()
        self.load_module(current_module_name, use_transition=False)

    def remove_external_module_overrides(self, module_names=None, include_bytecode=True):
        return self.model.remove_external_module_overrides(
            self.get_managed_module_names(),
            module_names=module_names,
            include_bytecode=include_bytecode,
        )

    def _setup_menu(self):
        self.view.configure_menu(
            self.menu_open,
            self.menu_save,
            self.menu_export,
            self.menu_import,
            self.menu_login,
            self.menu_change_login,
            self.menu_logout,
            lambda: self.load_module("help_viewer"),
            self.open_issue_report_page,
            lambda: self.load_module("about"),
            self.shutdown,
        )

    def open_issue_report_page(self):
        try:
            webbrowser.open(ISSUE_REPORT_URL)
        except Exception as exc:
            log_exception("open_issue_report_page", exc)
            self.host_ui_adapter.show_error("Report A Problem", f"Could not open the GitHub issue page:\n\n{exc}")

    def menu_open(self, event=None):
        if self.active_shell_backend == "pyqt6" and hasattr(self.view, "menu_open"):
            self.view.menu_open()
            self.active_module_name = getattr(self.view, "active_module_name", "production_log") or "production_log"
            return
        self.load_module("production_log")
        if hasattr(self.active_module_instance, "show_pending"):
            self.active_module_instance.show_pending()

    def menu_save(self, event=None):
        if self.active_shell_backend == "pyqt6" and hasattr(self.view, "menu_save"):
            self.view.menu_save()
            return
        if hasattr(self.active_module_instance, "save_draft"):
            self.active_module_instance.save_draft()
        elif hasattr(self.active_module_instance, "save_current_file"):
            self.active_module_instance.save_current_file()
        else:
            self.show_toast("Action Unavailable", "Save action is not supported on this page.", WARNING)

    def menu_export(self, event=None):
        if self.active_shell_backend == "pyqt6" and hasattr(self.view, "menu_export"):
            self.view.menu_export()
            return
        if hasattr(self.active_module_instance, "export_to_excel"):
            self.active_module_instance.export_to_excel()
        else:
            self.show_toast("Action Unavailable", "Export action is not supported on this page.", WARNING)

    def menu_import(self, event=None):
        if self.active_shell_backend == "pyqt6" and hasattr(self.view, "menu_import"):
            self.view.menu_import()
            self.active_module_name = getattr(self.view, "active_module_name", "production_log") or "production_log"
            return
        self.load_module("production_log")
        if hasattr(self.active_module_instance, "import_from_excel_ui"):
            self.active_module_instance.import_from_excel_ui()

    def menu_login(self):
        try:
            if not gatekeeper.authenticate(
                required_right="security:manage_vaults",
                parent=self.root,
                reason="Sign in to reveal protected pages and tools.",
                allowed_roles={"admin", "developer"},
            ):
                return
        except Exception as exc:
            log_exception("menu_login.error", exc)
            self.host_ui_adapter.show_error("Security Error", f"Sign in failed: {exc}")
            return

        self.refresh_navigation()
        self.refresh_active_module_access_state()
        self.show_toast("Security", f"Signed in: {self.security.get_session_summary()}", SUCCESS)

    def menu_change_login(self):
        try:
            if not gatekeeper.authenticate(
                required_right="security:manage_vaults",
                parent=self.root,
                reason="Change the active admin or developer session.",
                force_reauth=True,
                allowed_roles={"admin", "developer"},
            ):
                return
        except Exception as exc:
            log_exception("menu_change_login.error", exc)
            self.host_ui_adapter.show_error("Security Error", f"Change login failed: {exc}")
            return

        self.refresh_navigation()
        self.refresh_active_module_access_state()
        self._enforce_active_module_access()
        self.show_toast("Security", f"Active login: {self.security.get_session_summary()}", SUCCESS)

    def menu_logout(self):
        previous_summary = self.security.get_session_summary()
        gatekeeper.logout()
        self.refresh_navigation()
        self.refresh_active_module_access_state()
        self._enforce_active_module_access()
        self.show_toast("Security", f"Signed out: {previous_summary}", WARNING)

    def add_security_session_listener(self, listener):
        if callable(listener) and listener not in self.security_session_listeners:
            self.security_session_listeners.append(listener)

    def remove_security_session_listener(self, listener):
        if listener in self.security_session_listeners:
            self.security_session_listeners.remove(listener)

    def _handle_gatekeeper_session_change(self, event_name):
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        self.call_later(0, lambda: self._broadcast_security_session_change(event_name))

    def _broadcast_security_session_change(self, event_name):
        self.refresh_navigation()
        self.refresh_active_module_access_state()
        self._enforce_active_module_access()
        for listener in list(self.security_session_listeners):
            try:
                listener(event_name)
            except Exception as exc:
                log_exception("dispatcher.security_session_listener", exc)

    def _enforce_active_module_access(self):
        active_module_name = self.active_module_name
        if not active_module_name:
            return
        if not self.security.requires_authentication(active_module_name):
            return
        if self.security.can_access_module(active_module_name):
            return
        self.load_module("production_log", use_transition=False, ensure_authorized=False)

    def _refresh_module_access_state_for_instance(self, module_instance):
        if module_instance is None:
            return
        refresh_method = getattr(module_instance, "refresh_session_state", None)
        if callable(refresh_method):
            try:
                refresh_method()
            except Exception as exc:
                log_exception("refresh_active_module_access_state.refresh_session_state", exc)
            return
        for method_name in ("refresh_security_status", "refresh_developer_admin_status", "refresh_external_modules_status"):
            refresh_method = getattr(module_instance, method_name, None)
            if callable(refresh_method):
                try:
                    refresh_method()
                except Exception as exc:
                    log_exception(f"refresh_active_module_access_state.{method_name}", exc)

    def refresh_active_module_access_state(self):
        seen_instances = set()

        active_module = self.active_module_instance
        if active_module is not None:
            seen_instances.add(id(active_module))
            self._refresh_module_access_state_for_instance(active_module)

        for session in self.persistent_module_instances.values():
            module_instance = session.get("instance")
            if module_instance is None or id(module_instance) in seen_instances:
                continue
            seen_instances.add(id(module_instance))
            self._refresh_module_access_state_for_instance(module_instance)

    def pre_load_manifest(self):
        self._sync_managed_source_signature(force=True)
        self.start_module_preloader()

    def _load_modules_list(self):
        navigation_groups = self.get_navigation_groups()
        self.view.populate_navigation(navigation_groups, self.secure_load, self.active_module_name)

    def refresh_navigation(self):
        self._load_modules_list()

    def secure_load(self, module_name):
        try:
            success = self.security.authenticate_module(
                module_name,
                parent=self.root,
                reason=f"Unlock {self.get_module_display_name(module_name)} to continue.",
            )
            if success is False:
                return
        except Exception as exc:
            log_exception(f"secure_load.error.{module_name}", exc)
            self.host_ui_adapter.show_error("Security Error", f"Auth failed: {exc}")
            return

        self.refresh_navigation()
        self.load_module(module_name, ensure_authorized=False)

    def notify_non_secure_mode_state(self):
        if self.security.is_non_secure_mode_enabled():
            self.show_toast("Security", "Non-secure mode is enabled. Protected modules will open without password prompts.", WARNING)

    def notify_external_override_policy_state(self):
        if self.has_external_module_overrides() and not self.is_external_module_override_trust_enabled():
            self.show_toast("Security", "External module overrides are present but inactive until an admin enables override trust.", WARNING)

    def get_navigation_modules(self):
        visible_modules = self.get_user_facing_modules(apply_whitelist=True)
        return [(self.get_module_display_name(module_name), module_name) for module_name in visible_modules]

    def get_navigation_groups(self):
        grouped_items = {"top": [], "middle": [], "bottom": []}
        visible_modules = self.get_user_facing_modules(apply_whitelist=True)
        for module_name in visible_modules:
            entry = (self.get_module_display_name(module_name), module_name)
            navigation_group = self.module_registry.get_navigation_group(module_name)
            grouped_items.get(navigation_group, grouped_items["middle"]).append(entry)
        return grouped_items

    def get_hidden_module_names(self):
        return set(self.module_registry.get_non_navigation_module_names())

    def get_module_display_name(self, module_name):
        try:
            return self.module_registry.get_module_display_name(module_name)
        except Exception:
            return str(module_name).replace("_", " ").title()

    def notify_production_log_calculation_settings_changed(self):
        seen_instances = set()

        active_module = self.active_module_instance
        if active_module is not None and hasattr(active_module, "on_calculation_settings_changed"):
            seen_instances.add(id(active_module))
            try:
                active_module.on_calculation_settings_changed()
            except Exception as exc:
                log_exception("notify_production_log_calculation_settings_changed.active", exc)

        for session in self.persistent_module_instances.values():
            module_instance = session.get("instance")
            if module_instance is None or id(module_instance) in seen_instances:
                continue
            if not hasattr(module_instance, "on_calculation_settings_changed"):
                continue
            seen_instances.add(id(module_instance))
            try:
                module_instance.on_calculation_settings_changed()
            except Exception as exc:
                log_exception("notify_production_log_calculation_settings_changed.persistent", exc)

    def notify_active_form_changed(self, source_instance=None, active_form_info=None, form_id=None):
        self.invalidate_layout_manager_preload()
        self.schedule_layout_manager_preload(force=True)
        resolved_active_form_info = self._resolve_active_form_info(
            source_instance=source_instance,
            active_form_info=active_form_info,
            form_id=form_id,
        )
        seen_instances = set()
        source_instance_id = id(source_instance) if source_instance is not None else None

        for listener in list(self.active_form_listeners):
            try:
                self._call_with_active_form_payload(listener, resolved_active_form_info)
            except Exception as exc:
                log_exception("notify_active_form_changed.listener", exc)

        active_module = self.active_module_instance
        if active_module is not None and hasattr(active_module, "on_active_form_changed"):
            active_instance_id = id(active_module)
            if active_instance_id != source_instance_id:
                seen_instances.add(active_instance_id)
                try:
                    self._call_with_active_form_payload(active_module.on_active_form_changed, resolved_active_form_info)
                except Exception as exc:
                    log_exception("notify_active_form_changed.active", exc)

        for session in self.persistent_module_instances.values():
            module_instance = session.get("instance")
            if module_instance is None:
                continue
            instance_id = id(module_instance)
            if instance_id in seen_instances or instance_id == source_instance_id:
                continue
            if not hasattr(module_instance, "on_active_form_changed"):
                continue
            seen_instances.add(instance_id)
            try:
                self._call_with_active_form_payload(module_instance.on_active_form_changed, resolved_active_form_info)
            except Exception as exc:
                log_exception("notify_active_form_changed.persistent", exc)

        return resolved_active_form_info

    def get_user_facing_modules(self, apply_whitelist=False):
        whitelist = set(self.runtime_settings.get("module_whitelist", [])) if apply_whitelist else set()
        visible_modules = []

        for module_name in self.get_navigation_module_names():
            if not self.security.is_module_visible(module_name):
                continue
            if whitelist and module_name not in whitelist:
                if not self.security.can_access_module(module_name):
                    continue
            if module_name not in visible_modules:
                visible_modules.append(module_name)

        return sorted(visible_modules, key=lambda item: self.get_module_display_name(item).lower())

    def get_persistable_modules(self):
        return [
            (self.get_module_display_name(module_name), module_name)
            for module_name in self.get_user_facing_modules(apply_whitelist=False)
            if self.module_registry.is_module_persistable(module_name)
        ]

    def normalize_module_whitelist(self, raw_value):
        return self.model.normalize_module_names(raw_value, self.get_user_facing_modules(apply_whitelist=False))

    def normalize_persistent_modules(self, raw_value):
        valid_modules = [module_name for _display_name, module_name in self.get_persistable_modules()]
        return self.model.normalize_module_names(raw_value, valid_modules)

    def is_module_persistent(self, module_name):
        if not module_name:
            return False
        if self.module_registry.is_module_always_persistent(module_name):
            return True
        return module_name in self.runtime_settings.get("persistent_modules", [])

    def prune_persistent_module_instances(self):
        allowed_modules = set(self.runtime_settings.get("persistent_modules", [])) | {"update_manager"}
        for module_name in list(self.persistent_module_instances):
            if module_name in allowed_modules or module_name == self.active_module_name:
                continue
            session = self.persistent_module_instances.pop(module_name, None)
            if not session:
                continue
            instance = session.get("instance")
            container = self._get_session_container(session)
            if hasattr(instance, "on_unload"):
                try:
                    instance.on_unload()
                except Exception as exc:
                    log_exception(f"persistent_module_unload.{module_name}", exc)
            if self._module_container_exists(container):
                self._destroy_module_container(container)

    def _run_window_transition(self, action):
        if (
            not self.model.window_alpha_supported
            or not self.model.transitions_enabled
            or self.model.transition_duration_ms <= 0
            or self.model.transition_in_progress
        ):
            return action()

        self.model.transition_in_progress = True
        try:
            return self.host_ui_adapter.run_window_transition(
                action,
                duration_ms=self.model.transition_duration_ms,
                min_alpha=self.model.transition_min_alpha,
            )
        finally:
            self.model.transition_in_progress = False

    def _is_main_thread(self):
        return threading.current_thread() is threading.main_thread()

    def _enqueue_on_main_thread(self, callback):
        if self._is_main_thread():
            return callback()
        try:
            self.run_on_main_thread(callback)
        except Exception as exc:
            log_exception("dispatcher.enqueue_on_main_thread", exc)
        return None

    def _log_data_request_error(self, description, exc):
        log_exception(f"dispatcher.data_request.{description}", exc)

    def call_later(self, delay_ms, callback):
        return self.host_ui_adapter.call_later(delay_ms, callback)

    def run_on_main_thread(self, callback):
        return self.host_ui_adapter.run_on_main_thread(callback)

    def request_shutdown(self, delay_ms=0):
        self.host_ui_adapter.request_shutdown(delay_ms=delay_ms)

    def bind_shell_viewport_resize(self, callback, add="+"):
        return self.host_ui_adapter.bind_shell_viewport_resize(callback, add=add)

    def get_shell_viewport_size(self, min_width=0, min_height=0):
        return self.host_ui_adapter.get_shell_viewport_size(min_width=min_width, min_height=min_height)

    def invalidate_layout_manager_preload(self):
        if self.layout_manager_dispatcher is None:
            return
        self.layout_manager_dispatcher.invalidate_preload()

    def schedule_layout_manager_preload(self, force=False):
        if self.layout_manager_dispatcher is None:
            return
        self.layout_manager_dispatcher.schedule_preload(force=force)

    def consume_layout_manager_preload(self):
        if self.layout_manager_dispatcher is None:
            return None
        return self.layout_manager_dispatcher.consume_preload()

    def _can_navigate_away_from_active_module(self):
        active_module = self.active_module_instance
        if active_module is not None and hasattr(active_module, "can_navigate_away"):
            return bool(active_module.can_navigate_away())
        return True

    def _clear_active_module_state(self):
        self.active_module_name = None
        self.active_module_instance = None
        self.active_module_container = None

    def _deactivate_module_instance(self, module_name, module_instance, module_container):
        if module_instance is None:
            return

        if self.is_module_persistent(module_name):
            if hasattr(module_instance, "on_hide"):
                module_instance.on_hide()
            if self._module_container_exists(module_container):
                self._hide_module_container(module_container)
            return

        if hasattr(module_instance, "on_unload"):
            module_instance.on_unload()
        if self._module_container_exists(module_container):
            self._destroy_module_container(module_container)
        self.persistent_module_instances.pop(module_name, None)

    def _reset_module_viewport_for_load(self):
        self._clear_active_module_state()
        self._reset_shell_viewport_position()

    def _refresh_active_module_ui(self, module_name):
        active_module = self.active_module_instance
        if active_module is not None and hasattr(active_module, "apply_theme"):
            active_module.apply_theme()

        self.host_ui_adapter.refresh_viewport_appearance()

        if hasattr(self.view, "set_active_navigation_button"):
            self.view.set_active_navigation_button(module_name)

    def _set_active_module(self, module_name, module_instance, module_container):
        self.active_module_name = module_name
        self.active_module_instance = module_instance
        self.active_module_container = module_container

    def _restore_cached_module_session(self, module_name, session):
        cached_container = self._get_session_container(session)
        self._set_active_module(module_name, session.get("instance"), cached_container)
        self._show_module_container(cached_container)
        self._refresh_active_module_ui(module_name)
        return self.active_module_instance

    def _discard_stale_persistent_module_session(self, module_name, session):
        stale_instance = session.get("instance")
        stale_container = self._get_session_container(session)
        if hasattr(stale_instance, "on_unload"):
            try:
                stale_instance.on_unload()
            except Exception as exc:
                log_exception(f"persistent_module_stale.{module_name}", exc)
        if self._module_container_exists(stale_container):
            self._destroy_module_container(stale_container)
        self.persistent_module_instances.pop(module_name, None)

    def _try_restore_persistent_module(self, module_name):
        if not self.is_module_persistent(module_name) or module_name not in self.persistent_module_instances:
            return None

        session = self.persistent_module_instances[module_name]
        cached_container = self._get_session_container(session)
        session_generation = session.get("generation")
        if session_generation == self.model.managed_source_generation and self._module_container_exists(cached_container):
            return self._restore_cached_module_session(module_name, session)

        self._discard_stale_persistent_module_session(module_name, session)
        return None

    def _create_module_container_for_active_viewport(self, module_name=None):
        return self.host_ui_adapter.create_module_container(self.content_area, module_name=module_name)

    def _prepare_module_viewport_load(self):
        self._sync_managed_source_signature(force=False)
        if not self._can_navigate_away_from_active_module():
            return False

        self._deactivate_module_instance(
            self.active_module_name,
            self.active_module_instance,
            self.active_module_container,
        )
        self._reset_module_viewport_for_load()
        return True

    def _load_module_in_shared_viewport(self, module_name):
        if not self._prepare_module_viewport_load():
            return None

        restored_instance = self._try_restore_persistent_module(module_name)
        if restored_instance is not None:
            return restored_instance

        module_container = self._create_module_container_for_active_viewport(module_name=module_name)
        module_instance = self._instantiate_module_in_container(module_name, module_container)
        if module_instance is None:
            return None
        return self._finalize_loaded_module(module_name, module_instance, module_container)

    def _launch_module_in_external_shell_surface(self, module_name, restart=False):
        open_or_raise = getattr(self.view, "open_or_raise_module", None)
        if not callable(open_or_raise):
            return False

        launch_result = open_or_raise(module_name, restart=restart)
        return launch_result is not False

    def _finalize_external_module_load(self, module_name):
        self._set_active_module(module_name, None, None)
        self._refresh_active_module_ui(module_name)
        return None

    def _load_module_in_qt_sidecar_fallback(self, module_name):
        if not self._prepare_module_viewport_load():
            return None
        if not self._launch_module_in_external_shell_surface(module_name, restart=False):
            return None
        return self._finalize_external_module_load(module_name)

    def should_use_qt_in_viewport(self, module_name):
        return self.active_shell_backend == "pyqt6" and str(module_name or "").strip() in QT_IN_VIEWPORT_PILOT_MODULES

    def _instantiate_module_in_container(self, module_name, module_container):
        if module_name == "layout_manager" and self.layout_manager_dispatcher is not None:
            return self.layout_manager_dispatcher.launch(module_container)

        module = self.import_managed_module(module_name, force_fresh=False)
        if hasattr(module, "get_ui"):
            return module.get_ui(module_container, self)
        return None

    def _finalize_loaded_module(self, module_name, module_instance, module_container):
        self._set_active_module(module_name, module_instance, module_container)
        if self.is_module_persistent(module_name):
            self._register_persistent_module_session(module_name, module_instance, module_container)
        self._refresh_active_module_ui(module_name)
        return module_instance

    def _load_module_in_tk_viewport(self, module_name):
        return self._load_module_in_shared_viewport(module_name)

    def _load_module_in_qt_viewport(self, module_name):
        if self.should_use_qt_in_viewport(module_name):
            return self._load_module_in_shared_viewport(module_name)
        return self._load_module_in_qt_sidecar_fallback(module_name)

    def _load_module_in_active_viewport(self, module_name):
        if self.active_shell_backend == "pyqt6":
            return self._load_module_in_qt_viewport(module_name)
        return self._load_module_in_tk_viewport(module_name)

    def load_module(self, module_name, use_transition=True, ensure_authorized=True):
        # Tk widget creation stays on the UI thread; worker threads may only enqueue load requests.
        if not self._is_main_thread():
            return self._enqueue_on_main_thread(
                lambda: self.load_module(
                    module_name,
                    use_transition=use_transition,
                    ensure_authorized=ensure_authorized,
                )
            )

        if ensure_authorized and self.security.requires_authentication(module_name):
            try:
                success = self.security.authenticate_module(
                    module_name,
                    parent=self.root,
                    reason=f"Unlock {self.get_module_display_name(module_name)} to continue.",
                )
                if success is False:
                    self.refresh_navigation()
                    return
                self.refresh_navigation()
            except Exception as exc:
                log_exception(f"load_module.auth.{module_name}", exc)
                self.host_ui_adapter.show_error("Security Error", f"Auth failed: {exc}")
                return

        def perform_load():
            return self._load_module_in_active_viewport(module_name)

        try:
            if use_transition and self.active_module_name is not None:
                self._run_window_transition(perform_load)
            else:
                perform_load()
        except Exception as exc:
            log_exception(f"load_module.{module_name}", exc)
            if self.active_shell_backend == "pyqt6":
                placeholder = getattr(self.view, "show_viewport_placeholder", None)
                if callable(placeholder):
                    placeholder(
                        title=f"Failed to Load {self.get_module_display_name(module_name)}",
                        message=f"The dispatcher hit an exception while loading {module_name} into the PyQt6 shell.",
                        hint=str(exc),
                    )
                self.host_ui_adapter.show_error("Module Load Error", f"Could not load {module_name}: {exc}")
                return
            tb.Label(self.content_area, text=f"Error loading {module_name}: {exc}", bootstyle=DANGER).pack(pady=20)

    def open_module_window(self, module_name, title=None, geometry=None, minsize=None):
        top_window = self.host_ui_adapter.create_module_window(title=title, geometry=geometry, minsize=minsize)
        if top_window is None:
            self.host_ui_adapter.show_warning(
                "Module Window Unsupported",
                f"Standalone module windows are not available for active backend '{self.active_shell_backend}'.",
            )
            return None

        try:
            module = self.import_managed_module(module_name, force_fresh=False, track_loaded=False)
            if not hasattr(module, "get_ui"):
                raise AttributeError(f"Module '{module_name}' does not expose get_ui(parent, dispatcher).")
            module.get_ui(top_window, self)
        except Exception as exc:
            log_exception(f"open_module_window.{module_name}", exc)
            self.host_ui_adapter.destroy_module_window(top_window)
            self.host_ui_adapter.show_error("Module Window Error", f"Could not open {module_name}: {exc}")
            return None
        return top_window

    def open_help_document(self, relative_path):
        try:
            candidate = local_or_resource_path(relative_path)
            if os.path.exists(candidate):
                if hasattr(os, "startfile"):
                    os.startfile(candidate)
                else:
                    webbrowser.open(f"file://{candidate}")
                return
            raise FileNotFoundError(relative_path)
        except Exception as exc:
            self.host_ui_adapter.show_error("Help Document Error", f"Could not open help document: {exc}")

    def send_module_runtime_command(self, module_name, action, payload=None, restart=False):
        if self.active_shell_backend != "pyqt6":
            return False

        open_or_raise = getattr(self.view, "open_or_raise_module", None)
        runtime_managers = getattr(self.view, "runtime_managers", None)
        is_dispatcher_viewport_module = getattr(self.view, "_is_dispatcher_viewport_module", None)
        if not callable(open_or_raise) or not isinstance(runtime_managers, dict):
            return False
        if callable(is_dispatcher_viewport_module) and is_dispatcher_viewport_module(module_name):
            return False

        if open_or_raise(module_name, restart=bool(restart)) is False:
            return False

        manager = runtime_managers.get(module_name)
        if manager is None:
            return False

        command_payload = dict(payload or {}) if isinstance(payload, dict) else None
        manager.send_command(action, command_payload)
        return True

    def open_production_log_draft(self, draft_path):
        draft_path = str(draft_path or "").strip()
        if not draft_path:
            self.host_ui_adapter.show_warning("Production Log", "No draft path was provided.")
            return False

        if self.active_shell_backend == "pyqt6" and not self.should_use_qt_in_viewport("production_log"):
            self.load_module("production_log", use_transition=False, ensure_authorized=False)
            if self.send_module_runtime_command(
                "production_log",
                "load_draft_path",
                {"draft_path": draft_path},
                restart=False,
            ):
                return True
            self.host_ui_adapter.show_warning(
                "Production Log",
                "Could not open the Production Log runtime for the requested draft.",
            )
            return False

        self.load_module("production_log", use_transition=False, ensure_authorized=False)
        active_module = self.active_module_instance
        if active_module is not None and hasattr(active_module, "load_draft_path"):
            return bool(active_module.load_draft_path(draft_path))

        self.host_ui_adapter.show_warning(
            "Production Log",
            "The active Production Log session could not accept the requested draft.",
        )
        return False

    def load_runtime_settings(self):
        valid_navigation_modules = self.get_user_facing_modules(apply_whitelist=False)
        valid_persistent_modules = [module_name for _display_name, module_name in self.get_persistable_modules()]
        return self.model.load_runtime_settings(valid_navigation_modules, valid_persistent_modules)

    def refresh_runtime_settings(self):
        self.runtime_settings = self.load_runtime_settings()
        self._refresh_shell_backend_state()
        self._switch_active_host_ui_adapter()
        self._configure_module_import_paths()
        self.refresh_animation_settings()
        self.prune_persistent_module_instances()
        self._load_modules_list()
        for listener in list(self.runtime_settings_listeners):
            try:
                listener(self.runtime_settings)
            except Exception as exc:
                log_exception("dispatcher.refresh_runtime_settings.listener", exc)
        return self.runtime_settings

    def get_active_form_info(self):
        return dict(self.active_form_info or {})

    def register_active_form_listener(self, listener):
        if callable(listener) and listener not in self.active_form_listeners:
            self.active_form_listeners.append(listener)

    def unregister_active_form_listener(self, listener):
        if listener in self.active_form_listeners:
            self.active_form_listeners.remove(listener)

    def register_runtime_settings_listener(self, listener):
        if listener not in self.runtime_settings_listeners:
            self.runtime_settings_listeners.append(listener)

    def unregister_runtime_settings_listener(self, listener):
        if listener in self.runtime_settings_listeners:
            self.runtime_settings_listeners.remove(listener)

    def refresh_animation_settings(self):
        self.model.transitions_enabled = bool(self.runtime_settings.get("enable_screen_transitions", True))
        try:
            duration = int(self.runtime_settings.get("screen_transition_duration_ms", 360))
        except Exception:
            duration = 360
        self.model.transition_duration_ms = max(0, min(duration, 500))

    def get_setting(self, key, default=None):
        return self.runtime_settings.get(key, default)

    def _get_session_container(self, session):
        if not isinstance(session, dict):
            return None
        return session.get("container") or session.get("frame")

    def _store_session_container(self, session, container):
        if not isinstance(session, dict):
            return session
        session["container"] = container
        session["frame"] = container
        return session

    def _module_container_exists(self, container):
        return bool(self.host_ui_adapter.container_exists(container))

    def _hide_module_container(self, container):
        self.host_ui_adapter.hide_module_container(container)

    def _show_module_container(self, container):
        self.host_ui_adapter.show_module_container(container)

    def _destroy_module_container(self, container):
        self.host_ui_adapter.destroy_module_container(container)

    def _create_module_container(self):
        return self.host_ui_adapter.create_module_container(self.content_area)

    def _reset_shell_viewport_position(self):
        self.host_ui_adapter.reset_shell_viewport_position()

    def _register_persistent_module_session(self, module_name, module_instance, container):
        session = {
            "instance": module_instance,
            "generation": self.model.managed_source_generation,
        }
        self._store_session_container(session, container)
        self.persistent_module_instances[module_name] = session

    def _resolve_active_form_info(self, source_instance=None, active_form_info=None, form_id=None):
        resolved = dict(active_form_info) if isinstance(active_form_info, dict) else {}

        if not resolved:
            for candidate in (source_instance, getattr(source_instance, "model", None)):
                if candidate is None:
                    continue
                getter = getattr(candidate, "get_active_form_info", None)
                if not callable(getter):
                    continue
                try:
                    candidate_info = getter()
                except Exception as exc:
                    log_exception("dispatcher.resolve_active_form_info", exc)
                    continue
                if isinstance(candidate_info, dict):
                    resolved = dict(candidate_info)
                    break

        normalized_form_id = str(form_id).strip() if form_id is not None and str(form_id).strip() else None
        if normalized_form_id is not None:
            resolved["id"] = normalized_form_id

        if resolved:
            self.active_form_info = resolved
            return dict(self.active_form_info)

        cached = self.active_form_info
        if isinstance(cached, dict) and cached:
            fallback = dict(cached)
            if normalized_form_id is not None:
                fallback["id"] = normalized_form_id
            return fallback

        if normalized_form_id is not None:
            return {"id": normalized_form_id}
        return {}

    def _call_with_active_form_payload(self, callback, active_form_info):
        if not callable(callback):
            return None

        payload = dict(active_form_info or {})
        raw_form_id = payload.get("id")
        form_id = str(raw_form_id).strip() if raw_form_id is not None and str(raw_form_id).strip() else None

        try:
            signature = inspect.signature(callback)
        except (TypeError, ValueError):
            return callback()

        parameters = list(signature.parameters.values())
        accepts_var_keyword = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters)
        named_parameters = [
            parameter
            for parameter in parameters
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ]

        if not named_parameters and not accepts_var_keyword:
            return callback()

        args = []
        kwargs = {}
        parameter_names = [parameter.name for parameter in named_parameters]

        if accepts_var_keyword or "active_form_info" in parameter_names:
            kwargs["active_form_info"] = payload
        elif "form_info" in parameter_names:
            kwargs["form_info"] = payload
        elif named_parameters and named_parameters[0].kind != inspect.Parameter.KEYWORD_ONLY and parameter_names[0] != "form_id":
            args.append(payload)

        if form_id is not None:
            if accepts_var_keyword or "form_id" in parameter_names:
                kwargs["form_id"] = form_id
            elif len(named_parameters) > len(args) and named_parameters[len(args)].kind != inspect.Parameter.KEYWORD_ONLY:
                args.append(form_id)

        return callback(*args, **kwargs)

    def _refresh_shell_backend_state(self):
        self.requested_shell_backend = self.get_ui_shell_backend()
        active_backend = str(self.runtime_settings.get("active_ui_shell_backend", "") or "").strip().lower()
        if active_backend not in {"tk", "pyqt6"}:
            active_backend = "tk"
        self.active_shell_backend = active_backend

        fallback_reason = self.runtime_settings.get("ui_shell_backend_fallback_reason")
        if isinstance(fallback_reason, str) and fallback_reason.strip():
            self.shell_backend_fallback_reason = fallback_reason.strip()
            return

        if self.requested_shell_backend != self.active_shell_backend:
            self.shell_backend_fallback_reason = (
                f"Requested shell backend '{self.requested_shell_backend}' is not available in this build; using '{self.active_shell_backend}'."
            )
            return

        self.shell_backend_fallback_reason = None

    def _switch_active_host_ui_adapter(self):
        if callable(self.host_ui_adapter_factory):
            adapter = self.host_ui_adapter_factory(self.active_shell_backend, self)
            if adapter is not None:
                self.host_ui_adapter = adapter
                self.model.window_alpha_supported = bool(self.host_ui_adapter.supports_window_transition())
                return

        if self.active_shell_backend == "tk":
            self.host_ui_adapter = TkHostUiAdapter(self, toast_factory=ToastNotification)
            self.model.window_alpha_supported = bool(self.host_ui_adapter.supports_window_transition())
            return

        if self.active_shell_backend != "tk" and self.shell_backend_fallback_reason is None:
            self.shell_backend_fallback_reason = (
                f"Host adapter for backend '{self.active_shell_backend}' is not available in Dispatcher; using 'tk'."
            )
        self.host_ui_adapter = TkHostUiAdapter(self, toast_factory=ToastNotification)
        self.model.window_alpha_supported = bool(self.host_ui_adapter.supports_window_transition())

    def get_ui_shell_backend(self):
        backend = str(self.runtime_settings.get("ui_shell_backend", "pyqt6") or "pyqt6").strip().lower()
        return backend if backend in {"tk", "pyqt6"} else "pyqt6"

    def is_pyqt6_shell_requested(self):
        return self.get_ui_shell_backend() == "pyqt6"

    def get_active_shell_backend(self):
        return self.active_shell_backend

    def get_shell_backend_fallback_reason(self):
        return self.shell_backend_fallback_reason

    def _has_explicit_module_update_notification_setting(self):
        return bool(self.runtime_settings.get("_module_update_notifications_explicit", False))

    def check_for_available_module_updates(self, force=False):
        if self.module_update_check_in_progress:
            return
        if not force:
            if self._has_explicit_module_update_notification_setting():
                if not bool(self.get_setting("enable_module_update_notifications", True)):
                    return
            elif not bool(self.get_setting("enable_module_update_notifications", True)):
                return

        self.module_update_check_in_progress = True

        def worker():
            try:
                managed_update_module_path = self._resolve_managed_module_path("update_manager")
                update_manager_module = self.loaded_modules.get("update_manager") or sys.modules.get(managed_update_module_path)
                if update_manager_module is None:
                    update_manager_module = importlib.import_module(managed_update_module_path)

                scan_callable = getattr(update_manager_module, "scan_available_module_payload_updates", None)
                if callable(scan_callable):
                    scan_result = scan_callable(self)
                else:
                    from app.models.update_manager_model import UpdateManagerModel

                    scan_result = UpdateManagerModel(
                        data_registry=getattr(self, "external_data_registry", None)
                    ).scan_available_module_payload_updates(self)
            except Exception as exc:
                self.run_on_main_thread(lambda error=exc: self._finish_module_update_check(error=error))
                return

            self.run_on_main_thread(lambda result=scan_result: self._finish_module_update_check(result=result))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_module_update_check(self, result=None, error=None):
        self.module_update_check_in_progress = False
        if error is not None:
            log_exception("dispatcher.check_for_available_module_updates", error)
            return
        if not result:
            return

        available_results = result.get("available_results", [])
        if not available_results:
            return

        signature = tuple(sorted(item["option"].get("relative_path", "") for item in available_results))
        if signature == self.last_module_update_notification_signature:
            return
        self.last_module_update_notification_signature = signature

        available_names = []
        for item in available_results:
            label = item.get("module_name") or item["option"].get("module_name") or item["option"].get("fallback_name")
            if label and label not in available_names:
                available_names.append(label)

        preview = ", ".join(available_names[:3])
        if len(available_names) > 3:
            preview = f"{preview}, and {len(available_names) - 3} more"

        if len(available_results) == 1:
            message = f"A module payload update is available for {preview}. Open Update Manager to review or install it."
        else:
            message = f"{len(available_results)} module payload updates are available: {preview}. Open Update Manager to review or install them all."

        self.show_toast("Update Manager", message, INFO)

    def get_mousewheel_units(self, event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        if getattr(event, "delta", 0):
            return int(-1 * (event.delta / 120))
        return 0

    def bind_mousewheel_to_widget_tree(self, root_widget, scroll_target, axis="y"):
        return self.host_ui_adapter.bind_mousewheel_to_widget_tree(root_widget, scroll_target, axis=axis)

    def _normalize_bootstyle(self, style_value):
        if isinstance(style_value, str):
            normalized = style_value.strip().lower()
            if normalized in SEVERITY_TO_BOOTSTYLE:
                return SEVERITY_TO_BOOTSTYLE[normalized]
        return style_value

    def show_toast(self, title, message, bootstyle=INFO, duration_ms=None):
        return self.host_ui_adapter.show_toast(title, message, bootstyle=bootstyle, duration_ms=duration_ms)

    def notify_user(self, title, message, severity="info", duration_ms=None):
        self.show_toast(title, message, bootstyle=severity, duration_ms=duration_ms)

    def refresh_update_status_visibility(self):
        return self.host_ui_adapter.refresh_update_status_visibility()

    def _cancel_scheduled_update_status_clear(self):
        if self._update_status_clear_after_id is None:
            return
        self.host_ui_adapter.cancel_call_later(self._update_status_clear_after_id)
        self._update_status_clear_after_id = None

    def set_update_status(self, message, bootstyle=INFO, active=True, mode=None):
        self._cancel_scheduled_update_status_clear()
        resolved_bootstyle = self._normalize_bootstyle(bootstyle)
        self.update_coordinator.set_banner(message, bootstyle=resolved_bootstyle, active=active, mode=mode)
        self.refresh_update_status_visibility()

    def set_status_banner(self, message, severity="info", active=True, mode=None):
        self.set_update_status(message, bootstyle=severity, active=active, mode=mode)

    def clear_update_status(self):
        self._cancel_scheduled_update_status_clear()
        self.update_coordinator.clear_banner()
        self.refresh_update_status_visibility()

    def clear_update_status_after(self, delay_ms):
        self._cancel_scheduled_update_status_clear()
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        if delay_ms <= 0:
            self.clear_update_status()
            return

        def clear_if_alive():
            self._update_status_clear_after_id = None
            try:
                if not self.root.winfo_exists():
                    return
            except Exception:
                return
            self.update_coordinator.clear_banner()
            self.refresh_update_status_visibility()

        self._update_status_clear_after_id = self.call_later(delay_ms, clear_if_alive)

    def prompt_old_executable_cleanup(self):
        obsolete_executables = self.model.get_obsolete_local_executables(os.path.abspath(sys.executable), self.dispatcher_version)
        if not obsolete_executables:
            return

        file_list = "\n".join(f"- {entry['name']}" for entry in obsolete_executables)
        if not self.host_ui_adapter.ask_yes_no(
            "Remove Older Versions",
            (
                "Older local EXE versions were found next to the current build:\n\n"
                f"{file_list}\n\n"
                "Remove them now?"
            ),
        ):
            return

        removed, failed = self.model.remove_obsolete_local_executables(obsolete_executables)

        if removed:
            self.show_toast("Cleanup Complete", f"Removed {len(removed)} older EXE file(s).", SUCCESS)
        if failed:
            failure_list = "\n".join(f"- {name}" for name in failed)
            self.host_ui_adapter.show_warning(
                "Cleanup Incomplete",
                f"These EXE files could not be removed:\n\n{failure_list}",
            )

    def apply_theme(self, theme_name, redraw=False):
        normalized_theme = normalize_theme(theme_name)
        if self.active_shell_backend == "tk":
            style = tb.Style.get_instance() or tb.Style()
            style.theme_use(resolve_base_theme(normalized_theme))
            apply_readability_overrides(self.root, normalized_theme)
        view_apply_theme = getattr(self.view, "apply_theme", None)
        if callable(view_apply_theme):
            try:
                view_apply_theme(normalized_theme)
            except TypeError:
                view_apply_theme()
        if hasattr(self.active_module_instance, "apply_theme"):
            self.active_module_instance.apply_theme()
        update_idletasks = getattr(self.root, "update_idletasks", None)
        if callable(update_idletasks):
            update_idletasks()
        return normalized_theme

    def _bind_mousewheel(self):
        if getattr(self, "canvas", None) is None:
            return
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_horizontal_mousewheel)

    def _on_mousewheel(self, event):
        step = self.get_mousewheel_units(event)
        if step:
            self.canvas.yview_scroll(step, "units")

    def _on_horizontal_mousewheel(self, event):
        step = self.get_mousewheel_units(event)
        if step:
            self.canvas.xview_scroll(step, "units")