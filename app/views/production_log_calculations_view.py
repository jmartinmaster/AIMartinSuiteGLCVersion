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
from ttkbootstrap.constants import BOTH, EW, LEFT, SECONDARY, W, X

__module_name__ = "Production Log Calculations"
__version__ = "1.0.0"


class ProductionLogCalculationsView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.status_var = tk.StringVar(value="Developer calculation profile")
        self.editor_sections = self.controller.get_editor_sections()
        self.form_vars = {}
        self.preview_labels = []
        self.setup_ui()

    def setup_ui(self):
        self.content_frame = tb.Frame(self.parent, padding=20, style="Martin.Content.TFrame")
        self.content_frame.pack(fill=BOTH, expand=True)

        self.page_title = tb.Label(self.content_frame, text="Production Log Calculations", style="Martin.PageTitle.TLabel")
        self.page_title.pack(anchor=W)

        self.page_subtitle = tb.Label(
            self.content_frame,
            text="Developer-only controls for Production Log calculation behavior. Per-part rates still come from Rate Manager, while named formulas now drive the live runtime and workbook import/export path.",
            style="Martin.Muted.TLabel",
            justify=LEFT,
            wraplength=820,
        )
        self.page_subtitle.pack(anchor=W, pady=(6, 16))

        for section in self.editor_sections:
            self._build_section(section)

        self.preview_card = tb.Labelframe(self.content_frame, text=" Active Formula Preview ", padding=(14, 10), style="Martin.Card.TLabelframe")
        self.preview_card.pack(fill=X, pady=(16, 0))
        self.preview_body = tb.Frame(self.preview_card, style="Martin.Surface.TFrame")
        self.preview_body.pack(fill=X)

        self.note_label = tb.Label(
            self.content_frame,
            text="Saved changes apply to Production Log recalculations, target-time normalization, and workbook import/export transforms. Stored draft inputs remain intact, but recalculated minute fields will reflect the active profile.",
            style="Martin.Muted.TLabel",
            justify=LEFT,
            wraplength=840,
        )
        self.note_label.pack(anchor=W, pady=(16, 10))

        self.action_row = tb.Frame(self.content_frame, style="Martin.Content.TFrame")
        self.action_row.pack(fill=X)
        tb.Button(self.action_row, text="Save Profile", bootstyle="success", command=self.controller.save_settings).pack(side=LEFT)
        tb.Button(self.action_row, text="Reload Saved", bootstyle="info", command=self.controller.reload_from_disk).pack(side=LEFT, padx=(8, 0))
        tb.Button(self.action_row, text="Reset Defaults", bootstyle=SECONDARY, command=self.controller.reset_defaults).pack(side=LEFT, padx=(8, 0))
        tb.Button(self.action_row, text="Open Production Log", bootstyle=SECONDARY, command=self.controller.open_production_log).pack(side=LEFT, padx=(8, 0))

        self.status_label = tb.Label(self.content_frame, textvariable=self.status_var, style="Martin.Muted.TLabel", justify=LEFT, wraplength=820)
        self.status_label.pack(anchor=W, pady=(12, 0))

        self.apply_theme()

    def _add_label(self, parent, row_index, text):
        label = tb.Label(parent, text=text, style="Martin.Section.TLabel", justify=LEFT, wraplength=280)
        label.grid(row=row_index, column=0, sticky=W, padx=(0, 14), pady=6)
        return label

    def _build_section(self, section):
        card = tb.Labelframe(
            self.content_frame,
            text=f" {section.get('title', 'Section')} ",
            padding=(14, 10),
            style="Martin.Card.TLabelframe",
        )
        card.pack(fill=X, pady=(0, 12))
        card.columnconfigure(1, weight=1)

        row_index = 0
        for field in section.get("fields", []):
            row_index = self._add_field_row(card, row_index, field)

    def _add_field_row(self, parent, row_index, field):
        field_kind = field.get("kind", "entry")
        if field_kind == "choice":
            return self._add_combobox_row(parent, row_index, field)
        if field_kind == "bool":
            return self._add_bool_row(parent, row_index, field)
        return self._add_entry_row(parent, row_index, field)

    def _add_combobox_row(self, parent, row_index, field):
        variable = tk.StringVar(value="")
        self.form_vars[field["key"]] = variable
        self._add_label(parent, row_index, field.get("label", field["key"]))
        options = field.get("options", ())
        combobox = tb.Combobox(parent, state="readonly", width=34, textvariable=variable, values=[label for label, _value in options])
        combobox.grid(row=row_index, column=1, sticky=EW, pady=6)
        value_map = {label: value for label, value in options}
        reverse_map = {value: label for label, value in options}
        combobox.bind(
            "<<ComboboxSelected>>",
            lambda _event, current_var=variable, current_map=value_map: self._normalize_combobox_value(current_var, current_map),
            add="+",
        )
        variable.trace_add("write", lambda *_args, current_var=variable, current_reverse=reverse_map: self._sync_combobox_label(combobox, current_var, current_reverse))
        self._sync_combobox_label(combobox, variable, reverse_map)
        help_text = field.get("help")
        if help_text:
            tb.Label(parent, text=help_text, style="Martin.Muted.TLabel", justify=LEFT, wraplength=520).grid(row=row_index + 1, column=1, sticky=W, pady=(0, 6))
            return row_index + 2
        return row_index + 1

    def _add_entry_row(self, parent, row_index, field):
        variable = tk.StringVar(value="")
        self.form_vars[field["key"]] = variable
        self._add_label(parent, row_index, field.get("label", field["key"]))
        entry_frame = tb.Frame(parent, style="Martin.Surface.TFrame")
        entry_frame.grid(row=row_index, column=1, sticky=EW, pady=6)
        entry_frame.columnconfigure(0, weight=1)
        entry_width = 72 if field.get("kind") == "formula" else 18
        entry = tb.Entry(entry_frame, textvariable=variable, width=entry_width)
        entry.grid(row=0, column=0, sticky=W)
        entry.bind("<KeyRelease>", self.controller.on_form_changed, add="+")
        help_text = field.get("help", "")
        if help_text:
            tb.Label(entry_frame, text=help_text, style="Martin.Muted.TLabel", justify=LEFT, wraplength=520).grid(row=1, column=0, sticky=W, pady=(4, 0))
        return row_index + 1

    def _add_bool_row(self, parent, row_index, field):
        variable = tk.BooleanVar(value=False)
        self.form_vars[field["key"]] = variable
        row_frame = tb.Frame(parent, style="Martin.Surface.TFrame")
        row_frame.grid(row=row_index, column=0, columnspan=2, sticky=EW, pady=(8, 0))
        tb.Checkbutton(
            row_frame,
            text=field.get("label", field["key"]),
            variable=variable,
            command=self.controller.on_form_changed,
        ).pack(anchor=W)
        help_text = field.get("help")
        if help_text:
            tb.Label(row_frame, text=help_text, style="Martin.Muted.TLabel", justify=LEFT, wraplength=720).pack(anchor=W, pady=(4, 0))
        return row_index + 1

    def _normalize_combobox_value(self, variable, value_map):
        current_value = variable.get()
        if current_value in value_map:
            variable.set(value_map[current_value])
        self.controller.on_form_changed()

    def _sync_combobox_label(self, combobox, variable, reverse_map):
        current_value = variable.get()
        if current_value in reverse_map:
            combobox.set(reverse_map[current_value])

    def get_form_values(self):
        values = {}
        for key, variable in self.form_vars.items():
            if isinstance(variable, tk.BooleanVar):
                values[key] = bool(variable.get())
            else:
                values[key] = variable.get()
        return values

    def set_form_values(self, settings):
        for key, variable in self.form_vars.items():
            value = settings.get(key)
            if isinstance(variable, tk.BooleanVar):
                variable.set(bool(value))
            else:
                variable.set("" if value is None else str(value))
        self.controller.on_form_changed()

    def set_preview_lines(self, lines):
        for label in self.preview_labels:
            label.destroy()
        self.preview_labels = []
        for line in list(lines or []):
            label = tb.Label(
                self.preview_body,
                text=str(line),
                style="Martin.Section.TLabel",
                justify=LEFT,
                wraplength=820,
            )
            label.pack(anchor=W, pady=2)
            self.preview_labels.append(label)

    def set_status(self, message, _bootstyle=None):
        self.status_var.set(str(message or ""))

    def apply_theme(self):
        self.content_frame.configure(style="Martin.Content.TFrame")
        self.action_row.configure(style="Martin.Content.TFrame")
        self.preview_body.configure(style="Martin.Surface.TFrame")
        self.page_title.configure(style="Martin.PageTitle.TLabel")
        self.page_subtitle.configure(style="Martin.Muted.TLabel")
        self.note_label.configure(style="Martin.Muted.TLabel")
        self.status_label.configure(style="Martin.Muted.TLabel")
        self.content_frame.configure(padding=20)