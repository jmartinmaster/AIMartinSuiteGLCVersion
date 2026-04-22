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
__version__ = "0.2.2"

from PyQt6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

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


class _QtToastPresenter(QFrame if QFrame is not None else object):
    def __init__(self, host_window):
        if QFrame is not None:
            super().__init__(host_window)
        self.host_window = host_window
        self._theme_tokens = {}
        self._current_title = ""
        self._current_message = ""
        self._current_bootstyle = None
        self._hide_after_ms = 5000
        self._fade_target = None

        if QWidget is None:
            return

        self.setObjectName("martinToastPresenter")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

        self._build_ui()
        self._configure_effects()

    def _build_ui(self):
        self.setMinimumWidth(280)
        self.setMaximumWidth(420)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.accent_bar = QFrame(self)
        self.accent_bar.setFixedWidth(6)
        root_layout.addWidget(self.accent_bar)

        body_widget = QWidget(self)
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(14, 12, 14, 12)
        body_layout.setSpacing(4)

        self.title_label = QLabel(body_widget)
        self.title_label.setWordWrap(True)
        body_layout.addWidget(self.title_label)

        self.message_label = QLabel(body_widget)
        self.message_label.setWordWrap(True)
        body_layout.addWidget(self.message_label)

        root_layout.addWidget(body_widget, 1)

    def _configure_effects(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_animation.setDuration(180)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self._on_fade_finished)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.start_hide)

    def show_toast(self, title, message, bootstyle, duration_ms, theme_tokens):
        if QWidget is None:
            return

        self._current_title = str(title or "")
        self._current_message = str(message or "")
        self._current_bootstyle = bootstyle
        self._hide_after_ms = max(1200, int(duration_ms))
        self._theme_tokens = dict(theme_tokens or {})

        self._apply_theme()
        self._reflow()
        self.raise_()
        self.show()
        self._start_fade(1.0)
        self.hide_timer.start(self._hide_after_ms)

    def refresh_theme(self, theme_tokens):
        if QWidget is None or not self.isVisible():
            return
        self._theme_tokens = dict(theme_tokens or {})
        self._apply_theme()
        self._reflow()

    def start_hide(self):
        if QWidget is None or not self.isVisible():
            return
        self.hide_timer.stop()
        self._start_fade(0.0)

    def reposition(self):
        if QWidget is None:
            return

        host_rect = self.host_window.rect()
        status_bar = getattr(self.host_window, "statusBar", lambda: None)()
        status_bar_height = status_bar.height() if status_bar is not None else 0
        margin = 20
        bottom_gap = status_bar_height + margin

        self.adjustSize()
        width = min(self.sizeHint().width(), max(240, host_rect.width() - (margin * 2)))
        height = self.sizeHint().height()
        x_pos = max(margin, host_rect.width() - width - margin)
        y_pos = max(margin, host_rect.height() - height - bottom_gap)
        self.resize(width, height)
        self.move(x_pos, y_pos)

    def _reflow(self):
        if QWidget is None:
            return
        available_width = max(240, self.host_window.width() - 48)
        max_width = min(420, available_width)
        self.setMaximumWidth(max_width)
        text_width = max(200, max_width - 54)
        self.title_label.setMaximumWidth(text_width)
        self.message_label.setMaximumWidth(text_width)
        self.reposition()

    def _apply_theme(self):
        tokens = dict(self._theme_tokens or {})
        surface_bg = str(tokens.get("surface_bg") or "#ffffff")
        surface_fg = str(tokens.get("surface_fg") or "#152129")
        muted_fg = str(tokens.get("muted_fg") or surface_fg)
        border_color = str(tokens.get("border_color") or "#c6d2d8")
        accent_color = self._resolve_severity_color(tokens, self._current_bootstyle)
        soft_fill = self._blend_with_surface(surface_bg, accent_color, 0.10)

        self.setStyleSheet(
            "".join(
                [
                    "QFrame#martinToastPresenter {",
                    f"background-color: {soft_fill};",
                    f"border: 1px solid {border_color};",
                    "border-radius: 12px;",
                    "}",
                ]
            )
        )
        self.accent_bar.setStyleSheet(
            "".join(
                [
                    "QFrame {",
                    f"background-color: {accent_color};",
                    "border-top-left-radius: 12px;",
                    "border-bottom-left-radius: 12px;",
                    "}",
                ]
            )
        )
        self.title_label.setText(self._current_title)
        self.title_label.setVisible(bool(self._current_title))
        self.title_label.setStyleSheet(f"color: {surface_fg}; font-weight: 700;")
        self.message_label.setText(self._current_message)
        self.message_label.setStyleSheet(f"color: {muted_fg};")

    def _resolve_severity_color(self, tokens, bootstyle):
        base_color = QColor(str(tokens.get("accent") or "#0f7c8f"))
        style_name = str(bootstyle or "info").strip().lower()
        target_hues = {
            "success": 145,
            "warning": 36,
            "danger": 5,
            "error": 5,
            "critical": 5,
        }
        hue = target_hues.get(style_name, base_color.hslHue())
        if hue < 0:
            hue = 190
        saturation = max(base_color.hslSaturation(), 120)
        lightness = max(base_color.lightness(), 118)
        return QColor.fromHsl(hue, saturation, lightness).name()

    def _blend_with_surface(self, surface_hex, overlay_hex, overlay_alpha):
        surface_color = QColor(str(surface_hex))
        overlay_color = QColor(str(overlay_hex))
        alpha = max(0.0, min(float(overlay_alpha), 1.0))
        red = round((surface_color.red() * (1.0 - alpha)) + (overlay_color.red() * alpha))
        green = round((surface_color.green() * (1.0 - alpha)) + (overlay_color.green() * alpha))
        blue = round((surface_color.blue() * (1.0 - alpha)) + (overlay_color.blue() * alpha))
        return QColor(red, green, blue).name()

    def _start_fade(self, target_opacity):
        self._fade_target = float(target_opacity)
        self.fade_animation.stop()
        self.fade_animation.setStartValue(self.opacity_effect.opacity())
        self.fade_animation.setEndValue(self._fade_target)
        self.fade_animation.start()

    def _on_fade_finished(self):
        if self._fade_target == 0.0:
            self.hide()


