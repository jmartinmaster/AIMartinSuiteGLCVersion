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

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
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
    Qt = None
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
    PYQT6_AVAILABLE = False


class RecoveryViewerQtView(QMainWindow):
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
        self.setWindowTitle(str(self.payload.get("window_title") or "Backup / Recovery"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self.resize(1360, 900)

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

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Type", "File", "Form", "Saved", "Restore Target"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root_layout.addWidget(self.table, 1)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Recovery Viewer ready.", 5000)

    def refresh_table(self, records):
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            self.table.setItem(row_index, 0, QTableWidgetItem(str(record.get("kind") or "")))
            self.table.setItem(row_index, 1, QTableWidgetItem(str(record.get("name") or "")))
            self.table.setItem(row_index, 2, QTableWidgetItem(str(record.get("form_name") or "System")))
            self.table.setItem(row_index, 3, QTableWidgetItem(str(record.get("saved_at") or "")))
            self.table.setItem(row_index, 4, QTableWidgetItem(str(record.get("restore_target") or "")))
        self.status_bar.showMessage(f"Loaded {len(records)} recovery item(s).", 5000)

    def get_selected_index(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        return int(selected_rows[0].row())

    def set_selected_index(self, index):
        self.table.clearSelection()
        if index is None:
            return
        row_index = int(index)
        if row_index < 0 or row_index >= self.table.rowCount():
            return
        self.table.selectRow(row_index)

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
