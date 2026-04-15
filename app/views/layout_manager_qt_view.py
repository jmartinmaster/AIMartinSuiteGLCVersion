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
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from launcher import QT_MODULE_SESSION_ENV, create_qt_application
from app.theme_manager import get_qt_palette, get_qt_stylesheet

__module_name__ = "Layout Manager Qt View"
__version__ = "0.3.0"
LAYOUT_MANAGER_QT_SESSION_ENV = "AIMARTIN_LAYOUT_MANAGER_QT_SESSION"
REPO_ROOT = Path(__file__).resolve().parents[2]

try:
    from PyQt6.QtCore import QSignalBlocker, Qt, QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QComboBox,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QSplitter,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
        QInputDialog,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QApplication = None
    QComboBox = None
    QFormLayout = None
    QGridLayout = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
    QMainWindow = object
    QMessageBox = None
    QPlainTextEdit = None
    QPushButton = None
    QSplitter = None
    QStatusBar = None
    QTableWidget = None
    QTableWidgetItem = None
    QTabWidget = None
    QTreeWidget = None
    QTreeWidgetItem = None
    QVBoxLayout = None
    QWidget = None
    QInputDialog = None
    QSignalBlocker = None
    Qt = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_layout_manager_qt_runtime_available():
    return PYQT6_AVAILABLE