class PyQt6HostUiAdapter(QObject if QObject is not None else object):
    def __init__(self, host_window):
        if QObject is not None:
            super().__init__(host_window)
        self.host_window = host_window
        self._wheel_forwarders = []
        self._main_thread_invoker = _QtMainThreadInvoker(host_window) if PYQT6_ADAPTER_AVAILABLE else None
        self._toast_presenter = _QtToastPresenter(host_window) if QWidget is not None else None
        install_event_filter = getattr(self.host_window, "installEventFilter", None)
        if callable(install_event_filter):
            install_event_filter(self)

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
        payload = {
            "title": str(title or ""),
            "message": str(message or ""),
            "bootstyle": bootstyle,
            "duration_ms": self._resolve_toast_duration_ms(duration_ms),
            "theme_tokens": self._current_theme_tokens(),
            "has_presenter": self._toast_presenter is not None,
        }
        return self.run_on_main_thread(lambda current_payload=payload: self._present_toast(current_payload))

    def eventFilter(self, watched, event):
        if watched is self.host_window and event is not None and self._toast_presenter is not None:
            if event.type() in {
                QEvent.Type.Resize,
                QEvent.Type.Move,
                QEvent.Type.Show,
                QEvent.Type.WindowStateChange,
                QEvent.Type.StyleChange,
                QEvent.Type.PaletteChange,
                QEvent.Type.LayoutRequest,
            }:
                self._toast_presenter.refresh_theme(self._current_theme_tokens())
        return False

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

    def _present_toast(self, payload):
        if not payload.get("has_presenter") or self._toast_presenter is None:
            combined = f"{payload.get('title', '')}: {payload.get('message', '')}" if payload.get("title") else str(payload.get("message") or "")
            status_bar = self.host_window.statusBar()
            if status_bar is not None:
                status_bar.showMessage(combined, int(payload.get("duration_ms", 5000)))
            return None
        self._toast_presenter.show_toast(
            payload.get("title", ""),
            payload.get("message", ""),
            payload.get("bootstyle"),
            payload.get("duration_ms", 5000),
            payload.get("theme_tokens") or {},
        )
        return None

    def _current_theme_tokens(self):
        theme_tokens = getattr(self.host_window, "theme_tokens", None)
        if isinstance(theme_tokens, dict) and theme_tokens:
            return dict(theme_tokens)
        martin_theme_tokens = getattr(self.host_window, "_martin_theme_tokens", None)
        if isinstance(martin_theme_tokens, dict) and martin_theme_tokens:
            return dict(martin_theme_tokens)
        return {}

    def _resolve_toast_duration_ms(self, explicit_duration_ms=None):
        if explicit_duration_ms is not None:
            try:
                return max(800, int(explicit_duration_ms))
            except Exception:
                return 5000

        dispatcher = getattr(self.host_window, "dispatcher", None)
        get_setting = getattr(dispatcher, "get_setting", None)
        if callable(get_setting):
            try:
                return max(800, int(get_setting("toast_duration_sec", 5)) * 1000)
            except Exception:
                return 5000

        runtime_settings = getattr(self.host_window, "runtime_settings", {}) or {}
        try:
            return max(800, int(runtime_settings.get("toast_duration_sec", 5)) * 1000)
        except Exception:
            return 5000
