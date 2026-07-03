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
__module_name__ = "Rate Manager Qt View"
__version__ = "1.1.1"

from PyQt6.QtCore import Qt
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


class RateManagerQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self._build_ui()
        self.apply_theme(theme_tokens=self.theme_tokens)
        if self.embedded:
            self._attach_to_parent_container(parent_widget)

    def _attach_to_parent_container(self, parent_widget):
        if parent_widget is None:
            return
        self.setWindowFlag(Qt.WindowType.Window, False)
        layout = parent_widget.layout()
        if layout is None:
            layout = QVBoxLayout(parent_widget)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self)
        self.show()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Rate Manager"))
        if not self.embedded:
            self._fit_window_to_screen(1100, 800)

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
        self.search_input.setAccessibleName("Search Rates")
        self.search_input.setAccessibleDescription("Type here to filter part numbers in the rates list.")
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
        self.table.setAccessibleName("Rates standards list")
        self.table.setAccessibleDescription("Table containing part numbers and their respective target rates.")
        root_layout.addWidget(self.table, 1)

        form_row = QHBoxLayout()
        form_row.addWidget(QLabel("Part #:"))
        self.part_input = QLineEdit()
        self.part_input.setAccessibleName("Part Number input")
        self.part_input.setAccessibleDescription("Enter the part number to add or edit.")
        form_row.addWidget(self.part_input)
        form_row.addWidget(QLabel("Rate:"))
        self.rate_input = QLineEdit()
        self.rate_input.setAccessibleName("Target Rate input")
        self.rate_input.setAccessibleDescription("Enter the molds-per-hour target rate for the part.")
        form_row.addWidget(self.rate_input)
        root_layout.addLayout(form_row)

        actions = QHBoxLayout()
        self.primary_button = QPushButton("Add")
        self.primary_button.clicked.connect(self.controller.add_rate)
        self.primary_button.setAccessibleName("Add rate standards button")
        self.primary_button.setAccessibleDescription("Click to add the new part and target rate or save edits.")
        actions.addWidget(self.primary_button)
        self.secondary_button = QPushButton("Edit")
        self.secondary_button.clicked.connect(self.controller.enter_edit_mode)
        self.secondary_button.setAccessibleName("Edit selected rate standard button")
        self.secondary_button.setAccessibleDescription("Click to edit the selected part's target rate or cancel.")
        actions.addWidget(self.secondary_button)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.controller.delete_rate)
        self.delete_button.setAccessibleName("Delete selected rate standard button")
        self.delete_button.setAccessibleDescription("Click to delete the selected part number and its rate standard.")
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        root_layout.addLayout(actions)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Rate Manager ready.", 5000)

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
        max_width = max(760, geometry.width() - int(padding))
        max_height = max(560, geometry.height() - int(padding))
        self.resize(min(int(requested_width), max_width), min(int(requested_height), max_height))

    def _rebind_button_click(self, button, callback):
        try:
            button.clicked.disconnect()
        except TypeError:
            pass
        button.clicked.connect(callback)

    def get_search_text(self):
        return self.search_input.text()

    def refresh_table(self, rows):
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.table.setItem(row_index, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(row_index, 1, QTableWidgetItem(str(row[1])))
        self.set_status(f"Loaded {len(rows)} rate item(s).")

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
        self._rebind_button_click(self.primary_button, self.controller.save_edit)
        self.secondary_button.setText("Cancel")
        self._rebind_button_click(self.secondary_button, self.controller.cancel_edit)
        self.delete_button.setEnabled(False)

    def reset_form(self):
        self.part_input.setEnabled(True)
        self.part_input.clear()
        self.rate_input.clear()
        self.primary_button.setText("Add")
        self._rebind_button_click(self.primary_button, self.controller.add_rate)
        self.secondary_button.setText("Edit")
        self._rebind_button_click(self.secondary_button, self.controller.enter_edit_mode)
        self.delete_button.setEnabled(True)

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

    def show_toast(self, title, message, bootstyle=None):
        self.controller.show_toast(title, message, bootstyle)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
