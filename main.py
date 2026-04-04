# The Martin Suite (GLC Edition)
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
import sys
import importlib
import json
import ctypes
import time
import tkinter as tk
from tkinter import messagebox
from ctypes import wintypes
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToastNotification
from app_identity import LEGACY_EXE_NAME, normalize_version, parse_version, parse_versioned_exe_name
from modules.app_logging import log_exception
from modules.theme_manager import apply_readability_overrides, normalize_theme, DEFAULT_THEME
from modules.utils import external_path, local_or_resource_path, resource_path

__module_name__ = "Dispatcher Core"
__version__ = "1.2.4"
WINDOWS_APP_ID = "JamieMartin.TheMartinSuite.GLC"
APP_ICON_RELATIVE_PATH = "icon.ico"
APP_ICON_IMAGE_RELATIVE_PATHS = [
    "icon-16.png",
    "icon-24.png",
    "icon-32.png",
    "icon-48.png",
    "icon-64.png",
]
APP_ICON_SOURCE_RELATIVE_PATHS = [
    "icon.png",
    "icon.jpg",
]
SPLASH_LOGO_RELATIVE_PATH = "splash-logo.png"
WM_SETICON = 0x0080
WM_GETICON = 0x007F
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
GCLP_HICON = -14
GCLP_HICONSM = -34


def get_obsolete_local_executables(current_exe_path, current_version):
    if not getattr(sys, "frozen", False):
        return []

    current_version_parts = normalize_version(parse_version(current_version))
    if current_version_parts is None:
        return []

    current_name = os.path.basename(current_exe_path)
    current_directory = os.path.dirname(current_exe_path)
    obsolete_entries = []

    try:
        directory_entries = os.listdir(current_directory)
    except OSError:
        return []

    for file_name in directory_entries:
        if file_name.lower() == current_name.lower() or not file_name.lower().endswith(".exe"):
            continue

        file_path = os.path.join(current_directory, file_name)
        if not os.path.isfile(file_path):
            continue

        if file_name.lower() == LEGACY_EXE_NAME.lower():
            obsolete_entries.append({
                "name": file_name,
                "path": file_path,
                "version": "Legacy",
            })
            continue

        version_text = parse_versioned_exe_name(file_name)
        candidate_version = normalize_version(parse_version(version_text)) if version_text else None
        if candidate_version is None or candidate_version >= current_version_parts:
            continue

        obsolete_entries.append({
            "name": file_name,
            "path": file_path,
            "version": version_text,
        })

    return sorted(
        obsolete_entries,
        key=lambda entry: (
            0 if entry["version"] == "Legacy" else 1,
            normalize_version(parse_version(entry["version"])) or (0, 0, 0),
        ),
    )


def get_work_area_insets(root):
    right_inset = 0
    bottom_inset = 0
    if sys.platform.startswith("win"):
        try:
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                right_inset = max(0, root.winfo_screenwidth() - rect.right)
                bottom_inset = max(0, root.winfo_screenheight() - rect.bottom)
        except Exception:
            pass
    return right_inset, bottom_inset


def apply_windows_app_id():
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


def apply_windows_window_icons(root):
    if not sys.platform.startswith("win"):
        return

    icon_path = resource_path(APP_ICON_RELATIVE_PATH)
    if not os.path.exists(icon_path):
        return

    try:
        root.update_idletasks()
        hwnd = root.winfo_id()
        if not hwnd:
            return

        user32 = ctypes.windll.user32
        small_icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        big_icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE)

        if small_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
            user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, small_icon)
        if big_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big_icon)
            user32.SetClassLongPtrW(hwnd, GCLP_HICON, big_icon)

        root._windows_small_icon_handle = small_icon
        root._windows_big_icon_handle = big_icon
    except Exception as exc:
        log_exception("apply_windows_window_icons", exc)


