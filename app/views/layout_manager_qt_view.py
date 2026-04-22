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

from launcher import create_qt_application
from app.theme_manager import get_qt_palette, get_qt_stylesheet

__module_name__ = "Layout Manager Qt View"
__version__ = "0.4.0"
LAYOUT_MANAGER_QT_SESSION_ENV = "AIMARTIN_LAYOUT_MANAGER_QT_SESSION"
REPO_ROOT = Path(__file__).resolve().parents[2]

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
    QScrollArea,
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

    def _build_ui(self):
        self.setWindowTitle("Layout Manager Qt")
        self._fit_window_to_screen(1440, 920)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(central_widget)
        scroll_area.setWidgetResizable(True)
        self.content_scroll_area = scroll_area
        root_layout.addWidget(scroll_area, 1)

        scroll_content = QWidget(scroll_area)
        scroll_content.setMinimumWidth(1320)
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(12)

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
        content_layout.addLayout(header_layout)

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
        content_layout.addLayout(form_row)

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
        content_layout.addLayout(action_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setMinimumHeight(620)

        editor_panel = QWidget()
        editor_panel.setMinimumWidth(680)
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
        details_panel.setMinimumWidth(520)
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)
        self.tabs = QTabWidget()

        block_tab = QWidget()
        block_layout = QVBoxLayout(block_tab)
        block_layout.setContentsMargins(8, 8, 8, 8)
        block_layout.setSpacing(8)

        header_group = QGroupBox("Header Fields")
        header_layout = QVBoxLayout(header_group)
        self.header_fields_table = QTableWidget()
        self.header_fields_table.setColumnCount(11)
        self.header_fields_table.setHorizontalHeaderLabels(
            [
                "id",
                "label",
                "row",
                "col",
                "cell",
                "width",
                "readonly",
                "default",
                "role",
                "import_enabled",
                "export_enabled",
            ]
        )
        self.header_fields_table.horizontalHeader().setStretchLastSection(True)
        header_layout.addWidget(self.header_fields_table)

        header_actions = QHBoxLayout()
        header_add_button = QPushButton("Add Header Field")
        header_add_button.clicked.connect(self.controller.add_header_field_from_block)
        header_actions.addWidget(header_add_button)
        header_remove_button = QPushButton("Remove")
        header_remove_button.clicked.connect(self.controller.remove_header_field_from_block)
        header_actions.addWidget(header_remove_button)
        header_up_button = QPushButton("Move Up")
        header_up_button.clicked.connect(self.controller.move_header_field_up_from_block)
        header_actions.addWidget(header_up_button)
        header_down_button = QPushButton("Move Down")
        header_down_button.clicked.connect(self.controller.move_header_field_down_from_block)
        header_actions.addWidget(header_down_button)
        header_apply_button = QPushButton("Apply Selected")
        header_apply_button.clicked.connect(self.controller.apply_header_field_from_block)
        header_actions.addWidget(header_apply_button)
        header_actions.addStretch(1)
        header_layout.addLayout(header_actions)
        block_layout.addWidget(header_group)

        row_group = QGroupBox("Row Fields")
        row_layout = QVBoxLayout(row_group)
        row_section_row = QHBoxLayout()
        row_section_row.addWidget(QLabel("Section"))
        self.row_section_combo = QComboBox()
        self.row_section_combo.addItem("Production", "production_row_fields")
        self.row_section_combo.addItem("Downtime", "downtime_row_fields")
        self.row_section_combo.currentIndexChanged.connect(self.controller.on_row_section_changed)
        row_section_row.addWidget(self.row_section_combo)
        row_section_row.addStretch(1)
        row_layout.addLayout(row_section_row)

        self.row_fields_table = QTableWidget()
        self.row_fields_table.setColumnCount(10)
        self.row_fields_table.setHorizontalHeaderLabels(
            [
                "id",
                "label",
                "widget",
                "width",
                "role",
                "readonly",
                "derived",
                "open_row_trigger",
                "user_input",
                "values",
            ]
        )
        self.row_fields_table.horizontalHeader().setStretchLastSection(True)
        row_layout.addWidget(self.row_fields_table)

        row_actions = QHBoxLayout()
        row_add_button = QPushButton("Add Row Field")
        row_add_button.clicked.connect(self.controller.add_row_field_from_block)
        row_actions.addWidget(row_add_button)
        row_remove_button = QPushButton("Remove")
        row_remove_button.clicked.connect(self.controller.remove_row_field_from_block)
        row_actions.addWidget(row_remove_button)
        row_up_button = QPushButton("Move Up")
        row_up_button.clicked.connect(self.controller.move_row_field_up_from_block)
        row_actions.addWidget(row_up_button)
        row_down_button = QPushButton("Move Down")
        row_down_button.clicked.connect(self.controller.move_row_field_down_from_block)
        row_actions.addWidget(row_down_button)
        row_apply_button = QPushButton("Apply Selected")
        row_apply_button.clicked.connect(self.controller.apply_row_field_from_block)
        row_actions.addWidget(row_apply_button)
        row_actions.addStretch(1)
        row_layout.addLayout(row_actions)
        block_layout.addWidget(row_group)

        self.tabs.addTab(block_tab, "Block View")

        import_export_tab = QWidget()
        import_export_layout = QVBoxLayout(import_export_tab)
        import_export_layout.setContentsMargins(8, 8, 8, 8)
        import_export_layout.setSpacing(8)

        template_group = QGroupBox("Template Path")
        template_layout = QHBoxLayout(template_group)
        template_layout.addWidget(QLabel("template_path"))
        self.template_path_input = QLineEdit()
        template_layout.addWidget(self.template_path_input)
        template_apply_button = QPushButton("Apply")
        template_apply_button.clicked.connect(self.controller.apply_template_path_from_import_export)
        template_layout.addWidget(template_apply_button)
        import_export_layout.addWidget(template_group)

        mapping_group = QGroupBox("Row Mapping")
        mapping_layout = QVBoxLayout(mapping_group)

        mapping_selector_row = QHBoxLayout()
        mapping_selector_row.addWidget(QLabel("Mapping"))
        self.mapping_section_combo = QComboBox()
        self.mapping_section_combo.addItem("Production", "production_mapping")
        self.mapping_section_combo.addItem("Downtime", "downtime_mapping")
        self.mapping_section_combo.currentIndexChanged.connect(self.controller.on_mapping_section_changed)
        mapping_selector_row.addWidget(self.mapping_section_combo)
        mapping_selector_row.addWidget(QLabel("start_row"))
        self.mapping_start_row_input = QLineEdit()
        self.mapping_start_row_input.setFixedWidth(80)
        mapping_selector_row.addWidget(self.mapping_start_row_input)
        mapping_selector_row.addWidget(QLabel("max_rows"))
        self.mapping_max_rows_input = QLineEdit()
        self.mapping_max_rows_input.setFixedWidth(80)
        mapping_selector_row.addWidget(self.mapping_max_rows_input)
        mapping_selector_row.addStretch(1)
        mapping_layout.addLayout(mapping_selector_row)

        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(6)
        self.mapping_table.setHorizontalHeaderLabels(
            [
                "field_id",
                "column",
                "import_enabled",
                "export_enabled",
                "import_transform",
                "export_transform",
            ]
        )
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        mapping_layout.addWidget(self.mapping_table)

        mapping_actions = QHBoxLayout()
        mapping_apply_button = QPushButton("Apply Mapping")
        mapping_apply_button.clicked.connect(self.controller.apply_mapping_from_import_export)
        mapping_actions.addWidget(mapping_apply_button)
        mapping_actions.addStretch(1)
        mapping_layout.addLayout(mapping_actions)
        import_export_layout.addWidget(mapping_group)

        self.tabs.addTab(import_export_tab, "Import / Export")

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
        content_layout.addWidget(splitter, 1)

        content_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _apply_theme(self):
        tokens = self.theme_tokens
        self.setStyleSheet(get_qt_stylesheet(theme_tokens=tokens))
        application = QApplication.instance()
        if application is not None:
            application.setPalette(get_qt_palette(theme_tokens=tokens))

    def set_theme_tokens(self, theme_tokens):
        self.theme_tokens = dict(theme_tokens or {})
        self._apply_theme()

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

    def _set_table_text(self, table_widget, row_index, column_index, value):
        item = QTableWidgetItem(str(value if value is not None else ""))
        table_widget.setItem(row_index, column_index, item)

    def _cell_text(self, table_widget, row_index, column_index):
        item = table_widget.item(row_index, column_index)
        return str(item.text()).strip() if item is not None else ""

    def _selected_row_index(self, table_widget):
        selected_items = table_widget.selectedItems()
        if not selected_items:
            return -1
        return selected_items[0].row()

    def _mapping_name_to_row_section(self, mapping_name):
        return "downtime_row_fields" if mapping_name == "downtime_mapping" else "production_row_fields"

    def current_row_section_name(self):
        return str(self.row_section_combo.currentData() or "production_row_fields")

    def current_mapping_name(self):
        return str(self.mapping_section_combo.currentData() or "production_mapping")

    def render_block_authoring(self, config):
        header_fields = list(config.get("header_fields") or [])
        self.header_fields_table.setRowCount(len(header_fields))
        for row_index, field in enumerate(header_fields):
            self._set_table_text(self.header_fields_table, row_index, 0, field.get("id", ""))
            self._set_table_text(self.header_fields_table, row_index, 1, field.get("label", ""))
            self._set_table_text(self.header_fields_table, row_index, 2, field.get("row", 0))
            self._set_table_text(self.header_fields_table, row_index, 3, field.get("col", 0))
            self._set_table_text(self.header_fields_table, row_index, 4, field.get("cell", ""))
            self._set_table_text(self.header_fields_table, row_index, 5, field.get("width", ""))
            self._set_table_text(self.header_fields_table, row_index, 6, bool(field.get("readonly", False)))
            self._set_table_text(self.header_fields_table, row_index, 7, field.get("default", ""))
            self._set_table_text(self.header_fields_table, row_index, 8, field.get("role", ""))
            self._set_table_text(self.header_fields_table, row_index, 9, bool(field.get("import_enabled", True)))
            self._set_table_text(self.header_fields_table, row_index, 10, bool(field.get("export_enabled", True)))

        self.render_row_fields_authoring(config)

    def render_row_fields_authoring(self, config):
        section_name = self.current_row_section_name()
        row_fields = list(config.get(section_name) or [])
        self.row_fields_table.setRowCount(len(row_fields))
        for row_index, field in enumerate(row_fields):
            self._set_table_text(self.row_fields_table, row_index, 0, field.get("id", ""))
            self._set_table_text(self.row_fields_table, row_index, 1, field.get("label", ""))
            self._set_table_text(self.row_fields_table, row_index, 2, field.get("widget", "entry"))
            self._set_table_text(self.row_fields_table, row_index, 3, field.get("width", ""))
            self._set_table_text(self.row_fields_table, row_index, 4, field.get("role", ""))
            self._set_table_text(self.row_fields_table, row_index, 5, bool(field.get("readonly", False)))
            self._set_table_text(self.row_fields_table, row_index, 6, bool(field.get("derived", False)))
            self._set_table_text(self.row_fields_table, row_index, 7, bool(field.get("open_row_trigger", False)))
            self._set_table_text(self.row_fields_table, row_index, 8, bool(field.get("user_input", False)))
            values = field.get("values") if isinstance(field.get("values"), list) else []
            self._set_table_text(self.row_fields_table, row_index, 9, ", ".join(str(item).strip() for item in values if str(item).strip()))

    def render_import_export_authoring(self, config):
        self.template_path_input.setText(str(config.get("template_path") or ""))
        self.render_mapping_authoring(config)

    def render_mapping_authoring(self, config):
        mapping_name = self.current_mapping_name()
        mapping = config.get(mapping_name) if isinstance(config.get(mapping_name), dict) else {}
        self.mapping_start_row_input.setText(str(mapping.get("start_row", 1)))
        self.mapping_max_rows_input.setText(str(mapping.get("max_rows", 25)))
        row_section_name = self._mapping_name_to_row_section(mapping_name)
        row_fields = list(config.get(row_section_name) or [])
        columns = mapping.get("columns") if isinstance(mapping.get("columns"), dict) else {}

        self.mapping_table.setRowCount(len(row_fields))
        for row_index, field in enumerate(row_fields):
            field_id = str(field.get("id") or "").strip()
            self._set_table_text(self.mapping_table, row_index, 0, field_id)
            column_value = columns.get(field_id, "")
            if isinstance(column_value, dict):
                self._set_table_text(self.mapping_table, row_index, 1, column_value.get("column", ""))
                self._set_table_text(self.mapping_table, row_index, 2, bool(column_value.get("import_enabled", True)))
                self._set_table_text(self.mapping_table, row_index, 3, bool(column_value.get("export_enabled", True)))
                self._set_table_text(self.mapping_table, row_index, 4, column_value.get("import_transform", "value"))
                self._set_table_text(self.mapping_table, row_index, 5, column_value.get("export_transform", "value"))
            else:
                self._set_table_text(self.mapping_table, row_index, 1, column_value)
                self._set_table_text(self.mapping_table, row_index, 2, True)
                self._set_table_text(self.mapping_table, row_index, 3, True)
                self._set_table_text(self.mapping_table, row_index, 4, "value")
                self._set_table_text(self.mapping_table, row_index, 5, "value")

    def selected_header_field_id(self):
        row_index = self._selected_row_index(self.header_fields_table)
        if row_index < 0:
            return ""
        return self._cell_text(self.header_fields_table, row_index, 0)

    def selected_header_field_values(self):
        row_index = self._selected_row_index(self.header_fields_table)
        if row_index < 0:
            return None
        return {
            "row": self._cell_text(self.header_fields_table, row_index, 2),
            "col": self._cell_text(self.header_fields_table, row_index, 3),
            "cell": self._cell_text(self.header_fields_table, row_index, 4),
            "width": self._cell_text(self.header_fields_table, row_index, 5),
            "readonly": self._cell_text(self.header_fields_table, row_index, 6),
            "default": self._cell_text(self.header_fields_table, row_index, 7),
            "role": self._cell_text(self.header_fields_table, row_index, 8),
            "import_enabled": self._cell_text(self.header_fields_table, row_index, 9),
            "export_enabled": self._cell_text(self.header_fields_table, row_index, 10),
        }

    def selected_row_field_id(self):
        row_index = self._selected_row_index(self.row_fields_table)
        if row_index < 0:
            return ""
        return self._cell_text(self.row_fields_table, row_index, 0)

    def selected_row_field_values(self):
        row_index = self._selected_row_index(self.row_fields_table)
        if row_index < 0:
            return None
        return {
            "label": self._cell_text(self.row_fields_table, row_index, 1),
            "widget": self._cell_text(self.row_fields_table, row_index, 2),
            "width": self._cell_text(self.row_fields_table, row_index, 3),
            "role": self._cell_text(self.row_fields_table, row_index, 4),
            "readonly": self._cell_text(self.row_fields_table, row_index, 5),
            "derived": self._cell_text(self.row_fields_table, row_index, 6),
            "open_row_trigger": self._cell_text(self.row_fields_table, row_index, 7),
            "user_input": self._cell_text(self.row_fields_table, row_index, 8),
            "values": self._cell_text(self.row_fields_table, row_index, 9),
        }

    def template_path_value(self):
        return str(self.template_path_input.text()).strip()

    def mapping_form_values(self):
        column_values = {}
        for row_index in range(self.mapping_table.rowCount()):
            field_id = self._cell_text(self.mapping_table, row_index, 0)
            if not field_id:
                continue
            column_values[field_id] = {
                "column": self._cell_text(self.mapping_table, row_index, 1),
                "import_enabled": self._cell_text(self.mapping_table, row_index, 2),
                "export_enabled": self._cell_text(self.mapping_table, row_index, 3),
                "import_transform": self._cell_text(self.mapping_table, row_index, 4),
                "export_transform": self._cell_text(self.mapping_table, row_index, 5),
            }
        return {
            "start_row": self.mapping_start_row_input.text().strip(),
            "max_rows": self.mapping_max_rows_input.text().strip(),
            "columns": column_values,
        }

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
