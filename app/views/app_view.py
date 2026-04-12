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
import tkinter as tk

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, BOTTOM, HORIZONTAL, LEFT, RIGHT, TOP, VERTICAL, W, X, Y

__module_name__ = "Application Shell"
__version__ = "2.1.5"


class AppShellView:
    def __init__(self, root, update_coordinator):
        self.root = root
        self.update_coordinator = update_coordinator
        self.main_container = None
        self.sidebar = None
        self.nav_container = None
        self.nav_top_container = None
        self.nav_middle_container = None
        self.nav_bottom_container = None
        self.right_container = None
        self.update_status_frame = None
        self.update_status_label = None
        self.canvas = None
        self.scrollbar = None
        self.x_scrollbar = None
        self.content_area = None
        self.canvas_window = None
        self.sidebar_title = None
        self.nav_buttons = {}
        self.nav_button_labels = {}
        self.sidebar_toggle_button = None
        self.sidebar_collapsed = False
        self.sidebar_expanded_width = 184
        self.sidebar_collapsed_width = 60

    def build(self):
        self.main_container = tb.Frame(self.root, style="Martin.App.TFrame")
        self.main_container.pack(fill=BOTH, expand=True)

        self.sidebar = tb.Frame(self.main_container, style="Martin.Sidebar.TFrame", width=self.sidebar_expanded_width, padding=(8, 14, 8, 12))
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        header_frame = tb.Frame(self.sidebar, style="Martin.Sidebar.TFrame")
        header_frame.pack(fill=X)

        self.sidebar_title = tb.Label(
            header_frame,
            text="LOGGING CENTER",
            style="Martin.SidebarTitle.TLabel",
            anchor=W,
            justify=LEFT,
        )
        self.sidebar_title.pack(side=LEFT, fill=X, expand=True, pady=(6, 14), padx=(2, 2))

        self.sidebar_toggle_button = tb.Button(header_frame, text="<", bootstyle="secondary-link", width=2, command=self.toggle_sidebar)
        self.sidebar_toggle_button.pack(side=RIGHT, pady=(2, 10))

        self.nav_container = tb.Frame(self.sidebar, style="Martin.Sidebar.TFrame")
        self.nav_container.pack(fill=BOTH, expand=True)
        self.nav_top_container = tb.Frame(self.nav_container, style="Martin.Sidebar.TFrame")
        self.nav_top_container.pack(fill=X)
        self.nav_middle_container = tb.Frame(self.nav_container, style="Martin.Sidebar.TFrame")
        self.nav_middle_container.pack(fill=BOTH, expand=True, pady=(10, 10))
        self.nav_bottom_container = tb.Frame(self.nav_container, style="Martin.Sidebar.TFrame")
        self.nav_bottom_container.pack(side=BOTTOM, fill=X)

        self.right_container = tb.Frame(self.main_container, style="Martin.Content.TFrame", padding=(10, 10, 10, 10))
        self.right_container.pack(side=RIGHT, fill=BOTH, expand=True)

        self.update_status_frame = tb.Frame(self.right_container, padding=(14, 8), style="Martin.Status.TFrame")
        self.update_status_frame.pack(side=TOP, fill=X, pady=(0, 8))
        self.update_status_label = tb.Label(
            self.update_status_frame,
            textvariable=self.update_coordinator.banner_var,
            style="Martin.Status.TLabel",
            anchor=W,
        )
        self.update_status_label.pack(fill=X)

        self.canvas = tk.Canvas(self.right_container, highlightthickness=0, bd=0)
        self.scrollbar = tb.Scrollbar(self.right_container, orient=VERTICAL, command=self.canvas.yview)
        self.x_scrollbar = tb.Scrollbar(self.right_container, orient=HORIZONTAL, command=self.canvas.xview)
        self.content_area = tb.Frame(self.canvas, style="Martin.Content.TFrame")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_area, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.x_scrollbar.set)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.x_scrollbar.pack(side=BOTTOM, fill=X)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self.content_area.bind("<Configure>", self.sync_content_canvas_layout)
        self.canvas.bind("<Configure>", self.sync_content_canvas_layout)
        self.apply_theme()

    def populate_navigation(self, items, load_callback, active_module_name=None):
        for container in (self.nav_top_container, self.nav_middle_container, self.nav_bottom_container):
            for child in container.winfo_children():
                child.destroy()
        self.nav_buttons = {}
        self.nav_button_labels = {}

        if isinstance(items, dict):
            grouped_items = items
        else:
            grouped_items = {"top": [], "middle": list(items), "bottom": []}

        for group_name, container in (
            ("top", self.nav_top_container),
            ("middle", self.nav_middle_container),
            ("bottom", self.nav_bottom_container),
        ):
            for display_name, module_name in grouped_items.get(group_name, []):
                collapsed_label = self._collapse_label(display_name)
                button = tb.Button(
                    container,
                    text=collapsed_label if self.sidebar_collapsed else display_name,
                    style="Martin.Nav.TButton",
                    command=lambda current_module=module_name: load_callback(current_module),
                )
                button.pack(fill=X, pady=3)
                self.nav_buttons[module_name] = button
                self.nav_button_labels[module_name] = (display_name, collapsed_label)

        self.set_active_navigation_button(active_module_name)

    def toggle_sidebar(self):
        self.set_sidebar_collapsed(not self.sidebar_collapsed)

    def set_sidebar_collapsed(self, collapsed):
        self.sidebar_collapsed = bool(collapsed)
        self.sidebar.configure(width=self.sidebar_collapsed_width if self.sidebar_collapsed else self.sidebar_expanded_width)
        if self.sidebar_title is not None:
            self.sidebar_title.configure(text="LC" if self.sidebar_collapsed else "LOGGING CENTER", anchor="center" if self.sidebar_collapsed else W)
        if self.sidebar_toggle_button is not None:
            self.sidebar_toggle_button.configure(text=">" if self.sidebar_collapsed else "<")
        for module_name, button in self.nav_buttons.items():
            expanded_label, collapsed_label = self.nav_button_labels.get(module_name, (button.cget("text"), button.cget("text")))
            button.configure(text=collapsed_label if self.sidebar_collapsed else expanded_label)

    def _collapse_label(self, display_name):
        words = [word for word in str(display_name).replace("/", " ").split() if word]
        if not words:
            return "?"
        return "".join(word[0].upper() for word in words[:3]) or str(display_name)[:2].upper()

    def apply_theme(self):
        tokens = getattr(self.root, "_martin_theme_tokens", None) or {}
        self.main_container.configure(style="Martin.App.TFrame")
        self.sidebar.configure(style="Martin.Sidebar.TFrame")
        if self.sidebar_title is not None:
            self.sidebar_title.configure(style="Martin.SidebarTitle.TLabel")
        self.nav_container.configure(style="Martin.Sidebar.TFrame")
        self.right_container.configure(style="Martin.Content.TFrame")
        self.update_status_frame.configure(style="Martin.Status.TFrame")
        self.update_status_label.configure(style="Martin.Status.TLabel")
        self.content_area.configure(style="Martin.Content.TFrame")
        if tokens:
            self.canvas.configure(background=tokens.get("canvas_bg", tokens.get("content_bg", self.root.cget("bg"))))
            self.root.configure(bg=tokens.get("app_bg", self.root.cget("bg")))
        self.set_sidebar_collapsed(self.sidebar_collapsed)
        self.set_active_navigation_button()

    def set_active_navigation_button(self, module_name=None):
        for button_module_name, button in self.nav_buttons.items():
            button.configure(style="Martin.NavActive.TButton" if button_module_name == module_name else "Martin.Nav.TButton")

    def configure_menu(self, open_callback, save_callback, export_callback, import_callback, login_callback, change_login_callback, logout_callback, help_callback, report_problem_callback, about_callback, exit_callback):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Draft", command=open_callback, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Draft", command=save_callback, accelerator="Ctrl+S")
        file_menu.add_command(label="Export to Excel", command=export_callback, accelerator="Ctrl+E")
        file_menu.add_command(label="Import Excel", command=import_callback, accelerator="Ctrl+I")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=exit_callback)
        menubar.add_cascade(label="File", menu=file_menu)

        security_menu = tk.Menu(menubar, tearoff=0)
        security_menu.add_command(label="Sign In", command=login_callback)
        security_menu.add_command(label="Change Login", command=change_login_callback)
        security_menu.add_command(label="Sign Out", command=logout_callback)
        menubar.add_cascade(label="Security", menu=security_menu)

        self.root.bind("<Control-o>", open_callback)
        self.root.bind("<Control-s>", save_callback)
        self.root.bind("<Control-e>", export_callback)
        self.root.bind("<Control-i>", import_callback)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="User Guide", command=help_callback)
        help_menu.add_command(label="Report A Problem", command=report_problem_callback)
        help_menu.add_command(label="About", command=about_callback)
        menubar.add_cascade(label="Help", menu=help_menu)

    def refresh_update_status_visibility(self):
        if self.update_coordinator.active:
            if not self.update_status_frame.winfo_manager():
                self.update_status_frame.pack(side=TOP, fill=X, pady=(0, 8), before=self.canvas)
            self.update_status_frame.configure(bootstyle="info")
            self.update_status_label.configure(bootstyle=self.update_coordinator.banner_bootstyle)
            return

        if self.update_status_frame.winfo_manager():
            self.update_status_frame.pack_forget()

    def sync_content_canvas_layout(self, _event=None):
        viewport_width = max(self.canvas.winfo_width(), 1)
        requested_width = max(self.content_area.winfo_reqwidth(), 1)
        self.canvas.itemconfigure(self.canvas_window, width=max(viewport_width, requested_width))
        scroll_region = self.canvas.bbox("all")
        if scroll_region is not None:
            self.canvas.configure(scrollregion=scroll_region)