class LayoutManagerQtView(QMainWindow):
    def __init__(self, controller, theme_tokens=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.theme_tokens = dict(theme_tokens or {})
        self._updating_editor = False
        self._build_ui()
        self._apply_theme()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle("Layout Manager Qt")
        self.resize(1440, 920)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        header_layout = QGridLayout()
        header_layout.setHorizontalSpacing(18)
        header_layout.setVerticalSpacing(6)

        title_label = QLabel("Layout Manager")
        title_label.setObjectName("pageTitle")
        header_layout.addWidget(title_label, 0, 0, 1, 2)

        self.form_name_label = QLabel("Form: --")
        self.source_path_label = QLabel("Source: --")
        self.reason_label = QLabel("Ready")
        self.reason_label.setObjectName("mutedLabel")
        header_layout.addWidget(self.form_name_label, 1, 0)
        header_layout.addWidget(self.source_path_label, 1, 1)
        header_layout.addWidget(self.reason_label, 2, 0, 1, 2)
        root_layout.addLayout(header_layout)

        form_row = QHBoxLayout()
        form_row.setSpacing(8)
        form_row.addWidget(QLabel("Stored Forms"))
        self.form_combo = QComboBox()
        self.form_combo.setMinimumWidth(280)
        form_row.addWidget(self.form_combo)

        activate_button = QPushButton("Activate")
        activate_button.clicked.connect(self.controller.activate_selected_form)
        form_row.addWidget(activate_button)

        create_button = QPushButton("Create")
        create_button.clicked.connect(self.controller.create_form)
        form_row.addWidget(create_button)

        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(self.controller.duplicate_form)
        form_row.addWidget(duplicate_button)

        rename_button = QPushButton("Rename")
        rename_button.clicked.connect(self.controller.rename_form)
        form_row.addWidget(rename_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.controller.delete_form)
        form_row.addWidget(delete_button)
        form_row.addStretch(1)
        root_layout.addLayout(form_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        for label_text, callback in (
            ("Reload Current", self.controller.reload_current),
            ("Load Default", self.controller.load_default),
            ("Format JSON", self.controller.format_editor),
            ("Validate JSON", self.controller.validate_editor),
            ("Save", self.controller.save_current),
        ):
            button = QPushButton(label_text)
            button.clicked.connect(callback)
            action_row.addWidget(button)
        action_row.addStretch(1)
        root_layout.addLayout(action_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        editor_panel = QWidget()
        editor_layout = QVBoxLayout(editor_panel)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(8)
        editor_group = QGroupBox("JSON Editor")
        editor_group_layout = QVBoxLayout(editor_group)
        self.editor = QPlainTextEdit()
        self.editor.textChanged.connect(self._handle_editor_changed)
        editor_group_layout.addWidget(self.editor)
        editor_layout.addWidget(editor_group)
        splitter.addWidget(editor_panel)

        details_panel = QWidget()
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)
        self.tabs = QTabWidget()

        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(8)
        self.header_preview_table = QTableWidget()
        self.header_preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.header_preview_table.horizontalHeader().setStretchLastSection(True)
        self.header_preview_table.verticalHeader().setVisible(False)
        preview_layout.addWidget(self.header_preview_table, 2)

        self.row_sections_tree = QTreeWidget()
        self.row_sections_tree.setHeaderLabels(["Section / Field", "Details"])
        self.row_sections_tree.header().setStretchLastSection(True)
        preview_layout.addWidget(self.row_sections_tree, 1)
        self.tabs.addTab(preview_tab, "Preview")

        structure_tab = QWidget()
        structure_layout = QVBoxLayout(structure_tab)
        structure_layout.setContentsMargins(8, 8, 8, 8)
        structure_layout.setSpacing(8)
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderLabels(["Config Node", "Value"])
        self.structure_tree.header().setStretchLastSection(True)
        structure_layout.addWidget(self.structure_tree, 2)

        guardrail_group = QGroupBox("Guardrails")
        guardrail_layout = QVBoxLayout(guardrail_group)
        self.guardrails_view = QPlainTextEdit()
        self.guardrails_view.setReadOnly(True)
        guardrail_layout.addWidget(self.guardrails_view)
        structure_layout.addWidget(guardrail_group, 1)
        self.tabs.addTab(structure_tab, "Structure")

        summary_tab = QWidget()
        summary_layout = QFormLayout(summary_tab)
        self.field_count_value = QLabel("0")
        self.grid_shape_value = QLabel("0 x 0")
        self.dirty_value = QLabel("No")
        summary_layout.addRow("Header fields", self.field_count_value)
        summary_layout.addRow("Grid shape", self.grid_shape_value)
        summary_layout.addRow("Unsaved edits", self.dirty_value)
        self.tabs.addTab(summary_tab, "Summary")

        details_layout.addWidget(self.tabs)
        splitter.addWidget(details_panel)
        splitter.setSizes([780, 620])
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _apply_theme(self):
        tokens = self.theme_tokens
        self.setStyleSheet(get_qt_stylesheet(theme_tokens=tokens))
        application = QApplication.instance()
        if application is not None:
            application.setPalette(get_qt_palette(theme_tokens=tokens))

    def _handle_editor_changed(self):
        if self._updating_editor:
            return
        self.controller.mark_dirty()

    def set_editor_text(self, text):
        self._updating_editor = True
        self.editor.setPlainText(text)
        self._updating_editor = False

    def editor_text(self):
        return self.editor.toPlainText()

    def set_forms(self, forms, selected_form_id):
        blocker = QSignalBlocker(self.form_combo)
        self.form_combo.clear()
        for form_info in forms:
            form_name = str(form_info.get("name") or form_info.get("id") or "Unnamed Form")
            self.form_combo.addItem(form_name, form_info.get("id"))
        if selected_form_id:
            match_index = self.form_combo.findData(selected_form_id)
            if match_index >= 0:
                self.form_combo.setCurrentIndex(match_index)
        del blocker

    def current_form_id(self):
        return self.form_combo.currentData()

    def update_header(self, form_info, source_path, reason=""):
        form_name = str((form_info or {}).get("name") or (form_info or {}).get("id") or "Unknown")
        form_id = str((form_info or {}).get("id") or "")
        self.form_name_label.setText(f"Form: {form_name} [{form_id}]" if form_id else f"Form: {form_name}")
        self.source_path_label.setText(f"Source: {source_path or '--'}")
        self.reason_label.setText(reason or "Ready")

    def set_status(self, message, error=False):
        self.status_bar.showMessage(message, 10000)
        if error:
            self.reason_label.setText(message)

    def set_dirty(self, dirty):
        self.dirty_value.setText("Yes" if dirty else "No")
        title_suffix = " *" if dirty else ""
        self.setWindowTitle(f"Layout Manager Qt{title_suffix}")

    def render_preview_grid(self, preview_grid):
        preview = dict(preview_grid or {})
        row_count = int(preview.get("max_row", 0)) + 1
        column_count = int(preview.get("max_col", 0)) + 1
        self.header_preview_table.clear()
        self.header_preview_table.setRowCount(max(row_count, 1))
        self.header_preview_table.setColumnCount(max(column_count, 1))
        self.header_preview_table.setHorizontalHeaderLabels([f"Col {index}" for index in range(max(column_count, 1))])

        for cell in preview.get("cells", []):
            row = int(cell.get("row", 0))
            col = int(cell.get("col", 0))
            fields_here = cell.get("fields") or []
            text = "\n".join(
                f"{field.get('label', field.get('id', 'Field'))} -> {field.get('cell', '')}" for field in fields_here
            )
            item = QTableWidgetItem(text or "")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.header_preview_table.setItem(row, col, item)

        self.row_sections_tree.clear()
        for section in preview.get("row_sections", []):
            section_title = str(section.get("title") or section.get("section_name") or "Section")
            description = str(section.get("description") or "")
            section_item = QTreeWidgetItem([section_title, description])
            self.row_sections_tree.addTopLevelItem(section_item)
            for field in section.get("fields", []):
                details = [f"widget={field.get('widget', 'entry')}"]
                if field.get("protected"):
                    details.append("protected")
                if field.get("role"):
                    details.append(f"role={field.get('role')}")
                section_item.addChild(
                    QTreeWidgetItem(
                        [
                            str(field.get("label") or field.get("id") or "Field"),
                            ", ".join(details),
                        ]
                    )
                )
            section_item.setExpanded(True)

        self.field_count_value.setText(str(preview.get("field_count", 0)))
        self.grid_shape_value.setText(f"{row_count} x {column_count}")

    def render_structure(self, config, guardrails, protected_row_field_lookup):
        del protected_row_field_lookup
        self.structure_tree.clear()

        def add_node(parent_item, key, value):
            if isinstance(value, dict):
                item = QTreeWidgetItem([str(key), "object"])
                for child_key, child_value in value.items():
                    add_node(item, child_key, child_value)
            elif isinstance(value, list):
                item = QTreeWidgetItem([str(key), f"list[{len(value)}]"])
                for index, child_value in enumerate(value):
                    add_node(item, index, child_value)
            else:
                item = QTreeWidgetItem([str(key), json.dumps(value)])
            if parent_item is None:
                self.structure_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            return item

        for key, value in (config or {}).items():
            node = add_node(None, key, value)
            node.setExpanded(True)

        self.guardrails_view.setPlainText(json.dumps(guardrails or {}, indent=2))

    def prompt_text(self, title, label, default_text=""):
        text, accepted = QInputDialog.getText(self, title, label, QLineEdit.EchoMode.Normal, default_text)
        if not accepted:
            return None
        value = str(text).strip()
        return value or None

    def confirm(self, title, message):
        return QMessageBox.question(self, title, message) == QMessageBox.StandardButton.Yes

    def raise_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if not self.controller.can_close():
            event.ignore()
            return
        self.controller.handle_close()
        super().closeEvent(event)


def load_layout_manager_qt_session(session_path):
    session_file = Path(session_path)
    return json.loads(session_file.read_text(encoding="utf-8"))


def launch_layout_manager_qt_probe(payload):
    if not PYQT6_AVAILABLE:
        raise RuntimeError("PyQt6 is not installed in the active Python environment.")

    probe_payload = dict(payload or {})
    serialized_config = probe_payload.get("serialized_config") or "{}"
    config = json.loads(serialized_config)
    session_dir = Path(tempfile.mkdtemp(prefix="aimartin_layout_manager_qt_probe_"))
    state_path = session_dir / "state.json"
    command_path = session_dir / "command.json"
    session_path = session_dir / "session.json"
    state_path.write_text(
        json.dumps(
            {
                "status": "launching",
                "dirty": False,
                "change_token": 0,
                "message": "Launching Layout Manager Qt probe.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    session_path.write_text(
        json.dumps(
            {
                "module": "layout_manager",
                "form_info": {
                    "id": probe_payload.get("form_id") or "probe",
                    "name": probe_payload.get("form_name") or "Probe",
                },
                "source_path": probe_payload.get("source_label") or probe_payload.get("source_path") or "",
                "save_path": probe_payload.get("source_path") or "",
                "config": config,
                "guardrails": {},
                "protected_row_field_lookup": {},
                "theme_tokens": probe_payload.get("theme_tokens") or {},
                "state_path": str(state_path),
                "command_path": str(command_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env[LAYOUT_MANAGER_QT_SESSION_ENV] = str(session_path)
    env[QT_MODULE_SESSION_ENV] = str(session_path)
    command = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(REPO_ROOT / "main.py")]
    subprocess.Popen(command, cwd=str(REPO_ROOT), env=env, close_fds=True)


def run_layout_manager_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2
    from app.controllers.layout_manager_qt_controller import LayoutManagerQtController

    session_payload = load_layout_manager_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = LayoutManagerQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/layout_manager_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_layout_manager_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
