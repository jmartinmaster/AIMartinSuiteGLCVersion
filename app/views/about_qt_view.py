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

from launcher import create_qt_application

__module_name__ = "About Qt View"
__version__ = "1.0.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QApplication = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QStatusBar = None
    QTableWidget = None
    QTableWidgetItem = None
    QVBoxLayout = None
    QWidget = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_about_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_about_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("About Qt session payload must be a JSON object.")
    return payload


class AboutQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "About"))
        self.resize(980, 720)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "PRODUCTION LOGGING CENTER"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "GLC Edition"))
        subtitle_label.setObjectName("mutedLabel")
        root_layout.addWidget(subtitle_label)

        info_group = QGroupBox("Application Info")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(str(self.payload.get("info_text") or ""))
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        root_layout.addWidget(info_group)

        controls_layout = QHBoxLayout()
        open_license_button = QPushButton("Open License")
        open_license_button.clicked.connect(self.controller.open_license)
        controls_layout.addWidget(open_license_button)

        repack_button = QPushButton("Repack Suite")
        repack_button.clicked.connect(self.controller.request_repack)
        repack_button.setEnabled(bool(self.payload.get("can_repack")))
        controls_layout.addWidget(repack_button)
        controls_layout.addStretch(1)
        root_layout.addLayout(controls_layout)

        manifest_group = QGroupBox("Module Manifest")
        manifest_layout = QVBoxLayout(manifest_group)
        self.manifest_table = QTableWidget()
        self.manifest_table.setColumnCount(3)
        self.manifest_table.setHorizontalHeaderLabels(["Module", "Version", "Source"])
        self.manifest_table.horizontalHeader().setStretchLastSection(True)
        self.manifest_table.verticalHeader().setVisible(False)
        self.manifest_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._populate_manifest(list(self.payload.get("module_manifest") or []))
        manifest_layout.addWidget(self.manifest_table)
        root_layout.addWidget(manifest_group, 1)

        footer_label = QLabel(str(self.payload.get("footer_text") or ""))
        footer_label.setObjectName("mutedLabel")
        root_layout.addWidget(footer_label)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("About Qt window ready.", 5000)

    def _populate_manifest(self, manifest_rows):
        self.manifest_table.setRowCount(len(manifest_rows))
        for row_index, row in enumerate(manifest_rows):
            self.manifest_table.setItem(row_index, 0, QTableWidgetItem(str(row.get("display_name") or "Unknown")))
            self.manifest_table.setItem(row_index, 1, QTableWidgetItem(f"v{row.get('version') or 'Unknown'}"))
            self.manifest_table.setItem(row_index, 2, QTableWidgetItem(str(row.get("source_suffix") or "built-in")))

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_about_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2
    from app.controllers.about_qt_controller import AboutQtController

    session_payload = load_about_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = AboutQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/about_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_about_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())