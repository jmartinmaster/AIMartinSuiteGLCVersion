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
import time

from app.app_platform import SPLASH_LOGO_RELATIVE_PATH
from app.theme_manager import get_theme_tokens, normalize_theme
from app.utils import resource_path

try:
    from PyQt6.QtCore import QRect, Qt, QTimer
    from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
    from PyQt6.QtWidgets import QApplication, QSplashScreen

    PYQT6_AVAILABLE = True
except ImportError:
    QApplication = None
    QColor = None
    QFont = None
    QPainter = None
    QPixmap = None
    QRect = None
    QSplashScreen = object
    Qt = None
    QTimer = None
    PYQT6_AVAILABLE = False

__module_name__ = "Splash Screen"
__version__ = "2.0.1"

DEFAULT_SPLASH_DURATION_MS = 5000
DEFAULT_SPLASH_WIDTH = 820
DEFAULT_SPLASH_HEIGHT = 430


def is_splash_screen_available():
    return PYQT6_AVAILABLE


class MartinSplashScreen(QSplashScreen):
    def __init__(self, theme_name=None, minimum_duration_ms=DEFAULT_SPLASH_DURATION_MS, logo_path=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")

        self.theme_name = normalize_theme(theme_name)
        self.theme_tokens = get_theme_tokens(theme_name=self.theme_name)
        self.logo_path = logo_path or resource_path(SPLASH_LOGO_RELATIVE_PATH)
        splash_pixmap = self._build_splash_pixmap()
        super().__init__(splash_pixmap)

        self.minimum_duration_ms = max(DEFAULT_SPLASH_DURATION_MS, int(minimum_duration_ms or DEFAULT_SPLASH_DURATION_MS))
        self.host_shell = None
        self.host_shell_ready = False
        self._shown_at = None
        self._finish_timer = None

        if Qt is not None:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

    def show_for_startup(self):
        self._shown_at = time.perf_counter()
        self.show()
        application = QApplication.instance()
        if application is not None:
            application.processEvents()
        return self

    def attach_host_shell(self, host_shell):
        self.host_shell = host_shell
        add_listener = getattr(host_shell, "add_startup_ready_listener", None)
        if callable(add_listener):
            add_listener(self.mark_host_shell_ready)
        return self

    def detach_host_shell(self):
        remove_listener = getattr(self.host_shell, "remove_startup_ready_listener", None)
        if callable(remove_listener):
            remove_listener(self.mark_host_shell_ready)
        self.host_shell = None

    def mark_host_shell_ready(self):
        if self.host_shell_ready:
            return
        self.host_shell_ready = True

        elapsed_ms = self.minimum_duration_ms
        if self._shown_at is not None:
            elapsed_ms = int((time.perf_counter() - self._shown_at) * 1000.0)

        remaining_ms = max(0, self.minimum_duration_ms - elapsed_ms)
        if remaining_ms <= 0:
            self.finish_if_ready()
            return

        if self._finish_timer is None:
            self._finish_timer = QTimer(self)
            self._finish_timer.setSingleShot(True)
            self._finish_timer.timeout.connect(self.finish_if_ready)
        self._finish_timer.start(remaining_ms)

    def finish_if_ready(self):
        if not self.host_shell_ready:
            return

        target_shell = self.host_shell
        self.detach_host_shell()
        if self._finish_timer is not None:
            self._finish_timer.stop()

        if target_shell is not None:
            self.finish(target_shell)
            target_shell.raise_()
            target_shell.activateWindow()
            return
        self.close()

    def _font_from_token(self, token_name, fallback_size, bold=False):
        font_value = self.theme_tokens.get(token_name)
        font = QFont()
        fallback_point_size = max(int(fallback_size or 10), 1)
        if isinstance(font_value, (tuple, list)) and font_value:
            font.setFamily(str(font_value[0]))
            point_size = fallback_point_size
            if len(font_value) >= 2:
                try:
                    point_size = int(font_value[1])
                except (TypeError, ValueError):
                    point_size = fallback_point_size
            if point_size <= 0:
                point_size = fallback_point_size
            font.setPointSize(point_size)
            font.setBold(any(str(part).lower() == "bold" for part in font_value[2:]))
        else:
            font.setPointSize(fallback_point_size)
            font.setBold(bool(bold))
        if font.pointSize() <= 0:
            font.setPointSize(fallback_point_size)
        if bold:
            font.setBold(True)
        return font

    def _build_splash_pixmap(self):
        tokens = self.theme_tokens
        width = DEFAULT_SPLASH_WIDTH
        height = DEFAULT_SPLASH_HEIGHT
        left_panel_rect = QRect(28, 42, 240, 300)
        runtime_label_rect = QRect(48, 288, 180, 38)
        runtime_notice_rect = QRect(48, 352, 724, 50)
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(tokens["surface_bg"]))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.fillRect(0, 0, width, height, QColor(tokens["surface_bg"]))
        painter.fillRect(0, 0, width, 12, QColor(tokens["accent"]))
        painter.fillRect(0, height - 8, width, 8, QColor(tokens["accent"]))
        painter.fillRect(left_panel_rect, QColor(tokens["accent_soft"]))
        painter.setPen(QColor(tokens["border_color"]))
        painter.drawRect(left_panel_rect)
        painter.drawRect(0, 0, width - 1, height - 1)

        logo_pixmap = QPixmap(self.logo_path)
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaled(
                180,
                180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_x = 58
            logo_y = 82
            painter.drawPixmap(logo_x, logo_y, scaled_logo)

        painter.setPen(QColor(tokens["surface_fg"]))
        painter.setFont(self._font_from_token("title_font", fallback_size=22, bold=True))
        painter.drawText(304, 102, "PRODUCTION LOGGING CENTER")

        painter.setFont(self._font_from_token("heading_font", fallback_size=13, bold=True))
        painter.setPen(QColor(tokens["accent"]))
        painter.drawText(304, 140, "GLC Edition")

        painter.setFont(self._font_from_token("nav_font", fallback_size=11))
        painter.setPen(QColor(tokens["surface_fg"]))
        painter.drawText(
            QRect(304, 178, 470, 72),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
            "Starting the PyQt6 host shell and restoring the active runtime session.",
        )

        painter.setPen(QColor(tokens["muted_fg"]))
        painter.drawText(
            QRect(304, 240, 470, 54),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
            "Created with PyQt6 provided by Riverbank Computing Limited",
        )

        painter.setPen(QColor(tokens["surface_fg"]))
        painter.drawText(
            runtime_label_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom),
            "PyQt6 Runtime",
        )

        painter.setPen(QColor(tokens["muted_fg"]))
        painter.drawText(
            runtime_notice_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
            "PyQt6 Notice: This application uses PyQt6 for the Qt 6 interface. See the About module for the full PyQt6 notice and licensing guidance.",
        )

        painter.end()
        return pixmap


def show_splash_screen(root=None, duration=DEFAULT_SPLASH_DURATION_MS, logo_path=None, theme_name=None):
    splash = MartinSplashScreen(theme_name=theme_name, minimum_duration_ms=duration, logo_path=logo_path)
    splash.show_for_startup()
    if root is not None:
        splash.attach_host_shell(root)
    return splash