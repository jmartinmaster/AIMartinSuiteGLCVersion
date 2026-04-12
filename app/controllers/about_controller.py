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
import subprocess
import sys
from tkinter import messagebox

from app.views.about_view import AboutView

__module_name__ = "About System"
__version__ = "1.0.1"


class AboutController:
    def __init__(self, parent, dispatcher):
        self.dispatcher = dispatcher
        self.view = None
        self.view = AboutView(parent, dispatcher, self)

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def open_license(self):
        self.dispatcher.open_help_document("docs/legal/LICENSE.txt")

    def _iter_manifest_modules(self):
        loaded_modules = getattr(self.dispatcher, "loaded_modules", {}) or {}
        yielded_keys = set()

        main_module = loaded_modules.get("main")
        if main_module is not None:
            yielded_keys.add("main")
            yield "main", main_module

        preloaded_module_names = getattr(getattr(self.dispatcher, "model", None), "preloaded_module_names", set()) or set()
        ordered_module_names = []
        try:
            ordered_module_names.extend(self.dispatcher.get_user_facing_modules(apply_whitelist=False))
        except Exception:
            ordered_module_names.extend(sorted(preloaded_module_names))

        for module_name in ordered_module_names:
            if module_name in yielded_keys:
                continue
            module_obj = loaded_modules.get(module_name)
            if module_obj is None and module_name in preloaded_module_names:
                module_obj = sys.modules.get(f"app.{module_name}")
            if module_obj is None:
                continue
            yielded_keys.add(module_name)
            yield module_name, module_obj

        for module_name, module_obj in loaded_modules.items():
            if module_name in yielded_keys:
                continue
            yielded_keys.add(module_name)
            yield module_name, module_obj

    def render_module_manifest(self, parent):
        module_entries = list(self._iter_manifest_modules())
        if not module_entries:
            self.view.render_empty_manifest(parent)
            return
        for mod_key, mod_obj in module_entries:
            display_name = getattr(mod_obj, "__module_name__", mod_key)
            version = getattr(mod_obj, "__version__", "Unknown")
            source_suffix = " (external)" if self.dispatcher.is_module_loaded_from_external(mod_key, mod_obj) else ""
            self.view.render_module_row(parent, display_name, version, source_suffix)

    def can_repack(self):
        return bool(getattr(sys, "frozen", False))

    def confirm_repack(self):
        message = "This will compile a new executable with your current settings.\n\nThe app will close, build, and restart automatically.\n\nProceed?"
        if messagebox.askyesno("Confirm Repack", message):
            self.self_repack()

    def self_repack(self):
        exe_path = os.path.abspath(sys.executable)
        exe_dir = os.path.dirname(exe_path)
        python_exe = os.path.join(sys._MEIPASS, "python.exe")

        cmd = [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onefile",
            "--windowed",
            "--add-data",
            f"app{os.pathsep}app",
            "--add-data",
            f"assets{os.pathsep}assets",
            "--add-data",
            f"docs{os.pathsep}docs",
            "--add-data",
            f"templates{os.pathsep}templates",
            "--add-data",
            f"rates.json{os.pathsep}.",
            "--add-data",
            f"layout_config.json{os.pathsep}.",
            "--collect-submodules",
            "openpyxl",
            "--collect-submodules",
            "app",
            os.path.join(sys._MEIPASS, "main.py"),
        ]

        try:
            subprocess.run(cmd, check=True, cwd=exe_dir)

            new_exe = os.path.join(exe_dir, "dist", os.path.basename(exe_path))
            batch_path = os.path.join(exe_dir, "cleanup.bat")

            with open(batch_path, "w", encoding="utf-8") as handle:
                handle.write(
                    f"""
                @echo off
                timeout /t 3 /nobreak > nul
                del \"{exe_path}\"
                move \"{new_exe}\" \"{exe_path}\"
                rd /s /q \"{os.path.join(exe_dir, 'build')}\"
                rd /s /q \"{os.path.join(exe_dir, 'dist')}\"
                del \"{os.path.join(exe_dir, os.path.basename(exe_path) + '.spec')}\"
                start \"\" \"{exe_path}\"
                del \"%~f0\"
                """
                )

            os.startfile(batch_path)
            self.dispatcher.root.destroy()
            sys.exit()
        except Exception as exc:
            messagebox.showerror("Repack Error", f"Failed to repack suite:\n{exc}")
