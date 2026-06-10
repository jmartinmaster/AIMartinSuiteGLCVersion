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
__module_name__ = "Recovery Viewer Qt View"
__version__ = "1.0.0"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PYQT6_AVAILABLE = True


class RecoveryViewerQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self._tab_definitions = (
            ("draft", "Pending Drafts"),
            ("snapshot", "Recovery Snapshots"),
            ("config_backup", "Config Backups"),
        )
        self._tab_base_labels = {record_type: label for record_type, label in self._tab_definitions}
        self._tables_by_record_type = {}
        self._tab_row_to_global_index = {}
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
        self.setWindowTitle(str(self.payload.get("window_title") or "Backup / Recovery"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self._fit_window_to_screen(1360, 900)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "Backup / Recovery"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(
            str(
                self.payload.get("subtitle")
                or "Browse pending drafts, snapshots, and backup artifacts from the Qt sidecar."
            )
        )
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        controls_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.controller.refresh_records)
        controls_layout.addWidget(refresh_button)

        restore_button = QPushButton("Restore Selected")
        restore_button.clicked.connect(self.controller.restore_selected)
        controls_layout.addWidget(restore_button)

        resume_button = QPushButton("Resume Selected Draft")
        resume_button.clicked.connect(self.controller.resume_selected)
        controls_layout.addWidget(resume_button)

        open_file_button = QPushButton("Open Selected File")
        open_file_button.clicked.connect(self.controller.open_selected_file)
        controls_layout.addWidget(open_file_button)

        open_folder_button = QPushButton("Open Containing Folder")
        open_folder_button.clicked.connect(self.controller.open_selected_folder)
        controls_layout.addWidget(open_folder_button)

        controls_layout.addStretch(1)
        root_layout.addLayout(controls_layout)

        self.tabs = QTabWidget()
        for record_type, tab_label in self._tab_definitions:
            table = self._create_table_widget()
            self._tables_by_record_type[record_type] = table
            self._tab_row_to_global_index[record_type] = []
            self.tabs.addTab(table, tab_label)
        root_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Recovery Viewer ready.", 5000)

    def _create_table_widget(self):
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Type", "File", "Form", "Saved", "Restore Target"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

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
        max_width = max(820, geometry.width() - int(padding))
        max_height = max(620, geometry.height() - int(padding))
        self.resize(min(int(requested_width), max_width), min(int(requested_height), max_height))

    def refresh_table(self, records):
        records = list(records or [])
        for tab_index, (record_type, _) in enumerate(self._tab_definitions):
            table = self._tables_by_record_type[record_type]
            row_to_global_index = []
            table_records = [
                (global_index, record)
                for global_index, record in enumerate(records)
                if str(record.get("record_type") or "") == record_type
            ]
            table.setRowCount(len(table_records))
            for row_index, (global_index, record) in enumerate(table_records):
                row_to_global_index.append(global_index)
                table.setItem(row_index, 0, QTableWidgetItem(str(record.get("kind") or "")))
                table.setItem(row_index, 1, QTableWidgetItem(str(record.get("name") or "")))
                table.setItem(row_index, 2, QTableWidgetItem(str(record.get("form_name") or "System")))
                table.setItem(row_index, 3, QTableWidgetItem(str(record.get("saved_at") or "")))
                table.setItem(row_index, 4, QTableWidgetItem(str(record.get("restore_target") or "")))
            self._tab_row_to_global_index[record_type] = row_to_global_index
            base_label = self._tab_base_labels.get(record_type, record_type)
            self.tabs.setTabText(tab_index, f"{base_label} ({len(table_records)})")
        self.status_bar.showMessage(f"Loaded {len(records)} recovery item(s).", 5000)

    def _current_tab_record_type(self):
        current_index = self.tabs.currentIndex()
        if current_index < 0 or current_index >= len(self._tab_definitions):
            return None
        return self._tab_definitions[current_index][0]

    def get_selected_index(self):
        record_type = self._current_tab_record_type()
        if record_type is None:
            return None
        table = self._tables_by_record_type[record_type]
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row_index = int(selected_rows[0].row())
        row_to_global_index = self._tab_row_to_global_index.get(record_type) or []
        if row_index < 0 or row_index >= len(row_to_global_index):
            return None
        return int(row_to_global_index[row_index])

    def set_selected_index(self, index):
        for table in self._tables_by_record_type.values():
            table.clearSelection()
        if index is None:
            return
        global_index = int(index)
        if global_index < 0:
            return
        for tab_index, (record_type, _) in enumerate(self._tab_definitions):
            row_to_global_index = self._tab_row_to_global_index.get(record_type) or []
            if global_index not in row_to_global_index:
                continue
            row_index = row_to_global_index.index(global_index)
            table = self._tables_by_record_type[record_type]
            self.tabs.setCurrentIndex(tab_index)
            table.selectRow(row_index)
            return

    def set_status(self, message):
        self.status_bar.showMessage(str(message), 5000)

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
        result = QMessageBox.question(self, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return result == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
