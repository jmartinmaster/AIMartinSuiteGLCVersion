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

from app.theme_manager import get_theme_tokens

__module_name__ = "Production Log Calculations"
__version__ = "1.0.0"


class ProductionLogCalculationsView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.status_var = tk.StringVar(value="Developer calculation profile")
        self.preview_vars = []
        self.form_vars = {
            "production_minutes_rounding": tk.StringVar(value="floor"),
            "shift_total_rounding": tk.StringVar(value="nearest"),
            "missing_rate_fallback_mode": tk.StringVar(value="header_goal"),
            "missing_rate_fallback_value": tk.StringVar(value="240"),
            "shift_1_anchor_mode": tk.StringVar(value="start"),
            "shift_1_reference_time": tk.StringVar(value="0600"),
            "shift_2_anchor_mode": tk.StringVar(value="midpoint"),
            "shift_2_reference_time": tk.StringVar(value="1800"),
            "shift_3_anchor_mode": tk.StringVar(value="end"),
            "shift_3_reference_time": tk.StringVar(value="0600"),
            "allow_overnight_downtime": tk.BooleanVar(value=True),
            "negative_ghost_mode": tk.StringVar(value="allow_negative"),
            "default_balance_mix_pct": tk.StringVar(value="100"),
        }
        self.setup_ui()

    def setup_ui(self):
        self.content_frame = tb.Frame(self.parent, padding=20, style="Martin.Content.TFrame")
        self.content_frame.pack(fill=BOTH, expand=True)

        self.page_title = tb.Label(self.content_frame, text="Production Log Calculations", style="Martin.PageTitle.TLabel")
        self.page_title.pack(anchor=W)

        self.page_subtitle = tb.Label(
            self.content_frame,
            text="Developer-only controls for Production Log calculation behavior. Per-part rates still come from Rate Manager.",
            style="Martin.Muted.TLabel",
            justify=LEFT,
            wraplength=820,
        )
        self.page_subtitle.pack(anchor=W, pady=(6, 16))

        self.profile_card = tb.Labelframe(self.content_frame, text=" Calculation Profile ", padding=(14, 10), style="Martin.Card.TLabelframe")
        self.profile_card.pack(fill=X)
        self.profile_card.columnconfigure(1, weight=1)

        row_index = 0
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Production Minute Rounding",
            self.form_vars["production_minutes_rounding"],
            (("Floor (current default)", "floor"), ("Nearest", "nearest"), ("Ceiling", "ceil")),
        )
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Shift Minute Rounding",
            self.form_vars["shift_total_rounding"],
            (("Nearest (current default)", "nearest"), ("Floor", "floor"), ("Ceiling", "ceil")),
        )
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Missing Rate Fallback",
            self.form_vars["missing_rate_fallback_mode"],
            (("Use header Goal MPH", "header_goal"), ("Use fixed fallback MPH", "fixed_value"), ("No fallback", "no_fallback")),
        )
        row_index = self._add_entry_row(
            self.profile_card,
            row_index,
            "Fixed Fallback MPH",
            self.form_vars["missing_rate_fallback_value"],
            "Used only when Missing Rate Fallback is set to fixed value.",
        )
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Negative Ghost Handling",
            self.form_vars["negative_ghost_mode"],
            (("Allow negative ghost time", "allow_negative"), ("Clamp to 0", "clamp_zero")),
        )
        row_index = self._add_entry_row(
            self.profile_card,
            row_index,
            "Default Balance Mix %",
            self.form_vars["default_balance_mix_pct"],
            "The default weighted downtime balance percentage applied when a Production Log page opens or refreshes.",
        )
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Shift 1 Timing Rule",
            self.form_vars["shift_1_anchor_mode"],
            (("Anchor start time", "start"), ("Anchor midpoint", "midpoint"), ("Anchor end time", "end")),
        )
        row_index = self._add_entry_row(
            self.profile_card,
            row_index,
            "Shift 1 Reference Time",
            self.form_vars["shift_1_reference_time"],
            "HHMM. Example: start anchor + 0600 means Shift 1 starts at 0600.",
        )
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Shift 2 Timing Rule",
            self.form_vars["shift_2_anchor_mode"],
            (("Anchor start time", "start"), ("Anchor midpoint", "midpoint"), ("Anchor end time", "end")),
        )
        row_index = self._add_entry_row(
            self.profile_card,
            row_index,
            "Shift 2 Reference Time",
            self.form_vars["shift_2_reference_time"],
            "HHMM. Example: midpoint anchor + 1800 centers Shift 2 around 1800.",
        )
        row_index = self._add_combobox_row(
            self.profile_card,
            row_index,
            "Shift 3 Timing Rule",
            self.form_vars["shift_3_anchor_mode"],
            (("Anchor start time", "start"), ("Anchor midpoint", "midpoint"), ("Anchor end time", "end")),
        )
        row_index = self._add_entry_row(
            self.profile_card,
            row_index,
            "Shift 3 Reference Time",
            self.form_vars["shift_3_reference_time"],
            "HHMM. Example: end anchor + 0600 means Shift 3 ends at 0600.",
        )

        self.overnight_row = tb.Frame(self.profile_card, style="Martin.Surface.TFrame")
        self.overnight_row.grid(row=row_index, column=0, columnspan=2, sticky=EW, pady=(8, 0))
        self.overnight_toggle = tb.Checkbutton(
            self.overnight_row,
            text="Allow overnight downtime rollover when stop time is earlier than start time",
            variable=self.form_vars["allow_overnight_downtime"],
            command=self.controller.on_form_changed,
        )
        self.overnight_toggle.pack(anchor=W)

        self.preview_card = tb.Labelframe(self.content_frame, text=" Active Formula Preview ", padding=(14, 10), style="Martin.Card.TLabelframe")
        self.preview_card.pack(fill=X, pady=(16, 0))
        self.preview_body = tb.Frame(self.preview_card, style="Martin.Surface.TFrame")
        self.preview_body.pack(fill=X)
        for _index in range(9):
            preview_var = tk.StringVar(value="")
            self.preview_vars.append(preview_var)
            tb.Label(
                self.preview_body,
                textvariable=preview_var,
                style="Martin.Section.TLabel",
                justify=LEFT,
                wraplength=820,
            ).pack(anchor=W, pady=2)

        self.note_label = tb.Label(
            self.content_frame,
            text="Saved changes apply to Production Log recalculations and future loads. Stored draft inputs remain intact, but recalculated minute fields will reflect the active profile.",
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

    def _add_combobox_row(self, parent, row_index, label_text, variable, options):
        self._add_label(parent, row_index, label_text)
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
        return row_index + 1

    def _add_entry_row(self, parent, row_index, label_text, variable, help_text):
        self._add_label(parent, row_index, label_text)
        entry_frame = tb.Frame(parent, style="Martin.Surface.TFrame")
        entry_frame.grid(row=row_index, column=1, sticky=EW, pady=6)
        entry_frame.columnconfigure(0, weight=1)
        entry = tb.Entry(entry_frame, textvariable=variable, width=18)
        entry.grid(row=0, column=0, sticky=W)
        entry.bind("<KeyRelease>", self.controller.on_form_changed, add="+")
        tb.Label(entry_frame, text=help_text, style="Martin.Muted.TLabel", justify=LEFT, wraplength=520).grid(row=1, column=0, sticky=W, pady=(4, 0))
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
        return {
            "production_minutes_rounding": self.form_vars["production_minutes_rounding"].get(),
            "shift_total_rounding": self.form_vars["shift_total_rounding"].get(),
            "missing_rate_fallback_mode": self.form_vars["missing_rate_fallback_mode"].get(),
            "missing_rate_fallback_value": self.form_vars["missing_rate_fallback_value"].get(),
            "shift_1_anchor_mode": self.form_vars["shift_1_anchor_mode"].get(),
            "shift_1_reference_time": self.form_vars["shift_1_reference_time"].get(),
            "shift_2_anchor_mode": self.form_vars["shift_2_anchor_mode"].get(),
            "shift_2_reference_time": self.form_vars["shift_2_reference_time"].get(),
            "shift_3_anchor_mode": self.form_vars["shift_3_anchor_mode"].get(),
            "shift_3_reference_time": self.form_vars["shift_3_reference_time"].get(),
            "allow_overnight_downtime": bool(self.form_vars["allow_overnight_downtime"].get()),
            "negative_ghost_mode": self.form_vars["negative_ghost_mode"].get(),
            "default_balance_mix_pct": self.form_vars["default_balance_mix_pct"].get(),
        }

    def set_form_values(self, settings):
        for key, variable in self.form_vars.items():
            value = settings.get(key)
            if isinstance(variable, tk.BooleanVar):
                variable.set(bool(value))
            else:
                variable.set("" if value is None else str(value))
        self.controller.on_form_changed()

    def set_preview_lines(self, lines):
        normalized_lines = list(lines or [])
        for index, preview_var in enumerate(self.preview_vars):
            preview_var.set(normalized_lines[index] if index < len(normalized_lines) else "")

    def set_status(self, message, _bootstyle=None):
        self.status_var.set(str(message or ""))

    def apply_theme(self):
        self.content_frame.configure(style="Martin.Content.TFrame")
        self.action_row.configure(style="Martin.Content.TFrame")
        self.preview_body.configure(style="Martin.Surface.TFrame")
        self.overnight_row.configure(style="Martin.Surface.TFrame")
        self.page_title.configure(style="Martin.PageTitle.TLabel")
        self.page_subtitle.configure(style="Martin.Muted.TLabel")
        self.note_label.configure(style="Martin.Muted.TLabel")
        self.status_label.configure(style="Martin.Muted.TLabel")
        self.content_frame.configure(padding=20)