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
from ttkbootstrap.constants import INFO, SUCCESS

from app.models.production_log_calculations_model import ProductionLogCalculationsModel
from app.views.production_log_calculations_qt_view import ProductionLogCalculationsQtView

__module_name__ = "Production Log Calculations Qt Controller"
__version__ = "1.1.0"


class ProductionLogCalculationsQtController:
    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.model = ProductionLogCalculationsModel()
        self.payload = self._build_view_payload()
        self.view = ProductionLogCalculationsQtView(self, self.payload, parent_widget=parent)
        self.load_into_view(initial=True)
        self.view.show()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "Production Log Calculations - Production Logging Center",
            "title": "Production Log Calculations",
            "subtitle": (
                "Developer controls for named formulas and runtime calculation behavior in the shared PyQt6 workspace."
            ),
            "theme_tokens": theme_tokens,
        }

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def load_into_view(self, initial=False):
        settings = self.model.reload_settings()
        self.view.set_form_values(self.model.flatten_settings_for_form(settings))
        self.view.set_preview_lines(self.build_preview_lines(settings))
        message = "Production Log Calculations ready." if initial else "Loaded active calculation profile."
        self.view.set_status(message, INFO)

    def reload_from_disk(self):
        settings = self.model.load_settings_file()
        self.view.set_form_values(self.model.flatten_settings_for_form(settings))
        self.view.set_preview_lines(self.build_preview_lines(settings))
        self.view.set_status("Reloaded calculation profile from disk.", INFO)

    def save_settings(self):
        settings = self.model.update_settings(self.view.get_form_values())
        self.model.save_settings_with_backup()
        self.view.set_form_values(self.model.flatten_settings_for_form(settings))
        self.view.set_preview_lines(self.build_preview_lines(settings))
        if self.dispatcher is not None:
            self.dispatcher.notify_production_log_calculation_settings_changed()
        self.view.set_status("Saved the developer calculation profile and refreshed open Production Log pages.", SUCCESS)
        self.view.show_toast(
            "Production Log Calculations",
            "Saved calculation behavior and refreshed open Production Log pages.",
            SUCCESS,
        )

    def reset_defaults(self):
        defaults = self.model.get_default_settings()
        self.view.set_form_values(self.model.flatten_settings_for_form(defaults))
        self.view.set_preview_lines(self.build_preview_lines(defaults))
        self.view.set_status("Restored the default values in the editor. Save to make them active.", INFO)

    def on_form_changed(self, *_args):
        self.view.set_preview_lines(self.build_preview_lines(self.view.get_form_values()))

    def open_production_log(self):
        if self.dispatcher is not None:
            self.dispatcher.load_module("production_log")
            return
        self.view.show_info("Open Production Log", "Host navigation is unavailable.")

    def build_preview_lines(self, settings):
        fallback_mode = settings.get("missing_rate_fallback_mode", "header_goal")
        if fallback_mode == "fixed_value":
            fallback_label = f"Use fixed fallback rate {self._format_number(settings.get('missing_rate_fallback_value', 240.0))} mph"
        elif fallback_mode == "no_fallback":
            fallback_label = "No fallback rate; unresolved part numbers produce 0 production minutes"
        else:
            fallback_label = "Use the header Goal MPH when a part number is missing from Rate Manager"

        overnight_label = "Allow overnight rollover when downtime stop time is earlier than start time" if settings.get("allow_overnight_downtime", True) else "Treat earlier downtime stop times as invalid instead of rolling overnight"
        ghost_label = "Keep negative ghost time to surface shift overruns" if settings.get("negative_ghost_mode") == "allow_negative" else "Clamp ghost time to 0 when production and downtime exceed shift minutes"
        formulas = settings.get("formulas", {}) if isinstance(settings, dict) else {}

        return [
            f"Production minutes: round ((molds / rate) * 60) using {settings.get('production_minutes_rounding', 'floor')}",
            f"Shift total minutes: round (hours * 60) using {settings.get('shift_total_rounding', 'nearest')}",
            f"Missing rate fallback: {fallback_label}",
            f"Ghost time rule: {ghost_label}",
            f"Downtime rule: {overnight_label}",
            f"Default balance mix: {self._format_number(settings.get('default_balance_mix_pct', 100.0))}% weighted downtime distribution",
            f"Shift 1 timing: {settings.get('shift_1_anchor_mode', 'start')} anchor at {settings.get('shift_1_reference_time', '0600')}",
            f"Shift 2 timing: {settings.get('shift_2_anchor_mode', 'midpoint')} anchor at {settings.get('shift_2_reference_time', '1800')}",
            f"Shift 3 timing: {settings.get('shift_3_anchor_mode', 'end')} anchor at {settings.get('shift_3_reference_time', '0600')}",
            f"Formula production_minutes = {formulas.get('production_minutes', '')}",
            f"Formula shift_total_minutes = {formulas.get('shift_total_minutes', '')}",
            f"Formula shift_start_time = {formulas.get('shift_start_time', '')}",
            f"Formula shift_end_time = {formulas.get('shift_end_time', '')}",
            f"Formula downtime_minutes = {formulas.get('downtime_minutes', '')}",
            f"Formula downtime_stop_clock = {formulas.get('downtime_stop_clock', '')}",
            f"Formula ghost_minutes = {formulas.get('ghost_minutes', '')}",
            f"Formula efficiency_pct = {formulas.get('efficiency_pct', '')}",
        ]

    def _format_number(self, value):
        try:
            numeric_value = float(value)
        except Exception:
            return str(value)
        if numeric_value.is_integer():
            return str(int(numeric_value))
        return f"{numeric_value:.2f}".rstrip("0").rstrip(".")

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})

    def handle_close(self):
        return None

    def on_hide(self):
        return None

    def on_unload(self):
        try:
            self.view.close()
        except Exception:
            pass
