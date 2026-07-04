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
import sys
from pathlib import Path

from launcher import create_qt_application
from app.module_registry import ModuleRegistry
from app.security_service import SecurityService


def load_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as session_file:
        payload = json.load(session_file)
    if not isinstance(payload, dict):
        raise ValueError("Qt session payload must be a JSON object.")
    return payload


def run_generic_qt_session(session_path):
    session_payload = load_qt_session(session_path)
    module_name = str(session_payload.get("module") or "layout_manager").strip()
    theme_tokens = session_payload.get("theme_tokens") or {}

    application = create_qt_application(theme_tokens=theme_tokens)

    registry = ModuleRegistry()
    security = SecurityService(
        protected_modules=registry.get_protected_module_names(),
        module_allowed_roles=registry.get_module_allowed_roles(),
        hidden_modules=registry.get_hidden_security_module_names(),
    )

    if not security.authenticate_module(module_name, reason=f"Standalone Security Access for {module_name.replace('_', ' ').title()}"):
        print(f"Authentication failed or cancelled for module '{module_name}'. Standalone runtime exiting.", file=sys.stderr)
        return 1

    if module_name == "layout_manager":
        from app.controllers.layout_manager_qt_controller import LayoutManagerQtController
        controller = LayoutManagerQtController(session_payload)
    elif module_name == "internal_code_editor":
        from app.controllers.internal_code_editor_qt_controller import InternalCodeEditorQtController
        controller = InternalCodeEditorQtController(payload=session_payload)
    elif module_name == "production_log":
        from app.controllers.production_log_qt_controller import ProductionLogQtController
        controller = ProductionLogQtController(payload=session_payload)
    else:
        print(f"Module '{module_name}' is not supported for standalone session execution.", file=sys.stderr)
        return 2

    controller.show()
    return application.exec()
