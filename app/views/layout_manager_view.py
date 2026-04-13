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
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, DANGER, END, EW, HORIZONTAL, INFO, LEFT, NE, NONE, NS, NSEW, NW, PRIMARY, RIGHT, SECONDARY, SUCCESS, VERTICAL, W, X, Y
from ttkbootstrap.dialogs import Messagebox

__module_name__ = "Layout Manager"
__version__ = "1.1.0"


class LayoutManagerView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.preview_after_id = None
        self.preview_tooltip = None
        self.suppress_modified_event = False
        self.theme_tokens = {}
        self.form_option_map = {}
        self.card_shells = {}
        self.header_card_widgets = []
        self.production_row_card_widgets = []
        self.downtime_row_card_widgets = []
        self.mapping_card_widgets = []
        self.preview_cells = []
        self.setup_ui()

    def setup_ui(self):
        self.main_container = tb.Frame(self.parent, padding=10, style="Martin.Content.TFrame")
        self.main_container.pack(fill=BOTH, expand=True)
        self.editor_frame = tb.Frame(self.main_container, style="Martin.Content.TFrame")
        self.editor_frame.pack(fill=BOTH, expand=True, padx=5)

        tb.Label(self.editor_frame, text="Layout Editor", font=("-size 12 -weight bold")).pack(anchor=W)
        self.source_label = tb.Label(self.editor_frame, bootstyle=SECONDARY)
        self.source_label.pack(anchor=W)

        self.form_bar = tb.Frame(self.editor_frame, style="Martin.Content.TFrame")
        self.form_bar.pack(fill=X, pady=(4, 2))
        tb.Label(self.form_bar, text="Form Definition", style="Martin.Muted.TLabel").pack(side=LEFT)
        self.form_selector = ttk.Combobox(self.form_bar, state="readonly", width=38)
        self.form_selector.pack(side=LEFT, padx=(8, 6), fill=X, expand=True)
        self.form_selector.bind("<<ComboboxSelected>>", self.on_form_selection_changed, add="+")
        self.activate_form_button = tb.Button(self.form_bar, text="Activate", bootstyle=SECONDARY, command=self.controller.activate_selected_form)
        self.activate_form_button.pack(side=LEFT, padx=4)

        self.form_actions = tb.Frame(self.form_bar, style="Martin.Content.TFrame")
        self.form_actions.pack(side=RIGHT)
        self.create_form_button = tb.Button(self.form_actions, text="Create Form From Current", bootstyle=SUCCESS, command=self.controller.create_form_from_current)
        self.create_form_button.pack(side=RIGHT)
        self.duplicate_form_button = tb.Button(self.form_actions, text="Duplicate", bootstyle=PRIMARY, command=self.controller.duplicate_selected_form)
        self.duplicate_form_button.pack(side=RIGHT, padx=(0, 6))
        self.rename_form_button = tb.Button(self.form_actions, text="Rename", bootstyle=INFO, command=self.controller.rename_selected_form)
        self.rename_form_button.pack(side=RIGHT, padx=(0, 6))
        self.delete_form_button = tb.Button(self.form_actions, text="Delete", bootstyle=DANGER, command=self.controller.delete_selected_form)
        self.delete_form_button.pack(side=RIGHT, padx=(0, 6))

        self.editor_notebook = ttk.Notebook(self.editor_frame)
        self.editor_notebook.pack(fill=BOTH, expand=True, pady=5)

        self.block_tab = tb.Frame(self.editor_notebook, style="Martin.Content.TFrame")
        self.json_tab = tb.Frame(self.editor_notebook, style="Martin.Content.TFrame")
        self.preview_tab = tb.Frame(self.editor_notebook, style="Martin.Content.TFrame")
        self.editor_notebook.add(self.block_tab, text="Block View")
        self.editor_notebook.add(self.json_tab, text="JSON Editor")
        self.editor_notebook.add(self.preview_tab, text="Preview")

        block_help = tb.Label(
            self.block_tab,
            text="Block View lets you adjust field placement without working directly in raw JSON. Use JSON Editor for advanced edits.",
            bootstyle=INFO,
        )
        block_help.pack(anchor=W, pady=(0, 5))

        self.block_scroll_frame = tb.Frame(self.block_tab, style="Martin.Content.TFrame")
        self.block_scroll_frame.pack(fill=BOTH, expand=True)
        self.block_canvas = tk.Canvas(self.block_scroll_frame, highlightthickness=0, bd=0)
        self.block_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.block_scrollbar = tb.Scrollbar(self.block_scroll_frame, orient=VERTICAL, command=self.block_canvas.yview)
        self.block_scrollbar.pack(side=RIGHT, fill=Y)
        self.block_canvas.configure(yscrollcommand=self.block_scrollbar.set)
        self.block_inner = tb.Frame(self.block_canvas)
        self.block_canvas_window = self.block_canvas.create_window((0, 0), window=self.block_inner, anchor="nw")
        self.block_inner.bind("<Configure>", self.on_block_frame_configure)
        self.block_canvas.bind("<Configure>", self.on_block_canvas_configure)

        json_help = tb.Label(
            self.json_tab,
            text=(
                "JSON Editor accepts the full layout config or recognized top-level sections like header_fields, "
                "production_row_fields, downtime_row_fields, production_mapping, and downtime_mapping. "
                "Section payloads merge into the current form for preview, validation, formatting, and save."
            ),
            style="Martin.Muted.TLabel",
            wraplength=980,
            justify=LEFT,
        )
        json_help.pack(anchor=W, pady=(0, 5))

        self.editor_text_frame = tb.Frame(self.json_tab, style="Martin.Content.TFrame")
        self.editor_text_frame.pack(fill=BOTH, expand=True)
        self.text_area = tk.Text(self.editor_text_frame, wrap=NONE, font=("Monospace", 10), undo=True, bd=0, relief="flat", highlightthickness=0)
        self.text_area.grid(row=0, column=0, sticky=NSEW)
        self.y_scroll = tb.Scrollbar(self.editor_text_frame, orient=VERTICAL, command=self.text_area.yview)
        self.y_scroll.grid(row=0, column=1, sticky=NS)
        self.x_scroll = tb.Scrollbar(self.editor_text_frame, orient=HORIZONTAL, command=self.text_area.xview)
        self.x_scroll.grid(row=1, column=0, sticky=EW)
        self.editor_text_frame.rowconfigure(0, weight=1)
        self.editor_text_frame.columnconfigure(0, weight=1)
        self.text_area.configure(yscrollcommand=self.y_scroll.set, xscrollcommand=self.x_scroll.set)
        self.text_area.bind("<<Modified>>", self.on_text_modified)

        preview_help = tb.Label(
            self.preview_tab,
            text="Preview renders the active header grid plus production and downtime row schemas using the current editor content.",
            bootstyle=INFO,
        )
        preview_help.pack(anchor=W, pady=(0, 5))
        self.preview_wrapper = tb.Labelframe(self.preview_tab, text=" Live Grid Preview ", padding=10, style="Martin.Card.TLabelframe")
        self.preview_wrapper.pack(fill=BOTH, expand=True)
        self.preview_canvas = tb.Frame(self.preview_wrapper, style="Martin.Surface.TFrame")
        self.preview_canvas.pack(fill=BOTH, expand=True)

        btn_frame = tb.Frame(self.editor_frame, style="Martin.Content.TFrame")
        btn_frame.pack(fill=X, pady=5)
        tb.Button(btn_frame, text="Reload Current", bootstyle=SECONDARY, command=self.controller.load_config).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Load Default", bootstyle=SECONDARY, command=self.controller.load_default_config).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Format JSON", bootstyle=PRIMARY, command=self.controller.format_json).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Validate JSON", bootstyle=INFO, command=self.controller.validate_editor_json).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Update Preview", bootstyle=INFO, command=self.controller.update_preview).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Save to File", bootstyle=SUCCESS, command=self.controller.save_config).pack(side=RIGHT, padx=5)

        self.status_label = tb.Label(self.editor_frame, text="", bootstyle=SECONDARY)
        self.status_label.pack(anchor=W, pady=(0, 2))

        self.parent.bind_all("<Control-s>", self.on_save_shortcut)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_canvas, self.block_canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_inner, self.block_canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.text_area, self.text_area)
        self.update_form_action_state()

    def on_save_shortcut(self, _event=None):
        self.controller.save_config()
        return "break"

    def _resolve_parent_background(self):
        for option_name in ("background", "bg"):
            try:
                value = self.parent.cget(option_name)
                if value:
                    return value
            except Exception:
                continue
        return "#101b22"

    def apply_theme(self, theme_tokens):
        self.theme_tokens = dict(theme_tokens or {})
        fallback_bg = self._resolve_parent_background()
        surface_bg = self.theme_tokens.get("surface_bg", fallback_bg)
        surface_fg = self.theme_tokens.get("surface_fg", "#ffffff")
        content_bg = self.theme_tokens.get("content_bg", surface_bg)
        accent = self.theme_tokens.get("accent", "#0b5ed7")

        self.main_container.configure(style="Martin.Content.TFrame")
        self.editor_frame.configure(style="Martin.Content.TFrame")
        self.form_bar.configure(style="Martin.Content.TFrame")
        self.form_actions.configure(style="Martin.Content.TFrame")
        self.block_tab.configure(style="Martin.Content.TFrame")
        self.json_tab.configure(style="Martin.Content.TFrame")
        self.preview_tab.configure(style="Martin.Content.TFrame")
        self.block_scroll_frame.configure(style="Martin.Content.TFrame")
        self.editor_text_frame.configure(style="Martin.Content.TFrame")
        self.preview_wrapper.configure(style="Martin.Card.TLabelframe")
        self.preview_canvas.configure(style="Martin.Surface.TFrame")
        self.block_inner.configure(style="Martin.Content.TFrame")
        self.block_canvas.configure(background=self.theme_tokens.get("layout_block_canvas_bg", content_bg))
        self.text_area.configure(
            background=surface_bg,
            foreground=surface_fg,
            insertbackground=surface_fg,
            selectbackground=accent,
            selectforeground=self.theme_tokens.get("sidebar_button_active_fg", surface_fg),
        )

    def set_editor_text(self, serialized_text):
        self.suppress_modified_event = True
        self.text_area.delete("1.0", END)
        self.text_area.insert("1.0", serialized_text)
        self.text_area.edit_modified(False)
        self.suppress_modified_event = False

    def reset_editor_modified(self):
        self.suppress_modified_event = True
        self.text_area.edit_modified(False)
        self.suppress_modified_event = False

    def get_editor_text(self):
        return self.text_area.get("1.0", END).strip()

    def on_block_frame_configure(self, _event=None):
        self.block_canvas.configure(scrollregion=self.block_canvas.bbox("all"))

    def on_block_canvas_configure(self, event):
        self.block_canvas.itemconfigure(self.block_canvas_window, width=event.width)
        self.parent.after_idle(self._relayout_block_cards)

    def _reset_block_registries(self):
        self.card_shells = {}
        self.header_card_widgets = []
        self.production_row_card_widgets = []
        self.downtime_row_card_widgets = []
        self.mapping_card_widgets = []

    def _create_card_shell(self, parent, item_key, title):
        fallback_bg = self._resolve_parent_background()
        shell = tk.Frame(
            parent,
            bg=self.theme_tokens.get("layout_card_shell_bg", self.theme_tokens.get("surface_bg", fallback_bg)),
            highlightthickness=1,
            highlightbackground=self.theme_tokens.get("layout_preview_border", self.theme_tokens.get("border_color", fallback_bg)),
            highlightcolor=self.theme_tokens.get("layout_preview_border", self.theme_tokens.get("border_color", fallback_bg)),
            bd=0,
        )
        card = tb.Labelframe(shell, text=f" {title} ", padding=8, style="Martin.Card.TLabelframe")
        card.pack(fill=BOTH, expand=True)
        self.card_shells[item_key] = shell
        return shell, card

    def _bind_selectable(self, widget, item_key):
        widget.bind("<Button-1>", lambda _event, current_key=item_key: self.controller.select_block_item(current_key, scroll=True), add="+")

    def _relayout_card_group(self, container, widgets):
        if container is None or not widgets:
            return
        for column_index in range(10):
            container.columnconfigure(column_index, weight=0, uniform="")
        container.columnconfigure(0, weight=1, uniform="layout-cards")
        container.columnconfigure(1, weight=1, uniform="layout-cards")
        for index, widget in enumerate(widgets):
            widget.grid_forget()
            row = index // 2
            col = index % 2
            sticky = NW if col == 0 else NE
            widget.grid(row=row, column=col, padx=6, pady=6, sticky=sticky)

    def _relayout_block_cards(self):
        try:
            if not self.block_canvas.winfo_exists():
                return
        except tk.TclError:
            return
        self._relayout_card_group(getattr(self, "header_cards_container", None), self.header_card_widgets)
        self._relayout_card_group(getattr(self, "production_row_cards_container", None), self.production_row_card_widgets)
        self._relayout_card_group(getattr(self, "downtime_row_cards_container", None), self.downtime_row_card_widgets)
        self._relayout_card_group(getattr(self, "mapping_cards_container", None), self.mapping_card_widgets)
        self.on_block_frame_configure()

    def _scroll_card_into_view(self, item_key):
        shell = self.card_shells.get(item_key)
        if shell is None:
            return
        self.block_canvas.update_idletasks()
        scroll_region = self.block_canvas.bbox("all")
        if not scroll_region:
            return
        total_height = max(1, scroll_region[3] - scroll_region[1])
        y_position = max(0, shell.winfo_y() - 12)
        self.block_canvas.yview_moveto(min(1.0, y_position / total_height))

    def apply_selection(self, selected_item, scroll=False):
        for item_key, shell in self.card_shells.items():
            selected = item_key == selected_item
            shell.configure(
                highlightthickness=2 if selected else 1,
                highlightbackground=self.theme_tokens.get("layout_preview_selected_border") if selected else self.theme_tokens.get("layout_preview_border"),
                highlightcolor=self.theme_tokens.get("layout_preview_selected_border") if selected else self.theme_tokens.get("layout_preview_border"),
            )
            if selected and scroll:
                self._scroll_card_into_view(item_key)

        for cell_info in self.preview_cells:
            selected = selected_item in cell_info["item_keys"]
            background = self.theme_tokens.get("layout_preview_selected_bg") if selected else self.theme_tokens.get("layout_preview_cell_bg")
            border = self.theme_tokens.get("layout_preview_selected_border") if selected else self.theme_tokens.get("layout_preview_border")
            frame = cell_info["frame"]
            frame.configure(bg=background, highlightbackground=border, highlightcolor=border)
            for widget, foreground in cell_info["labels"]:
                widget.configure(bg=background, fg=foreground)

    def _get_row_field_card_widgets(self, section_name):
        if section_name == "production_row_fields":
            return self.production_row_card_widgets
        return self.downtime_row_card_widgets

    def _render_row_field_section(self, title, section_name, fields, protected_ids):
        section_title = tb.Label(self.block_inner, text=title, font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        section_title.pack(anchor=W, pady=(10, 6))

        section_actions = tb.Frame(self.block_inner)
        section_actions.pack(fill=X, pady=(0, 6))
        tb.Button(
            section_actions,
            text=f"+ Add {title[:-1]}",
            bootstyle=SUCCESS,
            command=lambda current_section=section_name: self.controller.add_row_field(current_section),
        ).pack(side=LEFT)

        tb.Separator(self.block_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))

        container = tb.Frame(self.block_inner)
        container.pack(fill=X)
        if section_name == "production_row_fields":
            self.production_row_cards_container = container
        else:
            self.downtime_row_cards_container = container

        widget_list = self._get_row_field_card_widgets(section_name)
        for field in fields:
            field_id = field.get("id", "")
            item_key = self.controller.get_row_field_item_key(section_name, field_id)
            card_shell, card = self._create_card_shell(container, item_key, field.get("label", "Unnamed Field"))
            widget_list.append(card_shell)
            self._bind_selectable(card_shell, item_key)

            is_protected = field_id in protected_ids

            header_row = tb.Frame(card)
            header_row.pack(fill=X, pady=(0, 6))
            tb.Label(header_row, text=f"ID: {field_id or '(missing)'}", style="Martin.Section.TLabel").pack(side=LEFT)
            if is_protected:
                tb.Label(header_row, text="Protected core field", style="Martin.Muted.TLabel").pack(side=RIGHT)

            role_row = tb.Frame(card)
            role_row.pack(fill=X, pady=(0, 6))
            tb.Label(role_row, text=f"Role: {field.get('role', '(none)')}", style="Martin.Muted.TLabel").pack(side=LEFT)

            action_row = tb.Frame(card)
            action_row.pack(fill=X, pady=(0, 6))
            state_bits = [field.get("widget", "entry")]
            if field.get("readonly"):
                state_bits.append("readonly")
            if field.get("derived"):
                state_bits.append("derived")
            if field.get("open_row_trigger"):
                state_bits.append("open-row")
            if field.get("user_input"):
                state_bits.append("user")
            tb.Label(action_row, text=f"State: {', '.join(state_bits)}", style="Martin.Muted.TLabel").pack(side=LEFT)
            tb.Button(
                action_row,
                text="Up",
                bootstyle=SECONDARY,
                command=lambda current_section=section_name, current_id=field_id: self.controller.move_row_field(current_section, current_id, -1),
            ).pack(side=RIGHT, padx=(4, 0))
            tb.Button(
                action_row,
                text="Down",
                bootstyle=SECONDARY,
                command=lambda current_section=section_name, current_id=field_id: self.controller.move_row_field(current_section, current_id, 1),
            ).pack(side=RIGHT, padx=(4, 0))
            remove_button = tb.Button(
                action_row,
                text="Remove",
                bootstyle=DANGER,
                command=lambda current_section=section_name, current_id=field_id: self.controller.remove_row_field(current_section, current_id),
            )
            remove_button.pack(side=RIGHT, padx=(4, 0))
            if is_protected:
                remove_button.state(["disabled"])

            form_row = tb.Frame(card)
            form_row.pack(fill=X)
            tb.Label(form_row, text="Label", bootstyle=PRIMARY).grid(row=0, column=0, padx=(0, 6), pady=2, sticky=W)
            label_var = tk.StringVar(value=str(field.get("label", "")))
            tb.Entry(form_row, textvariable=label_var, width=18).grid(row=0, column=1, padx=(0, 12), pady=2, sticky=W)
            tb.Label(form_row, text="Widget", bootstyle=PRIMARY).grid(row=0, column=2, padx=(0, 6), pady=2, sticky=W)
            widget_var = tk.StringVar(value=str(field.get("widget", "entry")))
            widget_combo = tb.Combobox(form_row, textvariable=widget_var, values=("entry", "display", "checkbutton", "combobox"), state="readonly", width=14)
            widget_combo.grid(row=0, column=3, padx=(0, 12), pady=2, sticky=W)
            tb.Label(form_row, text="Width", bootstyle=PRIMARY).grid(row=0, column=4, padx=(0, 6), pady=2, sticky=W)
            width_var = tk.StringVar(value=str(field.get("width", "")))
            tb.Entry(form_row, textvariable=width_var, width=8).grid(row=0, column=5, padx=(0, 12), pady=2, sticky=W)
            if is_protected:
                widget_combo.configure(state="disabled")

            meta_row = tb.Frame(card)
            meta_row.pack(fill=X, pady=(6, 0))
            tb.Label(meta_row, text="Default", bootstyle=PRIMARY).grid(row=0, column=0, padx=(0, 6), pady=2, sticky=W)
            default_var = tk.StringVar(value=str(field.get("default", "")))
            tb.Entry(meta_row, textvariable=default_var, width=16).grid(row=0, column=1, padx=(0, 12), pady=2, sticky=W)
            tb.Label(meta_row, text="Sticky", bootstyle=PRIMARY).grid(row=0, column=2, padx=(0, 6), pady=2, sticky=W)
            sticky_var = tk.StringVar(value=str(field.get("sticky", "")))
            tb.Entry(meta_row, textvariable=sticky_var, width=10).grid(row=0, column=3, padx=(0, 12), pady=2, sticky=W)
            tb.Label(meta_row, text="State", bootstyle=PRIMARY).grid(row=0, column=4, padx=(0, 6), pady=2, sticky=W)
            state_var = tk.StringVar(value=str(field.get("state", "")))
            tb.Entry(meta_row, textvariable=state_var, width=14).grid(row=0, column=5, padx=(0, 12), pady=2, sticky=W)

            options_row = tb.Frame(card)
            options_row.pack(fill=X, pady=(6, 0))
            tb.Label(options_row, text="Options Source", bootstyle=PRIMARY).grid(row=0, column=0, padx=(0, 6), pady=2, sticky=W)
            options_source_var = tk.StringVar(value=str(field.get("options_source", "")))
            tb.Entry(options_row, textvariable=options_source_var, width=20).grid(row=0, column=1, padx=(0, 12), pady=2, sticky=W)
            tb.Label(options_row, text="Bootstyle", bootstyle=PRIMARY).grid(row=0, column=2, padx=(0, 6), pady=2, sticky=W)
            bootstyle_var = tk.StringVar(value=str(field.get("bootstyle", "")))
            tb.Entry(options_row, textvariable=bootstyle_var, width=14).grid(row=0, column=3, padx=(0, 12), pady=2, sticky=W)
            tb.Label(options_row, text="Role", bootstyle=PRIMARY).grid(row=1, column=0, padx=(0, 6), pady=2, sticky=W)
            role_var = tk.StringVar(value=str(field.get("role", "")))
            role_entry = tb.Entry(options_row, textvariable=role_var, width=20)
            role_entry.grid(row=1, column=1, padx=(0, 12), pady=2, sticky=W)
            if is_protected:
                role_entry.configure(state="disabled")

            toggle_row = tb.Frame(card)
            toggle_row.pack(fill=X, pady=(6, 0))
            readonly_var = tk.BooleanVar(value=bool(field.get("readonly", False)))
            derived_var = tk.BooleanVar(value=bool(field.get("derived", False)))
            open_row_var = tk.BooleanVar(value=bool(field.get("open_row_trigger", False)))
            user_input_var = tk.BooleanVar(value=bool(field.get("user_input", False)))
            expand_var = tk.BooleanVar(value=bool(field.get("expand", False)))
            bold_var = tk.BooleanVar(value=bool(field.get("bold", False)))
            tb.Checkbutton(toggle_row, text="Readonly", variable=readonly_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="Derived", variable=derived_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="Open Row", variable=open_row_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="User Input", variable=user_input_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="Expand", variable=expand_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="Bold", variable=bold_var, bootstyle="round-toggle").pack(side=LEFT)

            apply_row = tb.Frame(card)
            apply_row.pack(fill=X, pady=(8, 0))
            tb.Button(
                apply_row,
                text="Apply",
                bootstyle=SUCCESS,
                command=lambda current_section=section_name, current_id=field_id, label_var=label_var, widget_var=widget_var, width_var=width_var, default_var=default_var, sticky_var=sticky_var, state_var=state_var, options_source_var=options_source_var, bootstyle_var=bootstyle_var, role_var=role_var, readonly_var=readonly_var, derived_var=derived_var, open_row_var=open_row_var, user_input_var=user_input_var, expand_var=expand_var, bold_var=bold_var: self.controller.update_row_field_from_block(
                    current_section,
                    current_id,
                    {
                        "label": label_var.get(),
                        "widget": widget_var.get(),
                        "width": width_var.get(),
                        "default": default_var.get(),
                        "sticky": sticky_var.get(),
                        "state": state_var.get(),
                        "options_source": options_source_var.get(),
                        "bootstyle": bootstyle_var.get(),
                        "role": role_var.get(),
                        "readonly": readonly_var.get(),
                        "derived": derived_var.get(),
                        "open_row_trigger": open_row_var.get(),
                        "user_input": user_input_var.get(),
                        "expand": expand_var.get(),
                        "bold": bold_var.get(),
                    },
                ),
            ).pack(anchor=W)

            if is_protected:
                note_row = tb.Frame(card)
                note_row.pack(fill=X, pady=(6, 0))
                tb.Label(
                    note_row,
                    text="Core runtime fields can be restyled here, but their IDs stay fixed and they cannot be removed.",
                    style="Martin.Muted.TLabel",
                    wraplength=300,
                    justify=LEFT,
                ).pack(side=LEFT)

    def render_block_view(self, config, protected_field_ids, protected_row_field_ids, selected_item=None):
        self._reset_block_registries()
        for child in self.block_inner.winfo_children():
            child.destroy()

        header_title = tb.Label(self.block_inner, text="Header Fields", font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        header_title.pack(anchor=W, pady=(0, 6))

        header_actions = tb.Frame(self.block_inner)
        header_actions.pack(fill=X, pady=(0, 6))
        tb.Button(header_actions, text="+ Add Header Field", bootstyle=SUCCESS, command=self.controller.add_header_field).pack(side=LEFT)

        tb.Separator(self.block_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))

        self.header_cards_container = tb.Frame(self.block_inner)
        self.header_cards_container.pack(fill=X)

        for field in config.get("header_fields", []):
            is_locked_readonly = field.get("id") == "cast_date"
            item_key = self.controller.get_field_item_key(field.get("id", ""))
            card_shell, card = self._create_card_shell(self.header_cards_container, item_key, field.get("label", "Unnamed Field"))
            self.header_card_widgets.append(card_shell)
            self._bind_selectable(card_shell, item_key)

            header_row = tb.Frame(card)
            header_row.pack(fill=X, pady=(0, 6))
            tb.Label(header_row, text=f"ID: {field.get('id', '(missing)')}", style="Martin.Section.TLabel").pack(side=LEFT)
            button_row = tb.Frame(header_row)
            button_row.pack(side=RIGHT)
            tb.Button(button_row, text="Up", width=4, bootstyle=SECONDARY, command=lambda field_id=field.get("id"): self.controller.move_header_field(field_id, -1)).pack(side=LEFT, padx=(4, 0))
            tb.Button(button_row, text="Down", width=5, bootstyle=SECONDARY, command=lambda field_id=field.get("id"): self.controller.move_header_field(field_id, 1)).pack(side=LEFT, padx=(4, 0))

            state_bits = []
            if field.get("readonly"):
                state_bits.append("readonly")
            if "default" in field:
                state_bits.append(f"default={field.get('default')}")
            if not state_bits:
                state_bits.append("editable")

            action_row = tb.Frame(card)
            action_row.pack(fill=X, pady=(0, 6))
            tb.Label(action_row, text=f"State: {', '.join(state_bits)}", style="Martin.Muted.TLabel").pack(side=LEFT)
            tb.Button(action_row, text="Up", bootstyle=SECONDARY, command=lambda field_id=field.get("id"): self.controller.move_header_field(field_id, -1)).pack(side=RIGHT, padx=(4, 0))
            tb.Button(action_row, text="Down", bootstyle=SECONDARY, command=lambda field_id=field.get("id"): self.controller.move_header_field(field_id, 1)).pack(side=RIGHT, padx=(4, 0))
            remove_button = tb.Button(action_row, text="Remove", bootstyle=DANGER, command=lambda field_id=field.get("id"): self.controller.remove_header_field(field_id))
            remove_button.pack(side=RIGHT, padx=(4, 0))
            if field.get("id") in protected_field_ids:
                remove_button.state(["disabled"])

            form_row = tb.Frame(card)
            form_row.pack(fill=X)
            tb.Label(form_row, text="Row", bootstyle=PRIMARY).grid(row=0, column=0, padx=(0, 6), pady=2, sticky=W)
            row_var = tk.StringVar(value=str(field.get("row", 0)))
            tb.Entry(form_row, textvariable=row_var, width=6).grid(row=0, column=1, padx=(0, 12), pady=2, sticky=W)
            tb.Label(form_row, text="Column", bootstyle=PRIMARY).grid(row=0, column=2, padx=(0, 6), pady=2, sticky=W)
            col_var = tk.StringVar(value=str(field.get("col", 0)))
            tb.Entry(form_row, textvariable=col_var, width=6).grid(row=0, column=3, padx=(0, 12), pady=2, sticky=W)
            tb.Label(form_row, text="Cell", bootstyle=PRIMARY).grid(row=0, column=4, padx=(0, 6), pady=2, sticky=W)
            cell_var = tk.StringVar(value=str(field.get("cell", "")))
            cell_entry = tb.Entry(form_row, textvariable=cell_var, width=10)
            cell_entry.grid(row=0, column=5, padx=(0, 12), pady=2, sticky=W)
            width_var = tk.StringVar(value=str(field.get("width", 10)))
            readonly_var = tk.BooleanVar(value=bool(field.get("readonly", False)))
            default_var = tk.StringVar(value=str(field.get("default", "")))
            role_var = tk.StringVar(value=str(field.get("role", "")))

            if not is_locked_readonly:
                tb.Label(form_row, text="Width", bootstyle=PRIMARY).grid(row=0, column=6, padx=(0, 6), pady=2, sticky=W)
                tb.Entry(form_row, textvariable=width_var, width=6).grid(row=0, column=7, padx=(0, 12), pady=2, sticky=W)
                readonly_toggle = tb.Checkbutton(form_row, text="Readonly", variable=readonly_var, bootstyle="round-toggle")
                readonly_toggle.grid(row=0, column=8, padx=(0, 12), pady=2, sticky=W)

            tb.Button(
                form_row,
                text="Apply",
                bootstyle=SUCCESS,
                command=lambda field_id=field.get("id"), row_var=row_var, col_var=col_var, cell_var=cell_var, width_var=width_var, readonly_var=readonly_var, default_var=default_var, role_var=role_var: self.controller.update_header_field_from_block(
                    field_id,
                    row_var.get(),
                    col_var.get(),
                    cell_var.get(),
                    width_var.get(),
                    readonly_var.get(),
                    default_var.get(),
                    role_var.get(),
                ),
            ).grid(row=0, column=9 if not is_locked_readonly else 6, padx=(0, 8), pady=2, sticky=W)

            if is_locked_readonly:
                note_row = tb.Frame(card)
                note_row.pack(fill=X, pady=(6, 0))
                tb.Label(note_row, text="Cast Date can only be moved here. It stays readonly and is derived from Date.", style="Martin.Muted.TLabel", wraplength=250, justify=LEFT).pack(side=LEFT)
            else:
                meta_row = tb.Frame(card)
                meta_row.pack(fill=X, pady=(6, 0))
                tb.Label(meta_row, text="Default", bootstyle=PRIMARY).pack(side=LEFT)
                tb.Entry(meta_row, textvariable=default_var, width=14).pack(side=LEFT, padx=(6, 10))
                tb.Label(meta_row, text="Role", bootstyle=PRIMARY).pack(side=LEFT)
                role_entry = tb.Entry(meta_row, textvariable=role_var, width=18)
                role_entry.pack(side=LEFT, padx=(6, 10))
                if field.get("id") in protected_field_ids:
                    role_entry.configure(state="disabled")
                tb.Label(meta_row, text=f"Current: {field.get('default', '(none)')}", style="Martin.Muted.TLabel").pack(side=LEFT)

        self._render_row_field_section(
            "Production Row Fields",
            "production_row_fields",
            config.get("production_row_fields", []),
            protected_row_field_ids.get("production_row_fields", set()),
        )
        self._render_row_field_section(
            "Downtime Row Fields",
            "downtime_row_fields",
            config.get("downtime_row_fields", []),
            protected_row_field_ids.get("downtime_row_fields", set()),
        )

        mappings_title = tb.Label(self.block_inner, text="Mappings", font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        mappings_title.pack(anchor=W, pady=(10, 6))
        tb.Separator(self.block_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))
        self.mapping_cards_container = tb.Frame(self.block_inner)
        self.mapping_cards_container.pack(fill=X)
        self.add_mapping_block("Production Mapping", config.get("production_mapping", {}), self.mapping_cards_container)
        self.add_mapping_block("Downtime Mapping", config.get("downtime_mapping", {}), self.mapping_cards_container)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_inner, self.block_canvas)
        self.apply_selection(selected_item)
        self.parent.after_idle(self._relayout_block_cards)

    def add_mapping_block(self, title, mapping, parent):
        mapping_name = title.lower().replace(" ", "_")
        item_key = self.controller.get_mapping_item_key(mapping_name)
        card_shell, card = self._create_card_shell(parent, item_key, title)
        self.mapping_card_widgets.append(card_shell)
        self._bind_selectable(card_shell, item_key)

        top_row = tb.Frame(card)
        top_row.pack(fill=X, pady=(0, 6))
        tb.Label(top_row, text="Start Row", bootstyle=PRIMARY).pack(side=LEFT)
        start_row_var = tk.StringVar(value=str(mapping.get("start_row", "")))
        tb.Entry(top_row, textvariable=start_row_var, width=8).pack(side=LEFT, padx=(6, 12))
        columns = mapping.get("columns", {})
        column_vars = {}
        if columns:
            columns_frame = tb.Frame(card)
            columns_frame.pack(fill=X)
            for column_index in range(2):
                columns_frame.columnconfigure(column_index, weight=1, uniform="mapping-fields")
            for index, (key, value) in enumerate(columns.items()):
                row = tb.Frame(columns_frame)
                row.grid(row=index // 2, column=index % 2, padx=4, pady=2, sticky=EW)
                tb.Label(row, text=key.replace("_", " ").title(), bootstyle=PRIMARY).pack(anchor=W)
                column_vars[key] = tk.StringVar(value=str(value))
                tb.Entry(row, textvariable=column_vars[key], width=8).pack(anchor=W, pady=(2, 0))
        else:
            tb.Label(card, text="No columns configured", style="Martin.Muted.TLabel").pack(anchor=W)

        action_row = tb.Frame(card)
        action_row.pack(fill=X, pady=(8, 0))
        tb.Button(
            action_row,
            text="Apply Mapping",
            bootstyle=SUCCESS,
            command=lambda mapping_name=mapping_name, start_row_var=start_row_var, column_vars=column_vars: self.controller.update_mapping_from_block(
                mapping_name,
                start_row_var.get(),
                {key: variable.get() for key, variable in column_vars.items()},
            ),
        ).pack(anchor=W, pady=(8, 0))

    def on_text_modified(self, _event=None):
        if self.suppress_modified_event:
            self.text_area.edit_modified(False)
            return
        if self.text_area.edit_modified():
            self.controller.handle_editor_modified()
            self.schedule_preview_update()
            self.text_area.edit_modified(False)

    def schedule_preview_update(self):
        if self.preview_after_id:
            try:
                self.parent.after_cancel(self.preview_after_id)
            except tk.TclError:
                pass
        self.preview_after_id = self.parent.after(400, self.controller.update_preview)

    def update_status(self, message, source_name, is_dirty, bootstyle=SECONDARY):
        dirty_text = "Unsaved changes" if is_dirty else "Saved"
        self.status_label.config(text=f"{message} | Source: {source_name} | State: {dirty_text}", bootstyle=bootstyle)

    def update_source_label(self, source_text):
        self.source_label.config(text=source_text)

    def _set_button_enabled(self, button, enabled):
        if enabled:
            button.state(["!disabled"])
        else:
            button.state(["disabled"])

    def on_form_selection_changed(self, _event=None):
        self.update_form_action_state()

    def set_form_options(self, forms, active_form_id=None, selected_form_id=None):
        values = []
        self.form_option_map = {}
        self.form_info_map = {}
        active_label = None
        selected_label = None
        for form in forms or []:
            label = f"{form.get('name', 'Unnamed Form')} [{form.get('id', 'form')}]"
            if form.get("built_in"):
                label += " (default)"
            values.append(label)
            form_id = form.get("id")
            self.form_option_map[label] = form_id
            self.form_info_map[form_id] = dict(form)
            if form_id == active_form_id:
                active_label = label
            if form_id == selected_form_id:
                selected_label = label

        self.form_selector.configure(values=values)
        if selected_label is not None:
            self.form_selector.set(selected_label)
        elif active_label is not None:
            self.form_selector.set(active_label)
        elif values:
            self.form_selector.set(values[0])
        else:
            self.form_selector.set("")
        self.update_form_action_state()

    def get_selected_form_id(self):
        return self.form_option_map.get(self.form_selector.get())

    def get_selected_form_info(self):
        selected_form_id = self.get_selected_form_id()
        if not selected_form_id:
            return None
        return dict(self.form_info_map.get(selected_form_id, {}))

    def update_form_action_state(self):
        selected_form = self.get_selected_form_info() or {}
        has_selection = bool(selected_form)
        is_active = bool(selected_form.get("is_active"))
        is_built_in = bool(selected_form.get("built_in"))
        self._set_button_enabled(self.activate_form_button, has_selection and not is_active)
        self._set_button_enabled(self.duplicate_form_button, has_selection)
        self._set_button_enabled(self.rename_form_button, has_selection and not is_built_in)
        self._set_button_enabled(self.delete_form_button, has_selection and not is_built_in)

    def ask_form_name(self, title="Create Form", prompt="Enter a name for the new form definition:", initialvalue=""):
        return simpledialog.askstring(
            title,
            prompt,
            initialvalue=initialvalue,
            parent=self.parent.winfo_toplevel(),
        )

    def confirm_delete_form(self, form_info):
        form_name = form_info.get("name", "the selected form")
        extra_text = "\n\nThis form is currently active. Deleting it will switch the app back to the default built-in form." if form_info.get("is_active") else ""
        return messagebox.askyesno(
            "Delete Form",
            f"Delete {form_name}?\n\nThis removes the form definition and its saved layout file from active use.{extra_text}",
        )

    def confirm_discard_changes(self, is_dirty):
        if not is_dirty:
            return True
        return messagebox.askyesno("Discard Unsaved Changes", "You have unsaved layout changes. Discard them and continue?")

    def bind_preview_tooltip(self, widget, field):
        widget.bind("<Enter>", lambda event, data=field: self.show_preview_tooltip(event, data))
        widget.bind("<Leave>", self.hide_preview_tooltip)

    def _build_preview_tooltip_lines(self, field):
        marker_parts = []
        if field.get("readonly"):
            marker_parts.append("readonly")
        if field.get("derived"):
            marker_parts.append("derived")
        if field.get("open_row_trigger"):
            marker_parts.append("open-row")
        if field.get("user_input"):
            marker_parts.append("user")
        marker_text = ", ".join(marker_parts) if marker_parts else "editable"

        if "row" in field and "col" in field:
            return [
                f"ID: {field.get('id', '(missing)')}",
                f"Role: {field.get('role', '(none)')}",
                f"Label: {field.get('label', '(missing)')}",
                f"Grid: row {field.get('row', 0)}, col {field.get('col', 0)}",
                f"Width: {field.get('width', 10)}",
                f"State: {marker_text}",
                f"Default: {field.get('default', '(none)')}",
                f"Cell: {field.get('cell', '(none)')}",
            ]

        return [
            f"ID: {field.get('id', '(missing)')}",
            f"Role: {field.get('role', '(none)')}",
            f"Label: {field.get('label', '(missing)')}",
            f"Widget: {field.get('widget', 'entry')}",
            f"Width: {field.get('width', '(auto)')}",
            f"State: {marker_text}",
            f"Default: {field.get('default', '(none)')}",
            f"Options Source: {field.get('options_source', '(none)')}",
            f"Bootstyle: {field.get('bootstyle', '(none)')}",
        ]

    def show_preview_tooltip(self, event, field):
        self.hide_preview_tooltip()
        tooltip_lines = self._build_preview_tooltip_lines(field)
        self.preview_tooltip = tk.Toplevel(self.preview_canvas)
        self.preview_tooltip.wm_overrideredirect(True)
        self.preview_tooltip.attributes("-topmost", True)
        self.preview_tooltip.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        tooltip_label = tk.Label(
            self.preview_tooltip,
            text="\n".join(tooltip_lines),
            justify=LEFT,
            padx=8,
            pady=8,
            bg=self.theme_tokens.get("layout_tooltip_bg", "#ffffff"),
            fg=self.theme_tokens.get("layout_tooltip_fg", "#000000"),
            highlightthickness=1,
            highlightbackground=self.theme_tokens.get("layout_tooltip_border", "#cccccc"),
            relief="flat",
            anchor="w",
        )
        tooltip_label.pack()

    def hide_preview_tooltip(self, _event=None):
        if self.preview_tooltip is not None:
            self.preview_tooltip.destroy()
            self.preview_tooltip = None

    def _add_row_field_preview_section(self, preview_grid_frame, section_row, column_span, section):
        grid_bg = self.theme_tokens.get("layout_preview_grid_bg", self.theme_tokens.get("content_bg", "#ffffff"))
        cell_bg = self.theme_tokens.get("layout_preview_cell_bg")
        text_fg = self.theme_tokens.get("layout_preview_text_fg")
        muted_fg = self.theme_tokens.get("layout_preview_muted_fg")
        border = self.theme_tokens.get("layout_preview_border")

        tb.Label(preview_grid_frame, text=section.get("title", "Section"), bootstyle=PRIMARY).grid(
            row=section_row,
            column=0,
            columnspan=column_span,
            padx=3,
            pady=(10, 2),
            sticky=W,
        )

        container = tk.Frame(preview_grid_frame, bg=grid_bg)
        container.grid(row=section_row + 1, column=0, columnspan=column_span, padx=3, pady=(0, 3), sticky=EW)

        fields = section.get("fields", [])
        if not fields:
            empty_label = tk.Label(container, text="No fields configured", bg=grid_bg, fg=muted_fg, anchor="w")
            empty_label.pack(anchor=W)
            return

        for column_index in range(2):
            container.columnconfigure(column_index, weight=1)

        for index, field in enumerate(fields):
            item_key = field.get("item_key")
            item_frame = tk.Frame(
                container,
                bg=cell_bg,
                highlightthickness=1,
                highlightbackground=border,
                highlightcolor=border,
                bd=0,
            )
            item_frame.grid(row=index // 2, column=index % 2, padx=3, pady=3, sticky=EW)
            title_label = tk.Label(
                item_frame,
                text=f"{field.get('label', field.get('id', 'Unnamed'))} [{field.get('widget', 'entry')}]",
                bg=cell_bg,
                fg=text_fg,
                anchor="w",
                justify=LEFT,
                wraplength=250,
            )
            title_label.pack(anchor=W, padx=8, pady=(8, 2))

            meta_bits = [f"id={field.get('id', '(missing)')}"]
            if field.get("readonly"):
                meta_bits.append("readonly")
            if field.get("derived"):
                meta_bits.append("derived")
            if field.get("open_row_trigger"):
                meta_bits.append("open-row")
            if field.get("options_source"):
                meta_bits.append(f"options={field.get('options_source')}")
            meta_label = tk.Label(
                item_frame,
                text=" | ".join(meta_bits),
                bg=cell_bg,
                fg=muted_fg,
                anchor="w",
                justify=LEFT,
                wraplength=250,
            )
            meta_label.pack(anchor=W, padx=8, pady=(0, 8))

            if item_key:
                self._bind_selectable(item_frame, item_key)
                self._bind_selectable(title_label, item_key)
                self._bind_selectable(meta_label, item_key)
            self.bind_preview_tooltip(item_frame, field)
            self.bind_preview_tooltip(title_label, field)
            self.bind_preview_tooltip(meta_label, field)
            self.preview_cells.append(
                {
                    "frame": item_frame,
                    "item_keys": [item_key] if item_key else [],
                    "labels": [(title_label, text_fg), (meta_label, muted_fg)],
                }
            )

    def _render_row_field_preview_sections(self, preview_grid_frame, preview_grid):
        sections = preview_grid.get("row_sections", [])
        if not sections:
            return
        column_span = max(2, preview_grid.get("max_col", 0) + 2)
        start_row = preview_grid.get("max_row", 0) + 2
        for index, section in enumerate(sections):
            section_row = start_row + (index * 2)
            self._add_row_field_preview_section(preview_grid_frame, section_row, column_span, section)

    def render_preview(self, preview_grid, selected_item=None):
        self.preview_after_id = None
        self.preview_cells = []
        self.hide_preview_tooltip()
        for child in self.preview_canvas.winfo_children():
            child.destroy()
        preview_grid_frame = tk.Frame(self.preview_canvas, bg=self.theme_tokens.get("layout_preview_grid_bg", self.theme_tokens.get("content_bg", "#ffffff")))
        preview_grid_frame.pack(anchor=NW, fill=BOTH, expand=True)
        tb.Label(preview_grid_frame, text=" ", width=6, bootstyle=PRIMARY).grid(row=0, column=0, padx=3, pady=3)

        for col in range(preview_grid["max_col"] + 1):
            tb.Label(preview_grid_frame, text=f"Col {col}", width=14, bootstyle=PRIMARY).grid(row=0, column=col + 1, padx=3, pady=3, sticky=EW)

        for row in range(preview_grid["max_row"] + 1):
            tb.Label(preview_grid_frame, text=f"Row {row}", width=8, bootstyle=PRIMARY).grid(row=row + 1, column=0, padx=3, pady=3, sticky=NS)

        for cell in preview_grid["cells"]:
            row = cell["row"]
            col = cell["col"]
            cell_frame = tk.Frame(
                preview_grid_frame,
                bg=self.theme_tokens.get("layout_preview_cell_bg"),
                highlightthickness=1,
                highlightbackground=self.theme_tokens.get("layout_preview_border"),
                highlightcolor=self.theme_tokens.get("layout_preview_border"),
                bd=0,
            )
            cell_frame.grid(row=row + 1, column=col + 1, padx=3, pady=3, sticky=NSEW)
            cell_frame.grid_propagate(False)
            cell_frame.configure(width=130, height=70)

            labels = []
            coordinate_label = tk.Label(
                cell_frame,
                text=f"({row}, {col})",
                bg=self.theme_tokens.get("layout_preview_cell_bg"),
                fg=self.theme_tokens.get("layout_preview_muted_fg"),
                anchor="w",
            )
            coordinate_label.pack(anchor=NW)
            labels.append((coordinate_label, self.theme_tokens.get("layout_preview_muted_fg")))

            if cell["fields"]:
                for field in cell["fields"]:
                    foreground = self.theme_tokens.get("layout_preview_readonly_fg") if field.get("readonly") else self.theme_tokens.get("layout_preview_text_fg")
                    field_label = tk.Label(
                        cell_frame,
                        text=field.get("label", field.get("id", "Unnamed")),
                        bg=self.theme_tokens.get("layout_preview_cell_bg"),
                        fg=foreground,
                        wraplength=110,
                        justify=LEFT,
                        anchor="w",
                    )
                    field_label.pack(anchor=W, pady=(4, 0))
                    labels.append((field_label, foreground))
                    self.bind_preview_tooltip(field_label, field)
                    self._bind_selectable(field_label, field.get("item_key"))
                    self._bind_selectable(cell_frame, field.get("item_key"))
            else:
                empty_label = tk.Label(
                    cell_frame,
                    text="empty",
                    bg=self.theme_tokens.get("layout_preview_cell_bg"),
                    fg=self.theme_tokens.get("layout_preview_empty_fg"),
                    anchor="w",
                )
                empty_label.pack(anchor=W, pady=(8, 0))
                labels.append((empty_label, self.theme_tokens.get("layout_preview_empty_fg")))

            self.preview_cells.append(
                {
                    "frame": cell_frame,
                    "item_keys": cell["item_keys"],
                    "labels": labels,
                }
            )

        for col in range(preview_grid["max_col"] + 2):
            preview_grid_frame.columnconfigure(col, weight=1)

        self._render_row_field_preview_sections(preview_grid_frame, preview_grid)

        self.apply_selection(selected_item)

    def show_preview_error(self, message):
        self.preview_after_id = None
        self.hide_preview_tooltip()
        for child in self.preview_canvas.winfo_children():
            child.destroy()
        tb.Label(self.preview_canvas, text=f"Preview Error: {message}", bootstyle=DANGER).pack()

    def show_error(self, title, message):
        Messagebox.show_error(message, title)

    def show_validation_success(self, message="Layout JSON is valid."):
        self.dispatcher.show_toast("Validation Success", message, SUCCESS)

    def show_form_created(self, form_info):
        self.dispatcher.show_toast("Form Created", f"Created and activated {form_info.get('name', 'the new form') }.", SUCCESS)

    def show_form_activated(self, form_info):
        self.dispatcher.show_toast("Form Activated", f"Active form set to {form_info.get('name', 'the selected form')}.", SUCCESS)

    def show_form_renamed(self, form_info):
        self.dispatcher.show_toast("Form Renamed", f"Renamed the form to {form_info.get('name', 'the selected form')}.", SUCCESS)

    def show_form_duplicated(self, form_info):
        self.dispatcher.show_toast("Form Duplicated", f"Created and activated {form_info.get('name', 'the duplicated form')}.", SUCCESS)

    def show_form_deleted(self, deleted_form, active_form=None, active_changed=False):
        deleted_name = deleted_form.get("name", "the selected form")
        if active_changed and active_form is not None:
            self.dispatcher.show_toast(
                "Form Deleted",
                f"Deleted {deleted_name}. Active form set to {active_form.get('name', 'the default form')}.",
                SUCCESS,
            )
            return
        self.dispatcher.show_toast("Form Deleted", f"Deleted {deleted_name}.", SUCCESS)

    def show_save_success(self, save_path, backup_info):
        backup_message = f"Layout saved to {save_path}."
        if backup_info.get("versioned_backup_path"):
            backup_message += " A recovery copy was stored in data/backups/layouts."
        elif backup_info.get("adjacent_backup_path"):
            backup_message += f" A backup was kept as {os.path.basename(backup_info['adjacent_backup_path'])}."
        self.dispatcher.show_toast("Layout Saved", backup_message, SUCCESS)

    def on_hide(self):
        return None

    def on_unload(self):
        if self.preview_after_id is not None:
            try:
                self.parent.after_cancel(self.preview_after_id)
            except tk.TclError:
                pass
            self.preview_after_id = None
        self.hide_preview_tooltip()
        try:
            self.parent.unbind_all("<Control-s>")
        except tk.TclError:
            pass
        return None
