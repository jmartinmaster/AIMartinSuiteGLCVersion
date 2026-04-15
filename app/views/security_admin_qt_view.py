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
from app.controllers.security_admin_qt_controller import SecurityAdminQtController
from app.views.settings_manager_qt_view import (
    PYQT6_AVAILABLE,
    load_settings_manager_qt_session,
)
from launcher import create_qt_application

__module_name__ = "Security Admin Qt View"
__version__ = "1.0.0"


def is_security_admin_qt_runtime_available():
    return PYQT6_AVAILABLE


def run_security_admin_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        return 2
    session_payload = load_settings_manager_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = SecurityAdminQtController(session_payload)
    controller.show()
    return application.exec()
