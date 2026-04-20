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
__module_name__ = "Host UI Adapter"
__version__ = "0.1.0"

from PyQt6.QtCore import QEvent, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

PYQT6_ADAPTER_AVAILABLE = True


class _QtMouseWheelForwarder(QObject if QObject is not None else object):
    def __init__(self, scroll_target, axis="y", parent=None):
        if QObject is not None:
            super().__init__(parent)
        self.scroll_target = scroll_target
        self.axis = "x" if str(axis).lower() == "x" else "y"

    def _resolve_scroll_bar(self):
        method_name = "horizontalScrollBar" if self.axis == "x" else "verticalScrollBar"
        getter = getattr(self.scroll_target, method_name, None)
        if callable(getter):
            return getter()
        return None

    def eventFilter(self, watched, event):
        _ = watched
        if QEvent is None or event is None or event.type() != QEvent.Type.Wheel:
            return False

        scroll_bar = self._resolve_scroll_bar()
        if scroll_bar is None:
            return False

        angle_delta = event.angleDelta()
        delta = angle_delta.x() if self.axis == "x" else angle_delta.y()
        if delta == 0:
            delta = angle_delta.y() or angle_delta.x()
        if delta == 0:
            return False

        base_step = scroll_bar.singleStep() or 20
        steps = max(1, abs(int(delta)) // 120)
        direction = -1 if delta > 0 else 1
        scroll_bar.setValue(scroll_bar.value() + (direction * base_step * 3 * steps))
        event.accept()
        return True


class _QtMainThreadInvoker(QObject if QObject is not None else object):
    if pyqtSignal is not None:
        invoke_callback = pyqtSignal(object)
        invoke_delayed_callback = pyqtSignal(int, object)

    def __init__(self, parent=None):
        if QObject is not None:
            super().__init__(parent)
        if pyqtSignal is not None:
            self.invoke_callback.connect(self._invoke_callback)
            self.invoke_delayed_callback.connect(self._invoke_delayed_callback)

    def _invoke_callback(self, callback):
        if callable(callback):
            callback()

    def _invoke_delayed_callback(self, delay_ms, callback):
        if not callable(callback):
            return
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        QTimer.singleShot(max(0, delay_ms), callback)


# DEPRECATED (Phase 9): Tk host UI adapter.
# `TkHostUiAdapter` remains for compatibility during the migration window.
# After Phase 9 validation and smoke tests, this adapter will be removed
# and `PyQt6HostUiAdapter` will be the sole host adapter implementation.
class TkHostUiAdapter:
    def __init__(self, dispatcher, toast_factory):
        _ = dispatcher
        _ = toast_factory
        raise RuntimeError("The Tk host UI adapter was removed in Phase 9. See shadow/app/host_ui_adapter.py.")


class PyQt6HostUiAdapter:
    def __init__(self, host_window):
        self.host_window = host_window
        self._wheel_forwarders = []
        self._main_thread_invoker = _QtMainThreadInvoker(host_window) if PYQT6_ADAPTER_AVAILABLE else None

    def call_later(self, delay_ms, callback):
        if not PYQT6_ADAPTER_AVAILABLE:
            return None
        try:
            delay_ms = int(delay_ms)
        except Exception:
            delay_ms = 0
        invoker = self._main_thread_invoker
        if invoker is not None and pyqtSignal is not None:
            if delay_ms <= 0:
                invoker.invoke_callback.emit(callback)
            else:
                invoker.invoke_delayed_callback.emit(delay_ms, callback)
            return None
        QTimer.singleShot(max(0, delay_ms), callback)
        return None

    def run_on_main_thread(self, callback):
        return self.call_later(0, callback)

    def cancel_call_later(self, timer_id):
        after_cancel = getattr(self.host_window, "after_cancel", None)
        if callable(after_cancel):
            after_cancel(timer_id)

    def request_shutdown(self, delay_ms=0):
        def close_window():
            self.host_window.close()

        return self.call_later(delay_ms, close_window)

    def supports_window_transition(self):
        return False

    def run_window_transition(self, action, duration_ms=0, min_alpha=0.86):
        _ = duration_ms
        _ = min_alpha
        return action()

    def bind_shell_viewport_resize(self, callback, add="+"):
        bind_viewport_resize = getattr(self.host_window, "bind_viewport_resize", None)
        if callable(bind_viewport_resize):
            return bind_viewport_resize(callback, add=add)
        return None

    def get_shell_viewport_size(self, min_width=0, min_height=0):
        get_viewport_size = getattr(self.host_window, "get_viewport_size", None)
        if callable(get_viewport_size):
            return get_viewport_size(min_width=min_width, min_height=min_height)

        try:
            min_width = int(min_width)
        except Exception:
            min_width = 0
        try:
            min_height = int(min_height)
        except Exception:
            min_height = 0
        width = max(self.host_window.width(), min_width)
        height = max(self.host_window.height(), min_height)
        return (width, height)

    def bind_mousewheel_to_widget_tree(self, root_widget, scroll_target, axis="y"):
        if QObject is None or root_widget is None or scroll_target is None:
            return None

        forwarder = _QtMouseWheelForwarder(scroll_target, axis=axis, parent=self.host_window)
        widgets = []

        if isinstance(root_widget, QObject):
            widgets.append(root_widget)

        find_children = getattr(root_widget, "findChildren", None)
        if callable(find_children):
            try:
                widgets.extend(root_widget.findChildren(QObject))
            except Exception:
                pass

        seen = set()
        for widget in widgets:
            if widget is None:
                continue
            widget_id = id(widget)
            if widget_id in seen:
                continue
            seen.add(widget_id)
            install_event_filter = getattr(widget, "installEventFilter", None)
            if callable(install_event_filter):
                try:
                    install_event_filter(forwarder)
                except Exception:
                    pass

        self._wheel_forwarders.append(forwarder)
        return forwarder

    def create_module_container(self, parent_reference, module_name=None):
        _ = parent_reference
        create_module_container = getattr(self.host_window, "create_module_container", None)
        if callable(create_module_container):
            return create_module_container(module_name=module_name)
        return None

    def container_exists(self, container):
        if container is None or getattr(container, "_dispatcher_destroyed", False):
            return False
        winfo_exists = getattr(container, "winfo_exists", None)
        if callable(winfo_exists):
            try:
                return bool(winfo_exists())
            except Exception:
                return False
        is_visible = getattr(container, "isVisible", None)
        if callable(is_visible):
            try:
                is_visible()
                return True
            except Exception:
                return False
        return True

    def hide_module_container(self, container):
        if container is None or getattr(container, "_dispatcher_destroyed", False):
            return
        hide = getattr(container, "hide", None)
        if callable(hide):
            hide()
            return
        set_visible = getattr(container, "setVisible", None)
        if callable(set_visible):
            set_visible(False)

    def show_module_container(self, container):
        if container is None or getattr(container, "_dispatcher_destroyed", False):
            return
        show = getattr(container, "show", None)
        if callable(show):
            show()
            return
        set_visible = getattr(container, "setVisible", None)
        if callable(set_visible):
            set_visible(True)

    def destroy_module_container(self, container):
        if container is None:
            return
        try:
            setattr(container, "_dispatcher_destroyed", True)
        except Exception:
            pass
        set_parent = getattr(container, "setParent", None)
        if callable(set_parent):
            try:
                set_parent(None)
            except Exception:
                pass
        delete_later = getattr(container, "deleteLater", None)
        if callable(delete_later):
            delete_later()
            return
        close = getattr(container, "close", None)
        if callable(close):
            close()

    def reset_shell_viewport_position(self):
        reset_viewport_position = getattr(self.host_window, "reset_viewport_position", None)
        if callable(reset_viewport_position):
            return reset_viewport_position()
        return None

    def refresh_viewport_appearance(self):
        refresh = getattr(self.host_window, "update_idletasks", None)
        if callable(refresh):
            return refresh()
        return None

    def show_toast(self, title, message, bootstyle=None, duration_ms=None):
        _ = bootstyle
        duration = duration_ms if duration_ms is not None else 5000
        combined = f"{title}: {message}" if title else str(message or "")
        status_bar = self.host_window.statusBar()
        if status_bar is not None:
            status_bar.showMessage(combined, max(0, int(duration)))

    def refresh_update_status_visibility(self):
        refresh = getattr(self.host_window, "refresh_update_status_visibility", None)
        if callable(refresh):
            return refresh()
        return None

    def show_error(self, title, message):
        if QMessageBox is not None:
            QMessageBox.critical(self.host_window, str(title), str(message))
            return
        self.show_toast(title, message, duration_ms=7000)

    def show_warning(self, title, message):
        if QMessageBox is not None:
            QMessageBox.warning(self.host_window, str(title), str(message))
            return
        self.show_toast(title, message, duration_ms=7000)

    def ask_yes_no(self, title, message):
        if QMessageBox is not None:
            response = QMessageBox.question(self.host_window, str(title), str(message))
            return response == QMessageBox.StandardButton.Yes
        return False

    def create_module_window(self, title=None, geometry=None, minsize=None):
        _ = title
        _ = geometry
        _ = minsize
        return None

    def destroy_module_window(self, window):
        _ = window
        return None