def apply_app_icon(root):
    icon_path = resource_path(APP_ICON_RELATIVE_PATH)
    try:
        if os.path.exists(icon_path):
            root.iconbitmap(default=icon_path)
    except Exception as exc:
        log_exception("apply_app_icon.iconbitmap", exc)
    try:
        icon_images = []
        for relative_path in APP_ICON_IMAGE_RELATIVE_PATHS:
            icon_image_path = resource_path(relative_path)
            if os.path.exists(icon_image_path):
                icon_images.append(tk.PhotoImage(file=icon_image_path))
        if icon_images:
            root._app_icon_images = icon_images
            root.iconphoto(True, *icon_images)
    except Exception as exc:
        log_exception("apply_app_icon.iconphoto", exc)
    try:
        root.after_idle(lambda widget=root: apply_windows_window_icons(widget) if widget.winfo_exists() else None)
    except Exception as exc:
        log_exception("apply_app_icon.after_idle", exc)

class Dispatcher:
    def __init__(self, root):
        apply_windows_app_id()
        self.root = root
        self.root.title(f"The Martin Suite - {__version__}")
        self.root.geometry("1000x600")
        apply_app_icon(self.root)

        self.modules_path = resource_path("modules")

        self.layout_config = local_or_resource_path("layout_config.json")
        self.rate_config = local_or_resource_path("rates.json")

        base_dir = os.path.dirname(self.modules_path)
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)

        self.shared_data = {}
        self.loaded_modules = {"main": sys.modules[__name__]}
        self.active_module_instance = None
        self.active_module_name = None
        self.settings_path = external_path("settings.json")
        self.runtime_settings = self.load_runtime_settings()
        self.window_alpha_supported = self._supports_window_alpha()
        self.transition_duration_ms = 360
        self.transitions_enabled = True
        self.transition_min_alpha = 0.82
        self._transition_in_progress = False
        self.refresh_animation_settings()

        self._setup_ui()
        self._setup_menu()
        self.pre_load_manifest()
        self._load_modules_list()
        self._bind_mousewheel()
        self.load_module("production_log", use_transition=False)
        self.root.after(900, self.prompt_old_executable_cleanup)

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Draft", command=self.menu_open, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Draft", command=self.menu_save, accelerator="Ctrl+S")
        file_menu.add_command(label="Export to Excel", command=self.menu_export, accelerator="Ctrl+E")
        file_menu.add_command(label="Import Excel", command=self.menu_import, accelerator="Ctrl+I")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        self.root.bind('<Control-o>', self.menu_open)
        self.root.bind('<Control-s>', self.menu_save)
        self.root.bind('<Control-e>', self.menu_export)
        self.root.bind('<Control-i>', self.menu_import)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="User Guide", command=lambda: self.load_module("help_viewer"))
        help_menu.add_command(label="About", command=lambda: self.load_module("about"))
        menubar.add_cascade(label="Help", menu=help_menu)

    def menu_open(self, event=None):
        self.load_module("production_log")
        if hasattr(self.active_module_instance, 'show_pending'):
            self.active_module_instance.show_pending()

    def menu_save(self, event=None):
        if hasattr(self.active_module_instance, 'save_draft'):
            self.active_module_instance.save_draft()
        else:
            self.show_toast("Action Unavailable", "Save action is not supported on this page.", WARNING)

    def menu_export(self, event=None):
        if hasattr(self.active_module_instance, 'export_to_excel'):
            self.active_module_instance.export_to_excel()
        else:
            self.show_toast("Action Unavailable", "Export action is not supported on this page.", WARNING)
            
    def menu_import(self, event=None):
        self.load_module("production_log")
        if hasattr(self.active_module_instance, 'import_from_excel_ui'):
            self.active_module_instance.import_from_excel_ui()

    def pre_load_manifest(self):
        module_list = ["production_log", "layout_manager", "data_handler", "about", "settings_manager", "theme_manager", "help_viewer", "update_manager", "recovery_viewer"]
        for mod_name in module_list:
            try:
                full_path = f"modules.{mod_name}"
                if mod_name not in self.loaded_modules:
                    self.loaded_modules[mod_name] = importlib.import_module(full_path)
            except Exception as e:
                log_exception(f"pre_load_manifest.{mod_name}", e)

    def _setup_ui(self):
        self.main_container = tb.Frame(self.root)
        self.main_container.pack(fill=BOTH, expand=True)

        self.sidebar = tb.Frame(self.main_container, bootstyle=DARK, width=200)
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        tb.Label(self.sidebar, text="MARTIN SUITE", font=("Helvetica", 14, "bold"), 
                 bootstyle="inverse-dark").pack(pady=20, padx=10)

        self.nav_container = tb.Frame(self.sidebar, bootstyle=DARK)
        self.nav_container.pack(fill=BOTH, expand=True)

        self.right_container = tb.Frame(self.main_container)
        self.right_container.pack(side=RIGHT, fill=BOTH, expand=True)

        self.canvas = tk.Canvas(self.right_container, highlightthickness=0)
        self.scrollbar = tb.Scrollbar(self.right_container, orient=VERTICAL, command=self.canvas.yview)
        
        self.content_area = tb.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_area, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self.content_area.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

    def _load_modules_list(self):
        if not os.path.exists(self.modules_path):
            return

        nav_modules = []

        for filename in os.listdir(self.modules_path):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                if module_name in ["about", "app_logging", "data_handler", "downtime_codes", "example_modules", "help_viewer", "persistence", "splash", "theme_manager", "utils"]:
                    continue
                display_name = module_name.replace("_", " ").title()

                nav_modules.append((display_name, module_name))

        for display_name, module_name in sorted(nav_modules, key=lambda item: item[0].lower()):
                tb.Button(self.nav_container, text=display_name,
                          bootstyle="link-light", 
                          command=lambda m=module_name: self.load_module(m)).pack(fill=X, padx=5, pady=2)

    def _supports_window_alpha(self):
        try:
            current_alpha = float(self.root.attributes("-alpha"))
            self.root.attributes("-alpha", current_alpha)
            return True
        except Exception:
            return False

    def _set_window_alpha(self, alpha_value):
        if not self.window_alpha_supported:
            return
        try:
            self.root.attributes("-alpha", alpha_value)
        except Exception as exc:
            self.window_alpha_supported = False
            log_exception("set_window_alpha", exc)

    def _run_window_transition(self, action):
        if (
            not self.window_alpha_supported
            or not self.transitions_enabled
            or self.transition_duration_ms <= 0
            or self._transition_in_progress
        ):
            return action()

        self._transition_in_progress = True
        steps = 6
        half_duration = max(0.12, self.transition_duration_ms / 2000)
        step_delay = half_duration / steps
        alpha_values = [1.0 - ((1.0 - self.transition_min_alpha) * (index + 1) / steps) for index in range(steps)]

        try:
            for alpha_value in alpha_values:
                self._set_window_alpha(alpha_value)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(step_delay)

            result = action()

            for alpha_value in reversed(alpha_values[:-1]):
                self._set_window_alpha(alpha_value)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(step_delay)

            self._set_window_alpha(1.0)
            self.root.update_idletasks()
            return result
        finally:
            self._set_window_alpha(1.0)
            self._transition_in_progress = False

    def load_module(self, module_name, use_transition=True):
        def perform_load():
            if hasattr(self.active_module_instance, 'on_unload'):
                self.active_module_instance.on_unload()

            for child in self.content_area.winfo_children():
                child.destroy()
            
            self.canvas.yview_moveto(0)
            
            module_path = f"modules.{module_name}"
            if module_name in self.loaded_modules:
                module = importlib.reload(self.loaded_modules[module_name])
            else:
                module = importlib.import_module(module_path)
                self.loaded_modules[module_name] = module

            if hasattr(module, 'get_ui'):
                self.active_module_name = module_name
                self.active_module_instance = module.get_ui(self.content_area, self)

        try:
            if use_transition and self.active_module_name is not None:
                self._run_window_transition(perform_load)
            else:
                perform_load()
        except Exception as e:
            log_exception(f"load_module.{module_name}", e)
            tb.Label(self.content_area, text=f"Error loading {module_name}: {e}", bootstyle=DANGER).pack(pady=20)

    def open_help_document(self, relative_path):
        try:
            candidate = local_or_resource_path(relative_path)
            if os.path.exists(candidate):
                os.startfile(candidate)
                return

            raise FileNotFoundError(relative_path)
        except Exception as e:
            messagebox.showerror("Help Document Error", f"Could not open help document: {e}")

    def load_runtime_settings(self):
        settings = {
            "theme": DEFAULT_THEME,
            "enable_screen_transitions": True,
            "screen_transition_duration_ms": 360,
            "toast_duration_sec": 5,
        }
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass

        try:
            settings["toast_duration_sec"] = max(1, int(settings.get("toast_duration_sec", 5)))
        except Exception:
            settings["toast_duration_sec"] = 5
        settings["enable_screen_transitions"] = bool(settings.get("enable_screen_transitions", True))
        try:
            settings["screen_transition_duration_ms"] = max(0, min(500, int(settings.get("screen_transition_duration_ms", 360))))
        except Exception:
            settings["screen_transition_duration_ms"] = 360
        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
        return settings

    def refresh_runtime_settings(self):
        self.runtime_settings = self.load_runtime_settings()
        self.refresh_animation_settings()
        return self.runtime_settings

    def refresh_animation_settings(self):
        self.transitions_enabled = bool(self.runtime_settings.get("enable_screen_transitions", True))
        try:
            duration = int(self.runtime_settings.get("screen_transition_duration_ms", 360))
        except Exception:
            duration = 360
        self.transition_duration_ms = max(0, min(duration, 500))

    def get_setting(self, key, default=None):
        return self.runtime_settings.get(key, default)

    def get_mousewheel_units(self, event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        if getattr(event, "delta", 0):
            return int(-1 * (event.delta / 120))
        return 0

    def bind_mousewheel_to_widget_tree(self, root_widget, scroll_target, axis="y"):
        def on_mousewheel(event):
            step = self.get_mousewheel_units(event)
            if not step:
                return None
            if axis == "x":
                scroll_target.xview_scroll(step, "units")
            else:
                scroll_target.yview_scroll(step, "units")
            return "break"

        def bind_widget(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
            for child in widget.winfo_children():
                bind_widget(child)

        bind_widget(root_widget)

    def show_toast(self, title, message, bootstyle=INFO, duration_ms=None):
        duration = duration_ms
        if duration is None:
            duration = int(self.get_setting("toast_duration_sec", 5)) * 1000
        right_inset, bottom_inset = get_work_area_insets(self.root)
        toast = ToastNotification(
            title=title,
            message=message,
            duration=duration,
            bootstyle=bootstyle,
            position=(24 + right_inset, 24 + bottom_inset, "se"),
        )
        toast.show_toast()

    def prompt_old_executable_cleanup(self):
        obsolete_executables = get_obsolete_local_executables(os.path.abspath(sys.executable), __version__)
        if not obsolete_executables:
            return

        file_list = "\n".join(f"- {entry['name']}" for entry in obsolete_executables)
        if not messagebox.askyesno(
            "Remove Older Versions",
            (
                "Older local EXE versions were found next to the current build:\n\n"
                f"{file_list}\n\n"
                "Remove them now?"
            ),
        ):
            return

        removed = []
        failed = []
        for entry in obsolete_executables:
            try:
                os.remove(entry["path"])
                removed.append(entry["name"])
            except OSError:
                failed.append(entry["name"])

        if removed:
            self.show_toast("Cleanup Complete", f"Removed {len(removed)} older EXE file(s).", SUCCESS)
        if failed:
            failure_list = "\n".join(f"- {name}" for name in failed)
            messagebox.showwarning(
                "Cleanup Incomplete",
                f"These EXE files could not be removed:\n\n{failure_list}",
            )

    def apply_theme(self, theme_name, redraw=False):
        normalized_theme = normalize_theme(theme_name)
        style = tb.Style.get_instance() or tb.Style()
        style.theme_use(normalized_theme)
        apply_readability_overrides(self.root)
        self.root.update_idletasks()

        return normalized_theme

    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        step = self.get_mousewheel_units(event)
        if step:
            self.canvas.yview_scroll(step, "units")

if __name__ == "__main__":
    settings_path = external_path("settings.json")
    theme_name = DEFAULT_THEME
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                theme_name = normalize_theme(json.load(f).get("theme", DEFAULT_THEME))
        except Exception as exc:
            log_exception("main.__main__.load_theme", exc)
    
    apply_windows_app_id()
    app_root = tb.Window(themename=theme_name)
    apply_readability_overrides(app_root)
    apply_app_icon(app_root)
    from modules.splash import show_splash_screen
    show_splash_screen(app_root, duration=5000, logo_path=resource_path(SPLASH_LOGO_RELATIVE_PATH))
        
    app = Dispatcher(app_root)
    app_root.mainloop()
