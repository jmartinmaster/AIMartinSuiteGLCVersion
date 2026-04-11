import json
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, DANGER, END, EW, HORIZONTAL, INFO, LEFT, NONE, NS, NSEW, NW, PRIMARY, RIGHT, SECONDARY, SUCCESS, VERTICAL, W, X, Y
from ttkbootstrap.dialogs import Messagebox

from app.theme_manager import normalize_theme

__module_name__ = "Layout Manager"
__version__ = "1.0.4"


class LayoutManagerView:
    def __init__(self, parent, dispatcher, controller, model):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.model = model
        self.preview_after_id = None
        self.preview_tooltip = None
        self.suppress_modified_event = False
        self.setup_ui()

    def setup_ui(self):
        theme_name = normalize_theme(tb.Style.get_instance().theme.name)
        is_dark_theme = theme_name in {"darkly", "superhero"}
        self.block_canvas_bg = "#1f242b" if is_dark_theme else "#f4f6f8"
        self.preview_grid_bg = "#1f242b" if is_dark_theme else "#eef2f5"
        self.preview_cell_bg = "#2a313a" if is_dark_theme else "#ffffff"
        self.preview_muted_fg = "#d6dde5" if is_dark_theme else "#6c757d"
        self.preview_empty_fg = "#9fb0c0" if is_dark_theme else "#6c757d"
        self.preview_text_fg = "#f8f9fa" if is_dark_theme else "#212529"
        self.preview_readonly_fg = "#7cc4ff" if is_dark_theme else "#0b5ed7"
        self.preview_border = "#5f6b78" if is_dark_theme else "#8b98a5"

        self.main_container = tb.Frame(self.parent, padding=10)
        self.main_container.pack(fill=BOTH, expand=True)
        editor_frame = tb.Frame(self.main_container)
        editor_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        tb.Label(editor_frame, text="JSON Editor", font=("-size 12 -weight bold")).pack(anchor=W)
        self.source_label = tb.Label(editor_frame, bootstyle=SECONDARY)
        self.source_label.pack(anchor=W)

        self.editor_notebook = ttk.Notebook(editor_frame)
        self.editor_notebook.pack(fill=BOTH, expand=True, pady=5)

        block_tab = tb.Frame(self.editor_notebook)
        json_tab = tb.Frame(self.editor_notebook)
        self.editor_notebook.add(block_tab, text="Block View")
        self.editor_notebook.add(json_tab, text="JSON Editor")

        block_help = tb.Label(
            block_tab,
            text="Block View lets you adjust field placement without working directly in raw JSON. Use JSON Editor for advanced edits.",
            bootstyle=INFO,
        )
        block_help.pack(anchor=W, pady=(0, 5))

        block_scroll_frame = tb.Frame(block_tab)
        block_scroll_frame.pack(fill=BOTH, expand=True)
        self.block_canvas = tk.Canvas(block_scroll_frame, highlightthickness=0, background=self.block_canvas_bg)
        self.block_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.block_scrollbar = tb.Scrollbar(block_scroll_frame, orient=VERTICAL, command=self.block_canvas.yview)
        self.block_scrollbar.pack(side=RIGHT, fill=Y)
        self.block_canvas.configure(yscrollcommand=self.block_scrollbar.set)
        self.block_inner = tb.Frame(self.block_canvas)
        self.block_canvas_window = self.block_canvas.create_window((0, 0), window=self.block_inner, anchor="nw")
        self.block_inner.bind("<Configure>", self.on_block_frame_configure)
        self.block_canvas.bind("<Configure>", self.on_block_canvas_configure)

        editor_text_frame = tb.Frame(json_tab)
        editor_text_frame.pack(fill=BOTH, expand=True)
        self.text_area = tk.Text(editor_text_frame, wrap=NONE, font=("Monospace", 10), undo=True)
        self.text_area.grid(row=0, column=0, sticky=NSEW)
        y_scroll = tb.Scrollbar(editor_text_frame, orient=VERTICAL, command=self.text_area.yview)
        y_scroll.grid(row=0, column=1, sticky=NS)
        x_scroll = tb.Scrollbar(editor_text_frame, orient=HORIZONTAL, command=self.text_area.xview)
        x_scroll.grid(row=1, column=0, sticky=EW)
        editor_text_frame.rowconfigure(0, weight=1)
        editor_text_frame.columnconfigure(0, weight=1)
        self.text_area.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.text_area.bind("<<Modified>>", self.on_text_modified)

        self.preview_wrapper = tb.Labelframe(self.main_container, text=" Live Grid Preview ", padding=10)
        self.preview_wrapper.pack(side=RIGHT, fill=BOTH, expand=True, padx=5)
        self.preview_canvas = tb.Frame(self.preview_wrapper)
        self.preview_canvas.pack(fill=BOTH, expand=True)

        btn_frame = tb.Frame(editor_frame)
        btn_frame.pack(fill=X, pady=5)
        tb.Button(btn_frame, text="Reload Current", bootstyle=SECONDARY, command=self.controller.load_config).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Load Default", bootstyle=SECONDARY, command=self.controller.load_default_config).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Format JSON", bootstyle=PRIMARY, command=self.controller.format_json).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Validate JSON", bootstyle=INFO, command=self.controller.validate_editor_json).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Update Preview", bootstyle=INFO, command=self.controller.update_preview).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="Save to File", bootstyle=SUCCESS, command=self.controller.save_config).pack(side=RIGHT, padx=5)

        self.status_label = tb.Label(editor_frame, text="", bootstyle=SECONDARY)
        self.status_label.pack(anchor=W, pady=(0, 2))

        self.parent.bind_all("<Control-s>", self.on_save_shortcut)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_canvas, self.block_canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_inner, self.block_canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.text_area, self.text_area)

    def on_save_shortcut(self, _event=None):
        self.controller.save_config()
        return "break"

    def set_editor_text(self, config_data, mark_clean=True):
        self.suppress_modified_event = True
        self.text_area.delete("1.0", END)
        self.text_area.insert("1.0", self.model.serialize_config(config_data))
        self.text_area.edit_modified(False)
        self.suppress_modified_event = False
        if mark_clean:
            self.model.mark_clean()
            self.update_status("Ready")
        else:
            self.model.mark_dirty()

    def get_editor_text(self):
        return self.text_area.get("1.0", END).strip()

    def get_current_config(self):
        return self.model.parse_editor_text(self.get_editor_text())

    def on_block_frame_configure(self, _event=None):
        self.block_canvas.configure(scrollregion=self.block_canvas.bbox("all"))

    def on_block_canvas_configure(self, event):
        self.block_canvas.itemconfigure(self.block_canvas_window, width=event.width)

    def refresh_block_view(self, config):
        for child in self.block_inner.winfo_children():
            child.destroy()

        header_title = tb.Label(self.block_inner, text="Header Fields", font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        header_title.pack(anchor=W, pady=(0, 6))

        header_actions = tb.Frame(self.block_inner)
        header_actions.pack(fill=X, pady=(0, 6))
        tb.Button(header_actions, text="+ Add Header Field", bootstyle=SUCCESS, command=self.controller.add_header_field).pack(side=LEFT)

        tb.Separator(self.block_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))

        for field in config.get("header_fields", []):
            is_locked_readonly = field.get("id") == "cast_date"
            card = tb.Labelframe(self.block_inner, text=f" {field.get('label', 'Unnamed Field')} ", padding=10, style="Martin.Card.TLabelframe")
            card.pack(fill=X, pady=4)

            header_row = tb.Frame(card)
            header_row.pack(fill=X, pady=(0, 8))
            tb.Label(header_row, text=f"ID: {field.get('id', '(missing)')}", style="Martin.Section.TLabel").pack(side=LEFT)

            state_bits = []
            if field.get("readonly"):
                state_bits.append("readonly")
            if "default" in field:
                state_bits.append(f"default={field.get('default')}")
            if not state_bits:
                state_bits.append("editable")

            action_row = tb.Frame(card)
            action_row.pack(fill=X, pady=(0, 8))
            tb.Label(action_row, text=f"State: {', '.join(state_bits)}", style="Martin.Muted.TLabel").pack(side=LEFT)
            tb.Button(action_row, text="Up", bootstyle=SECONDARY, command=lambda field_id=field.get("id"): self.controller.move_header_field(field_id, -1)).pack(side=RIGHT, padx=(4, 0))
            tb.Button(action_row, text="Down", bootstyle=SECONDARY, command=lambda field_id=field.get("id"): self.controller.move_header_field(field_id, 1)).pack(side=RIGHT, padx=(4, 0))
            remove_button = tb.Button(action_row, text="Remove", bootstyle=DANGER, command=lambda field_id=field.get("id"): self.controller.remove_header_field(field_id))
            remove_button.pack(side=RIGHT, padx=(4, 0))
            if field.get("id") in self.model.protected_field_ids:
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

            if not is_locked_readonly:
                tb.Label(form_row, text="Width", bootstyle=PRIMARY).grid(row=0, column=6, padx=(0, 6), pady=2, sticky=W)
                tb.Entry(form_row, textvariable=width_var, width=6).grid(row=0, column=7, padx=(0, 12), pady=2, sticky=W)
                readonly_toggle = tb.Checkbutton(form_row, text="Readonly", variable=readonly_var, bootstyle="round-toggle")
                readonly_toggle.grid(row=0, column=8, padx=(0, 12), pady=2, sticky=W)

            tb.Button(
                form_row,
                text="Apply",
                bootstyle=SUCCESS,
                command=lambda field_id=field.get("id"), row_var=row_var, col_var=col_var, cell_var=cell_var, width_var=width_var, readonly_var=readonly_var, default_var=default_var: self.controller.update_header_field_from_block(
                    field_id,
                    row_var.get(),
                    col_var.get(),
                    cell_var.get(),
                    width_var.get(),
                    readonly_var.get(),
                    default_var.get(),
                ),
            ).grid(row=0, column=9 if not is_locked_readonly else 6, padx=(0, 8), pady=2, sticky=W)

            if is_locked_readonly:
                note_row = tb.Frame(card)
                note_row.pack(fill=X, pady=(8, 0))
                tb.Label(note_row, text="Cast Date can only be repositioned here. It stays readonly and is driven from Date.", style="Martin.Muted.TLabel").pack(side=LEFT)
            else:
                meta_row = tb.Frame(card)
                meta_row.pack(fill=X, pady=(8, 0))
                tb.Label(meta_row, text="Default", bootstyle=PRIMARY).pack(side=LEFT)
                tb.Entry(meta_row, textvariable=default_var, width=18).pack(side=LEFT, padx=(6, 12))
                tb.Label(meta_row, text=f"Current: {field.get('default', '(none)')}", style="Martin.Muted.TLabel").pack(side=LEFT)

        mappings_title = tb.Label(self.block_inner, text="Mappings", font=("-size 12 -weight bold"), bootstyle=PRIMARY)
        mappings_title.pack(anchor=W, pady=(10, 6))
        tb.Separator(self.block_inner, bootstyle=PRIMARY).pack(fill=X, pady=(0, 8))
        self.add_mapping_block("Production Mapping", config.get("production_mapping", {}), self.block_inner)
        self.add_mapping_block("Downtime Mapping", config.get("downtime_mapping", {}), self.block_inner)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.block_inner, self.block_canvas)

    def add_mapping_block(self, title, mapping, parent):
        card = tb.Labelframe(parent, text=f" {title} ", padding=10, style="Martin.Card.TLabelframe")
        card.pack(fill=X, pady=4)
        mapping_name = title.lower().replace(" ", "_")
        top_row = tb.Frame(card)
        top_row.pack(fill=X, pady=(0, 8))
        tb.Label(top_row, text="Start Row", bootstyle=PRIMARY).pack(side=LEFT)
        start_row_var = tk.StringVar(value=str(mapping.get("start_row", "")))
        tb.Entry(top_row, textvariable=start_row_var, width=8).pack(side=LEFT, padx=(6, 12))
        columns = mapping.get("columns", {})
        column_vars = {}
        if columns:
            for key, value in columns.items():
                row = tb.Frame(card)
                row.pack(fill=X, pady=2)
                tb.Label(row, text=key.replace("_", " ").title(), bootstyle=PRIMARY, width=18).pack(side=LEFT)
                column_vars[key] = tk.StringVar(value=str(value))
                tb.Entry(row, textvariable=column_vars[key], width=10).pack(side=LEFT, padx=(6, 0))
        else:
            tb.Label(card, text="No columns configured", style="Martin.Muted.TLabel").pack(anchor=W)

        tb.Button(
            card,
            text="Apply Mapping",
            bootstyle=SUCCESS,
            command=lambda mapping_name=mapping_name, start_row_var=start_row_var, column_vars=column_vars: self.controller.update_mapping_from_block(
                mapping_name,
                start_row_var.get(),
                {key: variable.get() for key, variable in column_vars.items()},
            ),
        ).pack(anchor=W, pady=(8, 0))

    def build_layout_update(self, config, status_message):
        self.set_editor_text(config, mark_clean=False)
        self.refresh_block_view(config)
        self.update_preview()
        self.update_status(status_message, INFO)

    def on_text_modified(self, _event=None):
        if self.suppress_modified_event:
            self.text_area.edit_modified(False)
            return
        if self.text_area.edit_modified():
            self.model.mark_dirty()
            self.update_status("Unsaved changes")
            self.schedule_preview_update()
            self.text_area.edit_modified(False)

    def schedule_preview_update(self):
        if self.preview_after_id:
            try:
                self.parent.after_cancel(self.preview_after_id)
            except tk.TclError:
                pass
        self.preview_after_id = self.parent.after(400, self.controller.update_preview)

    def update_status(self, message, bootstyle=SECONDARY):
        source_name = self.model.local_config if self.model.config_path == self.model.local_config else os.path.basename(self.model.internal_config)
        dirty_text = "Unsaved changes" if self.model.is_dirty else "Saved"
        self.status_label.config(text=f"{message} | Source: {source_name} | State: {dirty_text}", bootstyle=bootstyle)

    def update_source_label(self):
        if self.model.config_path == self.model.local_config:
            source_text = f"Editing local config: {self.model.local_config}"
        else:
            source_text = f"Editing packaged default: {self.model.internal_config}"
        self.source_label.config(text=source_text)

    def confirm_discard_changes(self):
        if not self.model.is_dirty:
            return True
        return messagebox.askyesno("Discard Unsaved Changes", "You have unsaved layout changes. Discard them and continue?")

    def bind_preview_tooltip(self, widget, field):
        widget.bind("<Enter>", lambda event, data=field: self.show_preview_tooltip(event, data))
        widget.bind("<Leave>", self.hide_preview_tooltip)

    def show_preview_tooltip(self, event, field):
        self.hide_preview_tooltip()
        marker_parts = []
        if field.get("readonly"):
            marker_parts.append("readonly")
        if "default" in field:
            marker_parts.append(f"default={field.get('default')}")
        marker_text = ", ".join(marker_parts) if marker_parts else "editable"
        tooltip_lines = [
            f"ID: {field.get('id', '(missing)')}",
            f"Label: {field.get('label', '(missing)')}",
            f"Grid: row {field.get('row', 0)}, col {field.get('col', 0)}",
            f"Width: {field.get('width', 10)}",
            f"State: {marker_text}",
            f"Default: {field.get('default', '(none)')}",
            f"Cell: {field.get('cell', '(none)')}",
        ]
        self.preview_tooltip = tk.Toplevel(self.preview_canvas)
        self.preview_tooltip.wm_overrideredirect(True)
        self.preview_tooltip.attributes("-topmost", True)
        self.preview_tooltip.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        tooltip_label = tb.Label(self.preview_tooltip, text="\n".join(tooltip_lines), justify=LEFT, padding=8, bootstyle="light")
        tooltip_label.pack()

    def hide_preview_tooltip(self, _event=None):
        if self.preview_tooltip is not None:
            self.preview_tooltip.destroy()
            self.preview_tooltip = None

    def update_preview(self):
        self.preview_after_id = None
        try:
            if not self.preview_canvas.winfo_exists():
                return
        except tk.TclError:
            return
        self.hide_preview_tooltip()
        for child in self.preview_canvas.winfo_children():
            child.destroy()
        try:
            config = self.get_current_config()
            fields = config.get("header_fields", [])
            max_row = max((int(field.get("row", 0)) for field in fields), default=0)
            max_col = max((int(field.get("col", 0)) for field in fields), default=0)
            preview_grid = tk.Frame(self.preview_canvas, bg=self.preview_grid_bg)
            preview_grid.pack(anchor=NW, fill=BOTH, expand=True)
            tb.Label(preview_grid, text=" ", width=6, bootstyle=PRIMARY).grid(row=0, column=0, padx=3, pady=3)
            for col in range(max_col + 1):
                tb.Label(preview_grid, text=f"Col {col}", width=14, bootstyle=PRIMARY).grid(row=0, column=col + 1, padx=3, pady=3, sticky=EW)
            field_positions = {}
            for field in fields:
                position = (int(field.get("row", 0)), int(field.get("col", 0)))
                field_positions.setdefault(position, []).append(field)
            for row in range(max_row + 1):
                tb.Label(preview_grid, text=f"Row {row}", width=8, bootstyle=PRIMARY).grid(row=row + 1, column=0, padx=3, pady=3, sticky=NS)
                for col in range(max_col + 1):
                    cell_frame = tk.Frame(preview_grid, bg=self.preview_cell_bg, highlightthickness=1, highlightbackground=self.preview_border)
                    cell_frame.grid(row=row + 1, column=col + 1, padx=3, pady=3, sticky=NSEW)
                    cell_frame.grid_propagate(False)
                    cell_frame.configure(width=130, height=70)
                    tk.Label(cell_frame, text=f"({row}, {col})", bg=self.preview_cell_bg, fg=self.preview_muted_fg, anchor="w").pack(anchor=NW)
                    fields_here = field_positions.get((row, col), [])
                    if fields_here:
                        for field in fields_here:
                            field_label = tk.Label(
                                cell_frame,
                                text=field.get("label", field.get("id", "Unnamed")),
                                bg=self.preview_cell_bg,
                                fg=self.preview_readonly_fg if field.get("readonly") else self.preview_text_fg,
                                wraplength=110,
                                justify=LEFT,
                                anchor="w",
                            )
                            field_label.pack(anchor=W, pady=(4, 0))
                            self.bind_preview_tooltip(field_label, field)
                            self.bind_preview_tooltip(cell_frame, field)
                    else:
                        tk.Label(cell_frame, text="empty", bg=self.preview_cell_bg, fg=self.preview_empty_fg, anchor="w").pack(anchor=W, pady=(8, 0))
            for col in range(max_col + 2):
                preview_grid.columnconfigure(col, weight=1)
            self.update_status(f"Preview updated: {len(fields)} header fields on a {max_row + 1}x{max_col + 1} grid", SUCCESS)
        except Exception as exc:
            tb.Label(self.preview_canvas, text=f"Preview Error: {exc}", bootstyle=DANGER).pack()
            self.update_status(f"Preview error: {exc}", DANGER)

    def show_error(self, title, message):
        Messagebox.show_error(message, title)

    def show_validation_success(self):
        self.update_status("Layout JSON is valid", SUCCESS)
        self.dispatcher.show_toast("Validation Success", "Layout JSON is valid.", SUCCESS)

    def show_save_success(self, save_path, backup_info):
        self.text_area.edit_modified(False)
        self.refresh_block_view(self.get_current_config())
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
