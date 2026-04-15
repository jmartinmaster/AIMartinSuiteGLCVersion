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
import argparse
import json
import os
import signal
import sys

import ttkbootstrap as tb

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    PYQT6_LAUNCHER_SUPPORT = True
except ImportError:
    QApplication = None
    Qt = None
    PYQT6_LAUNCHER_SUPPORT = False

from app.app_logging import log_exception
from app.external_data_registry import ExternalDataRegistry
from app.module_registry import get_launcher_module_names
from app.theme_manager import (
    DEFAULT_THEME,
    apply_readability_overrides,
    get_qt_palette,
    get_qt_stylesheet,
    normalize_theme,
    resolve_base_theme,
)
from app.utils import resource_path
from app.controllers.app_controller import Dispatcher
from app.app_platform import SPLASH_LOGO_RELATIVE_PATH, apply_app_icon, apply_windows_app_id, apply_windows_window_icons

__module_name__ = "Dispatcher Core"
__version__ = "2.2.0"
LAYOUT_MANAGER_QT_SESSION_ENV = "AIMARTIN_LAYOUT_MANAGER_QT_SESSION"
QT_MODULE_SESSION_ENV = "AIMARTIN_QT_MODULE_SESSION"


class _SigintCoordinator:
    def __init__(self, root, dispatcher):
        self.root = root
        self.dispatcher = dispatcher
        self.sigint_count = 0
        self.pending_sigint = False
        self.graceful_shutdown_requested = False
        self._poll_after_id = None

    def handle_signal(self, _signum, _frame):
        self.sigint_count += 1
        self.pending_sigint = True
        if self.sigint_count == 1:
            sys.stderr.write("Ctrl+C received. Requesting graceful shutdown...\n")
            sys.stderr.flush()
            return
        sys.stderr.write("Second Ctrl+C received. Forcing exit.\n")
        sys.stderr.flush()

    def start(self):
        self._schedule_poll()

    def stop(self):
        if self._poll_after_id is None:
            return
        try:
            self.root.after_cancel(self._poll_after_id)
        except Exception:
            pass
        self._poll_after_id = None

    def _schedule_poll(self):
        try:
            self._poll_after_id = self.root.after(100, self._poll)
        except Exception:
            self._poll_after_id = None

    def _poll(self):
        self._poll_after_id = None
        if self.pending_sigint:
            self.pending_sigint = False
            if not self.graceful_shutdown_requested:
                self.graceful_shutdown_requested = True
                try:
                    self.dispatcher.shutdown()
                except Exception as exc:
                    log_exception("launcher.sigint_shutdown", exc)
                    os._exit(130)
            else:
                os._exit(130)
        self._schedule_poll()


def create_qt_application(theme_name=None, theme_tokens=None):
    if not PYQT6_LAUNCHER_SUPPORT:
        raise RuntimeError("PyQt6 is not installed in the active Python environment.")

    application = QApplication.instance()
    if application is None:
        try:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except AttributeError:
            pass
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except AttributeError:
            pass
        application = QApplication([sys.argv[0]])

    application.setStyleSheet(get_qt_stylesheet(theme_name=theme_name, theme_tokens=theme_tokens))
    application.setPalette(get_qt_palette(theme_name=theme_name, theme_tokens=theme_tokens))
    return application


def _load_qt_module_session_payload(session_path):
    with open(session_path, "r", encoding="utf-8") as session_file:
        payload = json.load(session_file)
    if not isinstance(payload, dict):
        raise ValueError("Qt module session payload must be a JSON object.")
    return payload


def _run_qt_module_session_from_payload(session_path, session_payload):
    module_name = str(session_payload.get("module") or "").strip()
    if not module_name:
        raise ValueError("Qt module session payload is missing the 'module' key.")

    if module_name == "about":
        from app.views.about_qt_view import run_about_qt_session

        return run_about_qt_session(session_path)

    if module_name == "help_viewer":
        from app.views.help_viewer_qt_view import run_help_viewer_qt_session

        return run_help_viewer_qt_session(session_path)

    if module_name == "recovery_viewer":
        from app.views.recovery_viewer_qt_view import run_recovery_viewer_qt_session

        return run_recovery_viewer_qt_session(session_path)

    if module_name == "layout_manager":
        from app.views.layout_manager_qt_view import run_layout_manager_qt_session

        return run_layout_manager_qt_session(session_path)

    if module_name == "rate_manager":
        from app.views.rate_manager_qt_view import run_rate_manager_qt_session

        return run_rate_manager_qt_session(session_path)

    if module_name == "production_log_calculations":
        from app.views.production_log_calculations_qt_view import run_production_log_calculations_qt_session

        return run_production_log_calculations_qt_session(session_path)

    if module_name == "production_log":
        from app.views.production_log_qt_view import run_production_log_qt_session

        return run_production_log_qt_session(session_path)

    if module_name == "internal_code_editor":
        from app.views.internal_code_editor_qt_view import run_internal_code_editor_qt_session

        return run_internal_code_editor_qt_session(session_path)

    if module_name == "settings_manager":
        from app.views.settings_manager_qt_view import run_settings_manager_qt_session

        return run_settings_manager_qt_session(session_path)

    if module_name == "developer_admin":
        from app.views.developer_admin_qt_view import run_developer_admin_qt_session

        return run_developer_admin_qt_session(session_path)

    if module_name == "security_admin":
        from app.views.security_admin_qt_view import run_security_admin_qt_session

        return run_security_admin_qt_session(session_path)

    if module_name == "update_manager":
        from app.views.update_manager_qt_view import run_update_manager_qt_session

        return run_update_manager_qt_session(session_path)

    raise ValueError(f"Unsupported Qt module session: {module_name}")


