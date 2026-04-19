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
import re
from functools import partial
from types import SimpleNamespace

from app.module_registry import ModuleRegistry
from app.qt_module_runtime import QtModuleRuntimeManager
from app.theme_manager import get_qt_palette, get_qt_stylesheet, get_theme_tokens, normalize_theme
from app.host_ui_adapter import PyQt6HostUiAdapter

__module_name__ = "PyQt6 Host Shell"
__version__ = "0.1.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QAction, QFont, QKeySequence
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QGroupBox,
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
    QAction = None
    QApplication = None
    QFrame = None
    QGroupBox = None
    QFont = None
    QHBoxLayout = None
    QLabel = None
    QKeySequence = None
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
        self.base_window_title = "Production Logging Center"
        self.module_registry = ModuleRegistry()
        self.runtime_managers = {}
        self.module_buttons = {}
        self._last_runtime_event_signatures = {}
        self.module_catalog = self._build_module_catalog()
        self.persistent_module_names = set()
        self._load_persistent_module_names()
        self.navigation_state_listeners = []
        self.dispatcher = None
        self.update_coordinator = None
        self.active_module_name = None
        self.main_container = None
        self.sidebar = None
        self.sidebar_title = None
        self.sidebar_subtitle = None
        self.sidebar_toggle_button = None
        self.nav_container = None
        self.nav_top_container = None
        self.nav_middle_container = None
        self.nav_bottom_container = None
        self.nav_layouts = {}
        self.nav_button_labels = {}
        self.sidebar_collapsed = False
        self.sidebar_expanded_width = 184
        self.sidebar_collapsed_width = 60
        self.right_container = None
        self.canvas = None
        self.scrollbar = None
        self.x_scrollbar = None
        self.content_area = None
        self.canvas_window = None
        self.update_status_frame = None
        self.update_status_label = None
        self.viewport_frame = None
        self.viewport_container = None
        self.viewport_container_layout = None
        self.viewport_placeholder = None
        self.viewport_title_label = None
        self.viewport_subtitle_label = None
        self.viewport_hint_label = None
        self.runtime_diagnostics_group = None
        self.module_session_title_label = None
        self.module_session_hint_label = None
        self.session_action_frame = None
        self.viewport_status_label = None
        self.host_ui_adapter = PyQt6HostUiAdapter(self)
        self._menu_actions = {}
        self._after_timers = {}
        self._after_sequence = 0
        self._window_close_callback = None
        self._closing_via_dispatcher = False
        self._update_trace_tokens = []
        self._runtime_details_visible = False
        self._viewport_resize_bindings = {}
        self._viewport_resize_sequence = 0
        self._viewport_resize_after_id = None
        self._build_ui()
        self._configure_menu_bar()

        self.state_timer = QTimer(self)
        self.state_timer.setInterval(900)
        self.state_timer.timeout.connect(self._poll_runtime_state)
        self.state_timer.start()

        self.initial_module_name = self._resolve_initial_module_name(initial_module_name)

    def build(self):
        return self

    def attach_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher
        self.update_coordinator = getattr(dispatcher, "update_coordinator", None)
        self._bind_update_coordinator()
        self.refresh_update_status_visibility()
        return self

    def title(self, value=None):
        if value is None:
            return self.windowTitle()
        self.setWindowTitle(str(value))
        return self.windowTitle()

    def geometry(self, spec=None):
        if spec is None:
            current_geometry = QMainWindow.geometry(self)
            return f"{current_geometry.width()}x{current_geometry.height()}+{current_geometry.x()}+{current_geometry.y()}"

        match = re.match(r"^(?P<width>\d+)x(?P<height>\d+)(?:\+(?P<x>-?\d+)\+(?P<y>-?\d+))?$", str(spec).strip())
        if match is None:
            return None

        width = int(match.group("width"))
        height = int(match.group("height"))
        self.resize(width, height)
        if match.group("x") is not None and match.group("y") is not None:
            self.move(int(match.group("x")), int(match.group("y")))
        return spec

    def protocol(self, name, callback):
        if str(name) == "WM_DELETE_WINDOW":
            self._window_close_callback = callback

    def after(self, delay_ms, callback):
        if QTimer is None:
            return None
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        self._after_sequence += 1
        timer_id = f"qt_after_{self._after_sequence}"
        timer = QTimer(self)
        timer.setSingleShot(True)

        def _run_callback():
            self._after_timers.pop(timer_id, None)
            callback()

        timer.timeout.connect(_run_callback)
        self._after_timers[timer_id] = timer
        timer.start(max(0, delay_ms))
        return timer_id

    def after_cancel(self, timer_id):
        timer = self._after_timers.pop(timer_id, None)
        if timer is None:
            return
        timer.stop()
        timer.deleteLater()

    def destroy(self):
        self._closing_via_dispatcher = True
        self.close()

    def winfo_exists(self):
        return not self.isHidden() or self.isVisible()

    def attributes(self, name, value=None):
        if str(name) != "-alpha":
            return None
        if value is None:
            return self.windowOpacity()
        self.setWindowOpacity(float(value))
        return self.windowOpacity()

    def update_idletasks(self):
        application = QApplication.instance()
        if application is not None:
            application.processEvents()

    def update(self):
        self.update_idletasks()

    def _bind_update_coordinator(self):
        if self.update_coordinator is None:
            return
        if self._update_trace_tokens:
            return
        for observable in (
            self.update_coordinator.banner_var,
            self.update_coordinator.status_var,
        ):
            trace_token = observable.trace_add("write", lambda *_args: self._sync_update_status_from_coordinator())
            self._update_trace_tokens.append((observable, trace_token))
        self._sync_update_status_from_coordinator()

    def _sync_update_status_from_coordinator(self):
        if self.update_coordinator is None or self.update_status_label is None:
            return
        banner_text = str(self.update_coordinator.banner_var.get() or "").strip()
        self.update_status_label.setText(banner_text)
        self.refresh_update_status_visibility()

    def _load_persistent_module_names(self):
        catalog_names = {entry.get("name") for entry in self.module_catalog}
        configured = self.runtime_settings.get("persistent_modules") or []
        if not isinstance(configured, (list, tuple, set)):
            configured = []
        self.persistent_module_names = {
            str(module_name).strip()
            for module_name in configured
            if str(module_name).strip() and str(module_name).strip() in catalog_names
        }

    def is_module_persistent(self, module_name):
        return str(module_name or "").strip() in self.persistent_module_names

    def add_navigation_state_listener(self, listener):
        if callable(listener) and listener not in self.navigation_state_listeners:
            self.navigation_state_listeners.append(listener)

    def remove_navigation_state_listener(self, listener):
        if listener in self.navigation_state_listeners:
            self.navigation_state_listeners.remove(listener)

    def _notify_navigation_state(self, event_name, **payload):
        for listener in list(self.navigation_state_listeners):
            try:
                listener(event_name, dict(payload))
            except Exception:
                pass

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
        self.setWindowTitle(self.base_window_title)
        self.resize(1260, 760)

        self.main_container = QWidget(self)
        root_layout = QHBoxLayout(self.main_container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = QFrame(self.main_container)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(self.sidebar_expanded_width)
        self.sidebar.setMaximumWidth(self.sidebar_expanded_width)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 14, 10, 12)
        sidebar_layout.setSpacing(8)

        header_frame = QFrame(self.sidebar)
        header_frame.setObjectName("sidebar")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.sidebar_title = QLabel("LOGGING CENTER", header_frame)
        self.sidebar_title.setObjectName("sidebarTitleLabel")
        header_layout.addWidget(self.sidebar_title, 1)

        self.sidebar_toggle_button = QPushButton("<", header_frame)
        self.sidebar_toggle_button.setObjectName("sidebarToggleButton")
        self.sidebar_toggle_button.setFixedWidth(32)
        self.sidebar_toggle_button.clicked.connect(self.toggle_sidebar)
        header_layout.addWidget(self.sidebar_toggle_button)
        sidebar_layout.addWidget(header_frame)

        self.sidebar_subtitle = QLabel("GLC Edition", self.sidebar)
        self.sidebar_subtitle.setObjectName("sidebarSubtitleLabel")
        sidebar_layout.addWidget(self.sidebar_subtitle)

        self.nav_container = QFrame(self.sidebar)
        self.nav_container.setObjectName("sidebar")
        nav_container_layout = QVBoxLayout(self.nav_container)
        nav_container_layout.setContentsMargins(0, 0, 0, 0)
        nav_container_layout.setSpacing(10)

        self.nav_top_container = QFrame(self.nav_container)
        self.nav_top_container.setObjectName("sidebar")
        self.nav_layouts["top"] = QVBoxLayout(self.nav_top_container)
        self.nav_layouts["top"].setContentsMargins(0, 0, 0, 0)
        self.nav_layouts["top"].setSpacing(6)
        nav_container_layout.addWidget(self.nav_top_container)

        self.nav_middle_container = QFrame(self.nav_container)
        self.nav_middle_container.setObjectName("sidebar")
        self.nav_layouts["middle"] = QVBoxLayout(self.nav_middle_container)
        self.nav_layouts["middle"].setContentsMargins(0, 0, 0, 0)
        self.nav_layouts["middle"].setSpacing(6)
        nav_container_layout.addWidget(self.nav_middle_container, 1)

        self.nav_bottom_container = QFrame(self.nav_container)
        self.nav_bottom_container.setObjectName("sidebar")
        self.nav_layouts["bottom"] = QVBoxLayout(self.nav_bottom_container)
        self.nav_layouts["bottom"].setContentsMargins(0, 0, 0, 0)
        self.nav_layouts["bottom"].setSpacing(6)
        nav_container_layout.addWidget(self.nav_bottom_container)

        sidebar_layout.addWidget(self.nav_container, 1)
        self._populate_navigation_buttons()
        sidebar_layout.addStretch(1)
        root_layout.addWidget(self.sidebar)

        self.right_container = QFrame(self.main_container)
        right_layout = QVBoxLayout(self.right_container)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        self.update_status_frame = QFrame(self.right_container)
        self.update_status_frame.setVisible(False)
        update_status_layout = QHBoxLayout(self.update_status_frame)
        update_status_layout.setContentsMargins(14, 8, 14, 8)
        update_status_layout.setSpacing(8)
        self.update_status_label = QLabel("", self.update_status_frame)
        self.update_status_label.setObjectName("mutedLabel")
        self.update_status_label.setWordWrap(True)
        update_status_layout.addWidget(self.update_status_label)
        right_layout.addWidget(self.update_status_frame)

        self.viewport_frame = QFrame(self.right_container)
        self.viewport_frame.setObjectName("surfaceCard")
        viewport_frame_layout = QVBoxLayout(self.viewport_frame)
        viewport_frame_layout.setContentsMargins(16, 16, 16, 16)
        viewport_frame_layout.setSpacing(12)

        self.viewport_placeholder = QWidget(self.viewport_frame)
        placeholder_layout = QVBoxLayout(self.viewport_placeholder)
        placeholder_layout.setContentsMargins(8, 8, 8, 8)
        placeholder_layout.setSpacing(10)
        self.viewport_title_label = QLabel("Main Workspace", self.viewport_placeholder)
        self.viewport_title_label.setObjectName("pageTitle")
        placeholder_layout.addWidget(self.viewport_title_label)

        self.viewport_subtitle_label = QLabel("Select a module from the navigation to start work.", self.viewport_placeholder)
        self.viewport_subtitle_label.setObjectName("mutedLabel")
        self.viewport_subtitle_label.setWordWrap(True)
        placeholder_layout.addWidget(self.viewport_subtitle_label)

        self.viewport_hint_label = QLabel(
            "Modules that still open in a separate window will keep their status and window actions connected here.",
            self.viewport_placeholder,
        )
        self.viewport_hint_label.setObjectName("sectionHint")
        self.viewport_hint_label.setWordWrap(True)
        placeholder_layout.addWidget(self.viewport_hint_label)
        placeholder_layout.addStretch(1)
        viewport_frame_layout.addWidget(self.viewport_placeholder)

        self.viewport_container = QFrame(self.viewport_frame)
        self.viewport_container.setObjectName("surfaceCard")
        self.viewport_container.setVisible(False)
        self.content_area = self.viewport_container
        self.viewport_container_layout = QVBoxLayout(self.viewport_container)
        self.viewport_container_layout.setContentsMargins(0, 0, 0, 0)
        self.viewport_container_layout.setSpacing(0)
        viewport_frame_layout.addWidget(self.viewport_container, 1)

        right_layout.addWidget(self.viewport_frame, 1)

        self.runtime_diagnostics_group = QGroupBox("Active Module", self.right_container)
        diagnostics_layout = QVBoxLayout(self.runtime_diagnostics_group)
        diagnostics_layout.setContentsMargins(12, 14, 12, 12)
        diagnostics_layout.setSpacing(10)

        self.module_session_title_label = QLabel("No module selected", self.runtime_diagnostics_group)
        self.module_session_title_label.setObjectName("pageTitle")
        diagnostics_layout.addWidget(self.module_session_title_label)

        self.module_session_hint_label = QLabel("", self.runtime_diagnostics_group)
        self.module_session_hint_label.setObjectName("sectionHint")
        self.module_session_hint_label.setWordWrap(True)
        self.module_session_hint_label.setVisible(False)
        diagnostics_layout.addWidget(self.module_session_hint_label)

        self.session_action_frame = QFrame(self.runtime_diagnostics_group)
        controls = QHBoxLayout(self.session_action_frame)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self.open_button = QPushButton("Show Window", self.session_action_frame)
        self.open_button.clicked.connect(self._open_active_module)
        controls.addWidget(self.open_button)

        self.restart_button = QPushButton("Reload Window", self.session_action_frame)
        self.restart_button.clicked.connect(self._restart_active_module)
        controls.addWidget(self.restart_button)

        self.stop_button = QPushButton("Close Window", self.session_action_frame)
        self.stop_button.clicked.connect(self._stop_active_module)
        controls.addWidget(self.stop_button)

        self.details_toggle_button = QPushButton("Show Details", self.session_action_frame)
        self.details_toggle_button.clicked.connect(self._toggle_runtime_details)
        controls.addWidget(self.details_toggle_button)
        controls.addStretch(1)
        self.session_action_frame.setVisible(False)
        diagnostics_layout.addWidget(self.session_action_frame)

        self.runtime_status_label = QLabel("Location: none selected", self.runtime_diagnostics_group)
        self.runtime_status_label.setObjectName("subtitleLabel")
        diagnostics_layout.addWidget(self.runtime_status_label)

        self.runtime_message_label = QLabel("Select a module to begin.", self.runtime_diagnostics_group)
        self.runtime_message_label.setObjectName("mutedLabel")
        self.runtime_message_label.setWordWrap(True)
        diagnostics_layout.addWidget(self.runtime_message_label)

        self.runtime_state_view = QPlainTextEdit(self.runtime_diagnostics_group)
        self.runtime_state_view.setReadOnly(True)
        self.runtime_state_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.runtime_state_view.setMinimumHeight(180)
        if QFont is not None:
            mono = QFont("Consolas")
            mono.setStyleHint(QFont.StyleHint.Monospace)
            self.runtime_state_view.setFont(mono)
        self.runtime_state_view.setPlainText("{}")
        self.runtime_state_view.setVisible(False)
        diagnostics_layout.addWidget(self.runtime_state_view)

        right_layout.addWidget(self.runtime_diagnostics_group)

        root_layout.addWidget(self.right_container, 1)
        self.setCentralWidget(self.main_container)

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.", 5000)

        self._apply_update_status_style()
        self.show_viewport_placeholder()
        self._refresh_nav_button_states()
        self.set_sidebar_collapsed(self.sidebar_collapsed)
        self._refresh_session_controls(session_mode="idle")

    def _rebuild_module_catalog_from_navigation_items(self, grouped_items):
        module_catalog = []
        for group_name, entries in grouped_items.items():
            for display_name, module_name in entries:
                module_catalog.append(
                    {
                        "name": module_name,
                        "display_name": str(display_name),
                        "navigation_group": str(group_name or "middle"),
                        "default_initial": False,
                    }
                )
        if module_catalog:
            self.module_catalog = module_catalog

    def _populate_navigation_buttons(self, grouped_items=None, load_callback=None):
        for layout in self.nav_layouts.values():
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        if isinstance(grouped_items, dict):
            self._rebuild_module_catalog_from_navigation_items(grouped_items)
        elif grouped_items is None:
            grouped_items = {
                "top": [
                    (entry["display_name"], entry["name"])
                    for entry in self.module_catalog
                    if entry.get("navigation_group") == "top"
                ],
                "middle": [
                    (entry["display_name"], entry["name"])
                    for entry in self.module_catalog
                    if entry.get("navigation_group") == "middle"
                ],
                "bottom": [
                    (entry["display_name"], entry["name"])
                    for entry in self.module_catalog
                    if entry.get("navigation_group") == "bottom"
                ],
            }

        self.module_buttons = {}
        self.nav_button_labels = {}
        for group_name in ("top", "middle", "bottom"):
            for display_name, module_name in grouped_items.get(group_name, []):
                button = QPushButton(str(display_name), self.sidebar)
                button.setObjectName("navButton")
                button.setProperty("active", False)
                if callable(load_callback):
                    button.clicked.connect(lambda _checked=False, name=module_name: load_callback(name))
                else:
                    button.clicked.connect(lambda _checked=False, name=module_name: self.open_or_raise_module(name, restart=False))
                target_layout = self.nav_layouts.get(group_name, self.nav_layouts["middle"])
                target_layout.addWidget(button)
                self.module_buttons[module_name] = button
                self.nav_button_labels[module_name] = (str(display_name), self._collapse_label(display_name))

        self.nav_layouts["middle"].addStretch(1)
        self.set_sidebar_collapsed(self.sidebar_collapsed)

    def populate_navigation(self, items, load_callback, active_module_name=None):
        grouped_items = items if isinstance(items, dict) else {"top": [], "middle": list(items or []), "bottom": []}
        self._populate_navigation_buttons(grouped_items=grouped_items, load_callback=load_callback)
        self.set_active_navigation_button(active_module_name)

    def _apply_update_status_style(self):
        frame_style = (
            "QFrame {"
            f" background-color: {self.theme_tokens['banner_bg']};"
            f" border: 1px solid {self.theme_tokens['banner_border']};"
            " border-radius: 6px;"
            "}"
        )
        self.update_status_frame.setStyleSheet(frame_style)
        self.update_status_label.setStyleSheet(f"color: {self.theme_tokens['banner_fg']};")

    def set_update_status(self, message, severity="info"):
        _ = severity
        text = str(message or "").strip()
        self.update_status_label.setText(text)
        self.refresh_update_status_visibility()

    def clear_update_status(self):
        self.update_status_label.setText("")
        self.refresh_update_status_visibility()

    def refresh_update_status_visibility(self):
        if self.update_coordinator is not None:
            banner_text = str(self.update_coordinator.banner_var.get() or "").strip()
            self.update_status_label.setText(banner_text)
            is_active = bool(self.update_coordinator.active)
        else:
            is_active = bool(str(self.update_status_label.text() or "").strip())
        self.update_status_frame.setVisible(is_active)
        self._queue_viewport_resize_notification()

    def get_viewport_container(self):
        return self.viewport_container

    def bind_viewport_resize(self, callback, add="+"):
        if not callable(callback):
            return None
        if str(add or "") != "+":
            self._viewport_resize_bindings.clear()
        self._viewport_resize_sequence += 1
        binding_id = f"qt_viewport_resize_{self._viewport_resize_sequence}"
        self._viewport_resize_bindings[binding_id] = callback
        self._queue_viewport_resize_notification()
        return binding_id

    def get_viewport_size(self, min_width=0, min_height=0):
        try:
            min_width = int(min_width)
        except Exception:
            min_width = 0
        try:
            min_height = int(min_height)
        except Exception:
            min_height = 0

        candidates = []
        if self.viewport_container is not None and self.viewport_container.isVisible():
            candidates.append((self.viewport_container, False))
        if self.viewport_placeholder is not None and self.viewport_placeholder.isVisible():
            candidates.append((self.viewport_placeholder, False))
        if self.viewport_frame is not None:
            candidates.append((self.viewport_frame, True))
        if self.right_container is not None:
            candidates.append((self.right_container, False))

        width = 0
        height = 0
        for widget, subtract_layout_margins in candidates:
            if widget is None:
                continue

            candidate_width = max(int(getattr(widget, "width", lambda: 0)() or 0), 0)
            candidate_height = max(int(getattr(widget, "height", lambda: 0)() or 0), 0)

            contents_rect = getattr(widget, "contentsRect", lambda: None)()
            if contents_rect is not None:
                rect_width = max(int(contents_rect.width() or 0), 0)
                rect_height = max(int(contents_rect.height() or 0), 0)
                if rect_width > 0:
                    candidate_width = rect_width
                if rect_height > 0:
                    candidate_height = rect_height

            if subtract_layout_margins:
                layout = widget.layout()
                if layout is not None:
                    margins = layout.contentsMargins()
                    candidate_width = max(0, candidate_width - margins.left() - margins.right())
                    candidate_height = max(0, candidate_height - margins.top() - margins.bottom())

            if candidate_width > 0:
                width = candidate_width
            if candidate_height > 0:
                height = candidate_height
            if width > 0 and height > 0:
                break

        return (max(width, min_width), max(height, min_height))

    def reset_viewport_position(self):
        self._queue_viewport_resize_notification()

    def _queue_viewport_resize_notification(self):
        if not self._viewport_resize_bindings:
            return
        if self._viewport_resize_after_id is not None:
            return

        def emit_later():
            self._viewport_resize_after_id = None
            self._notify_viewport_resize_bindings()

        timer_id = self.after(0, emit_later)
        if timer_id is None:
            emit_later()
            return
        self._viewport_resize_after_id = timer_id

    def _notify_viewport_resize_bindings(self):
        if not self._viewport_resize_bindings:
            return
        width, height = self.get_viewport_size()
        resize_event = SimpleNamespace(width=width, height=height)
        for callback in list(self._viewport_resize_bindings.values()):
            try:
                callback(resize_event)
            except Exception:
                pass

    def _viewport_has_content(self):
        return bool(self.viewport_container_layout is not None and self.viewport_container_layout.count())

    def clear_viewport_container(self, delete_widgets=False):
        if self.viewport_container_layout is None:
            return
        while self.viewport_container_layout.count():
            item = self.viewport_container_layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            widget.setParent(None)
            if delete_widgets:
                widget.deleteLater()
        self._queue_viewport_resize_notification()

    def create_module_container(self, module_name=None):
        module_container = QFrame(self.viewport_container)
        module_container.setObjectName("surfaceCard")
        module_layout = QVBoxLayout(module_container)
        module_layout.setContentsMargins(0, 0, 0, 0)
        module_layout.setSpacing(0)
        self.viewport_container_layout.addWidget(module_container)
        self.prepare_viewport_for_module(module_name=module_name)
        return module_container

    def prepare_viewport_for_module(self, module_name=None):
        if module_name is not None:
            self.active_module_name = module_name
        self.viewport_placeholder.setVisible(False)
        self.viewport_container.setVisible(True)
        self._refresh_nav_button_states()
        self._queue_viewport_resize_notification()

    def show_viewport_placeholder(self, title=None, message=None, hint=None):
        if not self._viewport_has_content():
            self.viewport_container.setVisible(False)
        self.viewport_placeholder.setVisible(True)
        self.viewport_title_label.setText(str(title or "Main Workspace"))
        self.viewport_subtitle_label.setText(
            str(
                message
                or "Select a module from the navigation to start work."
            )
        )
        self.viewport_hint_label.setText(
            str(
                hint
                or "Modules that still open in a separate window will keep their status and actions connected here."
            )
        )
        self._queue_viewport_resize_notification()

    def _display_name_for_module(self, module_name):
        entry = self._module_entry(module_name)
        if entry is not None:
            return str(entry.get("display_name") or module_name)
        return str(module_name or "")

    def _set_shell_window_title(self, module_name=None):
        display_name = self._display_name_for_module(module_name).strip()
        if display_name:
            self.setWindowTitle(f"{display_name} - {self.base_window_title}")
            return
        self.setWindowTitle(self.base_window_title)

    def mount_viewport_widget(self, widget, module_name=None):
        if widget is None or self.viewport_container_layout is None:
            return None
        self.clear_viewport_container(delete_widgets=False)
        widget.setParent(self.viewport_container)
        self.viewport_container_layout.addWidget(widget)
        self.prepare_viewport_for_module(module_name=module_name)
        return widget

    def set_active_navigation_button(self, module_name=None):
        if module_name is not None:
            self.active_module_name = module_name
        self._refresh_nav_button_states()

    def _configure_menu_bar(self):
        self.configure_menu(
            self.menu_open,
            self.menu_save,
            self.menu_export,
            self.menu_import,
            lambda: None,
            lambda: None,
            lambda: None,
            lambda: None,
            lambda: None,
            lambda: None,
            self.close,
        )

    def configure_menu(
        self,
        open_callback,
        save_callback,
        export_callback,
        import_callback,
        login_callback,
        change_login_callback,
        logout_callback,
        help_callback,
        report_problem_callback,
        about_callback,
        exit_callback,
    ):
        menu_bar = self.menuBar()
        if menu_bar is None or QAction is None:
            return
        menu_bar.clear()
        self._menu_actions = {}

        file_menu = menu_bar.addMenu("File")
        self._menu_actions["open"] = self._add_menu_action(file_menu, "Open Draft", open_callback, shortcut=QKeySequence.StandardKey.Open)
        self._menu_actions["save"] = self._add_menu_action(file_menu, "Save Draft", save_callback, shortcut=QKeySequence.StandardKey.Save)
        self._menu_actions["export"] = self._add_menu_action(file_menu, "Export to Excel", export_callback, shortcut="Ctrl+E")
        self._menu_actions["import"] = self._add_menu_action(file_menu, "Import Excel", import_callback, shortcut="Ctrl+I")
        file_menu.addSeparator()
        self._menu_actions["exit"] = self._add_menu_action(file_menu, "Exit", exit_callback, shortcut=QKeySequence.StandardKey.Quit)

        security_menu = menu_bar.addMenu("Security")
        self._menu_actions["login"] = self._add_menu_action(security_menu, "Sign In", login_callback)
        self._menu_actions["change_login"] = self._add_menu_action(security_menu, "Change Login", change_login_callback)
        self._menu_actions["logout"] = self._add_menu_action(security_menu, "Sign Out", logout_callback)

        help_menu = menu_bar.addMenu("Help")
        self._menu_actions["help"] = self._add_menu_action(help_menu, "User Guide", help_callback)
        self._menu_actions["report_problem"] = self._add_menu_action(help_menu, "Report A Problem", report_problem_callback)
        self._menu_actions["about"] = self._add_menu_action(help_menu, "About", about_callback)

    def apply_theme(self, theme_name=None):
        if theme_name is not None:
            self.theme_name = normalize_theme(theme_name)
        self.theme_tokens = get_theme_tokens(theme_name=self.theme_name)
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(get_qt_stylesheet(theme_name=self.theme_name, theme_tokens=self.theme_tokens))
            application.setPalette(get_qt_palette(theme_name=self.theme_name, theme_tokens=self.theme_tokens))
        self._apply_update_status_style()
        self._refresh_nav_button_states()
        self.refresh_update_status_visibility()

    def toggle_sidebar(self):
        self.set_sidebar_collapsed(not self.sidebar_collapsed)

    def set_sidebar_collapsed(self, collapsed):
        self.sidebar_collapsed = bool(collapsed)
        sidebar_width = self.sidebar_collapsed_width if self.sidebar_collapsed else self.sidebar_expanded_width
        if self.sidebar is not None:
            self.sidebar.setMinimumWidth(sidebar_width)
            self.sidebar.setMaximumWidth(sidebar_width)
        if self.sidebar_title is not None:
            self.sidebar_title.setText("LC" if self.sidebar_collapsed else "LOGGING CENTER")
        if self.sidebar_subtitle is not None:
            self.sidebar_subtitle.setVisible(not self.sidebar_collapsed)
        if self.sidebar_toggle_button is not None:
            self.sidebar_toggle_button.setText(">" if self.sidebar_collapsed else "<")
        for module_name, button in self.module_buttons.items():
            expanded_label, collapsed_label = self.nav_button_labels.get(module_name, (button.text(), button.text()))
            button.setText(collapsed_label if self.sidebar_collapsed else expanded_label)
        self._queue_viewport_resize_notification()

    def _collapse_label(self, display_name):
        words = [word for word in str(display_name).replace("/", " ").split() if word]
        if not words:
            return "?"
        return "".join(word[0].upper() for word in words[:3]) or str(display_name)[:2].upper()

    def _toggle_runtime_details(self):
        self._set_runtime_details_visible(not self._runtime_details_visible)

    def _set_runtime_details_visible(self, visible):
        self._runtime_details_visible = bool(visible)
        if self.runtime_state_view is not None:
            action_frame_visible = bool(self.session_action_frame is not None and self.session_action_frame.isVisible())
            self.runtime_state_view.setVisible(action_frame_visible and self._runtime_details_visible)
        if hasattr(self, "details_toggle_button") and self.details_toggle_button is not None:
            self.details_toggle_button.setText("Hide Details" if self._runtime_details_visible else "Show Details")

    def _refresh_session_controls(self, session_mode="idle"):
        has_active_module = bool(self.active_module_name)
        is_sidecar = session_mode == "sidecar"
        show_window_actions = has_active_module and is_sidecar

        if self.module_session_hint_label is not None:
            self.module_session_hint_label.setVisible(show_window_actions)
            self.module_session_hint_label.setText(
                "This module currently works in its own window. The shell keeps its window status and actions available here."
                if show_window_actions
                else ""
            )
        if self.session_action_frame is not None:
            self.session_action_frame.setVisible(show_window_actions)

        self.open_button.setEnabled(show_window_actions)
        self.restart_button.setEnabled(show_window_actions)
        self.stop_button.setEnabled(show_window_actions)
        self.details_toggle_button.setEnabled(show_window_actions)

        if not show_window_actions:
            self._runtime_details_visible = False
        self._set_runtime_details_visible(self._runtime_details_visible)

    def _set_module_session_context(self, title=None, route_text=None, message=None, state_payload=None, session_mode="idle"):
        display_title = str(title or "No module selected")
        route_line = str(route_text or "Location: none selected")
        detail_message = str(message or "Select a module to begin.")
        payload = state_payload if isinstance(state_payload, dict) else {}

        if self.module_session_title_label is not None:
            self.module_session_title_label.setText(display_title)
        self.runtime_status_label.setText(route_line)
        self.runtime_message_label.setText(detail_message)
        self.runtime_state_view.setPlainText(json.dumps(payload, indent=2, sort_keys=True))
        self._set_shell_window_title(payload.get("module"))
        self.status_bar.showMessage(detail_message, 4000)
        self._refresh_session_controls(session_mode=session_mode)

    def _add_menu_action(self, menu, title, callback, shortcut=None):
        action = QAction(str(title), self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _send_runtime_command(self, module_name, action, success_message, unavailable_message):
        manager = self.runtime_managers.get(module_name)
        if manager is None:
            self.open_or_raise_module(module_name, restart=False)
            manager = self.runtime_managers.get(module_name)
        if manager is None:
            self.host_ui_adapter.show_warning("Action Unavailable", unavailable_message)
            return False
        manager.send_command(action)
        self.host_ui_adapter.show_toast("File Menu", success_message, duration_ms=2500)
        return True

    def menu_open(self):
        self.open_or_raise_module("production_log", restart=False)
        self._send_runtime_command(
            "production_log",
            "show_pending",
            "Opened Production Log draft workflow.",
            "Open Draft is unavailable because the Production Log runtime could not be opened.",
        )

    def menu_save(self):
        active_module_name = str(self.active_module_name or "").strip()
        if active_module_name == "production_log":
            self._send_runtime_command(
                "production_log",
                "save_draft",
                "Sent save request to Production Log.",
                "Save Draft is unavailable because the Production Log runtime is not available.",
            )
            return
        if active_module_name == "internal_code_editor":
            self._send_runtime_command(
                "internal_code_editor",
                "save_current_file",
                "Sent save request to Internal Code Editor.",
                "Save is unavailable because the Internal Code Editor runtime is not available.",
            )
            return
        self.host_ui_adapter.show_warning(
            "Action Unavailable",
            "Save Draft is currently implemented for Production Log and Internal Code Editor runtimes only.",
        )

    def menu_export(self):
        self._send_runtime_command(
            "production_log",
            "export_to_excel",
            "Sent export request to Production Log.",
            "Export to Excel is unavailable because the Production Log runtime could not be opened.",
        )

    def menu_import(self):
        self._send_runtime_command(
            "production_log",
            "import_from_excel_ui",
            "Sent import request to Production Log.",
            "Import Excel is unavailable because the Production Log runtime could not be opened.",
        )

    def _module_entry(self, module_name):
        for entry in self.module_catalog:
            if entry["name"] == module_name:
                return entry
        return None

    def _is_dispatcher_viewport_module(self, module_name):
        if self.dispatcher is None:
            return False
        should_use_qt_in_viewport = getattr(self.dispatcher, "should_use_qt_in_viewport", None)
        if not callable(should_use_qt_in_viewport):
            return False
        return bool(should_use_qt_in_viewport(module_name))

    def _build_qt_session_payload(self, module_name):
        entry = self._module_entry(module_name) or {"display_name": module_name.replace("_", " ").title()}
        display_name = str(entry["display_name"])
        payload = {
            "window_title": f"{display_name} - {self.base_window_title}",
            "title": display_name,
            "subtitle": f"Opened from {self.base_window_title} for {display_name}.",
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

    def _stop_runtime_if_non_persistent(self, module_name):
        if not module_name or self.is_module_persistent(module_name):
            return
        manager = self.runtime_managers.get(module_name)
        if manager is None:
            return
        manager.stop_runtime(force=False)

    def _switch_active_module(self, module_name):
        previous_module = self.active_module_name
        if previous_module == module_name:
            return
        self._stop_runtime_if_non_persistent(previous_module)
        self.active_module_name = module_name
        self._notify_navigation_state(
            "active_module_changed",
            previous_module=previous_module,
            active_module=module_name,
            previous_was_persistent=self.is_module_persistent(previous_module),
            active_is_persistent=self.is_module_persistent(module_name),
        )

    def open_or_raise_module(self, module_name, restart=False):
        if self._module_entry(module_name) is None:
            return False

        if self._is_dispatcher_viewport_module(module_name) and self.dispatcher is not None:
            self.dispatcher.load_module(module_name, use_transition=False)
            return True

        manager = self._ensure_runtime_manager(module_name)
        manager.ensure_running(force_restart=bool(restart))
        self._switch_active_module(module_name)
        self._refresh_nav_button_states()
        self._refresh_active_module_text()
        self._notify_navigation_state("runtime_opened", module_name=module_name, restart=bool(restart))
        display_name = self._display_name_for_module(module_name) or module_name
        self.host_ui_adapter.show_toast(self.base_window_title, f"Opened {display_name} in a separate window.", duration_ms=3500)
        return True

    def _open_active_module(self):
        if self.active_module_name is None:
            return
        self.open_or_raise_module(self.active_module_name, restart=False)

    def _restart_active_module(self):
        if self.active_module_name is None:
            return
        if self._is_dispatcher_viewport_module(self.active_module_name) and self.dispatcher is not None:
            self.dispatcher.load_module(self.active_module_name, use_transition=False)
            return
        self.open_or_raise_module(self.active_module_name, restart=True)

    def _stop_active_module(self):
        if self.active_module_name is None:
            return
        if self._is_dispatcher_viewport_module(self.active_module_name):
            display_name = self._display_name_for_module(self.active_module_name) or self.active_module_name
            self.host_ui_adapter.show_warning(
                "Action Unavailable",
                f"{display_name} is already open in the main workspace and does not have a separate window to close.",
            )
            return
        module_name = self.active_module_name
        manager = self.runtime_managers.get(module_name)
        if manager is None:
            return
        manager.stop_runtime(force=False)
        self._notify_navigation_state("runtime_closed", module_name=module_name)
        display_name = self._display_name_for_module(module_name) or module_name
        self.host_ui_adapter.show_toast(self.base_window_title, f"Closed the separate window for {display_name}.", duration_ms=3500)
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
            self._set_module_session_context(
                title="No module selected",
                route_text="Location: none selected",
                message="Select a module from the navigation to begin.",
                state_payload={},
                session_mode="idle",
            )
            if not self._viewport_has_content():
                self.show_viewport_placeholder(
                    title="Main Workspace",
                    message="Select a module from the navigation to start work.",
                    hint="Modules that currently use a separate window will keep their status and actions connected here.",
                )
            return

        entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
        display_name = str(entry["display_name"])
        if self._is_dispatcher_viewport_module(self.active_module_name):
            self._set_module_session_context(
                title=display_name,
                route_text="Location: main workspace",
                message=f"{display_name} is open in the main workspace.",
                state_payload={
                    "module": self.active_module_name,
                    "status": "in_viewport",
                    "sidecar_runtime": False,
                },
                session_mode="viewport",
            )
            return

        persistence_text = "reusable window" if self.is_module_persistent(self.active_module_name) else "separate window"
        self._set_module_session_context(
            title=display_name,
            route_text="Location: separate window",
            message=f"{display_name} currently opens in a separate window.",
            state_payload={
                "module": self.active_module_name,
                "status": "separate_window",
                "persistence": persistence_text,
            },
            session_mode="sidecar",
        )
        if not self._viewport_has_content():
            self.show_viewport_placeholder(
                title="Main Workspace",
                message=f"{display_name} is currently open in a separate window.",
                hint="This workspace stays available for modules that load directly inside the shell.",
            )

    def _poll_runtime_state(self):
        if self.active_module_name is None:
            self._set_module_session_context(
                title="No module selected",
                route_text="Location: none selected",
                message="Select a module to begin.",
                state_payload={},
                session_mode="idle",
            )
            return

        if self._is_dispatcher_viewport_module(self.active_module_name):
            entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
            display_name = str(entry["display_name"])
            self._set_module_session_context(
                title=display_name,
                route_text="Location: main workspace",
                message=f"{display_name} is open in the main workspace.",
                state_payload={
                    "module": self.active_module_name,
                    "status": "in_viewport",
                    "sidecar_runtime": False,
                },
                session_mode="viewport",
            )
            return

        manager = self.runtime_managers.get(self.active_module_name)
        if manager is None:
            entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
            display_name = str(entry["display_name"])
            self._set_module_session_context(
                title=display_name,
                route_text="Location: separate window",
                message=f"{display_name} is not reporting separate-window status yet.",
                state_payload={},
                session_mode="sidecar",
            )
            return

        state = dict(manager.read_state() or {})
        self._handle_runtime_event(self.active_module_name, manager, state)
        status = str(state.get("status") or ("running" if manager.is_running() else "idle"))
        message = str(state.get("message") or "No runtime message available.")

        if not manager.is_running() and not self.is_module_persistent(self.active_module_name):
            # Drop completed non-persistent runtime managers so future opens rebuild a clean session payload.
            self.runtime_managers.pop(self.active_module_name, None)

        entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
        display_name = str(entry["display_name"])
        self._set_module_session_context(
            title=display_name,
            route_text=f"Location: separate window ({status})",
            message=message,
            state_payload=state,
            session_mode="sidecar",
        )

    def _handle_runtime_event(self, module_name, manager, state):
        runtime_event = str(state.get("runtime_event") or "").strip().lower()
        if not runtime_event:
            return

        event_signature = (runtime_event, state.get("updated_at"))
        if self._last_runtime_event_signatures.get(module_name) == event_signature:
            return
        self._last_runtime_event_signatures[module_name] = event_signature

        if module_name == "production_log" and runtime_event == "open_recovery_requested":
            self.open_or_raise_module("recovery_viewer", restart=False)
            recovery_instance = None
            if self._is_dispatcher_viewport_module("recovery_viewer") and self.dispatcher is not None:
                recovery_instance = getattr(self.dispatcher, "active_module_instance", None)
                if recovery_instance is not None and hasattr(recovery_instance, "refresh_records"):
                    try:
                        recovery_instance.refresh_records()
                    except Exception:
                        pass
            manager.send_command(
                "host_action_completed",
                {
                    "action_name": runtime_event,
                    "success": True,
                    "message": "Opened Recovery Viewer in the PyQt6 host runtime.",
                },
            )
            recovery_manager = self.runtime_managers.get("recovery_viewer")
            if recovery_manager is not None:
                recovery_manager.send_command("refresh_snapshot", {"reason": runtime_event})

    def closeEvent(self, event):
        if self._window_close_callback is not None and not self._closing_via_dispatcher:
            callback = self._window_close_callback
            callback()
            event.ignore()
            return

        for manager in list(self.runtime_managers.values()):
            try:
                manager.stop_runtime(force=False)
            except Exception:
                pass
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._queue_viewport_resize_notification()
