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
import ttkbootstrap as tb

__module_name__ = "Qt Module Bridge View"
__version__ = "1.0.0"


class QtModuleBridgeView:
    def __init__(self, parent, dispatcher, controller, bridge_config):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.controller.view = self
        self.bridge_config = dict(bridge_config or {})
        self.main_frame = tb.Frame(parent, style="Martin.Content.TFrame", padding=20)
        self.main_frame.pack(fill="both", expand=True)
        self._build_ui()
        self.controller.open_or_raise_qt_window()
        self._poll_state()

    def _build_ui(self):
        tb.Label(
            self.main_frame,
            text=str(self.bridge_config.get("title") or "Qt Runtime"),
            style="Martin.PageTitle.TLabel",
        ).pack(anchor="w")
        tb.Label(
            self.main_frame,
            text=str(self.bridge_config.get("subtitle") or "This module is running in a dedicated PyQt6 window."),
            style="Martin.Subtitle.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(4, 14))

        controls = tb.Frame(self.main_frame, style="Martin.Content.TFrame")
        controls.pack(fill="x", pady=(0, 12))
        tb.Button(
            controls,
            text=str(self.bridge_config.get("open_button_text") or "Open / Raise Qt Window"),
            bootstyle="primary",
            command=self.controller.open_or_raise_qt_window,
        ).pack(side="left")
        tb.Button(
            controls,
            text=str(self.bridge_config.get("restart_button_text") or "Restart Qt Window"),
            bootstyle="warning",
            command=self.controller.restart_qt_window,
        ).pack(side="left", padx=(8, 0))

        status_card = tb.Labelframe(
            self.main_frame,
            text=str(self.bridge_config.get("status_title") or "Qt Runtime Status"),
            style="Martin.Card.TLabelframe",
            padding=(14, 10),
        )
        status_card.pack(fill="x")
        self.status_label = tb.Label(
            status_card,
            text=str(self.bridge_config.get("initial_status") or "Launching Qt window..."),
            style="Martin.Section.TLabel",
        )
        self.status_label.pack(anchor="w")
        self.message_label = tb.Label(
            status_card,
            text="Waiting for state...",
            style="Martin.Muted.TLabel",
            wraplength=900,
            justify="left",
        )
        self.message_label.pack(anchor="w", pady=(6, 0))

    def _poll_state(self):
        state = self.controller.read_runtime_state()
        if not isinstance(state, dict):
            state = {}
        if hasattr(self.controller, "handle_runtime_state"):
            try:
                self.controller.handle_runtime_state(state)
            except Exception:
                pass
        status = str(state.get("status") or "launching").title()
        self.status_label.configure(text=f"Status: {status}")
        self.message_label.configure(text=str(state.get("message") or "Waiting for state..."))
        try:
            self.main_frame.after(900, self._poll_state)
        except Exception:
            pass

    def on_hide(self):
        return None

    def on_unload(self):
        self.controller.stop_qt_window()

    def apply_theme(self):
        return None