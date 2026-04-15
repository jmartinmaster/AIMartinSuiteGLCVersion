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
import json
import os
import time
import webbrowser

from app.views.about_qt_view import AboutQtView

__module_name__ = "About Qt Controller"
__version__ = "1.0.0"


class AboutQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.view = AboutQtView(self, self.payload)
        self.write_state(status="ready", message="About Qt window ready.")

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False):
        state_path = self.state_path
        if not state_path:
            return
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": "about",
            "updated_at": time.time(),
            "window_title": self.payload.get("window_title") or "About",
        }
        try:
            with open(state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def open_license(self):
        license_path = str(self.payload.get("license_path") or "").strip()
        if not license_path or not os.path.exists(license_path):
            self.view.show_error("License", "License file could not be found.")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(license_path)
            else:
                webbrowser.open(f"file://{license_path}")
            self.write_state(status="ready", message="Opened license document.")
        except Exception as exc:
            self.view.show_error("License", f"Could not open the license file:\n{exc}")

    def request_repack(self):
        self.view.show_info(
            "Repack Not Available",
            "Suite repacking is still handled by the Tk host shell in this migration phase.",
        )

    def poll_commands(self):
        command_path = self.command_path
        if not command_path or not os.path.exists(command_path):
            return
        try:
            with open(command_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            payload = {}
        try:
            os.remove(command_path)
        except OSError:
            pass
        action = str(payload.get("action") or "").strip().lower()
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised About Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="About Qt window closed.")