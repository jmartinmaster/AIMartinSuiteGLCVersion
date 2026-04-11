import os
import subprocess
import sys
from tkinter import messagebox

from app.views.about_view import AboutView


class AboutController:
    def __init__(self, parent, dispatcher):
        self.dispatcher = dispatcher
        self.view = AboutView(parent, dispatcher, self)

    def __getattr__(self, attribute_name):
        return getattr(self.view, attribute_name)

    def open_license(self):
        self.dispatcher.open_help_document("docs/legal/LICENSE.txt")

    def render_module_manifest(self, parent):
        loaded = getattr(self.dispatcher, "loaded_modules", {})
        if not loaded:
            self.view.render_empty_manifest(parent)
            return
        for mod_key, mod_obj in loaded.items():
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
