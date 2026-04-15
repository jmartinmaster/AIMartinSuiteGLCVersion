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

__module_name__ = "Rate Manager Qt View"
__version__ = "1.0.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QLineEdit,
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
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
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


def is_rate_manager_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_rate_manager_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Rate Manager Qt session payload must be a JSON object.")
    return payload


class RateManagerQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Rate Manager"))
        self.resize(1100, 800)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "Rate Manager"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Manage per-part target rates."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.controller.on_search_changed)
        search_row.addWidget(self.search_input, 1)
        root_layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Part Number", "Target Rate"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root_layout.addWidget(self.table, 1)

        form_row = QHBoxLayout()
        form_row.addWidget(QLabel("Part #:"))
        self.part_input = QLineEdit()
        form_row.addWidget(self.part_input)
        form_row.addWidget(QLabel("Rate:"))
        self.rate_input = QLineEdit()
        form_row.addWidget(self.rate_input)
        root_layout.addLayout(form_row)

        actions = QHBoxLayout()
        self.primary_button = QPushButton("Add")
        self.primary_button.clicked.connect(self.controller.add_rate)
        actions.addWidget(self.primary_button)
        self.secondary_button = QPushButton("Edit")
        self.secondary_button.clicked.connect(self.controller.enter_edit_mode)
        actions.addWidget(self.secondary_button)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.controller.delete_rate)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        root_layout.addLayout(actions)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Rate Manager Qt window ready.", 5000)

    def get_search_text(self):
        return self.search_input.text()

    def refresh_table(self, rows):
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(row_index, 1, QTableWidgetItem(str(row[1])))
        self.status_bar.showMessage(f"Loaded {len(rows)} rate item(s).", 5000)

    def get_selected_part(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row_index = selected_rows[0].row()
        part_item = self.table.item(row_index, 0)
        if part_item is None:
            return None
        return part_item.text()

    def get_form_values(self):
        return self.part_input.text().strip(), self.rate_input.text().strip()

    def populate_edit_form(self, part_key, rate):
        self.part_input.setText(str(part_key))
        self.part_input.setEnabled(False)
        self.rate_input.setText(str(rate))
        self.primary_button.setText("Save")
        self.primary_button.clicked.disconnect()
        self.primary_button.clicked.connect(self.controller.save_edit)
        self.secondary_button.setText("Cancel")
        self.secondary_button.clicked.disconnect()
        self.secondary_button.clicked.connect(self.controller.cancel_edit)
        self.delete_button.setEnabled(False)

    def reset_form(self):
        self.part_input.setEnabled(True)
        self.part_input.clear()
        self.rate_input.clear()
        self.primary_button.setText("Add")
        self.primary_button.clicked.disconnect()
        self.primary_button.clicked.connect(self.controller.add_rate)
        self.secondary_button.setText("Edit")
        self.secondary_button.clicked.disconnect()
        self.secondary_button.clicked.connect(self.controller.enter_edit_mode)
        self.delete_button.setEnabled(True)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_rate_manager_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2

    from app.controllers.rate_manager_qt_controller import RateManagerQtController

    session_payload = load_rate_manager_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = RateManagerQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/rate_manager_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_rate_manager_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
