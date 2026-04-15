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
from functools import partial

from app.module_registry import ModuleRegistry
from app.qt_module_runtime import QtModuleRuntimeManager
from app.theme_manager import get_theme_tokens, normalize_theme

__module_name__ = "PyQt6 Host Shell"
__version__ = "0.1.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QPlainTextEdit,
        QSizePolicy,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QFrame = None
    QFont = None
    QHBoxLayout = None
    QLabel = None
    QMainWindow = object
    QPushButton = None
    QPlainTextEdit = None
    QSizePolicy = None
    QStatusBar = None
    QTimer = None
    QVBoxLayout = None
    QWidget = None
    PYQT6_AVAILABLE = False


def is_pyqt6_host_shell_available():
    return PYQT6_AVAILABLE


class PyQt6HostShellView(QMainWindow):
    def __init__(self, theme_name, runtime_settings, initial_module_name=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.theme_name = normalize_theme(theme_name)
        self.runtime_settings = dict(runtime_settings or {})
        self.theme_tokens = get_theme_tokens(theme_name=self.theme_name)
        self.module_registry = ModuleRegistry()
        self.runtime_managers = {}
        self.module_buttons = {}
        self.module_catalog = self._build_module_catalog()
        self.active_module_name = None
        self._build_ui()

        self.state_timer = QTimer(self)
        self.state_timer.setInterval(900)
        self.state_timer.timeout.connect(self._poll_runtime_state)
        self.state_timer.start()

        initial = self._resolve_initial_module_name(initial_module_name)
        if initial is not None:
            self.open_or_raise_module(initial, restart=False)

    def _build_module_catalog(self):
        modules = []
        whitelist = set(self.runtime_settings.get("module_whitelist") or [])
        whitelist_enabled = bool(whitelist)

        group_order = {"top": 0, "middle": 1, "bottom": 2, "none": 3}

        for module in self.module_registry.list_modules():
            if not module.get("navigation_visible"):
                continue
            module_name = str(module.get("name") or "")
            if not module_name:
                continue
            if module.get("hidden_until_authorized"):
                continue
            if whitelist_enabled and module_name not in whitelist:
                continue
            modules.append(
                {
                    "name": module_name,
                    "display_name": str(module.get("display_name") or module_name.replace("_", " ").title()),
                    "navigation_group": str(module.get("navigation_group") or "middle"),
                    "default_initial": bool(module.get("default_initial", False)),
                }
            )

        modules.sort(key=lambda item: (group_order.get(item.get("navigation_group"), 3), item.get("display_name")))
        return modules

    def _resolve_initial_module_name(self, requested_name):
        module_names = [entry["name"] for entry in self.module_catalog]
        if not module_names:
            return None
        if requested_name in module_names:
            return requested_name

        default_name = self.module_registry.get_default_initial_module_name()
        if default_name in module_names:
            return default_name
        return module_names[0]

    def _build_ui(self):
        self.setWindowTitle("Production Logging Center - PyQt6 Host Shell")
        self.resize(1260, 760)

        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame(root)
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 12)
        sidebar_layout.setSpacing(8)

        title = QLabel("LOGGING CENTER", sidebar)
        title.setObjectName("pageTitle")
        sidebar_layout.addWidget(title)

        subtitle = QLabel("PyQt6 Host Shell", sidebar)
        subtitle.setObjectName("mutedLabel")
        sidebar_layout.addWidget(subtitle)

        for entry in self.module_catalog:
            module_name = entry["name"]
            button = QPushButton(entry["display_name"], sidebar)
            button.setObjectName("navButton")
            button.setProperty("active", False)
            button.clicked.connect(lambda _checked=False, name=module_name: self.open_or_raise_module(name, restart=False))
            sidebar_layout.addWidget(button)
            self.module_buttons[module_name] = button

        sidebar_layout.addStretch(1)
        root_layout.addWidget(sidebar)

        content = QFrame(root)
        content.setObjectName("surfaceCard")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(10)

        self.page_title = QLabel("No module selected", content)
        self.page_title.setObjectName("pageTitle")
        content_layout.addWidget(self.page_title)

        self.page_subtitle = QLabel(
            "Select a module from the left to open or raise its PyQt6 runtime window.",
            content,
        )
        self.page_subtitle.setObjectName("mutedLabel")
        self.page_subtitle.setWordWrap(True)
        content_layout.addWidget(self.page_subtitle)

        controls = QHBoxLayout()
        self.open_button = QPushButton("Open / Raise Window", content)
        self.open_button.clicked.connect(self._open_active_module)
        controls.addWidget(self.open_button)

        self.restart_button = QPushButton("Restart Window", content)
        self.restart_button.clicked.connect(self._restart_active_module)
        controls.addWidget(self.restart_button)

        self.stop_button = QPushButton("Close Window", content)
        self.stop_button.clicked.connect(self._stop_active_module)
        controls.addWidget(self.stop_button)
        controls.addStretch(1)
        content_layout.addLayout(controls)

        self.runtime_status_label = QLabel("Runtime Status: idle", content)
        content_layout.addWidget(self.runtime_status_label)

        self.runtime_message_label = QLabel("Waiting for module selection.", content)
        self.runtime_message_label.setObjectName("mutedLabel")
        self.runtime_message_label.setWordWrap(True)
        content_layout.addWidget(self.runtime_message_label)

        self.runtime_state_view = QPlainTextEdit(content)
        self.runtime_state_view.setReadOnly(True)
        self.runtime_state_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if QFont is not None:
            mono = QFont("Consolas")
            mono.setStyleHint(QFont.StyleHint.Monospace)
            self.runtime_state_view.setFont(mono)
        content_layout.addWidget(self.runtime_state_view)

        root_layout.addWidget(content)
        self.setCentralWidget(root)

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("PyQt6 host shell ready.", 5000)

        self._refresh_nav_button_states()

    def _module_entry(self, module_name):
        for entry in self.module_catalog:
            if entry["name"] == module_name:
                return entry
        return None

    def _build_qt_session_payload(self, module_name):
        entry = self._module_entry(module_name) or {"display_name": module_name.replace("_", " ").title()}
        payload = {
            "window_title": f"{entry['display_name']} - Production Logging Center",
            "title": entry["display_name"],
            "subtitle": f"Launched from PyQt6 host shell for {entry['display_name']}.",
            "module_name": module_name,
            "theme_tokens": dict(self.theme_tokens),
        }

        if module_name in {"settings_manager", "developer_admin", "security_admin"}:
            section_mode = "full"
            if module_name == "developer_admin":
                section_mode = "developer_admin"
            elif module_name == "security_admin":
                section_mode = "security_admin"

            payload["section_mode"] = section_mode
            payload["navigation_modules"] = [
                {
                    "display_name": item["display_name"],
                    "module_name": item["name"],
                }
                for item in self.module_catalog
            ]
            payload["persistable_modules"] = list(payload["navigation_modules"])

        return payload

    def _ensure_runtime_manager(self, module_name):
        manager = self.runtime_managers.get(module_name)
        if manager is not None:
            return manager

        manager = QtModuleRuntimeManager(
            module_name,
            payload_builder=partial(self._build_qt_session_payload, module_name),
        )
        self.runtime_managers[module_name] = manager
        return manager

    def open_or_raise_module(self, module_name, restart=False):
        if self._module_entry(module_name) is None:
            return

        manager = self._ensure_runtime_manager(module_name)
        manager.ensure_running(force_restart=bool(restart))
        self.active_module_name = module_name
        self._refresh_nav_button_states()
        self._refresh_active_module_text()
        self.status_bar.showMessage(f"Opened runtime for {module_name}.", 3500)

    def _open_active_module(self):
        if self.active_module_name is None:
            return
        self.open_or_raise_module(self.active_module_name, restart=False)

    def _restart_active_module(self):
        if self.active_module_name is None:
            return
        self.open_or_raise_module(self.active_module_name, restart=True)

    def _stop_active_module(self):
        if self.active_module_name is None:
            return
        manager = self.runtime_managers.get(self.active_module_name)
        if manager is None:
            return
        manager.stop_runtime(force=False)
        self.status_bar.showMessage(f"Closed runtime for {self.active_module_name}.", 3500)
        self._poll_runtime_state()

    def _refresh_nav_button_states(self):
        for module_name, button in self.module_buttons.items():
            is_active = module_name == self.active_module_name
            button.setProperty("active", bool(is_active))
            style = button.style()
            if style is not None:
                style.unpolish(button)
                style.polish(button)
            button.update()

    def _refresh_active_module_text(self):
        if self.active_module_name is None:
            self.page_title.setText("No module selected")
            self.page_subtitle.setText("Select a module from the left to open or raise its PyQt6 runtime window.")
            return

        entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
        self.page_title.setText(entry["display_name"])
        self.page_subtitle.setText(
            "This host shell coordinates dedicated module runtimes. "
            "Use Open/Restart/Close controls to manage each module window."
        )

    def _poll_runtime_state(self):
        if self.active_module_name is None:
            self.runtime_status_label.setText("Runtime Status: idle")
            self.runtime_message_label.setText("Waiting for module selection.")
            self.runtime_state_view.setPlainText("{}")
            return

        manager = self.runtime_managers.get(self.active_module_name)
        if manager is None:
            self.runtime_status_label.setText("Runtime Status: idle")
            self.runtime_message_label.setText("Runtime manager is not initialized yet.")
            self.runtime_state_view.setPlainText("{}")
            return

        state = dict(manager.read_state() or {})
        status = str(state.get("status") or ("running" if manager.is_running() else "idle"))
        message = str(state.get("message") or "No runtime message available.")

        self.runtime_status_label.setText(f"Runtime Status: {status}")
        self.runtime_message_label.setText(message)
        self.runtime_state_view.setPlainText(json.dumps(state, indent=2, sort_keys=True))

    def closeEvent(self, event):
        for manager in list(self.runtime_managers.values()):
            try:
                manager.stop_runtime(force=False)
            except Exception:
                pass
        super().closeEvent(event)