def run_application(main_module=None, initial_module_name=None):
    data_registry = ExternalDataRegistry()
    settings_path = data_registry.resolve_read_path("settings")
    theme_name = DEFAULT_THEME
    ui_shell_backend = "pyqt6"
    runtime_settings = {"ui_shell_backend": ui_shell_backend}
    if main_module is None:
        import sys

        main_module = sys.modules.get("main") or sys.modules.get("__main__") or sys.modules.get(__name__)

    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                settings_payload = json.load(handle)
                if isinstance(settings_payload, dict):
                    runtime_settings = dict(settings_payload)
                    theme_name = normalize_theme(settings_payload.get("theme", DEFAULT_THEME))
                    ui_shell_backend = str(settings_payload.get("ui_shell_backend", "pyqt6") or "pyqt6").strip().lower()
        except Exception as exc:
            log_exception("main.__main__.load_theme", exc)

    if ui_shell_backend not in {"tk", "pyqt6"}:
        ui_shell_backend = "pyqt6"

    if ui_shell_backend == "pyqt6" and PYQT6_LAUNCHER_SUPPORT:
        from app.views.pyqt6_host_shell_view import PyQt6HostShellView

        apply_windows_app_id()
        application = create_qt_application(theme_name=theme_name)
        host_shell = PyQt6HostShellView(
            theme_name=theme_name,
            runtime_settings=runtime_settings,
            initial_module_name=initial_module_name,
        )
        host_shell.show()
        return application.exec()

    apply_windows_app_id()
    app_root = tb.Window(themename=resolve_base_theme(theme_name))
    apply_readability_overrides(app_root, theme_name)
    apply_app_icon(app_root)
    apply_windows_window_icons(app_root)

    from app.splash import show_splash_screen

    show_splash_screen(app_root, duration=5000, logo_path=resource_path(SPLASH_LOGO_RELATIVE_PATH))
    dispatcher = Dispatcher(app_root, main_module=main_module, initial_module_name=initial_module_name)

    previous_sigint_handler = None
    sigint_coordinator = None
    try:
        previous_sigint_handler = signal.getsignal(signal.SIGINT)
        sigint_coordinator = _SigintCoordinator(app_root, dispatcher)
        signal.signal(signal.SIGINT, sigint_coordinator.handle_signal)
        sigint_coordinator.start()
    except (AttributeError, ValueError) as exc:
        log_exception("launcher.sigint_setup", exc)
        previous_sigint_handler = None
        sigint_coordinator = None

    try:
        app_root.mainloop()
    finally:
        if sigint_coordinator is not None:
            sigint_coordinator.stop()
        if previous_sigint_handler is not None:
            try:
                signal.signal(signal.SIGINT, previous_sigint_handler)
            except (AttributeError, ValueError):
                pass


def run_special_mode_from_environment():
    session_path = os.environ.get(QT_MODULE_SESSION_ENV, "").strip()
    if session_path:
        session_payload = _load_qt_module_session_payload(session_path)
        return _run_qt_module_session_from_payload(session_path, session_payload)

    session_path = os.environ.get(LAYOUT_MANAGER_QT_SESSION_ENV, "").strip()
    if not session_path:
        return None

    session_payload = _load_qt_module_session_payload(session_path)
    if not session_payload.get("module"):
        session_payload["module"] = "layout_manager"

    return _run_qt_module_session_from_payload(session_path, session_payload)


def build_argument_parser():
    launcher_module_names = get_launcher_module_names()
    parser = argparse.ArgumentParser(
        description="Launch Production Logging Center or open the shell focused on a specific module.",
    )
    parser.add_argument(
        "--module",
        choices=launcher_module_names,
        help="Open the application shell focused on the specified module.",
    )
    return parser


def main(argv=None):
    special_mode_exit_code = run_special_mode_from_environment()
    if special_mode_exit_code is not None:
        return special_mode_exit_code
    args = build_argument_parser().parse_args(argv)
    run_application(initial_module_name=args.module)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
