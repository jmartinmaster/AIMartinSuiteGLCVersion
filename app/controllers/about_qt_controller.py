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
import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from app.views.about_qt_view import AboutQtView

__module_name__ = "About Qt Controller"
__version__ = "2.5.2"


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
        dev_name = "Jamie Martin"
        dev_email = "jamie_martin333@live.com"
        if self.dispatcher is not None and hasattr(self.dispatcher, "runtime_settings"):
            dev_name = self.dispatcher.runtime_settings.get("developer_name", dev_name)
            dev_email = self.dispatcher.runtime_settings.get("developer_email", dev_email)
        return (
            "Author: Jamie Martin\n"
            "Your Developer: {} ({})\n"
            "License: GNU General Public License v3.0\n"
            "Location: Ludington, MI\n"
            "Environment: Windows / Portable Python 3.12"
        ).format(dev_name, dev_email)

    def get_pyqt6_notice_text(self):
        return (
            "This application uses PyQt6, the Python bindings for Qt 6 from Riverbank Computing Limited.\n"
            "PyQt6 and Qt are provided under their own licensing terms. Review the applicable PyQt6 and Qt licensing terms before repackaging or redistributing this application."
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
            yield {
                "module_name": "main",
                "module_path": "launcher",
                "fallback_display_name": "Dispatcher Core",
                "module_obj": main_module,
            }

        for module_entry in self._list_registered_modules():
            module_name = str(module_entry.get("name") or "").strip()
            if not module_name or module_name in yielded_keys:
                continue
            yielded_keys.add(module_name)
            yield {
                "module_name": module_name,
                "module_path": str(module_entry.get("module_path") or f"app.{module_name}").strip(),
                "fallback_display_name": str(module_entry.get("display_name") or module_name.replace("_", " ").title()).strip(),
                "module_obj": loaded_modules.get(module_name),
            }

        for module_name, module_obj in loaded_modules.items():
            if module_name in yielded_keys:
                continue
            yielded_keys.add(module_name)
            yield {
                "module_name": module_name,
                "module_path": f"app.{module_name}",
                "fallback_display_name": module_name.replace("_", " ").title(),
                "module_obj": module_obj,
            }

    def get_manifest_rows(self):
        dispatcher = self.dispatcher
        if dispatcher is None:
            return []

        manifest_rows = []
        for module_entry in self._iter_manifest_modules():
            module_name = module_entry.get("module_name") or "unknown"
            module_path = module_entry.get("module_path") or f"app.{module_name}"
            module_obj = module_entry.get("module_obj")
            metadata = self._resolve_manifest_metadata(
                module_name=module_name,
                module_path=module_path,
                fallback_display_name=module_entry.get("fallback_display_name") or module_name,
                module_obj=module_obj,
            )
            source_suffix = "external" if self._is_external_manifest_module(module_name, module_path, module_obj) else "built-in"
            manifest_rows.append(
                {
                    "module_name": module_name,
                    "display_name": metadata["display_name"],
                    "version": metadata["version"],
                    "source_suffix": source_suffix,
                }
            )
        return manifest_rows

    def _list_registered_modules(self):
        dispatcher = self.dispatcher
        module_registry = getattr(dispatcher, "module_registry", None)
        if module_registry is None:
            return []
        try:
            return module_registry.list_modules()
        except Exception:
            return []

    def _resolve_manifest_metadata(self, module_name, module_path, fallback_display_name, module_obj=None):
        display_name = getattr(module_obj, "__module_name__", "") if module_obj is not None else ""
        version = getattr(module_obj, "__version__", "") if module_obj is not None else ""

        access_point_metadata = self._read_module_metadata(module_path)
        if not display_name:
            display_name = access_point_metadata.get("display_name") or ""
        if not version:
            version = access_point_metadata.get("version") or ""

        if not version:
            for controller_module_path in self._get_controller_module_paths(module_name):
                controller_metadata = self._read_module_metadata(controller_module_path)
                if not display_name:
                    display_name = controller_metadata.get("display_name") or ""
                version = controller_metadata.get("version") or ""
                if version:
                    break

        return {
            "display_name": display_name or fallback_display_name or module_name,
            "version": version or "Unknown",
        }

    def _get_controller_module_paths(self, module_name):
        if not module_name or module_name == "main":
            return ()
        return (
            f"app.controllers.{module_name}_qt_controller",
            f"app.controllers.{module_name}_controller",
        )

    def _read_module_metadata(self, module_path):
        module_file = self._resolve_module_file_path(module_path)
        if not module_file or not module_file.endswith(".py"):
            return {}

        try:
            with open(module_file, "r", encoding="utf-8") as handle:
                module_source = handle.read()
        except OSError:
            return {}

        try:
            module_tree = ast.parse(module_source, filename=module_file)
        except SyntaxError:
            return {}

        metadata = {}
        metadata_field_map = {
            "__module_name__": "display_name",
            "__version__": "version",
        }
        for node in module_tree.body:
            if not isinstance(node, ast.Assign):
                continue
            string_value = self._get_string_constant(node.value)
            if string_value is None:
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                metadata_key = metadata_field_map.get(target.id)
                if metadata_key:
                    metadata[metadata_key] = string_value.strip()
        return {
            "display_name": metadata.get("display_name", ""),
            "version": metadata.get("version", ""),
        }

    def _resolve_module_file_path(self, module_path):
        try:
            module_spec = importlib.util.find_spec(module_path)
        except (ImportError, ModuleNotFoundError, ValueError):
            return ""
        if module_spec is None:
            return ""
        return getattr(module_spec, "origin", "") or ""

    @staticmethod
    def _get_string_constant(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _is_external_manifest_module(self, module_name, module_path, module_obj=None):
        dispatcher = self.dispatcher
        if dispatcher is None:
            return False
        if dispatcher.is_module_loaded_from_external(module_name, module_obj):
            return True
        overrides_enabled = getattr(dispatcher, "are_external_module_overrides_enabled", None)
        if not callable(overrides_enabled) or not overrides_enabled():
            return False
        external_root = getattr(dispatcher, "external_modules_path", "")
        module_file = self._resolve_module_file_path(module_path)
        if not external_root or not module_file:
            return False
        try:
            module_location = Path(module_file).resolve()
            external_location = Path(external_root).resolve()
            return module_location.is_relative_to(external_location)
        except Exception:
            return False

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        
        from app.security import gatekeeper
        session = gatekeeper.get_session()
        role = str(getattr(session, "role", "") or "").strip().lower()
        has_developer_access = (
            session is not None
            and gatekeeper.has_right("developer:update_configuration")
            and role in {"admin", "developer"}
        )
        
        return {
            "window_title": "About - Production Logging Center",
            "title": "PRODUCTION LOGGING CENTER",
            "subtitle": "GLC Edition",
            "info_text": self.get_info_text(),
            "pyqt6_notice_text": self.get_pyqt6_notice_text(),
            "module_manifest": self.get_manifest_rows(),
            "can_repack": False,
            "has_developer_access": has_developer_access,
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

    def open_github_issues(self):
        import webbrowser
        try:
            webbrowser.open("https://github.com/jmartinmaster/AIMartinSuiteGLCVersion/issues")
        except Exception as exc:
            self.view.show_error("GitHub Issues", f"Could not open browser:\n{exc}")

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
        if hasattr(self, "view") and self.view is not None:
            if hasattr(self.view, "controller"):
                self.view.controller = None
            self.view = None
        self.dispatcher = None
        self.parent = None