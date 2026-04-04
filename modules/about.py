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

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import * 
from tkinter import messagebox
import subprocess
import sys
import os
import time

__module_name__ = "About System"
__version__ = "1.0.1"

class AboutSection:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.setup_ui()

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=30)
        container.pack(fill=BOTH, expand=True)

        # Header / Branding
        tb.Label(container, text="THE MARTIN SUITE", font=("-size 24 -weight bold")).pack()
        tb.Label(container, text="GLC Edition", font=("-size 14 -slant italic"), bootstyle=INFO).pack(pady=5)
        
        tb.Separator(container, orient=HORIZONTAL).pack(fill=X, pady=20)

        # Main Info
        info_text = (
            "Author: Jamie Martin\n"
            "License: GNU General Public License v3.0\n"
            "Location: Ludington, MI\n"
            "Environment: Windows / Portable Python 3.12"
        )
        tb.Label(container, text=info_text, justify=CENTER).pack(pady=10)

        tb.Button(
            container,
            text="Open License",
            bootstyle=SECONDARY,
            command=lambda: self.dispatcher.open_help_document("LICENSE.txt")
        ).pack(pady=(0, 10))

        # Module Manifest
        version_frame = tb.Labelframe(container, text=" Module Manifest ", padding=15)
        version_frame.pack(fill=X, pady=20)

        loaded = getattr(self.dispatcher, 'loaded_modules', {})

        if not loaded:
            tb.Label(version_frame, text="No active modules loaded.", bootstyle=WARNING).pack()
        else:
            for mod_key, mod_obj in loaded.items():
                row = tb.Frame(version_frame)
                row.pack(fill=X, pady=2)
                
                display_name = getattr(mod_obj, '__module_name__', mod_key)
                version = getattr(mod_obj, '__version__', "Unknown")
                
                tb.Label(row, text=display_name, font=("-weight bold")).pack(side=LEFT)
                tb.Label(row, text=f"v{version}", bootstyle=SECONDARY).pack(side=RIGHT)

        # --- REPACK UTILITY SECTION ---
        # Only show this if we are actually running as an EXE
        if getattr(sys, 'frozen', False):
            repack_frame = tb.Frame(container, padding=10)
            repack_frame.pack(fill=X, side=BOTTOM, pady=20)
            
            tb.Separator(repack_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
            
            repack_btn = tb.Button(
                repack_frame, 
                text="REPACK SUITE (Bake Changes)", 
                bootstyle="warning-outline",
                command=self.confirm_repack
            )
            repack_btn.pack(pady=10)
            
            tb.Label(
                repack_frame, 
                text="Note: This will bake current JSON/Module changes into a new EXE and restart.",
                font=("-size 8"),
                bootstyle=SECONDARY
            ).pack()

        # Footer
        tb.Label(container, text="Copyright © 2026 Jamie Martin", font=("-size 8")).pack(side=BOTTOM)

    def confirm_repack(self):
        """Ask before we blow up the current session."""
        msg = "This will compile a new executable with your current settings.\n\nThe app will close, build, and restart automatically.\n\nProceed?"
        if messagebox.askyesno("Confirm Repack", msg):
            self.self_repack()

    def self_repack(self):
        exe_path = os.path.abspath(sys.executable)
        exe_dir = os.path.dirname(exe_path)
        
        # Use the internal python.exe bundled in the _internal or temp folder
        python_exe = os.path.join(sys._MEIPASS, "python.exe")

        # Command to bake everything in
        cmd = [
            python_exe, "-m", "PyInstaller",
            "--noconfirm", "--onefile", "--windowed",
            "--add-data", f"modules{os.pathsep}modules",
            "--add-data", f"templates{os.pathsep}templates",
            "--add-data", f"layout_config.json{os.pathsep}.",
            "--add-data", f"rates.json{os.pathsep}.",
            "--collect-submodules", "openpyxl",
            os.path.join(sys._MEIPASS, "main.py") 
        ]

        try:
            # Show a simple "Wait" message would be nice, but PyInstaller takes over
            subprocess.run(cmd, check=True, cwd=exe_dir)
            
            new_exe = os.path.join(exe_dir, "dist", os.path.basename(exe_path))
            batch_path = os.path.join(exe_dir, "cleanup.bat")
            
            # The Hot-Swap Batch Script
            with open(batch_path, "w") as f:
                f.write(f"""
                @echo off
                timeout /t 3 /nobreak > nul
                del "{exe_path}"
                move "{new_exe}" "{exe_path}"
                rd /s /q "{os.path.join(exe_dir, 'build')}"
                rd /s /q "{os.path.join(exe_dir, 'dist')}"
                del "{os.path.join(exe_dir, os.path.basename(exe_path) + '.spec')}"
                start "" "{exe_path}"
                del "%~f0"
                """)

            os.startfile(batch_path)
            self.dispatcher.root.destroy() # Using dispatcher to close the main window
            sys.exit()

        except Exception as e:
            messagebox.showerror("Repack Error", f"Failed to repack suite:\n{e}")

def get_ui(parent, dispatcher):
    return AboutSection(parent, dispatcher)