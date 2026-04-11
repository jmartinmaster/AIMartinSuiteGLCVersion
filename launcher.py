import os
import json

import ttkbootstrap as tb

from app.app_logging import log_exception
from app.theme_manager import DEFAULT_THEME, apply_readability_overrides, normalize_theme, resolve_base_theme
from app.utils import external_path, resource_path
from app.controllers.app_controller import Dispatcher
from app.app_platform import SPLASH_LOGO_RELATIVE_PATH, apply_app_icon, apply_windows_app_id, apply_windows_window_icons

__module_name__ = "Dispatcher Core"
__version__ = "2.0.4"


def run_application(main_module=None):
    settings_path = external_path("settings.json")
    theme_name = DEFAULT_THEME
    if main_module is None:
        import sys

        main_module = sys.modules.get("main") or sys.modules.get("__main__")

    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                theme_name = normalize_theme(json.load(handle).get("theme", DEFAULT_THEME))
        except Exception as exc:
            log_exception("main.__main__.load_theme", exc)

    apply_windows_app_id()
    app_root = tb.Window(themename=resolve_base_theme(theme_name))
    apply_readability_overrides(app_root, theme_name)
    apply_app_icon(app_root)
    apply_windows_window_icons(app_root)

    from app.splash import show_splash_screen

    show_splash_screen(app_root, duration=5000, logo_path=resource_path(SPLASH_LOGO_RELATIVE_PATH))
    Dispatcher(app_root, main_module=main_module)
    app_root.mainloop()