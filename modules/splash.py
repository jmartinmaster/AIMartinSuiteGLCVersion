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
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

def show_splash_screen(root, duration=5000, logo_path=None):
    """
    Displays a borderless splash screen for the specified duration (in milliseconds),
    while keeping the main application window hidden.
    
    Please use a PNG image for the logo to ensure compatibility across platforms. TKinter's PhotoImage supports PNG natively, while formats like JPEG may require additional libraries and can cause issues in some environments. Size requirements for the logo are flexible, but a width of around 400px is recommended for optimal display on most screens. The height can be adjusted proportionally based on the original aspect ratio of the image.
    """
    # Hide the main window while the splash is active
    root.withdraw()
    
    splash = tb.Toplevel(root)
    splash.overrideredirect(True) # Removes window borders and title bar
    splash.attributes('-topmost', True) # Keep it on top of other windows
    
    width = 500
    height = 350 if logo_path else 250
    
    # Center the splash screen on the monitor
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    splash.geometry(f'{width}x{height}+{x}+{y}')
    
    frame = tb.Frame(splash, padding=30)
    frame.pack(fill=BOTH, expand=True)
    
    # Dynamically load and display a custom logo if provided
    if logo_path and os.path.exists(logo_path):
        try:
            img = tk.PhotoImage(file=logo_path)
            splash.logo_img = img # Keep a reference to prevent Python's garbage collector from deleting it
            tb.Label(frame, image=img).pack(pady=(0, 10))
        except Exception as e:
            print(f"Error loading splash logo: {e}")

    tb.Label(frame, text="THE MARTIN SUITE", font=("-size 24 -weight bold")).pack(pady=(20, 0))
    tb.Label(frame, text="GLC Edition", font=("-size 14 -slant italic"), bootstyle=INFO).pack(pady=5)
    
    tb.Label(frame, text="Copyright © 2026 Jamie Martin", font=("-size 10")).pack(pady=(20, 0))
    tb.Label(frame, text="Licensed under GNU GPLv3", font=("-size 9"), bootstyle=SECONDARY).pack(pady=5)
    
    progress = tb.Progressbar(frame, bootstyle=SUCCESS, mode="indeterminate")
    progress.pack(fill=X, pady=(20, 0), padx=20)
    progress.start(15)
    
    # Schedule the splash screen to close and reveal the main app
    root.after(duration, lambda: (progress.stop(), splash.destroy(), root.deiconify()))