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
import re
from types import SimpleNamespace

from app.module_registry import ModuleRegistry
from app.theme_manager import get_qt_palette, get_qt_stylesheet, get_theme_tokens, normalize_theme
from app.host_ui_adapter import PyQt6HostUiAdapter
from app.app_logging import log_exception

__module_name__ = "PyQt6 Host Shell"
__version__ = "0.1.6"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QAction, QKeySequence
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QPushButton,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QAction = None
    QApplication = None
    QFrame = None
    QHBoxLayout = None
    QLabel = None
    QKeySequence = None
    QMainWindow = object
    QPushButton = None
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
        self._martin_theme_tokens = dict(self.theme_tokens)
        self.base_window_title = "Production Logging Center"
        self.module_registry = ModuleRegistry()
        self.module_buttons = {}
        self.module_catalog = self._build_module_catalog()
        self.persistent_module_names = set()
        self._load_persistent_module_names()
        self.navigation_state_listeners = []
        self.startup_ready_listeners = []
        self._startup_ready_emitted = False
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
        self.sidebar_manually_expanded_narrow = False
        self.sidebar_auto_collapsed = False
        self.root_layout = None
        self.sidebar_expanded_width = 184
        self.sidebar_collapsed_width = 60
        self.sidebar_title_expanded_text = "Logging\nCenter"
        self.sidebar_title_collapsed_text = "LC"
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
        self.viewport_status_label = None
        self.host_ui_adapter = PyQt6HostUiAdapter(self)
        self._menu_actions = {}
        self._after_timers = {}
        self._after_sequence = 0
        self._window_close_callback = None
        self._closing_via_dispatcher = False
        self._update_trace_tokens = []
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

    def add_startup_ready_listener(self, listener):
        if callable(listener) and listener not in self.startup_ready_listeners:
            self.startup_ready_listeners.append(listener)

    def remove_startup_ready_listener(self, listener):
        if listener in self.startup_ready_listeners:
            self.startup_ready_listeners.remove(listener)

    def _emit_startup_ready(self):
        if self._startup_ready_emitted:
            return
        self._startup_ready_emitted = True
        for listener in list(self.startup_ready_listeners):
            try:
                listener()
            except Exception:
                pass

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
        self.root_layout = root_layout
        self.setMinimumWidth(428)

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

        self.sidebar_title = QLabel(self.sidebar_title_expanded_text, header_frame)
        self.sidebar_title.setObjectName("sidebarTitleLabel")
        self.sidebar_title.setWordWrap(True)
        self.sidebar_title.setMinimumHeight(40)
        header_layout.addWidget(self.sidebar_title, 1)

        self.sidebar_toggle_button = QPushButton("<", header_frame)
        self.sidebar_toggle_button.setObjectName("sidebarToggleButton")
        self.sidebar_toggle_button.setFixedWidth(32)
        self.sidebar_toggle_button.clicked.connect(self.toggle_sidebar)
        self.sidebar_toggle_button.setAccessibleName("Toggle sidebar navigation panel")
        self.sidebar_toggle_button.setAccessibleDescription("Collapses or expands the sidebar navigation panel.")
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
        self.viewport_title_label = QLabel("Workspace", self.viewport_placeholder)
        self.viewport_title_label.setObjectName("pageTitle")
        placeholder_layout.addWidget(self.viewport_title_label)

        self.viewport_subtitle_label = QLabel("Select a module from the navigation to start work.", self.viewport_placeholder)
        self.viewport_subtitle_label.setObjectName("mutedLabel")
        self.viewport_subtitle_label.setWordWrap(True)
        placeholder_layout.addWidget(self.viewport_subtitle_label)

        self.viewport_hint_label = QLabel(
            "Layout Manager keeps its own window. Other modules load here in the workspace.",
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

        root_layout.addWidget(self.right_container, 1)
        self.setCentralWidget(self.main_container)

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.", 5000)

        self.notifications_btn = QPushButton("Notifications (0)", self)
        self.notifications_btn.setObjectName("notificationsButton")
        self.notifications_btn.setFlat(True)
        self.notifications_btn.setAccessibleName("Notification Center")
        self.notifications_btn.setAccessibleDescription("Click to open notification center history dialog.")
        accent_color = self.theme_tokens.get("accent", "#0f7c8f")
        self.notifications_btn.setStyleSheet(
            f"QPushButton {{ color: {accent_color}; font-weight: bold; border: none; padding: 2px 8px; }}"
            f"QPushButton:hover {{ background-color: rgba(15, 124, 143, 0.1); border-radius: 4px; }}"
        )
        self.notifications_btn.clicked.connect(self.show_notification_center)
        self.status_bar.addPermanentWidget(self.notifications_btn)

        self._apply_update_status_style()
        self.show_viewport_placeholder()
        self._refresh_nav_button_states()
        self.set_sidebar_collapsed(self.sidebar_collapsed)

    def showEvent(self, event):
        super().showEvent(event)
        if self._startup_ready_emitted:
            return
        if QTimer is not None:
            QTimer.singleShot(0, self._emit_startup_ready)
            return
        self._emit_startup_ready()

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
        MODULE_ICONS = {
            "about": "ℹ️",
            "developer_admin": "🛠️",
            "help_viewer": "📖",
            "internal_code_editor": "💻",
            "layout_manager": "📐",
            "production_log": "📋",
            "production_log_calculations": "🧮",
            "rate_manager": "📊",
            "recovery_viewer": "🔄",
            "security_admin": "🔒",
            "settings_manager": "⚙️",
            "update_manager": "📥",
        }
        for group_name in ("top", "middle", "bottom"):
            for display_name, module_name in grouped_items.get(group_name, []):
                icon = MODULE_ICONS.get(module_name, "📄")
                button = QPushButton(f"{icon}  {display_name}", self.sidebar)
                button.setObjectName("navButton")
                button.setProperty("active", False)
                button.setAccessibleName(f"Navigate to {display_name}")
                button.setAccessibleDescription(f"Opens the {display_name} module in the main view.")
                if callable(load_callback):
                    button.clicked.connect(lambda _checked=False, name=module_name: load_callback(name))
                else:
                    button.clicked.connect(lambda _checked=False, name=module_name: self.open_or_raise_module(name, restart=False))
                target_layout = self.nav_layouts.get(group_name, self.nav_layouts["middle"])
                target_layout.addWidget(button)
                self.module_buttons[module_name] = button
                self.nav_button_labels[module_name] = (f"{icon}  {display_name}", icon)

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
        if self.width() < 552:
            self.sidebar_manually_expanded_narrow = False
            self.update_sidebar_layout_state()
        self._queue_viewport_resize_notification()

    def show_viewport_placeholder(self, title=None, message=None, hint=None):
        title_str = str(title or "Workspace")
        msg_str = str(message or "Select a module from the navigation to start work.")
        hint_str = str(hint or "Layout Manager keeps its own window. Other modules load here in the workspace.")

        if (hasattr(self, "_last_placeholder_title") and self._last_placeholder_title == title_str and
            hasattr(self, "_last_placeholder_msg") and self._last_placeholder_msg == msg_str and
            hasattr(self, "_last_placeholder_hint") and self._last_placeholder_hint == hint_str and
            self.viewport_placeholder.isVisible()):
            return

        self._last_placeholder_title = title_str
        self._last_placeholder_msg = msg_str
        self._last_placeholder_hint = hint_str

        if not self._viewport_has_content():
            self.viewport_container.setVisible(False)
        self.viewport_placeholder.setVisible(True)
        self.viewport_title_label.setText(title_str)
        self.viewport_subtitle_label.setText(msg_str)
        self.viewport_hint_label.setText(hint_str)
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
        self._martin_theme_tokens = dict(self.theme_tokens)
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(get_qt_stylesheet(theme_name=self.theme_name, theme_tokens=self.theme_tokens))
            application.setPalette(get_qt_palette(theme_name=self.theme_name, theme_tokens=self.theme_tokens))
        self._apply_update_status_style()
        self._refresh_nav_button_states()
        self.refresh_update_status_visibility()

    def toggle_sidebar(self):
        if self.width() < 552:
            self.sidebar_manually_expanded_narrow = not self.sidebar_manually_expanded_narrow
            self.sidebar_collapsed = not self.sidebar_manually_expanded_narrow
            self.sidebar_auto_collapsed = False
            self.update_sidebar_layout_state()
        else:
            self.set_sidebar_collapsed(not self.sidebar_collapsed)

    def set_sidebar_collapsed(self, collapsed):
        self.sidebar_collapsed = bool(collapsed)
        self.sidebar_auto_collapsed = False
        self.sidebar_manually_expanded_narrow = False
        self.update_sidebar_layout_state()

    def update_sidebar_layout_state(self):
        if self.sidebar is None or self.root_layout is None:
            return

        current_width = self.width()
        is_narrow = current_width < 552

        if is_narrow:
            if self.sidebar_manually_expanded_narrow:
                # 1. Overlay expanded mode: float on top of right container
                self._set_sidebar_collapsed_visuals(False)
                if self.root_layout.indexOf(self.sidebar) != -1:
                    self.root_layout.removeWidget(self.sidebar)
                self.sidebar.setParent(self.main_container)
                self.sidebar.show()
                self.sidebar.raise_()
                self.sidebar.setGeometry(0, 0, self.sidebar_expanded_width, self.main_container.height())
            else:
                # 2. Collapsed mode: inside root horizontal layout
                if not self.sidebar_collapsed:
                    self.sidebar_auto_collapsed = True
                self._set_sidebar_collapsed_visuals(True)
                if self.root_layout.indexOf(self.sidebar) == -1:
                    self.root_layout.insertWidget(0, self.sidebar)
                self.sidebar.setMinimumWidth(self.sidebar_collapsed_width)
                self.sidebar.setMaximumWidth(self.sidebar_collapsed_width)
        else:
            # 3. Wide mode (>= 552px)
            if self.sidebar_auto_collapsed:
                self.sidebar_collapsed = False
                self.sidebar_auto_collapsed = False
                self.sidebar_manually_expanded_narrow = False

            self._set_sidebar_collapsed_visuals(self.sidebar_collapsed)
            if self.root_layout.indexOf(self.sidebar) == -1:
                self.root_layout.insertWidget(0, self.sidebar)
            
            sidebar_width = self.sidebar_collapsed_width if self.sidebar_collapsed else self.sidebar_expanded_width
            self.sidebar.setMinimumWidth(sidebar_width)
            self.sidebar.setMaximumWidth(sidebar_width)

    def _set_sidebar_collapsed_visuals(self, collapsed):
        self.sidebar_collapsed = bool(collapsed)
        if self.sidebar_title is not None:
            self.sidebar_title.setText(
                self.sidebar_title_collapsed_text if self.sidebar_collapsed else self.sidebar_title_expanded_text
            )
        if self.sidebar_subtitle is not None:
            self.sidebar_subtitle.setVisible(not self.sidebar_collapsed)
        if self.sidebar_toggle_button is not None:
            self.sidebar_toggle_button.setText(">" if self.sidebar_collapsed else "<")
        for module_name, button in self.module_buttons.items():
            expanded_label, collapsed_label = self.nav_button_labels.get(module_name, (button.text(), button.text()))
            button.setText(collapsed_label if self.sidebar_collapsed else expanded_label)
            if self.sidebar_collapsed:
                button.setStyleSheet("text-align: center; padding-left: 0; padding-right: 0;")
            else:
                button.setStyleSheet("")
        self._queue_viewport_resize_notification()

    def _collapse_label(self, display_name):
        words = [word for word in str(display_name).replace("/", " ").split() if word]
        if not words:
            return "?"
        return "".join(word[0].upper() for word in words[:3]) or str(display_name)[:2].upper()

    def _set_workspace_status(self, module_name=None, message=None):
        if (hasattr(self, "_last_status_module") and self._last_status_module == module_name and
            hasattr(self, "_last_status_message") and self._last_status_message == message):
            return
        self._last_status_module = module_name
        self._last_status_message = message

        self._set_shell_window_title(module_name)
        if self.status_bar is not None and message:
            self.status_bar.showMessage(str(message), 4000)

    def _add_menu_action(self, menu, title, callback, shortcut=None):
        action = QAction(str(title), self)
        if shortcut is not None:
            action.setShortcut(shortcut)

        def _safe_triggered(_checked=False):
            try:
                callback()
            except Exception as exc:
                log_exception(f"pyqt6_host_shell.menu_action.{title}", exc)
                self.host_ui_adapter.show_error("Action Error", f"{title} failed: {exc}")

        action.triggered.connect(_safe_triggered)
        menu.addAction(action)
        return action

    def _invoke_viewport_module_action(self, module_name, action_name, unavailable_message, ensure_loaded=False):
        if not self._is_dispatcher_viewport_module(module_name) or self.dispatcher is None:
            return False
        if ensure_loaded:
            self.open_or_raise_module(module_name, restart=False)
        module_instance = getattr(self.dispatcher, "active_module_instance", None)
        active_module_name = str(getattr(self.dispatcher, "active_module_name", "") or "")
        if active_module_name != str(module_name or ""):
            if ensure_loaded:
                self.host_ui_adapter.show_warning("Action Unavailable", unavailable_message)
                return True
            return False
        action = getattr(module_instance, action_name, None)
        if not callable(action):
            self.host_ui_adapter.show_warning("Action Unavailable", unavailable_message)
            return True
        action()
        return True

    def menu_open(self):
        if self._invoke_viewport_module_action(
            "production_log",
            "show_pending",
            "Open Draft is unavailable because the Form Loader viewport is not available.",
            ensure_loaded=True,
        ):
            return
        self.host_ui_adapter.show_warning("Action Unavailable", "Open Draft is unavailable because the Form Loader viewport could not be loaded.")

    def menu_save(self):
        active_module_name = str(self.active_module_name or "").strip()
        if active_module_name == "production_log":
            if self._invoke_viewport_module_action(
                "production_log",
                "save_draft",
                "Save Draft is unavailable because the Form Loader viewport is not available.",
            ):
                return
            self.host_ui_adapter.show_warning("Action Unavailable", "Save Draft is unavailable because the Form Loader viewport is not available.")
            return
        if active_module_name == "internal_code_editor":
            if self._invoke_viewport_module_action(
                "internal_code_editor",
                "save_current_file",
                "Save is unavailable because the Internal Code Editor viewport is not available.",
            ):
                return
            self.host_ui_adapter.show_warning("Action Unavailable", "Save is unavailable because the Internal Code Editor viewport is not available.")
            return
        self.host_ui_adapter.show_warning(
            "Action Unavailable",
            "Save is currently implemented for the active Form Loader or Internal Code Editor viewport.",
        )

    def menu_export(self):
        if self._invoke_viewport_module_action(
            "production_log",
            "export_to_excel",
            "Export to Excel is unavailable because the Form Loader viewport is not available.",
            ensure_loaded=True,
        ):
            return
        self.host_ui_adapter.show_warning("Action Unavailable", "Export to Excel is unavailable because the Form Loader viewport could not be loaded.")

    def menu_import(self):
        if self._invoke_viewport_module_action(
            "production_log",
            "import_from_excel_ui",
            "Import Excel is unavailable because the Form Loader viewport is not available.",
            ensure_loaded=True,
        ):
            return
        self.host_ui_adapter.show_warning("Action Unavailable", "Import Excel is unavailable because the Form Loader viewport could not be loaded.")

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

    def _get_layout_manager_runtime_dispatcher(self):
        if self.dispatcher is None:
            return None
        return getattr(self.dispatcher, "layout_manager_dispatcher", None)

    def _uses_dedicated_window_contract(self, module_name):
        return str(module_name or "").strip() == "layout_manager" and self._get_layout_manager_runtime_dispatcher() is not None

    def _stop_runtime_if_non_persistent(self, module_name):
        if not module_name or self.is_module_persistent(module_name):
            return
        if self._uses_dedicated_window_contract(module_name):
            dedicated_runtime = self._get_layout_manager_runtime_dispatcher()
            if dedicated_runtime is not None:
                dedicated_runtime.stop_window()
        return

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

        if self._uses_dedicated_window_contract(module_name):
            dedicated_runtime = self._get_layout_manager_runtime_dispatcher()
            if dedicated_runtime is None:
                return False
            dedicated_runtime.open_or_raise_window(restart=bool(restart))
            self._switch_active_module(module_name)
            self._refresh_nav_button_states()
            self._refresh_active_module_text()
            self._notify_navigation_state("runtime_opened", module_name=module_name, restart=bool(restart))
            display_name = self._display_name_for_module(module_name) or module_name
            self.host_ui_adapter.show_toast(self.base_window_title, f"Opened {display_name} in its dedicated window.", duration_ms=3500)
            return True

        self.host_ui_adapter.show_warning(
            "Action Unavailable",
            f"{self._display_name_for_module(module_name) or module_name} does not expose a dedicated window contract on the active PyQt6 shell.",
        )
        return False

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
            self._set_workspace_status(message="Select a module from the navigation to begin.")
            if not self._viewport_has_content():
                self.show_viewport_placeholder(
                    title="Workspace",
                    message="Select a module from the navigation to start work.",
                )
            return

        entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
        display_name = str(entry["display_name"])
        if self._is_dispatcher_viewport_module(self.active_module_name):
            self._set_workspace_status(self.active_module_name, f"{display_name} is ready in the workspace.")
            return

        if self._uses_dedicated_window_contract(self.active_module_name):
            self._set_workspace_status(self.active_module_name, f"{display_name} uses its own window.")
            if not self._viewport_has_content():
                self.show_viewport_placeholder(
                    title=display_name,
                    message=f"{display_name} uses its own window.",
                    hint="Select Layout Manager again in the navigation to raise or restart its window.",
                )
            return
        self._set_workspace_status(self.active_module_name, f"{display_name} is not mapped to the workspace.")

    def _poll_runtime_state(self):
        if self.active_module_name is None:
            self._set_workspace_status(message="Select a module to begin.")
            return

        if self._is_dispatcher_viewport_module(self.active_module_name):
            entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
            display_name = str(entry["display_name"])
            self._set_workspace_status(self.active_module_name, f"{display_name} is ready in the workspace.")
            return

        if self._uses_dedicated_window_contract(self.active_module_name):
            dedicated_runtime = self._get_layout_manager_runtime_dispatcher()
            if dedicated_runtime is None:
                return
            state = dedicated_runtime.build_host_runtime_state()
            status = str(state.get("status") or "idle")
            message = str(state.get("message") or "No dedicated-window status is available.")
            entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
            display_name = str(entry["display_name"])
            self._set_workspace_status(self.active_module_name, message)
            if not self._viewport_has_content():
                hint = "Select Layout Manager again in the navigation to raise or restart its window."
                if status == "closed":
                    hint = "Select Layout Manager in the navigation to reopen its window."
                self.show_viewport_placeholder(
                    title=display_name,
                    message=message,
                    hint=hint,
                )
            return
        entry = self._module_entry(self.active_module_name) or {"display_name": self.active_module_name}
        display_name = str(entry["display_name"])
        message = f"{display_name} is not mapped to the workspace."
        self._set_workspace_status(self.active_module_name, message)
        if not self._viewport_has_content():
            self.show_viewport_placeholder(
                title=display_name,
                message=message,
                hint="Select another module from the navigation to continue working.",
            )

    def update_notification_button(self, count):
        if hasattr(self, "notifications_btn") and self.notifications_btn is not None:
            self.notifications_btn.setText(f"Notifications ({count})")

    def show_notification_center(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QDialogButtonBox, QFrame, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Notification History")
        dialog.resize(500, 400)
        dialog.setObjectName("notificationCenterDialog")
        
        surface_bg = self.theme_tokens.get("surface_bg", "#ffffff")
        surface_fg = self.theme_tokens.get("surface_fg", "#152129")
        muted_fg = self.theme_tokens.get("muted_fg", "#64748b")
        border_color = self.theme_tokens.get("border_color", "#e2e8f0")
        
        dialog.setStyleSheet(
            f"QDialog#notificationCenterDialog {{"
            f"  background-color: {surface_bg};"
            f"  border: 1px solid {border_color};"
            f"}}"
        )
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title_label = QLabel("Session Notifications", dialog)
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {surface_fg};")
        layout.addWidget(title_label)
        
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)
        
        history = getattr(self.host_ui_adapter, "_notification_history", [])
        unread_ids = {id(item) for item in history if not item.get("read", False)}
        
        if hasattr(self.host_ui_adapter, "mark_all_notifications_read"):
            self.host_ui_adapter.mark_all_notifications_read()
        else:
            for item in history:
                item["read"] = True
            self.update_notification_button(0)
            
        if not history:
            no_notif = QLabel("No notifications received in this session.", scroll_content)
            no_notif.setStyleSheet(f"color: {muted_fg}; font-style: italic; padding: 10px;")
            scroll_layout.addWidget(no_notif)
        else:
            for item in reversed(history):
                card = QFrame(scroll_content)
                is_new = id(item) in unread_ids
                
                if is_new:
                    bg_color = self.theme_tokens.get("accent_soft", "#eff6ff")
                    card_border_color = self.theme_tokens.get("accent", "#3b82f6")
                else:
                    bg_color = self.theme_tokens.get("content_bg", "#f8fafc")
                    card_border_color = border_color
                
                accent_color = self.theme_tokens.get("accent", "#0f7c8f")
                bootstyle = str(item.get("bootstyle") or "info").strip().lower()
                if bootstyle in {"success"}:
                    accent_color = "#10b981"
                elif bootstyle in {"warning"}:
                    accent_color = "#f59e0b"
                elif bootstyle in {"danger", "error", "critical"}:
                    accent_color = "#ef4444"
                
                card.setStyleSheet(
                    f"QFrame {{"
                    f"  background-color: {bg_color};"
                    f"  border: 1px solid {card_border_color};"
                    f"  border-left: 4px solid {accent_color};"
                    f"  border-radius: 6px;"
                    f"}}"
                )
                
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(12, 10, 12, 10)
                card_layout.setSpacing(4)
                
                header = QHBoxLayout()
                card_title = QLabel(item.get("title", "Notification"), card)
                card_title.setStyleSheet(f"font-weight: bold; color: {surface_fg}; border: none; background: transparent;")
                header.addWidget(card_title)
                
                if is_new:
                    new_badge = QLabel("NEW", card)
                    badge_fg = self.theme_tokens.get("sidebar_button_active_fg", "#ffffff")
                    badge_bg = self.theme_tokens.get("accent", "#0f7c8f")
                    new_badge.setStyleSheet(
                        f"color: {badge_fg};"
                        f"background-color: {badge_bg};"
                        f"font-size: 9px;"
                        f"font-weight: bold;"
                        f"padding: 1px 4px;"
                        f"border-radius: 3px;"
                        f"border: none;"
                    )
                    header.addWidget(new_badge)
                
                header.addStretch(1)
                card_time = QLabel(item.get("time", ""), card)
                card_time.setStyleSheet(f"color: {muted_fg}; font-size: 11px; border: none; background: transparent;")
                header.addWidget(card_time)
                card_layout.addLayout(header)
                
                card_msg = QLabel(item.get("message", ""), card)
                card_msg.setWordWrap(True)
                card_msg.setStyleSheet(f"color: {surface_fg}; border: none; background: transparent;")
                card_layout.addWidget(card_msg)
                
                scroll_layout.addWidget(card)
                
        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        dialog.exec()
        
    def closeEvent(self, event):
        if self._window_close_callback is not None and not self._closing_via_dispatcher:
            callback = self._window_close_callback
            callback()
            event.ignore()
            return

        dedicated_runtime = self._get_layout_manager_runtime_dispatcher()
        if dedicated_runtime is not None:
            try:
                dedicated_runtime.stop_window()
            except Exception:
                pass
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_sidebar_layout_state()
        self._queue_viewport_resize_notification()
