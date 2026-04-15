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
from app.models.production_log_calculations_model import EDITOR_SECTIONS

__module_name__ = "Production Log Calculations Qt View"
__version__ = "1.0.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFormLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QApplication = None
    QCheckBox = None
    QComboBox = None
    QFormLayout = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
    QListWidget = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QScrollArea = None
    QStatusBar = None
    QVBoxLayout = None
    QWidget = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_production_log_calculations_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_production_log_calculations_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Production Log Calculations Qt session payload must be a JSON object.")
    return payload


class ProductionLogCalculationsQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.form_widgets = {}
        self.choice_maps = {}
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Production Log Calculations"))
        self.resize(1200, 900)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        title_label = QLabel(str(self.payload.get("title") or "Production Log Calculations"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Developer controls for calculation behavior."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        for section in EDITOR_SECTIONS:
            group_box = QGroupBox(str(section.get("title") or "Section"))
            form_layout = QFormLayout(group_box)
            form_layout.setHorizontalSpacing(14)
            form_layout.setVerticalSpacing(8)
            for field in section.get("fields", []):
                widget = self._create_field_widget(field)
                label_text = str(field.get("label") or field.get("key") or "Field")
                form_layout.addRow(QLabel(label_text), widget)
            scroll_layout.addWidget(group_box)

        preview_group = QGroupBox("Active Formula Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_list = QListWidget()
        preview_layout.addWidget(self.preview_list)
        scroll_layout.addWidget(preview_group)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

        action_row = QHBoxLayout()
        save_button = QPushButton("Save Profile")
        save_button.clicked.connect(self.controller.save_settings)
        action_row.addWidget(save_button)

        reload_button = QPushButton("Reload Saved")
        reload_button.clicked.connect(self.controller.reload_from_disk)
        action_row.addWidget(reload_button)

        defaults_button = QPushButton("Reset Defaults")
        defaults_button.clicked.connect(self.controller.reset_defaults)
        action_row.addWidget(defaults_button)

        open_button = QPushButton("Open Production Log")
        open_button.clicked.connect(self.controller.open_production_log)
        action_row.addWidget(open_button)

        action_row.addStretch(1)
        root_layout.addLayout(action_row)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _create_field_widget(self, field):
        key = str(field.get("key") or "")
        kind = str(field.get("kind") or "entry")

        if kind == "bool":
            widget = QCheckBox()
            widget.stateChanged.connect(self.controller.on_form_changed)
            self.form_widgets[key] = widget
            return widget

        if kind == "choice":
            widget = QComboBox()
            value_by_label = {}
            label_by_value = {}
            for label, value in field.get("options", []):
                label_text = str(label)
                value_text = str(value)
                widget.addItem(label_text, value_text)
                value_by_label[label_text] = value_text
                label_by_value[value_text] = label_text
            widget.currentIndexChanged.connect(self.controller.on_form_changed)
            self.choice_maps[key] = {
                "value_by_label": value_by_label,
                "label_by_value": label_by_value,
            }
            self.form_widgets[key] = widget
            return widget

        widget = QLineEdit()
        widget.textChanged.connect(self.controller.on_form_changed)
        self.form_widgets[key] = widget
        return widget

    def get_form_values(self):
        values = {}
        for key, widget in self.form_widgets.items():
            if isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[key] = str(widget.currentData() or "")
            else:
                values[key] = widget.text()
        return values

    def set_form_values(self, values):
        values = values if isinstance(values, dict) else {}
        for key, widget in self.form_widgets.items():
            value = values.get(key)
            if isinstance(widget, QCheckBox):
                widget.blockSignals(True)
                widget.setChecked(bool(value))
                widget.blockSignals(False)
            elif isinstance(widget, QComboBox):
                widget.blockSignals(True)
                target = "" if value is None else str(value)
                index = widget.findData(target)
                if index < 0:
                    index = 0
                widget.setCurrentIndex(index)
                widget.blockSignals(False)
            else:
                widget.blockSignals(True)
                widget.setText("" if value is None else str(value))
                widget.blockSignals(False)

    def set_preview_lines(self, lines):
        self.preview_list.clear()
        for line in list(lines or []):
            self.preview_list.addItem(str(line))

    def set_status(self, message):
        self.status_bar.showMessage(str(message or ""), 6000)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_production_log_calculations_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2

    from app.controllers.production_log_calculations_qt_controller import ProductionLogCalculationsQtController

    session_payload = load_production_log_calculations_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = ProductionLogCalculationsQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/production_log_calculations_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_production_log_calculations_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
