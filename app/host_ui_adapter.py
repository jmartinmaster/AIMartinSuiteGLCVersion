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
from app.app_platform import get_work_area_insets
from tkinter import messagebox
import tkinter as tk

__module_name__ = "Host UI Adapter"
__version__ = "0.1.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QMessageBox

    PYQT6_ADAPTER_AVAILABLE = True
except ImportError:
    QTimer = None
    QMessageBox = None
    PYQT6_ADAPTER_AVAILABLE = False


class TkHostUiAdapter:
    def __init__(self, dispatcher, toast_factory):
        self.dispatcher = dispatcher
        self.toast_factory = toast_factory

    def call_later(self, delay_ms, callback):
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        return self.dispatcher.root.after(max(0, delay_ms), callback)

    def run_on_main_thread(self, callback):
        return self.call_later(0, callback)

    def request_shutdown(self, delay_ms=0):
        self.call_later(delay_ms, self.dispatcher.root.destroy)

    def bind_shell_viewport_resize(self, callback, add="+"):
        return self.dispatcher.canvas.bind("<Configure>", callback, add=add)

    def get_shell_viewport_size(self, min_width=0, min_height=0):
        try:
            min_width = int(min_width)
        except Exception:
            min_width = 0
        try:
            min_height = int(min_height)
        except Exception:
            min_height = 0
        width = max(self.dispatcher.canvas.winfo_width(), min_width)
        height = max(self.dispatcher.canvas.winfo_height(), min_height)
        return (width, height)

    def bind_mousewheel_to_widget_tree(self, root_widget, scroll_target, axis="y"):
        def on_mousewheel(event):
            step = self.dispatcher.get_mousewheel_units(event)
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

    def show_toast(self, title, message, bootstyle=None, duration_ms=None):
        duration = duration_ms
        if duration is None:
            duration = int(self.dispatcher.get_setting("toast_duration_sec", 5)) * 1000
        resolved_bootstyle = self.dispatcher._normalize_bootstyle(bootstyle)
        right_inset, bottom_inset = get_work_area_insets(self.dispatcher.root)
        toast = self.toast_factory(
            title=title,
            message=message,
            duration=duration,
            bootstyle=resolved_bootstyle,
            position=(24 + right_inset, 24 + bottom_inset, "se"),
        )
        toast.show_toast()

    def refresh_update_status_visibility(self):
        self.dispatcher.view.refresh_update_status_visibility()

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def show_warning(self, title, message):
        messagebox.showwarning(title, message)

    def ask_yes_no(self, title, message):
        return bool(messagebox.askyesno(title, message))

    def create_module_window(self, title=None, geometry=None, minsize=None):
        top_window = tk.Toplevel(self.dispatcher.root)
        if title:
            top_window.title(str(title))
        if geometry:
            top_window.geometry(str(geometry))
        if isinstance(minsize, (tuple, list)) and len(minsize) == 2:
            try:
                top_window.minsize(int(minsize[0]), int(minsize[1]))
            except Exception:
                pass
        return top_window

    def destroy_module_window(self, window):
        if window is None:
            return
        try:
            window.destroy()
        except Exception:
            pass


class PyQt6HostUiAdapter:
    def __init__(self, host_window):
        self.host_window = host_window

    def call_later(self, delay_ms, callback):
        if not PYQT6_ADAPTER_AVAILABLE:
            return None
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        QTimer.singleShot(max(0, delay_ms), callback)
        return None

    def run_on_main_thread(self, callback):
        return self.call_later(0, callback)

    def request_shutdown(self, delay_ms=0):
        def close_window():
            self.host_window.close()

        return self.call_later(delay_ms, close_window)

    def bind_shell_viewport_resize(self, callback, add="+"):
        _ = callback
        _ = add
        return None

    def get_shell_viewport_size(self, min_width=0, min_height=0):
        try:
            min_width = int(min_width)
        except Exception:
            min_width = 0
        try:
            min_height = int(min_height)
        except Exception:
            min_height = 0
        width = max(self.host_window.width(), min_width)
        height = max(self.host_window.height(), min_height)
        return (width, height)

    def bind_mousewheel_to_widget_tree(self, root_widget, scroll_target, axis="y"):
        _ = root_widget
        _ = scroll_target
        _ = axis
        return None

    def show_toast(self, title, message, bootstyle=None, duration_ms=None):
        _ = bootstyle
        duration = duration_ms if duration_ms is not None else 5000
        combined = f"{title}: {message}" if title else str(message or "")
        status_bar = self.host_window.statusBar()
        if status_bar is not None:
            status_bar.showMessage(combined, max(0, int(duration)))

    def refresh_update_status_visibility(self):
        return None

    def show_error(self, title, message):
        if QMessageBox is not None:
            QMessageBox.critical(self.host_window, str(title), str(message))
            return
        self.show_toast(title, message, duration_ms=7000)

    def show_warning(self, title, message):
        if QMessageBox is not None:
            QMessageBox.warning(self.host_window, str(title), str(message))
            return
        self.show_toast(title, message, duration_ms=7000)

    def ask_yes_no(self, title, message):
        if QMessageBox is not None:
            response = QMessageBox.question(self.host_window, str(title), str(message))
            return response == QMessageBox.StandardButton.Yes
        return False

    def create_module_window(self, title=None, geometry=None, minsize=None):
        _ = title
        _ = geometry
        _ = minsize
        return None

    def destroy_module_window(self, window):
        _ = window
        return None
