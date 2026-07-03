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
__module_name__ = "About Qt View"
__version__ = "1.0.2"

from PyQt6.QtCore import Qt
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


class AboutQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self._build_ui()
        self._attach_to_parent_container(parent_widget)

    def _attach_to_parent_container(self, parent_widget):
        if not self.embedded or parent_widget is None:
            return
        if Qt is not None:
            self.setWindowFlag(Qt.WindowType.Window, False)
        parent_layout = getattr(parent_widget, "layout", lambda: None)()
        if parent_layout is not None:
            parent_layout.addWidget(self)
        self.show()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "About"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self._fit_window_to_screen(980, 720)

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

        pyqt6_notice_text = str(self.payload.get("pyqt6_notice_text") or "").strip()
        if pyqt6_notice_text:
            pyqt6_group = QGroupBox("PyQt6 Notice")
            pyqt6_layout = QVBoxLayout(pyqt6_group)
            pyqt6_label = QLabel(pyqt6_notice_text)
            pyqt6_label.setWordWrap(True)
            pyqt6_layout.addWidget(pyqt6_label)
            root_layout.addWidget(pyqt6_group)

        controls_layout = QHBoxLayout()
        open_license_button = QPushButton("Open License")
        open_license_button.clicked.connect(self.controller.open_license)
        open_license_button.setAccessibleName("Open GPL license file")
        open_license_button.setAccessibleDescription("Opens the bundled GNU GPL license document in a text editor.")
        controls_layout.addWidget(open_license_button)

        repack_button = QPushButton("Repack Suite")
        repack_button.clicked.connect(self.controller.request_repack)
        repack_button.setEnabled(bool(self.payload.get("can_repack")))
        repack_button.setAccessibleName("Repack Suite button")
        repack_button.setAccessibleDescription("Regenerates the versioned suite ZIP archive from the active directory.")
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
        self.manifest_table.setAccessibleName("Module manifest table")
        self.manifest_table.setAccessibleDescription("List of modules in the application suite showing their versions and load sources.")
        self._populate_manifest(list(self.payload.get("module_manifest") or []))
        manifest_layout.addWidget(self.manifest_table)
        root_layout.addWidget(manifest_group, 1)

        footer_label = QLabel(str(self.payload.get("footer_text") or ""))
        footer_label.setObjectName("mutedLabel")
        root_layout.addWidget(footer_label)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("About view ready.", 5000)

    def _available_screen_geometry(self):
        window_handle = self.windowHandle()
        screen = window_handle.screen() if window_handle is not None else None
        if screen is None and hasattr(self, "screen"):
            try:
                screen = self.screen()
            except Exception:
                screen = None
        application = QApplication.instance()
        if screen is None and application is not None:
            screen = application.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _fit_window_to_screen(self, requested_width, requested_height, padding=48):
        geometry = self._available_screen_geometry()
        if geometry is None:
            self.resize(requested_width, requested_height)
            return
        max_width = max(720, geometry.width() - int(padding))
        max_height = max(540, geometry.height() - int(padding))
        self.resize(min(int(requested_width), max_width), min(int(requested_height), max_height))

    def _populate_manifest(self, manifest_rows):
        self.manifest_table.setRowCount(len(manifest_rows))
        for row_index, row in enumerate(manifest_rows):
            self.manifest_table.setItem(row_index, 0, QTableWidgetItem(str(row.get("display_name") or "Unknown")))
            self.manifest_table.setItem(row_index, 1, QTableWidgetItem(f"v{row.get('version') or 'Unknown'}"))
            self.manifest_table.setItem(row_index, 2, QTableWidgetItem(str(row.get("source_suffix") or "built-in")))

    def refresh_manifest(self, manifest_rows):
        self._populate_manifest(list(manifest_rows or []))

    def apply_theme(self, theme_tokens=None):
        if theme_tokens is not None:
            self.theme_tokens = dict(theme_tokens or {})
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)
        self.update()

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def ask_yes_no(self, title, message):
        decision = QMessageBox.question(
            self,
            str(title or "Confirm"),
            str(message or ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return decision == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
