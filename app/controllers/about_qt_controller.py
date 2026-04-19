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
import sys

from app.views.about_qt_view import AboutQtView

__module_name__ = "About Qt Controller"
__version__ = "1.0.0"


class AboutQtController:
    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.payload = self._build_view_payload()
        self.view = AboutQtView(self, self.payload, parent_widget=parent)
        self.view.show()

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
            return []

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

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "About - Production Logging Center",
            "title": "PRODUCTION LOGGING CENTER",
            "subtitle": "GLC Edition",
            "info_text": self.get_info_text(),
            "module_manifest": self.get_manifest_rows(),
            "can_repack": False,
            "footer_text": "Copyright © 2026 Jamie Martin",
            "theme_tokens": theme_tokens,
        }

    def show(self):
        if hasattr(self.view, "refresh_manifest"):
            self.view.refresh_manifest(self.get_manifest_rows())
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def open_license(self):
        if self.dispatcher is not None:
            self.dispatcher.open_help_document("docs/legal/LICENSE.txt")
            return
        self.view.show_error("License", "Help document dispatch is unavailable.")

    def request_repack(self):
        self.view.show_info(
            "Repack Not Available",
            "Suite repacking is still handled by the Tk host shell in this migration phase.",
        )

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        if hasattr(self.view, "refresh_manifest"):
            self.view.refresh_manifest(self.get_manifest_rows())
        if hasattr(self.view, "apply_theme"):
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