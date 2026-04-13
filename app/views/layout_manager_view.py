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

from app.app_logging import log_error

__module_name__ = "Layout Manager"
__version__ = "1.1.0"


class LayoutManagerView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.preview_after_id = None
        self.relayout_after_id = None
        self.preview_tooltip = None
        self.suppress_modified_event = False
        self.theme_tokens = {}
        self.form_option_map = {}
        self.card_shells = {}
        self.card_shell_scroll_targets = {}
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
        self.import_export_tab = tb.Frame(self.editor_notebook, style="Martin.Content.TFrame")
        self.json_tab = tb.Frame(self.editor_notebook, style="Martin.Content.TFrame")
        self.preview_tab = tb.Frame(self.editor_notebook, style="Martin.Content.TFrame")
        self.editor_notebook.add(self.block_tab, text="Block View")
        self.editor_notebook.add(self.import_export_tab, text="Import / Export")
        self.editor_notebook.add(self.json_tab, text="JSON Editor")
        self.editor_notebook.add(self.preview_tab, text="Preview")
        self.editor_notebook.bind("<<NotebookTabChanged>>", self.on_editor_tab_changed, add="+")

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

        self.import_export_help = tb.Label(
            self.import_export_tab,
            text=(
                "Import / Export centralizes workbook template and column mapping settings. "
                "Use Block View for layout and field structure, and use this tab for workbook-facing behavior."
            ),
            bootstyle=INFO,
            wraplength=980,
            justify=LEFT,
        )
        self.import_export_help.pack(anchor=W, pady=(0, 5))
        self.import_export_scroll_frame = tb.Frame(self.import_export_tab, style="Martin.Content.TFrame")
        self.import_export_scroll_frame.pack(fill=BOTH, expand=True)
        self.import_export_canvas = tk.Canvas(self.import_export_scroll_frame, highlightthickness=0, bd=0)
        self.import_export_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.import_export_scrollbar = tb.Scrollbar(
            self.import_export_scroll_frame,
            orient=VERTICAL,
            command=self.import_export_canvas.yview,
        )
        self.import_export_scrollbar.pack(side=RIGHT, fill=Y)
        self.import_export_canvas.configure(yscrollcommand=self.import_export_scrollbar.set)
        self.import_export_inner = tb.Frame(self.import_export_canvas)
        self.import_export_canvas_window = self.import_export_canvas.create_window((0, 0), window=self.import_export_inner, anchor="nw")
        self.import_export_inner.bind("<Configure>", self.on_import_export_frame_configure)
        self.import_export_canvas.bind("<Configure>", self.on_import_export_canvas_configure)

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
            text="Preview renders the current header grid plus operator-style production and downtime row templates using the editor content.",
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
        self.dispatcher.bind_mousewheel_to_widget_tree(self.import_export_canvas, self.import_export_canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.import_export_inner, self.import_export_canvas)
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

    def _get_tk_color(self, token_name, fallback=None):
        root = self.parent.winfo_toplevel()
        candidates = [
            self.theme_tokens.get(token_name),
            fallback,
            self.theme_tokens.get("border_color"),
            self.theme_tokens.get("surface_bg"),
            self.theme_tokens.get("content_bg"),
            self._resolve_parent_background(),
            "#ffffff",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                root.winfo_rgb(candidate)
                return candidate
            except tk.TclError:
                continue
        return "#ffffff"

    def get_active_editor_tab(self):
        current_tab = self.editor_notebook.select()
        if current_tab == str(self.block_tab):
            return "block"
        if current_tab == str(self.import_export_tab):
            return "import_export"
        if current_tab == str(self.json_tab):
            return "json"
        if current_tab == str(self.preview_tab):
            return "preview"
        return "block"

    def on_editor_tab_changed(self, _event=None):
        self.controller.handle_editor_tab_changed()

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
        self.import_export_tab.configure(style="Martin.Content.TFrame")
        self.json_tab.configure(style="Martin.Content.TFrame")
        self.preview_tab.configure(style="Martin.Content.TFrame")
        self.block_scroll_frame.configure(style="Martin.Content.TFrame")
        self.import_export_scroll_frame.configure(style="Martin.Content.TFrame")
        self.editor_text_frame.configure(style="Martin.Content.TFrame")
        self.preview_wrapper.configure(style="Martin.Card.TLabelframe")
        self.preview_canvas.configure(style="Martin.Surface.TFrame")
        self.block_inner.configure(style="Martin.Content.TFrame")
        self.import_export_inner.configure(style="Martin.Content.TFrame")
        self.block_canvas.configure(background=self._get_tk_color("layout_block_canvas_bg", content_bg))
        self.import_export_canvas.configure(background=self._get_tk_color("layout_block_canvas_bg", content_bg))
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

    def on_import_export_frame_configure(self, _event=None):
        self.import_export_canvas.configure(scrollregion=self.import_export_canvas.bbox("all"))

    def on_import_export_canvas_configure(self, event):
        self.import_export_canvas.itemconfigure(self.import_export_canvas_window, width=event.width)

    def _schedule_relayout_block_cards(self):
        if self.relayout_after_id is not None:
            return
        self.relayout_after_id = self.parent.after_idle(self._relayout_block_cards)

    def _reset_block_registries(self):
        self.card_shells = {}
        self.card_shell_scroll_targets = {}
        self.header_card_widgets = []
        self.production_row_card_widgets = []
        self.downtime_row_card_widgets = []
        self.mapping_card_widgets = []

    def _create_card_shell(self, parent, item_key, title, scroll_target=None):
        fallback_bg = self._resolve_parent_background()
        shell = tk.Frame(
            parent,
            bg=self._get_tk_color("layout_card_shell_bg", self.theme_tokens.get("surface_bg", fallback_bg)),
            highlightthickness=1,
            highlightbackground=self._get_tk_color("layout_preview_border", self.theme_tokens.get("border_color", fallback_bg)),
            highlightcolor=self._get_tk_color("layout_preview_border", self.theme_tokens.get("border_color", fallback_bg)),
            bd=0,
        )
        card = tb.Labelframe(shell, text=f" {title} ", padding=8, style="Martin.Card.TLabelframe")
        card.pack(fill=BOTH, expand=True)
        self.card_shells[item_key] = shell
        self.card_shell_scroll_targets[item_key] = scroll_target
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
            widget.grid(row=row, column=col, padx=6, pady=6, sticky=EW)

    def _relayout_block_cards(self):
        self.relayout_after_id = None
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
        self.on_import_export_frame_configure()

    def _scroll_card_into_view(self, item_key):
        shell = self.card_shells.get(item_key)
        if shell is None:
            return
        scroll_target = self.card_shell_scroll_targets.get(item_key) or self.block_canvas
        scroll_target.update_idletasks()
        scroll_region = scroll_target.bbox("all")
        if not scroll_region:
            return
        total_height = max(1, scroll_region[3] - scroll_region[1])
        y_position = max(0, shell.winfo_y() - 12)
        scroll_target.yview_moveto(min(1.0, y_position / total_height))

    def apply_selection(self, selected_item, scroll=False):
        for item_key, shell in self.card_shells.items():
            selected = item_key == selected_item
            shell.configure(
                highlightthickness=2 if selected else 1,
                highlightbackground=self._get_tk_color("layout_preview_selected_border" if selected else "layout_preview_border"),
                highlightcolor=self._get_tk_color("layout_preview_selected_border" if selected else "layout_preview_border"),
            )
            if selected and scroll:
                self._scroll_card_into_view(item_key)

        for cell_info in self.preview_cells:
            selected = selected_item in cell_info["item_keys"]
            background = self._get_tk_color("layout_preview_selected_bg" if selected else "layout_preview_cell_bg")
            border = self._get_tk_color("layout_preview_selected_border" if selected else "layout_preview_border")
            frame = cell_info["frame"]
            frame.configure(bg=background, highlightbackground=border, highlightcolor=border)
            for widget, foreground in cell_info["labels"]:
                widget.configure(bg=background, fg=foreground)

    def _get_row_field_card_widgets(self, section_name):
        if section_name == "production_row_fields":
            return self.production_row_card_widgets
        return self.downtime_row_card_widgets

    def _format_row_field_values(self, values):
        if not isinstance(values, list):
            return ""
        return ", ".join(text for text in (str(item).strip() for item in values) if text)

    def _render_row_field_section(self, title, section_name, fields, protected_ids, section_metadata=None):
        section_title = tb.Label(self.block_inner, text=title, font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        section_title.pack(anchor=W, pady=(10, 6))

        section_metadata = section_metadata or {}
        section_id = "production" if section_name == "production_row_fields" else "downtime"

        section_meta_row = tb.Frame(self.block_inner)
        section_meta_row.pack(fill=X, pady=(0, 6))
        tb.Label(section_meta_row, text="Section Name", bootstyle=PRIMARY).pack(side=LEFT)
        section_name_var = tk.StringVar(value=str(section_metadata.get("name", title)))
        tb.Entry(section_meta_row, textvariable=section_name_var, width=24).pack(side=LEFT, padx=(6, 12))
        tb.Label(section_meta_row, text="Description", bootstyle=PRIMARY).pack(side=LEFT)
        section_description_var = tk.StringVar(value=str(section_metadata.get("description", "")))
        tb.Entry(section_meta_row, textvariable=section_description_var, width=24).pack(side=LEFT, padx=(6, 12))
        tb.Label(section_meta_row, text="Type", bootstyle=PRIMARY).pack(side=LEFT)
        section_type_var = tk.StringVar(value=str(section_metadata.get("section_type", "repeating")))
        tb.Combobox(section_meta_row, textvariable=section_type_var, values=("single", "repeating"), state="readonly", width=10).pack(side=LEFT, padx=(6, 12))
        tb.Label(section_meta_row, text="Profile", bootstyle=PRIMARY).pack(side=LEFT)
        behavior_profile_var = tk.StringVar(value=str(section_metadata.get("behavior_profile", section_id)))
        tb.Combobox(section_meta_row, textvariable=behavior_profile_var, values=("header", "production", "downtime"), state="readonly", width=12).pack(side=LEFT, padx=(6, 12))
        tb.Button(
            section_meta_row,
            text="Apply Section",
            bootstyle=SUCCESS,
            command=lambda current_section_id=section_id, name_var=section_name_var, description_var=section_description_var, section_type_var=section_type_var, behavior_profile_var=behavior_profile_var: self.controller.update_section_metadata_from_block(
                current_section_id,
                {
                    "name": name_var.get(),
                    "description": description_var.get(),
                    "section_type": section_type_var.get(),
                    "behavior_profile": behavior_profile_var.get(),
                },
            ),
        ).pack(side=RIGHT)

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
            card_shell, card = self._create_card_shell(container, item_key, field.get("label", "Unnamed Field"), scroll_target=self.block_canvas)
            widget_list.append(card_shell)
            self._bind_selectable(card_shell, item_key)

            is_protected = field_id in protected_ids
            protection_label = "Protected core field" if is_protected else None

            header_row = tb.Frame(card)
            header_row.pack(fill=X, pady=(0, 6))
            tb.Label(header_row, text=f"ID: {field_id or '(missing)'}", style="Martin.Section.TLabel").pack(side=LEFT)
            if protection_label:
                tb.Label(header_row, text=protection_label, style="Martin.Muted.TLabel").pack(side=RIGHT)

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
            tb.Label(options_row, text="Values", bootstyle=PRIMARY).grid(row=1, column=2, padx=(0, 6), pady=2, sticky=W)
            values_var = tk.StringVar(value=self._format_row_field_values(field.get("values")))
            tb.Entry(options_row, textvariable=values_var, width=24).grid(row=1, column=3, padx=(0, 12), pady=2, sticky=W)
            tb.Label(options_row, text="Lookup Source", bootstyle=PRIMARY).grid(row=2, column=0, padx=(0, 6), pady=2, sticky=W)
            lookup_source_var = tk.StringVar(value=str(field.get("lookup_source", "")))
            tb.Entry(options_row, textvariable=lookup_source_var, width=20).grid(row=2, column=1, padx=(0, 12), pady=2, sticky=W)
            tb.Label(options_row, text="Lookup Key Role", bootstyle=PRIMARY).grid(row=2, column=2, padx=(0, 6), pady=2, sticky=W)
            lookup_key_role_var = tk.StringVar(value=str(field.get("lookup_key_role", "")))
            tb.Entry(options_row, textvariable=lookup_key_role_var, width=24).grid(row=2, column=3, padx=(0, 12), pady=2, sticky=W)
            tb.Label(options_row, text="Override Toggle", bootstyle=PRIMARY).grid(row=3, column=0, padx=(0, 6), pady=2, sticky=W)
            override_toggle_role_var = tk.StringVar(value=str(field.get("override_toggle_role", "")))
            tb.Entry(options_row, textvariable=override_toggle_role_var, width=20).grid(row=3, column=1, padx=(0, 12), pady=2, sticky=W)
            tb.Label(options_row, text="Toggle Target", bootstyle=PRIMARY).grid(row=3, column=2, padx=(0, 6), pady=2, sticky=W)
            toggle_target_role_var = tk.StringVar(value=str(field.get("toggle_target_role", "")))
            tb.Entry(options_row, textvariable=toggle_target_role_var, width=24).grid(row=3, column=3, padx=(0, 12), pady=2, sticky=W)
            if field_id in protected_ids:
                role_entry.configure(state="disabled")

            toggle_row = tb.Frame(card)
            toggle_row.pack(fill=X, pady=(6, 0))
            readonly_var = tk.BooleanVar(value=bool(field.get("readonly", False)))
            derived_var = tk.BooleanVar(value=bool(field.get("derived", False)))
            math_trigger_var = tk.BooleanVar(value=bool(field.get("math_trigger", False)))
            open_row_var = tk.BooleanVar(value=bool(field.get("open_row_trigger", False)))
            user_input_var = tk.BooleanVar(value=bool(field.get("user_input", False)))
            expand_var = tk.BooleanVar(value=bool(field.get("expand", False)))
            bold_var = tk.BooleanVar(value=bool(field.get("bold", False)))
            tb.Checkbutton(toggle_row, text="Readonly", variable=readonly_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="Derived", variable=derived_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
            tb.Checkbutton(toggle_row, text="Math Trigger", variable=math_trigger_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
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
                command=lambda current_section=section_name, current_id=field_id, label_var=label_var, widget_var=widget_var, width_var=width_var, default_var=default_var, sticky_var=sticky_var, state_var=state_var, options_source_var=options_source_var, bootstyle_var=bootstyle_var, role_var=role_var, values_var=values_var, lookup_source_var=lookup_source_var, lookup_key_role_var=lookup_key_role_var, override_toggle_role_var=override_toggle_role_var, toggle_target_role_var=toggle_target_role_var, readonly_var=readonly_var, derived_var=derived_var, math_trigger_var=math_trigger_var, open_row_var=open_row_var, user_input_var=user_input_var, expand_var=expand_var, bold_var=bold_var: self.controller.update_row_field_from_block(
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
                        "values": values_var.get(),
                        "lookup_source": lookup_source_var.get(),
                        "lookup_key_role": lookup_key_role_var.get(),
                        "override_toggle_role": override_toggle_role_var.get(),
                        "toggle_target_role": toggle_target_role_var.get(),
                        "readonly": readonly_var.get(),
                        "derived": derived_var.get(),
                        "math_trigger": math_trigger_var.get(),
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
                    text="Protected runtime fields cannot be removed while they carry required IDs or roles.",
                    style="Martin.Muted.TLabel",
                    wraplength=300,
                    justify=LEFT,
                ).pack(side=LEFT)

    def render_block_view(self, config, protected_field_ids, protected_row_field_ids, selected_item=None, guardrail_summary=None):
        self._reset_block_registries()
        for child in self.block_inner.winfo_children():
            child.destroy()

        sections = {section.get("id"): section for section in config.get("sections", []) if isinstance(section, dict)}
        header_section = sections.get("header", {})
        production_section = sections.get("production", {})
        downtime_section = sections.get("downtime", {})

        guardrail_summary = guardrail_summary or {}
        guardrail_card = tb.Labelframe(self.block_inner, text=" Guard Rails ", padding=10, style="Martin.Card.TLabelframe")
        guardrail_card.pack(fill=X, pady=(0, 10))

        routed_sections = guardrail_summary.get("routed_sections", [])
        warnings = guardrail_summary.get("warnings", [])
        notes = guardrail_summary.get("notes", [])

        if routed_sections:
            routed_text = " | ".join(
                f"{section['profile']}: {section['name']} [{section['section_type']}]"
                for section in routed_sections
            )
            tb.Label(
                guardrail_card,
                text=f"Active routed sections: {routed_text}",
                style="Martin.Section.TLabel",
                wraplength=1100,
                justify=LEFT,
            ).pack(anchor=W)

        for warning_text in warnings:
            tb.Label(
                guardrail_card,
                text=f"Warning: {warning_text}",
                bootstyle=DANGER,
                wraplength=1100,
                justify=LEFT,
            ).pack(anchor=W, pady=(6, 0))

        for note_text in notes:
            tb.Label(
                guardrail_card,
                text=note_text,
                style="Martin.Muted.TLabel",
                wraplength=1100,
                justify=LEFT,
            ).pack(anchor=W, pady=(6, 0))

        header_title = tb.Label(
            self.block_inner,
            text=str(header_section.get("name", "Header Fields")),
            font=("-size 12 -weight bold"),
            bootstyle=PRIMARY,
        )
        header_title.pack(anchor=W, pady=(0, 6))

        header_meta_row = tb.Frame(self.block_inner)
        header_meta_row.pack(fill=X, pady=(0, 6))
        tb.Label(header_meta_row, text="Section Name", bootstyle=PRIMARY).pack(side=LEFT)
        header_name_var = tk.StringVar(value=str(header_section.get("name", "Header Fields")))
        tb.Entry(header_meta_row, textvariable=header_name_var, width=24).pack(side=LEFT, padx=(6, 12))
        tb.Label(header_meta_row, text="Description", bootstyle=PRIMARY).pack(side=LEFT)
        header_description_var = tk.StringVar(value=str(header_section.get("description", "")))
        tb.Entry(header_meta_row, textvariable=header_description_var, width=24).pack(side=LEFT, padx=(6, 12))
        tb.Label(header_meta_row, text="Type", bootstyle=PRIMARY).pack(side=LEFT)
        header_section_type_var = tk.StringVar(value=str(header_section.get("section_type", "single")))
        tb.Combobox(header_meta_row, textvariable=header_section_type_var, values=("single", "repeating"), state="readonly", width=10).pack(side=LEFT, padx=(6, 12))
        tb.Label(header_meta_row, text="Profile", bootstyle=PRIMARY).pack(side=LEFT)
        header_behavior_profile_var = tk.StringVar(value=str(header_section.get("behavior_profile", "header")))
        tb.Combobox(header_meta_row, textvariable=header_behavior_profile_var, values=("header", "production", "downtime"), state="readonly", width=12).pack(side=LEFT, padx=(6, 12))
        tb.Button(
            header_meta_row,
            text="Apply Section",
            bootstyle=SUCCESS,
            command=lambda: self.controller.update_section_metadata_from_block(
                "header",
                {
                    "name": header_name_var.get(),
                    "description": header_description_var.get(),
                    "section_type": header_section_type_var.get(),
                    "behavior_profile": header_behavior_profile_var.get(),
                },
            ),
        ).pack(side=RIGHT)

        header_actions = tb.Frame(self.block_inner)
        header_actions.pack(fill=X, pady=(0, 6))
        tb.Button(header_actions, text="+ Add Header Field", bootstyle=SUCCESS, command=self.controller.add_header_field).pack(side=LEFT)

        tb.Separator(self.block_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))

        self.header_cards_container = tb.Frame(self.block_inner)
        self.header_cards_container.pack(fill=X)

        for field in config.get("header_fields", []):
            is_locked_readonly = field.get("id") == "cast_date"
            item_key = self.controller.get_field_item_key(field.get("id", ""))
            card_shell, card = self._create_card_shell(self.header_cards_container, item_key, field.get("label", "Unnamed Field"), scroll_target=self.block_canvas)
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
            state_bits.append("import=on" if field.get("import_enabled", True) else "import=off")
            state_bits.append("export=on" if field.get("export_enabled", True) else "export=off")
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
            import_enabled_var = tk.BooleanVar(value=bool(field.get("import_enabled", True)))
            export_enabled_var = tk.BooleanVar(value=bool(field.get("export_enabled", True)))

            if not is_locked_readonly:
                tb.Label(form_row, text="Width", bootstyle=PRIMARY).grid(row=0, column=6, padx=(0, 6), pady=2, sticky=W)
                tb.Entry(form_row, textvariable=width_var, width=6).grid(row=0, column=7, padx=(0, 12), pady=2, sticky=W)
                readonly_toggle = tb.Checkbutton(form_row, text="Readonly", variable=readonly_var, bootstyle="round-toggle")
                readonly_toggle.grid(row=0, column=8, padx=(0, 12), pady=2, sticky=W)

            tb.Button(
                form_row,
                text="Apply",
                bootstyle=SUCCESS,
                command=lambda field_id=field.get("id"), row_var=row_var, col_var=col_var, cell_var=cell_var, width_var=width_var, readonly_var=readonly_var, default_var=default_var, role_var=role_var, import_enabled_var=import_enabled_var, export_enabled_var=export_enabled_var: self.controller.update_header_field_from_block(
                    field_id,
                    row_var.get(),
                    col_var.get(),
                    cell_var.get(),
                    width_var.get(),
                    readonly_var.get(),
                    default_var.get(),
                    role_var.get(),
                    import_enabled_var.get(),
                    export_enabled_var.get(),
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
                tb.Checkbutton(meta_row, text="Import", variable=import_enabled_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
                tb.Checkbutton(meta_row, text="Export", variable=export_enabled_var, bootstyle="round-toggle").pack(side=LEFT, padx=(0, 10))
                if field.get("id") in protected_field_ids:
                    role_entry.configure(state="disabled")
                tb.Label(meta_row, text=f"Current: {field.get('default', '(none)')}", style="Martin.Muted.TLabel").pack(side=LEFT)

        self._render_row_field_section(
            str(production_section.get("name", "Production Row Fields")),
            "production_row_fields",
            config.get("production_row_fields", []),
            protected_row_field_ids.get("production_row_fields", set()),
            section_metadata=production_section,
        )
        self._render_row_field_section(
            str(downtime_section.get("name", "Downtime Row Fields")),
            "downtime_row_fields",
            config.get("downtime_row_fields", []),
            protected_row_field_ids.get("downtime_row_fields", set()),
            section_metadata=downtime_section,
        )
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_inner, self.block_canvas)
        self._relayout_block_cards()
        self.apply_selection(selected_item)

    def render_import_export(self, config, selected_item=None, guardrail_summary=None):
        self.mapping_card_widgets = []
        self.card_shell_scroll_targets = {
            key: value for key, value in self.card_shell_scroll_targets.items() if not str(key).startswith("mapping:")
        }
        self.card_shells = {key: value for key, value in self.card_shells.items() if not str(key).startswith("mapping:")}
        for child in self.import_export_inner.winfo_children():
            child.destroy()

        guardrail_summary = guardrail_summary or {}
        sections = {section.get("id"): section for section in config.get("sections", []) if isinstance(section, dict)}
        production_section = sections.get("production", {})
        downtime_section = sections.get("downtime", {})

        template_card = tb.Labelframe(self.import_export_inner, text=" Export Template ", padding=10, style="Martin.Card.TLabelframe")
        template_card.pack(fill=X, pady=(0, 10))
        tb.Label(
            template_card,
            text=(
                "Template path is used when export creates the workbook. Leave it blank to export into a fresh workbook."
            ),
            style="Martin.Muted.TLabel",
            wraplength=1100,
            justify=LEFT,
        ).pack(anchor=W)

        template_row = tb.Frame(template_card, style="Martin.Content.TFrame")
        template_row.pack(fill=X, pady=(8, 0))
        tb.Label(template_row, text="Template Path", bootstyle=PRIMARY).pack(side=LEFT)
        template_path_var = tk.StringVar(value=str(config.get("template_path", "")))
        tb.Entry(template_row, textvariable=template_path_var, width=72).pack(side=LEFT, padx=(8, 10), fill=X, expand=True)
        tb.Button(
            template_row,
            text="Apply Template Path",
            bootstyle=SUCCESS,
            command=lambda: self.controller.update_template_path_from_tab(template_path_var.get()),
        ).pack(side=RIGHT)

        routing_card = tb.Labelframe(self.import_export_inner, text=" Routing Summary ", padding=10, style="Martin.Card.TLabelframe")
        routing_card.pack(fill=X, pady=(0, 10))
        routed_sections = guardrail_summary.get("routed_sections", [])
        if routed_sections:
            routed_text = " | ".join(
                f"{section['profile']}: {section['name']} [{section['section_type']}]"
                for section in routed_sections
            )
            tb.Label(
                routing_card,
                text=f"Current routed sections: {routed_text}",
                style="Martin.Section.TLabel",
                wraplength=1100,
                justify=LEFT,
            ).pack(anchor=W)
        for warning_text in guardrail_summary.get("warnings", []):
            tb.Label(
                routing_card,
                text=f"Warning: {warning_text}",
                bootstyle=DANGER,
                wraplength=1100,
                justify=LEFT,
            ).pack(anchor=W, pady=(6, 0))

        mappings_title = tb.Label(self.import_export_inner, text="Workbook Column Mappings", font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        mappings_title.pack(anchor=W, pady=(0, 6))
        tb.Label(
            self.import_export_inner,
            text="Column letters, transforms, and import/export toggles now live here instead of Block View.",
            style="Martin.Muted.TLabel",
            wraplength=1100,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 6))
        tb.Separator(self.import_export_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))
        self.mapping_cards_container = tb.Frame(self.import_export_inner, style="Martin.Content.TFrame")
        self.mapping_cards_container.pack(fill=X)
        self.add_mapping_block(
            "production_mapping",
            f"{production_section.get('name', 'Production')} Mapping",
            config.get("production_mapping", {}),
            self.mapping_cards_container,
        )
        self.add_mapping_block(
            "downtime_mapping",
            f"{downtime_section.get('name', 'Downtime')} Mapping",
            config.get("downtime_mapping", {}),
            self.mapping_cards_container,
        )
        self.dispatcher.bind_mousewheel_to_widget_tree(self.import_export_inner, self.import_export_canvas)
        self._relayout_block_cards()
        self.apply_selection(selected_item)

    def add_mapping_block(self, mapping_name, title, mapping, parent):
        item_key = self.controller.get_mapping_item_key(mapping_name)
        card_shell, card = self._create_card_shell(parent, item_key, title, scroll_target=self.import_export_canvas)
        self.mapping_card_widgets.append(card_shell)
        self._bind_selectable(card_shell, item_key)

        top_row = tb.Frame(card)
        top_row.pack(fill=X, pady=(0, 6))
        tb.Label(top_row, text="Start Row", bootstyle=PRIMARY).pack(side=LEFT)
        start_row_var = tk.StringVar(value=str(mapping.get("start_row", "")))
        tb.Entry(top_row, textvariable=start_row_var, width=8).pack(side=LEFT, padx=(6, 12))
        tb.Label(top_row, text="Max Rows", bootstyle=PRIMARY).pack(side=LEFT)
        max_rows_var = tk.StringVar(value=str(mapping.get("max_rows", "")))
        tb.Entry(top_row, textvariable=max_rows_var, width=8).pack(side=LEFT, padx=(6, 12))
        columns = mapping.get("columns", {})
        column_vars = {}
        if columns:
            columns_frame = tb.Frame(card)
            columns_frame.pack(fill=X)
            columns_frame.columnconfigure(0, weight=1)
            for index, (key, value) in enumerate(columns.items()):
                row = tb.Frame(columns_frame)
                row.grid(row=index, column=0, padx=4, pady=4, sticky=EW)
                row.columnconfigure(7, weight=1)
                tb.Label(row, text=key.replace("_", " ").title(), bootstyle=PRIMARY).grid(row=0, column=0, padx=(0, 8), sticky=W)

                if isinstance(value, dict):
                    column_value = value.get("column", "")
                    import_enabled = bool(value.get("import_enabled", True))
                    export_enabled = bool(value.get("export_enabled", True))
                    import_transform = value.get("import_transform", "value")
                    export_transform = value.get("export_transform", "value")
                else:
                    column_value = value
                    import_enabled = True
                    export_enabled = True
                    import_transform = "value"
                    export_transform = "value"

                column_var = tk.StringVar(value=str(column_value))
                import_enabled_var = tk.BooleanVar(value=import_enabled)
                export_enabled_var = tk.BooleanVar(value=export_enabled)
                import_transform_var = tk.StringVar(value=str(import_transform))
                export_transform_var = tk.StringVar(value=str(export_transform))

                tb.Label(row, text="Column", bootstyle=SECONDARY).grid(row=0, column=1, padx=(0, 4), sticky=W)
                tb.Entry(row, textvariable=column_var, width=8).grid(row=0, column=2, padx=(0, 10), sticky=W)
                tb.Checkbutton(row, text="Import", variable=import_enabled_var, bootstyle="round-toggle").grid(row=0, column=3, padx=(0, 10), sticky=W)
                tb.Checkbutton(row, text="Export", variable=export_enabled_var, bootstyle="round-toggle").grid(row=0, column=4, padx=(0, 10), sticky=W)
                tb.Label(row, text="Import Transform", bootstyle=SECONDARY).grid(row=0, column=5, padx=(0, 4), sticky=W)
                tb.Combobox(row, textvariable=import_transform_var, values=("value", "code_lookup", "stop_from_duration"), state="readonly", width=16).grid(row=0, column=6, padx=(0, 10), sticky=W)
                tb.Label(row, text="Export Transform", bootstyle=SECONDARY).grid(row=0, column=7, padx=(0, 4), sticky=W)
                tb.Combobox(row, textvariable=export_transform_var, values=("value", "code_number", "duration_minutes", "bool_int", "minutes_label"), state="readonly", width=16).grid(row=0, column=8, sticky=W)

                column_vars[key] = {
                    "column": column_var,
                    "import_enabled": import_enabled_var,
                    "export_enabled": export_enabled_var,
                    "import_transform": import_transform_var,
                    "export_transform": export_transform_var,
                }
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
                max_rows_var.get(),
                {
                    key: {
                        "column": variables["column"].get(),
                        "import_enabled": variables["import_enabled"].get(),
                        "export_enabled": variables["export_enabled"].get(),
                        "import_transform": variables["import_transform"].get(),
                        "export_transform": variables["export_transform"].get(),
                    }
                    for key, variables in column_vars.items()
                },
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
        if self.get_active_editor_tab() != "preview":
            return
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

    def ask_form_details(self, title, name_prompt, initial_name="", initial_description="", default_activate=True):
        form_name = self.ask_form_name(title=title, prompt=name_prompt, initialvalue=initial_name)
        if form_name is None:
            return None
        form_name = form_name.strip()
        if not form_name:
            return {"name": "", "description": "", "activate": bool(default_activate)}

        description = simpledialog.askstring(
            title,
            "Optional description for this form definition:",
            initialvalue=initial_description,
            parent=self.parent.winfo_toplevel(),
        )
        if description is None:
            return None

        activate_now = messagebox.askyesno(
            title,
            "Activate this form immediately after saving?",
            parent=self.parent.winfo_toplevel(),
            default=(messagebox.YES if default_activate else messagebox.NO),
        )
        return {
            "name": form_name,
            "description": str(description or "").strip(),
            "activate": activate_now,
        }

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
        if field.get("math_trigger"):
            marker_parts.append("math")
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
            f"Protected: {'yes' if field.get('protected') else 'no'}",
            f"Default: {field.get('default', '(none)')}",
            f"Options Source: {field.get('options_source', '(none)')}",
            f"Lookup Source: {field.get('lookup_source', '(none)')}",
            f"Lookup Key Role: {field.get('lookup_key_role', '(none)')}",
            f"Override Toggle Role: {field.get('override_toggle_role', '(none)')}",
            f"Toggle Target Role: {field.get('toggle_target_role', '(none)')}",
            f"Values: {self._format_row_field_values(field.get('values')) or '(none)'}",
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
            bg=self._get_tk_color("layout_tooltip_bg", "#ffffff"),
            fg=self._get_tk_color("layout_tooltip_fg", "#000000"),
            highlightthickness=1,
            highlightbackground=self._get_tk_color("layout_tooltip_border", "#cccccc"),
            relief="flat",
            anchor="w",
        )
        tooltip_label.pack()

    def hide_preview_tooltip(self, _event=None):
        if self.preview_tooltip is not None:
            self.preview_tooltip.destroy()
            self.preview_tooltip = None

    def _add_row_field_preview_section(self, preview_grid_frame, section_row, column_span, section):
        grid_bg = self._get_tk_color("layout_preview_grid_bg", self.theme_tokens.get("content_bg", "#ffffff"))
        cell_bg = self._get_tk_color("layout_preview_cell_bg", "#ffffff")
        text_fg = self._get_tk_color("layout_preview_text_fg", self.theme_tokens.get("surface_fg", "#000000"))
        muted_fg = self._get_tk_color("layout_preview_muted_fg", self.theme_tokens.get("muted_fg", "#666666"))
        border = self._get_tk_color("layout_preview_border", self.theme_tokens.get("border_color", "#cccccc"))

        section_title = section.get("title", "Section")
        tb.Label(preview_grid_frame, text=f"{section_title} Row Template", bootstyle=PRIMARY).grid(
            row=section_row,
            column=0,
            columnspan=column_span,
            padx=3,
            pady=(10, 2),
            sticky=W,
        )

        description_text = str(section.get("description", "")).strip()
        fields_row = section_row + 1
        if description_text:
            tk.Label(
                preview_grid_frame,
                text=description_text,
                bg=grid_bg,
                fg=muted_fg,
                anchor="w",
                justify=LEFT,
            ).grid(
                row=fields_row,
                column=0,
                columnspan=column_span,
                padx=3,
                pady=(0, 3),
                sticky=EW,
            )
            fields_row += 1

        container = tk.Frame(preview_grid_frame, bg=grid_bg)
        container.grid(row=fields_row, column=0, columnspan=column_span, padx=3, pady=(0, 3), sticky=EW)

        fields = section.get("fields", [])
        if not fields:
            empty_label = tk.Label(container, text="No fields configured", bg=grid_bg, fg=muted_fg, anchor="w")
            empty_label.pack(anchor=W)
            return

        for column_index in range(len(fields)):
            container.columnconfigure(column_index, weight=1)

        for index, field in enumerate(fields):
            item_key = field.get("item_key")
            widget_name = str(field.get("widget", "entry") or "entry").strip().lower()
            field_width = field.get("width", 12)
            try:
                pixel_width = max(90, min(190, int(field_width) * 8))
            except (TypeError, ValueError):
                pixel_width = 120
            item_frame = tk.Frame(
                container,
                bg=cell_bg,
                highlightthickness=1,
                highlightbackground=border,
                highlightcolor=border,
                bd=0,
            )
            item_frame.grid(row=0, column=index, padx=3, pady=3, sticky=NSEW)
            item_frame.grid_propagate(False)
            item_frame.configure(width=pixel_width, height=88)
            title_label = tk.Label(
                item_frame,
                text=field.get("label", field.get("id", "Unnamed")),
                bg=cell_bg,
                fg=text_fg,
                anchor="w",
                justify=LEFT,
                wraplength=max(80, pixel_width - 12),
                font=("Segoe UI", 10, "bold"),
            )
            title_label.pack(anchor=W, padx=8, pady=(8, 2))

            if widget_name == "checkbutton":
                preview_text = "Toggle control"
            elif widget_name == "combobox":
                preview_text = self._format_row_field_values(field.get("values")) or "Dropdown selection"
            elif widget_name == "display":
                preview_text = "Derived display"
            else:
                preview_text = str(field.get("default", "")).strip() or "Text input"

            preview_fg = self._get_tk_color("layout_preview_readonly_fg", text_fg) if field.get("readonly") else text_fg
            preview_label = tk.Label(
                item_frame,
                text=preview_text,
                bg=cell_bg,
                fg=preview_fg,
                anchor="w",
                justify=LEFT,
                wraplength=max(80, pixel_width - 12),
            )
            preview_label.pack(anchor=W, padx=8, pady=(0, 4))

            meta_bits = []
            if field.get("role"):
                meta_bits.append(str(field.get("role")))
            if field.get("readonly"):
                meta_bits.append("readonly")
            if field.get("derived"):
                meta_bits.append("derived")
            if field.get("open_row_trigger"):
                meta_bits.append("open-row")
            if field.get("math_trigger"):
                meta_bits.append("math")
            if field.get("protected"):
                meta_bits.append("protected")
            if field.get("options_source"):
                meta_bits.append(f"options={field.get('options_source')}")
            if isinstance(field.get("values"), list) and field.get("values"):
                meta_bits.append(f"{len(field.get('values', []))} values")
            if not meta_bits:
                meta_bits.append("Editable field")
            meta_label = tk.Label(
                item_frame,
                text=" | ".join(meta_bits),
                bg=cell_bg,
                fg=muted_fg,
                anchor="w",
                justify=LEFT,
                wraplength=max(80, pixel_width - 12),
            )
            meta_label.pack(anchor=W, padx=8, pady=(0, 8))

            if item_key:
                self._bind_selectable(item_frame, item_key)
                self._bind_selectable(title_label, item_key)
                self._bind_selectable(preview_label, item_key)
                self._bind_selectable(meta_label, item_key)
            self.bind_preview_tooltip(item_frame, field)
            self.bind_preview_tooltip(title_label, field)
            self.bind_preview_tooltip(preview_label, field)
            self.bind_preview_tooltip(meta_label, field)
            self.preview_cells.append(
                {
                    "frame": item_frame,
                    "item_keys": [item_key] if item_key else [],
                    "labels": [(title_label, text_fg), (preview_label, preview_fg), (meta_label, muted_fg)],
                }
            )

    def _render_row_field_preview_sections(self, preview_grid_frame, preview_grid):
        sections = preview_grid.get("row_sections", [])
        if not sections:
            return
        column_span = max(2, preview_grid.get("max_col", 0) + 2)
        start_row = preview_grid.get("max_row", 0) + 2
        for index, section in enumerate(sections):
            section_row = start_row + (index * 3)
            self._add_row_field_preview_section(preview_grid_frame, section_row, column_span, section)

    def render_preview(self, preview_grid, selected_item=None):
        self.preview_after_id = None
        self.preview_cells = []
        self.hide_preview_tooltip()
        for child in self.preview_canvas.winfo_children():
            child.destroy()
        preview_grid_frame = tk.Frame(self.preview_canvas, bg=self._get_tk_color("layout_preview_grid_bg", self.theme_tokens.get("content_bg", "#ffffff")))
        preview_grid_frame.pack(anchor=NW, fill=BOTH, expand=True)
        tb.Label(preview_grid_frame, text="Header Grid", width=12, bootstyle=PRIMARY).grid(row=0, column=0, padx=3, pady=3)

        for col in range(preview_grid["max_col"] + 1):
            tb.Label(preview_grid_frame, text=f"Col {col}", width=14, bootstyle=PRIMARY).grid(row=0, column=col + 1, padx=3, pady=3, sticky=EW)

        for row in range(preview_grid["max_row"] + 1):
            tb.Label(preview_grid_frame, text=f"Row {row}", width=8, bootstyle=PRIMARY).grid(row=row + 1, column=0, padx=3, pady=3, sticky=NS)

        for cell in preview_grid["cells"]:
            row = cell["row"]
            col = cell["col"]
            cell_frame = tk.Frame(
                preview_grid_frame,
                bg=self._get_tk_color("layout_preview_cell_bg", "#ffffff"),
                highlightthickness=1,
                highlightbackground=self._get_tk_color("layout_preview_border", "#cccccc"),
                highlightcolor=self._get_tk_color("layout_preview_border", "#cccccc"),
                bd=0,
            )
            cell_frame.grid(row=row + 1, column=col + 1, padx=3, pady=3, sticky=NSEW)
            cell_frame.grid_propagate(False)
            cell_frame.configure(width=130, height=70)

            labels = []
            if cell["fields"]:
                for field in cell["fields"]:
                    foreground = self._get_tk_color("layout_preview_readonly_fg", self.theme_tokens.get("surface_fg", "#000000")) if field.get("readonly") else self._get_tk_color("layout_preview_text_fg", self.theme_tokens.get("surface_fg", "#000000"))
                    field_label = tk.Label(
                        cell_frame,
                        text=field.get("label", field.get("id", "Unnamed")),
                        bg=self._get_tk_color("layout_preview_cell_bg", "#ffffff"),
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
                    self.bind_preview_tooltip(cell_frame, field)
            else:
                empty_label = tk.Label(
                    cell_frame,
                    text="Empty cell",
                    bg=self._get_tk_color("layout_preview_cell_bg", "#ffffff"),
                    fg=self._get_tk_color("layout_preview_empty_fg", self.theme_tokens.get("muted_fg", "#666666")),
                    anchor="w",
                )
                empty_label.pack(anchor=W, pady=(8, 0))
                labels.append((empty_label, self._get_tk_color("layout_preview_empty_fg", self.theme_tokens.get("muted_fg", "#666666"))))

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
        normalized_title = str(title or "Layout Manager").strip().lower().replace(" ", "_")
        log_error(f"layout_manager.dialog.{normalized_title}", message)
        Messagebox.show_error(message, title)

    def show_validation_success(self, message="Layout JSON is valid."):
        self.dispatcher.show_toast("Validation Success", message, SUCCESS)

    def show_form_created(self, form_info):
        action_text = "Created and activated" if form_info.get("is_active") else "Created"
        self.dispatcher.show_toast("Form Created", f"{action_text} {form_info.get('name', 'the new form') }.", SUCCESS)

    def show_form_activated(self, form_info):
        self.dispatcher.show_toast("Form Activated", f"Active form set to {form_info.get('name', 'the selected form')}.", SUCCESS)

    def show_form_renamed(self, form_info):
        self.dispatcher.show_toast("Form Renamed", f"Renamed the form to {form_info.get('name', 'the selected form')}.", SUCCESS)

    def show_form_duplicated(self, form_info):
        action_text = "Created and activated" if form_info.get("is_active") else "Created"
        self.dispatcher.show_toast("Form Duplicated", f"{action_text} {form_info.get('name', 'the duplicated form') }.", SUCCESS)

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
        if self.relayout_after_id is not None:
            try:
                self.parent.after_cancel(self.relayout_after_id)
            except tk.TclError:
                pass
            self.relayout_after_id = None
        self.hide_preview_tooltip()
        try:
            self.block_inner.unbind("<Configure>")
            self.import_export_inner.unbind("<Configure>")
        except tk.TclError:
            pass
        try:
            self.parent.unbind_all("<Control-s>")
        except tk.TclError:
            pass
        return None
