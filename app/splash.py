import os
import tkinter as tk

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, BOTTOM, INFO, SECONDARY, SUCCESS, X

from app.app_platform import apply_app_icon

__module_name__ = "Splash Screen"
__version__ = "1.1.4"


def show_splash_screen(root, duration=5000, logo_path=None):
    root.withdraw()

    splash = tb.Toplevel(root)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    apply_app_icon(splash)

    width = 520
    height = 470 if logo_path else 280

    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    frame = tb.Frame(splash, padding=(30, 24))
    frame.pack(fill=BOTH, expand=True)

    content = tb.Frame(frame)
    content.pack(fill=BOTH, expand=True)

    footer = tb.Frame(frame)
    footer.pack(fill=X, side=BOTTOM, pady=(12, 0))

    if logo_path and os.path.exists(logo_path):
        try:
            img = tk.PhotoImage(file=logo_path)
            max_logo_width = 400
            max_logo_height = 180
            width_scale = max(1, (img.width() + max_logo_width - 1) // max_logo_width)
            height_scale = max(1, (img.height() + max_logo_height - 1) // max_logo_height)
            subsample = max(width_scale, height_scale)
            if subsample > 1:
                img = img.subsample(subsample, subsample)
            splash.logo_img = img
            tb.Label(content, image=img).pack(pady=(0, 12))
        except Exception as exc:
            print(f"Error loading splash logo: {exc}")

    tb.Label(content, text="PRODUCTION LOGGING CENTER", font=("-size 24 -weight bold")).pack(pady=(8, 0))
    tb.Label(content, text="GLC Edition", font=("-size 14 -slant italic"), bootstyle=INFO).pack(pady=5)

    tb.Label(footer, text="Copyright © 2026 Jamie Martin", font=("-size 10")).pack()
    tb.Label(footer, text="Licensed under GNU GPLv3", font=("-size 9"), bootstyle=SECONDARY).pack(pady=(4, 8))

    progress = tb.Progressbar(footer, bootstyle=SUCCESS, mode="indeterminate")
    progress.pack(fill=X, pady=(6, 0), padx=20)
    progress.start(15)

    root.after(duration, lambda: (progress.stop(), splash.destroy(), root.deiconify()))