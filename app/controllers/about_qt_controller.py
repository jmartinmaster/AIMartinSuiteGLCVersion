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
import sys
import time
import webbrowser

from app.utils import local_or_resource_path
from app.views.about_qt_view import AboutQtView

__module_name__ = "About Qt Controller"
__version__ = "1.0.0"


class AboutQtController:
    def __init__(self, payload=None, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.embedded = parent is not None and dispatcher is not None
        self.payload = self._build_embedded_payload() if self.embedded else dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.view = AboutQtView(self, self.payload, parent_widget=parent if self.embedded else None)
        if self.embedded:
            self.view.show()
        else:
            self.write_state(status="ready", message="About Qt window ready.")

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def get_info_text(self):
        return (
            "Author: Jamie Martin\n"
            "License: GNU General Public License v3.0\n"
            "Location: Ludington, MI\n"
            "Environment: Windows / Portable Python 3.12"
        )

    def _iter_manifest_modules(self):
        dispatcher = self.dispatcher
        if dispatcher is None:
            return []

        loaded_modules = getattr(dispatcher, "loaded_modules", {}) or {}
        yielded_keys = set()

        main_module = loaded_modules.get("main")
        if main_module is not None:
            yielded_keys.add("main")
            yield "main", main_module

        preloaded_module_names = getattr(getattr(dispatcher, "model", None), "preloaded_module_names", set()) or set()
        ordered_module_names = []
        try:
            ordered_module_names.extend(dispatcher.get_user_facing_modules(apply_whitelist=False))
        except Exception:
            ordered_module_names.extend(sorted(preloaded_module_names))

        for module_name in ordered_module_names:
            if module_name in yielded_keys:
                continue
            module_obj = loaded_modules.get(module_name)
            if module_obj is None and module_name in preloaded_module_names:
                module_obj = sys.modules.get(f"app.{module_name}")
            if module_obj is None:
                continue
            yielded_keys.add(module_name)
            yield module_name, module_obj

        for module_name, module_obj in loaded_modules.items():
            if module_name in yielded_keys:
                continue
            yielded_keys.add(module_name)
            yield module_name, module_obj

    def get_manifest_rows(self):
        dispatcher = self.dispatcher
        if dispatcher is None:
            return list(self.payload.get("module_manifest") or [])

        manifest_rows = []
        for mod_key, mod_obj in self._iter_manifest_modules():
            display_name = getattr(mod_obj, "__module_name__", mod_key)
            version = getattr(mod_obj, "__version__", "Unknown")
            source_suffix = "external" if dispatcher.is_module_loaded_from_external(mod_key, mod_obj) else "built-in"
            manifest_rows.append(
                {
                    "display_name": display_name,
                    "version": version,
                    "source_suffix": source_suffix,
                }
            )
        return manifest_rows

    def _build_embedded_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "About - Production Logging Center",
            "title": "PRODUCTION LOGGING CENTER",
            "subtitle": "GLC Edition",
            "info_text": self.get_info_text(),
            "module_manifest": self.get_manifest_rows(),
            "license_path": local_or_resource_path("docs/legal/LICENSE.txt"),
            "can_repack": False,
            "footer_text": "Copyright © 2026 Jamie Martin",
            "theme_tokens": theme_tokens,
        }

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
        if self.dispatcher is not None:
            self.dispatcher.open_help_document("docs/legal/LICENSE.txt")
            return
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

    def on_hide(self):
        return None

    def on_unload(self):
        if self.embedded:
            try:
                self.view.close()
            except Exception:
                pass