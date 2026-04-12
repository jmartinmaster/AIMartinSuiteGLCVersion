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
import builtins
import io
import keyword
import tkinter as tk
import tokenize
from tkinter import messagebox, ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, EW, HORIZONTAL, LEFT, NSEW, NS, RIGHT, VERTICAL, W, X, Y
from app.theme_manager import get_theme_tokens

__module_name__ = "Internal Code Editor"
__version__ = "0.1.0"


class InternalCodeEditorView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.file_options = {}
        self.definition_entries = {}
        self.theme_tokens = {}
        self.highlight_after_id = None
        self.suppress_modified_event = False
        self.index_pane_visible = True
        self.python_builtins = {name for name in dir(builtins) if not name.startswith("_")}
        self.syntax_tags = (
            "py_keyword",
            "py_string",
            "py_comment",
            "py_number",
            "py_class_name",
            "py_function_name",
            "py_method_name",
            "py_builtin",
            "py_decorator",
            "py_import_name",
            "current_definition",
        )
        self.setup_ui()

    def setup_ui(self):
        self.main_container = tb.Frame(self.parent, padding=(18, 16), style="Martin.Content.TFrame")
        self.main_container.pack(fill=BOTH, expand=True)

        tb.Label(self.main_container, text="Internal Code Editor", style="Martin.PageTitle.TLabel").pack(anchor=W)
        tb.Label(
            self.main_container,
            text="Edit Python modules in-place with native Tk search, richer token coloring, and a current-file symbol index.",
            style="Martin.Muted.TLabel",
        ).pack(anchor=W, pady=(2, 12))

        controls_card = tb.Labelframe(self.main_container, text=" Editor Controls ", padding=(14, 10), style="Martin.Card.TLabelframe")
        controls_card.pack(fill=X, pady=(0, 12))
        controls_card.columnconfigure(1, weight=1)

        self.file_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.source_var = tk.StringVar(value="")
        self.save_target_var = tk.StringVar(value="")
        self.definition_summary_var = tk.StringVar(value="Definitions will appear for the open file.")

        tb.Label(controls_card, text="File", style="Martin.Section.TLabel").grid(row=0, column=0, sticky=W, padx=(0, 10), pady=2)
        self.file_selector = tb.Combobox(controls_card, textvariable=self.file_var, state="readonly", width=48)
        self.file_selector.grid(row=0, column=1, sticky=EW, pady=2)
        self.file_selector.bind("<<ComboboxSelected>>", lambda _event: self.controller.on_file_selected())

        action_row = tb.Frame(controls_card, style="Martin.Surface.TFrame")
        action_row.grid(row=0, column=2, sticky=EW, padx=(10, 0), pady=2)
        tb.Button(action_row, text="Reload", bootstyle="secondary", command=self.controller.reload_current_file).pack(side=LEFT)
        tb.Button(action_row, text="Save", bootstyle="success", command=self.controller.save_current_file).pack(side=LEFT, padx=(8, 0))

        tb.Label(controls_card, textvariable=self.source_var, style="Martin.Muted.TLabel", wraplength=920, justify=LEFT).grid(row=1, column=0, columnspan=3, sticky=W, pady=(8, 0))
        tb.Label(controls_card, textvariable=self.save_target_var, style="Martin.Muted.TLabel", wraplength=920, justify=LEFT).grid(row=2, column=0, columnspan=3, sticky=W, pady=(2, 0))

        search_row = tb.Frame(controls_card, style="Martin.Surface.TFrame")
        search_row.grid(row=3, column=0, columnspan=3, sticky=EW, pady=(10, 0))
        tb.Label(search_row, text="Search", style="Martin.Section.TLabel").pack(side=LEFT)
        self.search_entry = tb.Entry(search_row, textvariable=self.search_var, width=32)
        self.search_entry.pack(side=LEFT, padx=(10, 8))
        tb.Button(search_row, text="Previous", bootstyle="info", command=self.controller.find_previous).pack(side=LEFT)
        tb.Button(search_row, text="Next", bootstyle="info", command=self.controller.find_next).pack(side=LEFT, padx=(8, 0))
        self.index_toggle_button = tb.Button(search_row, text="Hide Index", bootstyle="secondary", command=self.toggle_index_pane)
        self.index_toggle_button.pack(side=RIGHT)

        self.workspace_frame = tb.Frame(self.main_container, style="Martin.Content.TFrame")
        self.workspace_frame.pack(fill=BOTH, expand=True)

        self.index_card = tb.Labelframe(self.workspace_frame, text=" Definitions ", padding=(10, 10), style="Martin.Card.TLabelframe")
        self.index_card.pack(side=LEFT, fill=Y, padx=(0, 12))
        self.index_card.pack_propagate(False)
        self.index_card.configure(width=300)

        tb.Label(self.index_card, text="Current File Index", style="Martin.Section.TLabel").pack(anchor=W)
        tb.Label(self.index_card, textvariable=self.definition_summary_var, style="Martin.Muted.TLabel", wraplength=260, justify=LEFT).pack(anchor=W, pady=(4, 10))

        index_frame = tb.Frame(self.index_card, style="Martin.Surface.TFrame")
        index_frame.pack(fill=BOTH, expand=True)
        index_frame.rowconfigure(0, weight=1)
        index_frame.columnconfigure(0, weight=1)

        self.definition_tree = ttk.Treeview(index_frame, columns=("kind", "line"), show="tree headings", height=18)
        self.definition_tree.heading("#0", text="Name")
        self.definition_tree.heading("kind", text="Kind")
        self.definition_tree.heading("line", text="Line")
        self.definition_tree.column("#0", width=150, anchor="w")
        self.definition_tree.column("kind", width=80, anchor="w", stretch=False)
        self.definition_tree.column("line", width=56, anchor="center", stretch=False)
        self.definition_tree.grid(row=0, column=0, sticky=NSEW)
        self.definition_tree.bind("<<TreeviewSelect>>", lambda _event: self.controller.on_definition_selected())

        self.definition_scroll = tb.Scrollbar(index_frame, orient=VERTICAL, command=self.definition_tree.yview)
        self.definition_scroll.grid(row=0, column=1, sticky=NS)
        self.definition_tree.configure(yscrollcommand=self.definition_scroll.set)

        self.editor_card = tb.Labelframe(self.workspace_frame, text=" Python Source ", padding=(0, 0), style="Martin.Card.TLabelframe")
        self.editor_card.pack(side=RIGHT, fill=BOTH, expand=True)
        self.editor_card.rowconfigure(0, weight=1)
        self.editor_card.columnconfigure(0, weight=1)

        editor_frame = tb.Frame(self.editor_card, style="Martin.Surface.TFrame")
        editor_frame.grid(row=0, column=0, sticky=NSEW)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(1, weight=1)

        self.line_number_gutter = tk.Text(
            editor_frame,
            width=5,
            wrap="none",
            state="disabled",
            bd=0,
            relief="flat",
            highlightthickness=0,
            padx=8,
            pady=14,
            takefocus=0,
            cursor="arrow",
        )
        self.line_number_gutter.grid(row=0, column=0, sticky=NS)

        self.text_area = tk.Text(editor_frame, wrap="none", undo=True, bd=0, relief="flat", highlightthickness=0, padx=16, pady=14)
        self.text_area.grid(row=0, column=1, sticky=NSEW)
        self.text_area.bind("<<Modified>>", self.on_text_modified)
        self.text_area.bind("<Configure>", lambda _event: self.refresh_line_numbers(), add="+")

        self.y_scroll = tb.Scrollbar(editor_frame, orient=VERTICAL, command=self.on_vertical_scrollbar)
        self.y_scroll.grid(row=0, column=2, sticky=NS)
        self.x_scroll = tb.Scrollbar(editor_frame, orient=HORIZONTAL, command=self.text_area.xview)
        self.x_scroll.grid(row=1, column=1, sticky=EW)
        self.text_area.configure(yscrollcommand=self.on_text_vertical_scroll, xscrollcommand=self.x_scroll.set)

        for sequence in ("<Button-1>", "<B1-Motion>", "<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.line_number_gutter.bind(sequence, lambda _event: "break")

        self.status_label = tb.Label(self.main_container, text="", style="Martin.Muted.TLabel")
        self.status_label.pack(anchor=W, pady=(10, 0))

        self._bind_shortcuts(self.text_area)
        self._bind_shortcuts(self.search_entry)
        self._bind_shortcuts(self.file_selector)
        self._bind_shortcuts(self.definition_tree)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.text_area, self.text_area)
        self.dispatcher.bind_mousewheel_to_widget_tree(self.definition_tree, self.definition_tree)
        self.refresh_line_numbers()

    def apply_theme(self):
        self.theme_tokens = dict(get_theme_tokens(root=self.parent.winfo_toplevel()) or {})
        content_bg = self.theme_tokens.get("content_bg", "#ffffff")
        surface_bg = self.theme_tokens.get("surface_bg", content_bg)
        surface_fg = self.theme_tokens.get("surface_fg", "#000000")
        accent = self.theme_tokens.get("accent", surface_fg)
        accent_alt = self.theme_tokens.get("layout_preview_readonly_fg", accent)
        accent_soft = self.theme_tokens.get("accent_soft", surface_bg)
        banner_fg = self.theme_tokens.get("banner_fg", accent)
        muted_fg = self.theme_tokens.get("muted_fg", surface_fg)
        current_match_fg = self.theme_tokens.get("sidebar_button_active_fg", surface_fg)
        function_color = self._blend_color(accent, surface_fg, 0.18)
        class_color = self._blend_color(accent_alt, surface_fg, 0.10)
        decorator_color = self._blend_color(banner_fg, accent_alt, 0.40)
        import_color = self._blend_color(accent, surface_fg, 0.34)
        current_definition_bg = self._blend_color(accent_soft, accent, 0.22)

        self.main_container.configure(style="Martin.Content.TFrame")
        gutter_bg = self._blend_color(surface_bg, accent_soft, 0.28)
        gutter_fg = self._blend_color(muted_fg, surface_fg, 0.10)
        self.line_number_gutter.configure(
            background=gutter_bg,
            foreground=gutter_fg,
            insertbackground=gutter_fg,
            selectbackground=gutter_bg,
            selectforeground=gutter_fg,
        )
        self.text_area.configure(
            background=surface_bg,
            foreground=surface_fg,
            insertbackground=surface_fg,
            selectbackground=accent_soft,
            selectforeground=surface_fg,
        )
        self.text_area.tag_configure("py_keyword", foreground=accent)
        self.text_area.tag_configure("py_string", foreground=accent_alt)
        self.text_area.tag_configure("py_comment", foreground=muted_fg)
        self.text_area.tag_configure("py_number", foreground=banner_fg)
        self.text_area.tag_configure("py_class_name", foreground=class_color, underline=True)
        self.text_area.tag_configure("py_function_name", foreground=function_color, underline=True)
        self.text_area.tag_configure("py_method_name", foreground=accent_alt, underline=True)
        self.text_area.tag_configure("py_builtin", foreground=self._blend_color(surface_fg, accent_alt, 0.20), underline=True)
        self.text_area.tag_configure("py_decorator", foreground=decorator_color)
        self.text_area.tag_configure("py_import_name", foreground=import_color)
        self.text_area.tag_configure("current_definition", background=current_definition_bg)
        self.text_area.tag_configure("search_match", background=accent, foreground=current_match_fg)

    def set_file_options(self, entries, selected_key):
        self.file_options = {entry["label"]: entry["key"] for entry in entries}
        self.file_selector.configure(values=[entry["label"] for entry in entries], state="readonly" if entries else "disabled")
        if selected_key is not None:
            self.select_file_key(selected_key)

    def select_file_key(self, file_key):
        if not file_key:
            self.file_var.set("")
            return
        for label, mapped_key in self.file_options.items():
            if mapped_key == file_key:
                self.file_var.set(label)
                return

    def get_selected_file_key(self):
        return self.file_options.get(self.file_var.get())

    def update_file_details(self, source_text, save_target_text):
        self.source_var.set(source_text)
        self.save_target_var.set(save_target_text)

    def set_editor_text(self, text):
        self.suppress_modified_event = True
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", text)
        self.text_area.edit_modified(False)
        self.suppress_modified_event = False
        self.refresh_line_numbers()
        self.clear_search_match()
        self.clear_definition_location()

    def get_editor_text(self):
        return self.text_area.get("1.0", "end-1c")

    def get_search_text(self):
        return self.search_var.get()

    def focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")

    def find_text(self, search_text, backwards=False):
        self.clear_search_match()
        if not search_text:
            return None
        match_length = tk.IntVar(value=0)
        insertion_index = self.text_area.index("insert")
        if backwards:
            start_index = self.text_area.search(search_text, f"{insertion_index} - 1c", stopindex="1.0", backwards=True, nocase=True, count=match_length)
            if not start_index:
                start_index = self.text_area.search(search_text, "end-1c", stopindex="1.0", backwards=True, nocase=True, count=match_length)
        else:
            start_index = self.text_area.search(search_text, f"{insertion_index} + 1c", stopindex="end", nocase=True, count=match_length)
            if not start_index:
                start_index = self.text_area.search(search_text, "1.0", stopindex="end", nocase=True, count=match_length)
        if not start_index or match_length.get() <= 0:
            return None
        end_index = f"{start_index}+{match_length.get()}c"
        self.text_area.tag_add("search_match", start_index, end_index)
        self.text_area.mark_set("insert", start_index if backwards else end_index)
        self.text_area.see(start_index)
        self.text_area.focus_set()
        return start_index, end_index

    def clear_search_match(self):
        self.text_area.tag_remove("search_match", "1.0", "end")

    def set_definition_entries(self, definition_entries):
        current_selection = self.get_selected_definition_key()
        self.definition_entries = {entry["key"]: entry for entry in definition_entries}
        for item_id in self.definition_tree.get_children():
            self.definition_tree.delete(item_id)
        for entry in definition_entries:
            self.definition_tree.insert(
                "",
                "end",
                iid=entry["key"],
                text=entry["qualified_name"],
                values=(entry["kind"].title(), entry["line"]),
            )
        if current_selection and current_selection in self.definition_entries:
            self.definition_tree.selection_set(current_selection)
        elif current_selection:
            self.definition_tree.selection_remove(current_selection)

    def get_selected_definition_key(self):
        selection = self.definition_tree.selection()
        return selection[0] if selection else None

    def update_definition_summary(self, definition_count, parse_error=None):
        if parse_error:
            self.definition_summary_var.set(f"Index unavailable: {parse_error}")
            return
        noun = "definition" if definition_count == 1 else "definitions"
        self.definition_summary_var.set(f"Indexed {definition_count} {noun} for the active file.")

    def show_definition_location(self, definition_entry):
        self.clear_definition_location()
        start_index = definition_entry.get("name_start_index") or definition_entry.get("target_index")
        end_index = definition_entry.get("name_end_index") or f"{start_index} lineend"
        self.text_area.tag_add("current_definition", start_index, end_index)
        self.text_area.mark_set("insert", start_index)
        self.text_area.see(start_index)
        self.text_area.focus_set()

    def clear_definition_location(self):
        self.text_area.tag_remove("current_definition", "1.0", "end")

    def toggle_index_pane(self):
        self.set_index_pane_visible(not self.index_pane_visible)

    def set_index_pane_visible(self, visible):
        self.index_pane_visible = bool(visible)
        if self.index_pane_visible:
            if not self.index_card.winfo_manager():
                self.index_card.pack(side=LEFT, fill=Y, padx=(0, 12), before=self.editor_card)
            self.index_toggle_button.configure(text="Hide Index")
            return
        if self.index_card.winfo_manager():
            self.index_card.pack_forget()
        self.index_toggle_button.configure(text="Show Index")

    def update_status(self, message, bootstyle="secondary"):
        self.status_label.config(text=message, bootstyle=bootstyle)

    def show_error(self, title, message):
        messagebox.showerror(title, message)

    def confirm_discard_changes(self):
        return messagebox.askyesno("Discard Unsaved Changes", "You have unsaved changes in the editor. Discard them and continue?")

    def on_text_modified(self, _event=None):
        if self.suppress_modified_event:
            self.text_area.edit_modified(False)
            return
        if self.text_area.edit_modified():
            self.refresh_line_numbers()
            self.controller.handle_editor_modified()
            self.text_area.edit_modified(False)

    def refresh_line_numbers(self):
        total_lines = int(self.text_area.index("end-1c").split(".")[0])
        gutter_text = "\n".join(str(line_number) for line_number in range(1, max(total_lines, 1) + 1))
        self.line_number_gutter.configure(state="normal")
        self.line_number_gutter.delete("1.0", "end")
        self.line_number_gutter.insert("1.0", gutter_text)
        self.line_number_gutter.configure(state="disabled")

    def on_text_vertical_scroll(self, first, last):
        self.y_scroll.set(first, last)
        self.line_number_gutter.yview_moveto(first)

    def on_vertical_scrollbar(self, *args):
        self.text_area.yview(*args)
        self.line_number_gutter.yview(*args)

    def schedule_analysis_refresh(self):
        if self.highlight_after_id is not None:
            try:
                self.parent.after_cancel(self.highlight_after_id)
            except tk.TclError:
                pass
        self.highlight_after_id = self.parent.after(220, self.controller.refresh_editor_analysis)

    def refresh_syntax_highlighting(self, definition_entries=None):
        self.highlight_after_id = None
        for tag_name in self.syntax_tags:
            self.text_area.tag_remove(tag_name, "1.0", "end")

        source_text = self.get_editor_text()
        if not source_text.strip():
            return

        decorator_active = False
        import_statement_active = False
        try:
            token_stream = tokenize.generate_tokens(io.StringIO(source_text).readline)
            for token_info in token_stream:
                token_type = token_info.type
                token_string = token_info.string
                start_line, start_col = token_info.start
                end_line, end_col = token_info.end
                start_index = f"{start_line}.{start_col}"
                end_index = f"{end_line}.{end_col}"

                if decorator_active and token_type not in {tokenize.NEWLINE, tokenize.NL}:
                    self.text_area.tag_add("py_decorator", start_index, end_index)

                if token_type == tokenize.COMMENT:
                    self.text_area.tag_add("py_comment", start_index, end_index)
                elif token_type == tokenize.STRING:
                    self.text_area.tag_add("py_string", start_index, end_index)
                elif token_type == tokenize.NUMBER:
                    self.text_area.tag_add("py_number", start_index, end_index)
                elif token_type == tokenize.OP and token_string == "@":
                    decorator_active = True
                    self.text_area.tag_add("py_decorator", start_index, end_index)
                elif token_type == tokenize.NAME:
                    if token_string in {"def", "class", "return", "yield", "await"}:
                        self.text_area.tag_add("py_keyword", start_index, end_index)
                        import_statement_active = False
                    elif token_string in {"import", "from", "as"}:
                        self.text_area.tag_add("py_keyword", start_index, end_index)
                        import_statement_active = True
                    elif keyword.iskeyword(token_string):
                        self.text_area.tag_add("py_keyword", start_index, end_index)
                        import_statement_active = False
                    elif token_string in self.python_builtins:
                        self.text_area.tag_add("py_builtin", start_index, end_index)
                    elif import_statement_active:
                        self.text_area.tag_add("py_import_name", start_index, end_index)
                elif token_type in {tokenize.NEWLINE, tokenize.NL}:
                    decorator_active = False
                    import_statement_active = False
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return

        for definition_entry in definition_entries or []:
            tag_name = {
                "class": "py_class_name",
                "function": "py_function_name",
                "method": "py_method_name",
            }.get(definition_entry["kind"])
            if tag_name:
                self.text_area.tag_add(tag_name, definition_entry["name_start_index"], definition_entry["name_end_index"])

    def on_save_shortcut(self, _event=None):
        self.controller.save_current_file()
        return "break"

    def on_find_shortcut(self, _event=None):
        self.controller.focus_search()
        return "break"

    def on_find_next_shortcut(self, _event=None):
        self.controller.find_next()
        return "break"

    def on_find_previous_shortcut(self, _event=None):
        self.controller.find_previous()
        return "break"

    def _bind_shortcuts(self, widget):
        widget.bind("<Control-s>", self.on_save_shortcut, add="+")
        widget.bind("<Control-f>", self.on_find_shortcut, add="+")
        widget.bind("<F3>", self.on_find_next_shortcut, add="+")
        widget.bind("<Shift-F3>", self.on_find_previous_shortcut, add="+")

    def _blend_color(self, base_color, mix_color, mix_ratio):
        if not (self._is_hex_color(base_color) and self._is_hex_color(mix_color)):
            return base_color
        ratio = max(0.0, min(1.0, float(mix_ratio)))
        base_rgb = tuple(int(base_color[index:index + 2], 16) for index in (1, 3, 5))
        mix_rgb = tuple(int(mix_color[index:index + 2], 16) for index in (1, 3, 5))
        blended = tuple(round(base_value * (1.0 - ratio) + mix_value * ratio) for base_value, mix_value in zip(base_rgb, mix_rgb))
        return f"#{blended[0]:02x}{blended[1]:02x}{blended[2]:02x}"

    def _is_hex_color(self, color_value):
        return isinstance(color_value, str) and len(color_value) == 7 and color_value.startswith("#")

    def on_hide(self):
        return None

    def on_unload(self):
        if self.highlight_after_id is not None:
            try:
                self.parent.after_cancel(self.highlight_after_id)
            except tk.TclError:
                pass
            self.highlight_after_id = None
        return None