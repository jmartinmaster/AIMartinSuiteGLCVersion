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
from copy import deepcopy

from app.models.production_log_model import DEFAULT_CALCULATION_SETTINGS, DEFAULT_CALCULATION_FORMULAS, ProductionLogModel

__module_name__ = "Form Calculations"
__version__ = "1.0.1"

EDITOR_SECTIONS = [
    {
        "title": "Behavior Rules",
        "fields": [
            {
                "key": "production_minutes_rounding",
                "path": ("production_minutes_rounding",),
                "label": "Production Minute Rounding",
                "kind": "choice",
                "options": (("Floor (current default)", "floor"), ("Nearest", "nearest"), ("Ceiling", "ceil")),
                "help": "Applied after the production minutes formula resolves ((molds / rate) * 60).",
            },
            {
                "key": "shift_total_rounding",
                "path": ("shift_total_rounding",),
                "label": "Shift Minute Rounding",
                "kind": "choice",
                "options": (("Nearest (current default)", "nearest"), ("Floor", "floor"), ("Ceiling", "ceil")),
                "help": "Used by target time, shift start/end window derivation, and ghost-time balancing.",
            },
            {
                "key": "missing_rate_fallback_mode",
                "path": ("missing_rate_fallback_mode",),
                "label": "Missing Rate Fallback",
                "kind": "choice",
                "options": (("Use header Goal MPH", "header_goal"), ("Use fixed fallback MPH", "fixed_value"), ("No fallback", "no_fallback")),
                "help": "Controls what happens when a part number is not found in Rate Manager.",
            },
            {
                "key": "missing_rate_fallback_value",
                "path": ("missing_rate_fallback_value",),
                "label": "Fixed Fallback MPH",
                "kind": "entry",
                "help": "Used only when Missing Rate Fallback is set to the fixed-value option.",
            },
            {
                "key": "negative_ghost_mode",
                "path": ("negative_ghost_mode",),
                "label": "Negative Ghost Handling",
                "kind": "choice",
                "options": (("Allow negative ghost time", "allow_negative"), ("Clamp to 0", "clamp_zero")),
                "help": "Decides whether overruns are surfaced as negative ghost time or flattened to zero.",
            },
            {
                "key": "default_balance_mix_pct",
                "path": ("default_balance_mix_pct",),
                "label": "Default Balance Mix %",
                "kind": "entry",
                "help": "Default weighted downtime distribution applied when Form Loader opens or refreshes.",
            },
            {
                "key": "downtime_code_export_mode",
                "path": ("downtime_code_export_mode",),
                "label": "Downtime Code Export Mode",
                "kind": "choice",
                "options": (
                    ("Code and Description (e.g. '1 Misc Reason')", "both"),
                    ("Code Only (e.g. '1')", "code"),
                    ("Description Only (e.g. 'Misc Reason')", "description"),
                ),
                "help": "Controls how downtime codes and descriptions are formatted when exporting to Excel.",
            },
            {
                "key": "allow_overnight_downtime",
                "path": ("allow_overnight_downtime",),
                "label": "Allow overnight downtime rollover when stop time is earlier than start time",
                "kind": "bool",
                "help": "If disabled, earlier stop times are treated as invalid instead of rolling across midnight.",
            },
        ],
    },
    {
        "title": "Shift Timing",
        "fields": [
            {
                "key": "shift_1_anchor_mode",
                "path": ("shift_1_anchor_mode",),
                "label": "Shift 1 Timing Rule",
                "kind": "choice",
                "options": (("Anchor start time", "start"), ("Anchor midpoint", "midpoint"), ("Anchor end time", "end")),
                "help": "Determines whether the reference time is treated as the start, midpoint, or end of Shift 1.",
            },
            {
                "key": "shift_1_reference_time",
                "path": ("shift_1_reference_time",),
                "label": "Shift 1 Reference Time",
                "kind": "entry",
                "help": "HHMM. Example: start anchor + 0600 means Shift 1 starts at 0600.",
            },
            {
                "key": "shift_2_anchor_mode",
                "path": ("shift_2_anchor_mode",),
                "label": "Shift 2 Timing Rule",
                "kind": "choice",
                "options": (("Anchor start time", "start"), ("Anchor midpoint", "midpoint"), ("Anchor end time", "end")),
                "help": "Determines whether the reference time is treated as the start, midpoint, or end of Shift 2.",
            },
            {
                "key": "shift_2_reference_time",
                "path": ("shift_2_reference_time",),
                "label": "Shift 2 Reference Time",
                "kind": "entry",
                "help": "HHMM. Example: midpoint anchor + 1800 centers Shift 2 around 1800.",
            },
            {
                "key": "shift_3_anchor_mode",
                "path": ("shift_3_anchor_mode",),
                "label": "Shift 3 Timing Rule",
                "kind": "choice",
                "options": (("Anchor start time", "start"), ("Anchor midpoint", "midpoint"), ("Anchor end time", "end")),
                "help": "Determines whether the reference time is treated as the start, midpoint, or end of Shift 3.",
            },
            {
                "key": "shift_3_reference_time",
                "path": ("shift_3_reference_time",),
                "label": "Shift 3 Reference Time",
                "kind": "entry",
                "help": "HHMM. Example: end anchor + 0600 means Shift 3 ends at 0600.",
            },
        ],
    },
    {
        "title": "Display Targets",
        "fields": [
            {
                "key": "display_target_production_minutes_role",
                "path": ("display_targets", "production_minutes_role"),
                "label": "Production Minutes Display Role",
                "kind": "choice",
                "options": (
                    ("Duration Minutes (recommended)", "duration_minutes"),
                    ("Mold Count", "mold_count"),
                    ("Part Number", "part_number"),
                    ("Job Order", "job_order"),
                ),
                "help": "Chooses which production row role receives the calculated production minutes label.",
            },
            {
                "key": "display_target_downtime_minutes_role",
                "path": ("display_targets", "downtime_minutes_role"),
                "label": "Downtime Minutes Display Role",
                "kind": "choice",
                "options": (
                    ("Duration Minutes (recommended)", "duration_minutes"),
                    ("Cause Text", "cause_text"),
                    ("Downtime Code", "downtime_code"),
                    ("Start Clock", "start_clock"),
                    ("Stop Clock", "stop_clock"),
                ),
                "help": "Chooses which downtime row role receives the calculated downtime minutes label.",
            },
            {
                "key": "display_target_efficiency_header_role",
                "path": ("display_targets", "efficiency_header_role"),
                "label": "Efficiency Header Display Role",
                "kind": "choice",
                "options": (
                    ("Efficiency % (recommended)", "efficiency_pct"),
                    ("MTD %", "mtd_percentage"),
                    ("Total Molds", "total_molds"),
                    ("Goal Rate", "goal_rate"),
                ),
                "help": "Chooses which header role gets updated with calculated efficiency.",
            },
            {
                "key": "display_target_ghost_display_mode",
                "path": ("display_targets", "ghost_display_mode"),
                "label": "Ghost Time Display Mode",
                "kind": "choice",
                "options": (
                    ("Metrics Bar Only", "metrics_only"),
                    ("Header Field Only", "header_only"),
                    ("Metrics Bar and Header", "metrics_and_header"),
                ),
                "help": "Controls whether ghost minutes are shown only in metrics or also pushed into a header field.",
            },
            {
                "key": "display_target_ghost_header_role",
                "path": ("display_targets", "ghost_header_role"),
                "label": "Ghost Header Display Role",
                "kind": "choice",
                "options": (
                    ("Target Time", "target_time"),
                    ("Cast Date", "cast_date"),
                    ("MTD %", "mtd_percentage"),
                    ("Efficiency %", "efficiency_pct"),
                ),
                "help": "Header role used when Ghost Time Display Mode includes header output.",
            },
        ],
    },
    {
        "title": "Named Formulas",
        "fields": [
            {
                "key": "formula_context_reference",
                "kind": "info",
                "label": "Formula Value Reference",
                "value": (
                    "Variables: molds, rate, hours, goal_rate, total_molds, shift_total_minutes, "
                    "production_total_minutes, downtime_total_minutes, start_minutes, stop_minutes, "
                    "duration_minutes, day_minutes, invalid_value, allow_overnight_downtime.\n"
                    "Helpers: round_minutes(value, mode), format_clock(minutes), if_value(cond, a, b), "
                    "max_value(a, b), min_value(a, b), abs_value(value), float_value(value), int_value(value)."
                ),
                "help": "Use these runtime values and helper functions in Named Formula expressions.",
            },
            {
                "key": "formula_production_minutes",
                "path": ("formulas", "production_minutes"),
                "label": "Production Minutes Formula",
                "kind": "formula",
                "help": "Context: molds, rate, production_minutes_rounding. Helpers: round_minutes(), if_value(), max_value(), min_value(), abs_value(), float_value(), int_value().",
            },
            {
                "key": "formula_shift_total_minutes",
                "path": ("formulas", "shift_total_minutes"),
                "label": "Shift Total Minutes Formula",
                "kind": "formula",
                "help": "Context: hours, shift_total_rounding. Used by target time and shift window calculations.",
            },
            {
                "key": "formula_shift_start_time",
                "path": ("formulas", "shift_start_time"),
                "label": "Shift Start Clock Formula",
                "kind": "formula",
                "help": "Context: shift_anchor_mode, anchor_minutes, shift_total_minutes, default_start_minutes, default_end_minutes, day_minutes. Return HHMM text or minutes; format_clock() is available.",
            },
            {
                "key": "formula_shift_end_time",
                "path": ("formulas", "shift_end_time"),
                "label": "Shift End Clock Formula",
                "kind": "formula",
                "help": "Context: shift_anchor_mode, anchor_minutes, shift_total_minutes, default_start_minutes, default_end_minutes, day_minutes. Return HHMM text or minutes; format_clock() is available.",
            },
            {
                "key": "formula_downtime_minutes",
                "path": ("formulas", "downtime_minutes"),
                "label": "Downtime Minutes Formula",
                "kind": "formula",
                "help": "Context: start_minutes, stop_minutes, allow_overnight_downtime, day_minutes, invalid_value.",
            },
            {
                "key": "formula_downtime_stop_clock",
                "path": ("formulas", "downtime_stop_clock"),
                "label": "Downtime Stop Clock Formula",
                "kind": "formula",
                "help": "Context: start_minutes, duration_minutes, default_stop_minutes, day_minutes. Used when importing workbook rows that store duration minutes instead of a stop clock.",
            },
            {
                "key": "formula_ghost_minutes",
                "path": ("formulas", "ghost_minutes"),
                "label": "Ghost Minutes Formula",
                "kind": "formula",
                "help": "Context: shift_total_minutes, production_total_minutes, downtime_total_minutes. Negative ghost handling still applies after this formula.",
            },
            {
                "key": "formula_efficiency_pct",
                "path": ("formulas", "efficiency_pct"),
                "label": "Efficiency % Formula",
                "kind": "formula",
                "help": "Context: total_molds, hours, goal_rate.",
            },
        ],
    },
]


