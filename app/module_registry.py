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

from app.utils import local_or_resource_path

__module_name__ = "Module Registry"
__version__ = "1.0.0"

MODULE_REGISTRY_RELATIVE_PATH = os.path.join("app", "module_registry.json")
VALID_NAVIGATION_GROUPS = {"top", "middle", "bottom", "none"}


class ModuleRegistryError(RuntimeError):
    pass


class ModuleRegistry:
    def __init__(self, registry_path=None):
        self.registry_path = registry_path or local_or_resource_path(MODULE_REGISTRY_RELATIVE_PATH)
        self._payload = None
        self._module_map = None

    def _load_registry_payload(self):
        if self._payload is not None and self._module_map is not None:
            return self._payload

        try:
            with open(self.registry_path, "r", encoding="utf-8") as handle:
                raw_payload = json.load(handle)
        except OSError as exc:
            raise ModuleRegistryError(f"Could not read module registry at {self.registry_path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ModuleRegistryError(f"Module registry is not valid JSON: {exc}") from exc

        self._payload, self._module_map = self._normalize_payload(raw_payload)
        return self._payload

    def _normalize_payload(self, payload):
        if not isinstance(payload, dict):
            raise ModuleRegistryError("Module registry payload must be a JSON object.")

        raw_modules = payload.get("modules")
        if not isinstance(raw_modules, list) or not raw_modules:
            raise ModuleRegistryError("Module registry must define a non-empty 'modules' list.")

        modules = []
        module_map = {}
        default_initial_name = None

        for index, raw_module in enumerate(raw_modules, start=1):
            if not isinstance(raw_module, dict):
                raise ModuleRegistryError(f"Module registry item {index} must be an object.")

            module_name = str(raw_module.get("name") or "").strip()
            if not module_name:
                raise ModuleRegistryError(f"Module registry item {index} is missing a name.")
            if module_name in module_map:
                raise ModuleRegistryError(f"Module registry contains duplicate module '{module_name}'.")

            display_name = str(raw_module.get("display_name") or module_name.replace("_", " ").title()).strip()
            module_path = str(raw_module.get("module_path") or f"app.{module_name}").strip()
            navigation_visible = bool(raw_module.get("navigation_visible", False))
            navigation_group = str(raw_module.get("navigation_group") or ("middle" if navigation_visible else "none")).strip().lower()
            if navigation_group not in VALID_NAVIGATION_GROUPS:
                raise ModuleRegistryError(
                    f"Module '{module_name}' uses invalid navigation_group '{navigation_group}'."
                )
            if not navigation_visible:
                navigation_group = "none"

            allowed_roles = []
            for raw_role in raw_module.get("allowed_roles", []) or []:
                role_name = str(raw_role or "").strip().lower()
                if role_name and role_name not in allowed_roles:
                    allowed_roles.append(role_name)

            normalized_module = {
                "name": module_name,
                "module_path": module_path,
                "display_name": display_name,
                "navigation_visible": navigation_visible,
                "navigation_group": navigation_group,
                "launcher_visible": bool(raw_module.get("launcher_visible", False)) and navigation_visible,
                "persistable": bool(raw_module.get("persistable", navigation_visible)),
                "always_persistent": bool(raw_module.get("always_persistent", False)),
                "protected": bool(raw_module.get("protected", False)),
                "hidden_until_authorized": bool(raw_module.get("hidden_until_authorized", False)),
                "preload_enabled": bool(raw_module.get("preload_enabled", navigation_visible)),
                "allowed_roles": tuple(allowed_roles),
                "default_initial": bool(raw_module.get("default_initial", False)),
            }

            if normalized_module["default_initial"]:
                if default_initial_name is not None:
                    raise ModuleRegistryError(
                        f"Module registry defines multiple default modules: '{default_initial_name}' and '{module_name}'."
                    )
                default_initial_name = module_name

            modules.append(normalized_module)
            module_map[module_name] = normalized_module

        if default_initial_name is None:
            if "production_log" in module_map and module_map["production_log"]["navigation_visible"]:
                default_initial_name = "production_log"
            else:
                default_initial_name = next(
                    (module["name"] for module in modules if module["navigation_visible"]),
                    modules[0]["name"],
                )

        normalized_payload = {
            "schema_version": int(payload.get("schema_version") or 1),
            "default_initial_module": default_initial_name,
            "modules": tuple(modules),
        }
        return normalized_payload, module_map

    def list_modules(self):
        payload = self._load_registry_payload()
        return [dict(module) for module in payload["modules"]]

    def get_module(self, module_name):
        self._load_registry_payload()
        if module_name not in self._module_map:
            raise ModuleRegistryError(f"Module '{module_name}' is not registered.")
        return dict(self._module_map[module_name])

    def get_module_path(self, module_name):
        return self.get_module(module_name).get("module_path") or f"app.{module_name}"

    def get_module_display_name(self, module_name):
        return self.get_module(module_name).get("display_name") or str(module_name).replace("_", " ").title()

    def get_navigation_group(self, module_name):
        return self.get_module(module_name).get("navigation_group", "none")

    def get_default_initial_module_name(self):
        payload = self._load_registry_payload()
        return payload["default_initial_module"]

    def get_managed_module_names(self):
        payload = self._load_registry_payload()
        return [module["name"] for module in payload["modules"]]

    def get_navigation_module_names(self):
        return [module["name"] for module in self.list_modules() if module.get("navigation_visible")]

    def get_non_navigation_module_names(self):
        return [module["name"] for module in self.list_modules() if not module.get("navigation_visible")]

    def get_launcher_module_names(self):
        return [module["name"] for module in self.list_modules() if module.get("launcher_visible")]

    def get_preload_module_names(self):
        return [module["name"] for module in self.list_modules() if module.get("preload_enabled")]

    def get_always_persistent_module_names(self):
        return [module["name"] for module in self.list_modules() if module.get("always_persistent")]

    def get_protected_module_names(self):
        return [module["name"] for module in self.list_modules() if module.get("protected")]

    def get_hidden_security_module_names(self):
        return [module["name"] for module in self.list_modules() if module.get("hidden_until_authorized")]

    def get_module_allowed_roles(self):
        role_map = {}
        for module in self.list_modules():
            if module.get("allowed_roles"):
                role_map[module["name"]] = set(module.get("allowed_roles", ()))
        return role_map

    def is_navigation_module(self, module_name):
        return bool(self.get_module(module_name).get("navigation_visible"))

    def is_module_persistable(self, module_name):
        return bool(self.get_module(module_name).get("persistable"))

    def is_module_always_persistent(self, module_name):
        return bool(self.get_module(module_name).get("always_persistent"))


def get_launcher_module_names():
    return tuple(ModuleRegistry().get_launcher_module_names())