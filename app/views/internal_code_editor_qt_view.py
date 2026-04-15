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

__module_name__ = "Internal Code Editor Qt View"
__version__ = "1.0.0"

try:
    from PyQt6.QtCore import QSignalBlocker, QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QPlainTextEdit,
        QSplitter,
        QStatusBar,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QApplication = None
    QComboBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QPlainTextEdit = None
    QSplitter = None
    QStatusBar = None
    QTreeWidget = None
    QTreeWidgetItem = None
    QVBoxLayout = None
    QWidget = None
    QSignalBlocker = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_internal_code_editor_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_internal_code_editor_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Internal Code Editor Qt session payload must be a JSON object.")
    return payload


class InternalCodeEditorQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.file_options = {}
        self.definition_entries = {}
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Internal Code Editor"))
        self.resize(1360, 900)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(10)

        title_label = QLabel(str(self.payload.get("title") or "Internal Code Editor"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Edit Python modules in-place."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("File"))
        self.file_selector = QComboBox()
        self.file_selector.currentIndexChanged.connect(self.controller.on_file_selected)
        controls_row.addWidget(self.file_selector, 1)

        reload_button = QPushButton("Reload")
        reload_button.clicked.connect(self.controller.reload_current_file)
        controls_row.addWidget(reload_button)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.controller.save_current_file)
        controls_row.addWidget(save_button)
        root_layout.addLayout(controls_row)

        self.source_label = QLabel("")
        self.source_label.setObjectName("mutedLabel")
        self.source_label.setWordWrap(True)
        root_layout.addWidget(self.source_label)

        self.save_target_label = QLabel("")
        self.save_target_label.setObjectName("mutedLabel")
        self.save_target_label.setWordWrap(True)
        root_layout.addWidget(self.save_target_label)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search"))
        self.search_entry = QLineEdit()
        search_row.addWidget(self.search_entry)

        prev_button = QPushButton("Previous")
        prev_button.clicked.connect(self.controller.find_previous)
        search_row.addWidget(prev_button)

        next_button = QPushButton("Next")
        next_button.clicked.connect(self.controller.find_next)
        search_row.addWidget(next_button)
        root_layout.addLayout(search_row)

        self.splitter = QSplitter()

        self.definition_tree = QTreeWidget()
        self.definition_tree.setHeaderLabels(["Name", "Kind", "Line"])
        self.definition_tree.itemSelectionChanged.connect(self.controller.on_definition_selected)
        self.splitter.addWidget(self.definition_tree)

        self.text_editor = QPlainTextEdit()
        self.text_editor.textChanged.connect(self.controller.handle_editor_modified)
        self.splitter.addWidget(self.text_editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)

        root_layout.addWidget(self.splitter, 1)

        self.definition_summary_label = QLabel("Definitions will appear for the open file.")
        self.definition_summary_label.setObjectName("mutedLabel")
        root_layout.addWidget(self.definition_summary_label)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Internal Code Editor Qt window ready.", 5000)

    def set_file_options(self, entries, selected_key):
        self.file_options = {entry["label"]: entry["key"] for entry in entries}
        with QSignalBlocker(self.file_selector):
            self.file_selector.clear()
            for entry in entries:
                self.file_selector.addItem(entry["label"])
        if selected_key is not None:
            self.select_file_key(selected_key)

    def select_file_key(self, file_key):
        if not file_key:
            return
        for index in range(self.file_selector.count()):
            label = self.file_selector.itemText(index)
            if self.file_options.get(label) == file_key:
                with QSignalBlocker(self.file_selector):
                    self.file_selector.setCurrentIndex(index)
                return

    def get_selected_file_key(self):
        label = self.file_selector.currentText()
        return self.file_options.get(label)

    def update_file_details(self, source_text, save_target_text):
        self.source_label.setText(str(source_text or ""))
        self.save_target_label.setText(str(save_target_text or ""))

    def set_editor_text(self, text):
        with QSignalBlocker(self.text_editor):
            self.text_editor.setPlainText(str(text or ""))

    def get_editor_text(self):
        return self.text_editor.toPlainText()

    def get_search_text(self):
        return self.search_entry.text()

    def focus_search(self):
        self.search_entry.setFocus()
        self.search_entry.selectAll()

    def find_text(self, search_text, backwards=False):
        if not search_text:
            return False
        text_cursor = self.text_editor.textCursor()
        document = self.text_editor.document()
        flags = text_cursor.FindFlag.FindBackward if backwards else text_cursor.FindFlag(0)
        found_cursor = document.find(search_text, text_cursor, flags)
        if found_cursor.isNull():
            start_cursor = self.text_editor.textCursor()
            start_cursor.movePosition(start_cursor.MoveOperation.End if backwards else start_cursor.MoveOperation.Start)
            found_cursor = document.find(search_text, start_cursor, flags)
        if found_cursor.isNull():
            return False
        self.text_editor.setTextCursor(found_cursor)
        return True

    def set_definition_entries(self, definition_entries):
        current_key = self.get_selected_definition_key()
        self.definition_entries = {entry["key"]: entry for entry in definition_entries}
        with QSignalBlocker(self.definition_tree):
            self.definition_tree.clear()
            for entry in definition_entries:
                item = QTreeWidgetItem([
                    str(entry["qualified_name"]),
                    str(entry["kind"].title()),
                    str(entry["line"]),
                ])
                item.setData(0, 0x0100, entry["key"])
                self.definition_tree.addTopLevelItem(item)
        if current_key and current_key in self.definition_entries:
            self.select_definition_key(current_key)

    def select_definition_key(self, definition_key):
        for index in range(self.definition_tree.topLevelItemCount()):
            item = self.definition_tree.topLevelItem(index)
            if item.data(0, 0x0100) == definition_key:
                self.definition_tree.setCurrentItem(item)
                return

    def get_selected_definition_key(self):
        item = self.definition_tree.currentItem()
        if item is None:
            return None
        return item.data(0, 0x0100)

    def update_definition_summary(self, definition_count, parse_error=None):
        if parse_error:
            self.definition_summary_label.setText(f"Index unavailable: {parse_error}")
            return
        noun = "definition" if definition_count == 1 else "definitions"
        self.definition_summary_label.setText(f"Indexed {definition_count} {noun} for the active file.")

    def show_definition_location(self, definition_entry):
        line_number = max(1, int(definition_entry.get("line") or 1))
        cursor = self.text_editor.textCursor()
        block = self.text_editor.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            cursor.setPosition(block.position())
            self.text_editor.setTextCursor(cursor)
            self.text_editor.centerCursor()
            self.text_editor.setFocus()

    def update_status(self, message):
        self.status_bar.showMessage(str(message or ""), 6000)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def confirm_discard_changes(self):
        response = QMessageBox.question(
            self,
            "Discard Unsaved Changes",
            "You have unsaved changes in the editor. Discard them and continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return response == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_internal_code_editor_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2

    from app.controllers.internal_code_editor_qt_controller import InternalCodeEditorQtController

    session_payload = load_internal_code_editor_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = InternalCodeEditorQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/internal_code_editor_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_internal_code_editor_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