class ProductionLogCalculationsModel:
    def __init__(self):
        self.production_log_model = ProductionLogModel()
        self.data_registry = self.production_log_model.data_registry
        companion_info = self.production_log_model._resolve_calculation_companion_paths(
            config=self.production_log_model.layout_config,
        )
        self.settings_path = companion_info.get("path")
        self.settings = self.production_log_model.get_calculation_settings_copy()

    def get_settings_copy(self):
        return deepcopy(self.settings)

    def get_default_settings(self):
        return deepcopy(DEFAULT_CALCULATION_SETTINGS)

    def get_default_formulas(self):
        return deepcopy(DEFAULT_CALCULATION_FORMULAS)

    def get_editor_sections(self):
        return deepcopy(EDITOR_SECTIONS)

    def iter_editor_fields(self):
        for section in EDITOR_SECTIONS:
            for field in section.get("fields", []):
                yield field

    def flatten_settings_for_form(self, settings=None):
        source = settings if isinstance(settings, dict) else self.get_settings_copy()
        flattened = {}
        for field in self.iter_editor_fields():
            if str(field.get("kind") or "").strip().lower() == "info":
                continue
            flattened[field["key"]] = self._resolve_path_value(source, field.get("path", (field["key"],)))
        return flattened

    def inflate_form_values(self, payload):
        normalized_payload = {}
        raw_values = payload if isinstance(payload, dict) else {}
        for field in self.iter_editor_fields():
            if str(field.get("kind") or "").strip().lower() == "info":
                continue
            self._assign_path_value(
                normalized_payload,
                field.get("path", (field["key"],)),
                raw_values.get(field["key"]),
            )
        return normalized_payload

    def reload_settings(self):
        self.settings = self.production_log_model.refresh_calculation_settings()
        return self.get_settings_copy()

    def normalize_settings(self, payload=None):
        return self.production_log_model.normalize_calculation_settings(payload)

    def update_settings(self, payload):
        self.settings = self.normalize_settings(self.inflate_form_values(payload))
        return self.get_settings_copy()

    def load_settings_file(self):
        self.settings = self.production_log_model.refresh_calculation_settings()
        companion_info = self.production_log_model._resolve_calculation_companion_paths(
            config=self.production_log_model.layout_config,
        )
        self.settings_path = companion_info.get("path")
        return self.get_settings_copy()

    def save_settings_with_backup(self):
        backup_info = self.production_log_model.save_calculation_settings(self.settings)
        companion_info = self.production_log_model._resolve_calculation_companion_paths(
            config=self.production_log_model.layout_config,
        )
        self.settings_path = companion_info.get("path")
        return backup_info

    def _resolve_path_value(self, payload, path):
        current = payload
        for segment in path:
            if not isinstance(current, dict) or segment not in current:
                return None
            current = current.get(segment)
        return current

    def _assign_path_value(self, payload, path, value):
        current = payload
        for segment in path[:-1]:
            next_value = current.get(segment)
            if not isinstance(next_value, dict):
                next_value = {}
                current[segment] = next_value
            current = next_value
        current[path[-1]] = value