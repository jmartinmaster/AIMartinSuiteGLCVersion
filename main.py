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
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from modules.theme_manager import apply_readability_overrides, normalize_theme, DEFAULT_THEME

__module_name__ = "Dispatcher Core"
__version__ = "1.0.6"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class Dispatcher:
    def __init__(self, root):
        self.root = root
        self.root.title(f"The Martin Suite - {__version__}")
        self.root.geometry("1000x600")
        
        if getattr(sys, 'frozen', False):
            self.internal_base = sys._MEIPASS
            self.external_base = os.path.dirname(sys.executable)
        else:
            self.internal_base = os.path.abspath(".")
            self.external_base = os.path.abspath(".")

        self.modules_path = resource_path("modules")

        ext_layout = os.path.join(self.external_base, "layout_config.json")
        self.layout_config = ext_layout if os.path.exists(ext_layout) else resource_path("layout_config.json")
        
        ext_rate = os.path.join(self.external_base, "rate.json")
        self.rate_config = ext_rate if os.path.exists(ext_rate) else resource_path("rate.json")

        base_dir = os.path.dirname(self.modules_path)
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)

        self.shared_data = {}
        self.loaded_modules = {"main": sys.modules[__name__]}
        self.active_module_instance = None
        self.active_module_name = None

        self._setup_ui()
        self._setup_menu()
        self.pre_load_manifest()
        self._load_modules_list()
        self._bind_mousewheel()

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
            from ttkbootstrap.dialogs import Messagebox
            Messagebox.show_warning("Save action is not supported on this page.", "Action Unavailable")

    def menu_export(self, event=None):
        if hasattr(self.active_module_instance, 'export_to_excel'):
            self.active_module_instance.export_to_excel()
        else:
            from ttkbootstrap.dialogs import Messagebox
            Messagebox.show_warning("Export action is not supported on this page.", "Action Unavailable")
            
    def menu_import(self, event=None):
        self.load_module("production_log")
        if hasattr(self.active_module_instance, 'import_from_excel_ui'):
            self.active_module_instance.import_from_excel_ui()

    def pre_load_manifest(self):
        module_list = ["production_log", "layout_manager", "data_handler", "about", "settings_manager", "theme_manager", "help_viewer", "update_manager"]
        for mod_name in module_list:
            try:
                full_path = f"modules.{mod_name}"
                if mod_name not in self.loaded_modules:
                    self.loaded_modules[mod_name] = importlib.import_module(full_path)
            except Exception as e:
                pass

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

        for filename in sorted(os.listdir(self.modules_path)):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                if module_name in ["about", "data_handler", "splash", "example_modules", "theme_manager", "help_viewer"]: continue 
                display_name = module_name.replace("_", " ").title()
                
                tb.Button(self.nav_container, text=display_name,
                          bootstyle="link-light", 
                          command=lambda m=module_name: self.load_module(m)).pack(fill=X, padx=5, pady=2)

    def load_module(self, module_name):
        try:
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
                
        except Exception as e:
            print(f"LOAD ERROR: {e}")
            tb.Label(self.content_area, text=f"Error loading {module_name}: {e}", bootstyle=DANGER).pack(pady=20)

    def open_help_document(self, relative_path):
        try:
            if getattr(sys, 'frozen', False):
                internal_root = sys._MEIPASS
                external_root = os.path.dirname(sys.executable)
            else:
                internal_root = os.path.abspath(".")
                external_root = os.path.abspath(".")

            candidate_paths = [
                os.path.join(external_root, relative_path),
                os.path.join(internal_root, relative_path),
            ]
            for candidate in candidate_paths:
                if os.path.exists(candidate):
                    os.startfile(candidate)
                    return

            raise FileNotFoundError(relative_path)
        except Exception as e:
            messagebox.showerror("Help Document Error", f"Could not open help document: {e}")

    def apply_theme(self, theme_name, redraw=False):
        normalized_theme = normalize_theme(theme_name)
        style = tb.Style.get_instance() or tb.Style()
        style.theme_use(normalized_theme)
        apply_readability_overrides(self.root)
        self.root.update_idletasks()

        if redraw and self.active_module_name:
            active_module_name = self.active_module_name
            self.active_module_instance = None
            self.load_module(active_module_name)

        return normalized_theme

    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            # Handle Windows delta
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

if __name__ == "__main__":
    settings_path = os.path.abspath("settings.json")
    theme_name = DEFAULT_THEME
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                theme_name = normalize_theme(json.load(f).get("theme", DEFAULT_THEME))
        except: pass
    
    app_root = tb.Window(themename=theme_name)
    apply_readability_overrides(app_root)
    from modules.splash import show_splash_screen
    show_splash_screen(app_root, duration=5000)
        
    app = Dispatcher(app_root)
    app_root.mainloop()
