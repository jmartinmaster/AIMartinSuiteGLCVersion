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
from app.production_log_roles import HEADER_FIELD_ROLE_DEFAULTS, ROW_FIELD_ROLE_DEFAULTS
from app.theme_manager import get_qt_palette, get_qt_stylesheet
from PyQt6.QtGui import QFont, QFontDatabase, QKeySequence, QShortcut

__module_name__ = "Layout Manager Qt View"
__version__ = "0.6.10"
LAYOUT_MANAGER_QT_SESSION_ENV = "AIMARTIN_LAYOUT_MANAGER_QT_SESSION"
REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_ROLE_OPTIONS = [""] + sorted(set(HEADER_FIELD_ROLE_DEFAULTS.values()))
HEADER_WIDGET_OPTIONS = ["entry", "combobox"]
ROW_ROLE_OPTIONS = {
    "production_row_fields": [""] + sorted(set(ROW_FIELD_ROLE_DEFAULTS["production"].values())),
    "downtime_row_fields": [""] + sorted(set(ROW_FIELD_ROLE_DEFAULTS["downtime"].values())),
}
STICKY_OPTIONS = ["", "w", "e", "n", "s", "ew", "we", "ns", "nw", "ne", "sw", "se", "nsew"]
STATE_OPTIONS = ["", "normal", "disabled", "readonly"]
OPTIONS_SOURCE_OPTIONS = ["", "downtime_codes"]
BOOTSTYLE_OPTIONS = ["", "primary", "secondary", "success", "info", "warning", "danger", "light", "dark"]

from PyQt6.QtCore import QEvent, QSignalBlocker, Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
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
        self._busy_cursor_active = False
        self.high_contrast_enabled = False
        self.font_profile = "default"
        self._preview_cell_fields = {}
        self._header_fields_cache_key = ""
        self._row_fields_cache_key = ""
        self._mapping_cache_key = ""
        self._table_render_tokens = {}
        self._excel_column_choices = self._build_excel_column_choices(260)
        self._row_section_to_mapping = {
            "production_row_fields": "production_mapping",
            "downtime_row_fields": "downtime_mapping",
        }
        self._mapping_to_row_section = {
            "production_mapping": "production_row_fields",
            "downtime_mapping": "downtime_row_fields",
        }
        application = QApplication.instance()
        self._default_app_font = QFont(application.font()) if application is not None else QFont(self.font())
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
        self.setObjectName("layoutManagerWindow")
        self._fit_window_to_screen(1500, 1040)

        central_widget = QWidget(self)
        central_widget.setObjectName("layoutManagerRoot")
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(central_widget)
        scroll_area.setWidgetResizable(True)
        self.content_scroll_area = scroll_area
        root_layout.addWidget(scroll_area, 1)

        scroll_content = QWidget(scroll_area)
        self.scroll_content = scroll_content
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(12)

        header_layout = QGridLayout()
        header_layout.setHorizontalSpacing(18)
        header_layout.setVerticalSpacing(6)

        self.form_name_label = QLabel("Form: --")
        self.form_name_label.setObjectName("mutedLabel")
        self.source_path_label = QLabel("Source: --")
        self.source_path_label.setObjectName("mutedLabel")
        self.reason_label = QLabel("Ready")
        self.reason_label.setObjectName("mutedLabel")
        header_layout.addWidget(self.form_name_label, 0, 0)
        header_layout.addWidget(self.source_path_label, 0, 1)
        header_layout.addWidget(self.reason_label, 1, 0, 1, 2)
        content_layout.addLayout(header_layout)

        ribbon_row = QHBoxLayout()
        ribbon_row.setSpacing(10)

        form_group = QGroupBox("Forms")
        form_row = QHBoxLayout(form_group)
        form_row.setSpacing(6)
        form_row.setContentsMargins(8, 8, 8, 8)
        form_row.addWidget(QLabel("Stored"))
        self.form_combo = QComboBox()
        self.form_combo.setMinimumWidth(260)
        form_row.addWidget(self.form_combo)

        activate_button = QPushButton("Activate")
        activate_button.clicked.connect(self.controller.activate_selected_form)
        activate_button.setMinimumHeight(26)
        form_row.addWidget(activate_button)
        ribbon_row.addWidget(form_group, 2)

        form_manage_group = QGroupBox("Manage")
        form_manage_row = QHBoxLayout(form_manage_group)
        form_manage_row.setSpacing(6)
        form_manage_row.setContentsMargins(8, 8, 8, 8)
        create_button = QPushButton("Create")
        create_button.clicked.connect(self.controller.create_form)
        create_button.setMinimumHeight(26)
        form_manage_row.addWidget(create_button)

        create_blank_button = QPushButton("Create Blank")
        create_blank_button.clicked.connect(self.controller.create_blank_form)
        create_blank_button.setMinimumHeight(26)
        form_manage_row.addWidget(create_blank_button)

        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(self.controller.duplicate_form)
        duplicate_button.setMinimumHeight(26)
        form_manage_row.addWidget(duplicate_button)

        rename_button = QPushButton("Rename")
        rename_button.clicked.connect(self.controller.rename_form)
        rename_button.setMinimumHeight(26)
        form_manage_row.addWidget(rename_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.controller.delete_form)
        delete_button.setMinimumHeight(26)
        form_manage_row.addWidget(delete_button)
        ribbon_row.addWidget(form_manage_group, 2)

        editor_group = QGroupBox("Editor")
        action_row = QHBoxLayout(editor_group)
        action_row.setSpacing(6)
        action_row.setContentsMargins(8, 8, 8, 8)
        for label_text, callback in (
            ("Reload Current", self.controller.reload_current),
            ("Load Default", self.controller.load_default),
            ("Format JSON", self.controller.format_editor),
            ("Validate JSON", self.controller.validate_editor),
            ("Save", self.controller.save_current),
        ):
            button = QPushButton(label_text)
            button.clicked.connect(callback)
            button.setMinimumHeight(26)
            action_row.addWidget(button)
        undo_button = QPushButton("Undo")
        undo_button.clicked.connect(self.controller.undo_last_change)
        undo_button.setMinimumHeight(26)
        action_row.addWidget(undo_button)
        redo_button = QPushButton("Redo")
        redo_button.clicked.connect(self.controller.redo_last_change)
        redo_button.setMinimumHeight(26)
        action_row.addWidget(redo_button)
        ribbon_row.addWidget(editor_group, 3)
        ribbon_row.addStretch(1)
        content_layout.addLayout(ribbon_row)

        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(760)

        self.json_editor_tab = QWidget()
        json_editor_layout = QVBoxLayout(self.json_editor_tab)
        json_editor_layout.setContentsMargins(8, 8, 8, 8)
        json_editor_layout.setSpacing(8)
        editor_group = QGroupBox("JSON Editor")
        editor_group_layout = QVBoxLayout(editor_group)
        self.editor = QPlainTextEdit()
        self.editor.textChanged.connect(self._handle_editor_changed)
        editor_group_layout.addWidget(self.editor)
        json_editor_layout.addWidget(editor_group)
        self.tabs.addTab(self.json_editor_tab, "JSON Editor")

        block_tab = QWidget()
        block_layout = QVBoxLayout(block_tab)
        block_layout.setContentsMargins(8, 8, 8, 8)
        block_layout.setSpacing(8)

        block_views_tabs = QTabWidget()
        block_views_tabs.setDocumentMode(True)

        header_fields_tab = QWidget()
        header_layout = QVBoxLayout(header_fields_tab)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(8)
        header_preset_row = QHBoxLayout()
        header_preset_row.addWidget(QLabel("Preset"))
        self.header_field_preset_combo = QComboBox()
        self.header_field_preset_combo.setMinimumWidth(240)
        header_preset_row.addWidget(self.header_field_preset_combo)
        header_preset_add_button = QPushButton("Add Preset Field")
        header_preset_add_button.clicked.connect(self.controller.add_selected_preset_header_field_from_block)
        header_preset_row.addWidget(header_preset_add_button)
        header_preset_row.addStretch(1)
        header_layout.addLayout(header_preset_row)

        self.header_fields_table = QTableWidget()
        self._configure_authoring_table(self.header_fields_table)
        self.header_fields_table.setColumnCount(15)
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
                "widget",
                "state",
                "options_source",
                "values",
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
        block_views_tabs.addTab(header_fields_tab, "Header Fields")

        row_fields_tab = QWidget()
        row_layout = QVBoxLayout(row_fields_tab)
        row_layout.setContentsMargins(8, 8, 8, 8)
        row_layout.setSpacing(8)
        row_section_row = QHBoxLayout()
        row_section_row.addWidget(QLabel("Section"))
        self.row_section_combo = QComboBox()
        self.row_section_combo.currentIndexChanged.connect(self.controller.on_row_section_changed)
        row_section_row.addWidget(self.row_section_combo)
        row_section_row.addWidget(QLabel("Preset"))
        self.row_field_preset_combo = QComboBox()
        self.row_field_preset_combo.setMinimumWidth(240)
        row_section_row.addWidget(self.row_field_preset_combo)
        row_preset_add_button = QPushButton("Add Preset Column")
        row_preset_add_button.clicked.connect(self.controller.add_selected_preset_row_field_from_block)
        row_section_row.addWidget(row_preset_add_button)
        row_section_row.addStretch(1)
        row_layout.addLayout(row_section_row)

        self.row_fields_table = QTableWidget()
        self._configure_authoring_table(self.row_fields_table)
        self.row_fields_table.setColumnCount(18)
        self.row_fields_table.setHorizontalHeaderLabels(
            [
                "id",
                "label",
                "widget",
                "width",
                "role",
                "readonly",
                "derived",
                "math_trigger",
                "open_row_trigger",
                "user_input",
                "expand",
                "bold",
                "default",
                "sticky",
                "state",
                "options_source",
                "bootstyle",
                "values",
            ]
        )
        self.row_fields_table.horizontalHeader().setStretchLastSection(True)
        row_layout.addWidget(self.row_fields_table)

        row_actions = QHBoxLayout()
        row_add_button = QPushButton("Add Blank Field")
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
        bulk_rename_button = QPushButton("Bulk Rename")
        bulk_rename_button.clicked.connect(self.controller.bulk_rename_row_fields)
        row_actions.addWidget(bulk_rename_button)
        bulk_delete_button = QPushButton("Bulk Delete Match")
        bulk_delete_button.clicked.connect(self.controller.bulk_delete_row_fields)
        row_actions.addWidget(bulk_delete_button)
        bulk_convert_button = QPushButton("Bulk Convert Widget")
        bulk_convert_button.clicked.connect(self.controller.bulk_convert_row_widgets)
        row_actions.addWidget(bulk_convert_button)
        row_actions.addStretch(1)
        row_layout.addLayout(row_actions)
        block_views_tabs.addTab(row_fields_tab, "Row Fields")

        block_layout.addWidget(block_views_tabs, 1)

        self.tabs.addTab(block_tab, "Block View")

        import_export_tab = QWidget()
        import_export_layout = QVBoxLayout(import_export_tab)
        import_export_layout.setContentsMargins(8, 8, 8, 8)
        import_export_layout.setSpacing(8)

        import_export_views_tabs = QTabWidget()
        import_export_views_tabs.setDocumentMode(True)

        template_group = QGroupBox("Template Path")
        template_layout = QHBoxLayout(template_group)
        template_layout.addWidget(QLabel("template_path"))
        self.template_path_input = QLineEdit()
        template_layout.addWidget(self.template_path_input)
        template_apply_button = QPushButton("Apply")
        template_apply_button.clicked.connect(self.controller.apply_template_path_from_import_export)
        template_layout.addWidget(template_apply_button)

        template_tab = QWidget()
        template_tab_layout = QVBoxLayout(template_tab)
        template_tab_layout.setContentsMargins(8, 8, 8, 8)
        template_tab_layout.setSpacing(8)
        template_tab_layout.addWidget(template_group)
        template_tab_layout.addStretch(1)
        import_export_views_tabs.addTab(template_tab, "Template Path")

        mapping_group = QGroupBox("Row Mapping")
        mapping_layout = QVBoxLayout(mapping_group)

        mapping_selector_row = QHBoxLayout()
        mapping_selector_row.addWidget(QLabel("Mapping"))
        self.mapping_section_combo = QComboBox()
        self.mapping_section_combo.currentIndexChanged.connect(self.controller.on_mapping_section_changed)
        mapping_selector_row.addWidget(self.mapping_section_combo)
        mapping_selector_row.addWidget(QLabel("Column"))
        self.mapping_column_selector = QComboBox()
        self.mapping_column_selector.setEditable(True)
        self.mapping_column_selector.setMinimumWidth(110)
        mapping_selector_row.addWidget(self.mapping_column_selector)
        mapping_assign_button = QPushButton("Assign Column")
        mapping_assign_button.clicked.connect(self.controller.assign_selected_mapping_column_from_import_export)
        mapping_selector_row.addWidget(mapping_assign_button)
        mapping_clear_button = QPushButton("Clear Selected")
        mapping_clear_button.clicked.connect(self.controller.clear_selected_mapping_column_from_import_export)
        mapping_selector_row.addWidget(mapping_clear_button)
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
        self._configure_authoring_table(self.mapping_table)
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

        mapping_tab = QWidget()
        mapping_tab_layout = QVBoxLayout(mapping_tab)
        mapping_tab_layout.setContentsMargins(8, 8, 8, 8)
        mapping_tab_layout.setSpacing(8)
        mapping_tab_layout.addWidget(mapping_group, 1)
        import_export_views_tabs.addTab(mapping_tab, "Row Mapping")

        self.import_export_metadata_label = QLabel("")
        self.import_export_metadata_label.setObjectName("mutedLabel")
        self.import_export_metadata_label.setWordWrap(True)

        self.import_export_status_label = QLabel("")
        self.import_export_status_label.setObjectName("mutedLabel")
        self.import_export_status_label.setVisible(False)

        import_export_status_tab = QWidget()
        import_export_status_layout = QVBoxLayout(import_export_status_tab)
        import_export_status_layout.setContentsMargins(8, 8, 8, 8)
        import_export_status_layout.setSpacing(8)
        import_export_status_layout.addWidget(self.import_export_metadata_label)
        import_export_status_layout.addWidget(self.import_export_status_label)
        import_export_status_layout.addStretch(1)
        import_export_views_tabs.addTab(import_export_status_tab, "Status")

        import_export_layout.addWidget(import_export_views_tabs, 1)

        self.tabs.addTab(import_export_tab, "Import / Export")
        self.set_available_mapping_columns(self._excel_column_choices)
        self.set_header_field_presets([])
        self.set_row_field_presets([])

        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(8)

        preview_views_tabs = QTabWidget()
        preview_views_tabs.setDocumentMode(True)

        header_preview_tab = QWidget()
        header_preview_layout = QVBoxLayout(header_preview_tab)
        header_preview_layout.setContentsMargins(8, 8, 8, 8)
        header_preview_layout.setSpacing(8)
        self.header_preview_table = QTableWidget()
        self.header_preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.header_preview_table.horizontalHeader().setStretchLastSection(True)
        self.header_preview_table.verticalHeader().setVisible(False)
        self.header_preview_table.cellClicked.connect(self._on_preview_cell_selected)
        header_preview_layout.addWidget(self.header_preview_table, 1)
        preview_views_tabs.addTab(header_preview_tab, "Header Preview")

        row_sections_tab = QWidget()
        row_sections_layout = QVBoxLayout(row_sections_tab)
        row_sections_layout.setContentsMargins(8, 8, 8, 8)
        row_sections_layout.setSpacing(8)
        self.row_sections_tree = QTreeWidget()
        self.row_sections_tree.setHeaderLabels(["Section / Field", "Details"])
        self.row_sections_tree.header().setStretchLastSection(True)
        row_sections_layout.addWidget(self.row_sections_tree, 1)
        preview_views_tabs.addTab(row_sections_tab, "Row Sections")

        preview_metadata_group = QGroupBox("Preview Metadata")
        preview_metadata_layout = QVBoxLayout(preview_metadata_group)
        self.preview_metadata_view = QPlainTextEdit()
        self.preview_metadata_view.setReadOnly(True)
        preview_metadata_layout.addWidget(self.preview_metadata_view)

        preview_metadata_tab = QWidget()
        preview_metadata_tab_layout = QVBoxLayout(preview_metadata_tab)
        preview_metadata_tab_layout.setContentsMargins(8, 8, 8, 8)
        preview_metadata_tab_layout.setSpacing(8)
        preview_metadata_tab_layout.addWidget(preview_metadata_group, 1)
        preview_views_tabs.addTab(preview_metadata_tab, "Metadata")

        preview_layout.addWidget(preview_views_tabs, 1)
        self.tabs.addTab(preview_tab, "Preview")

        structure_tab = QWidget()
        structure_layout = QVBoxLayout(structure_tab)
        structure_layout.setContentsMargins(8, 8, 8, 8)
        structure_layout.setSpacing(8)

        structure_views_tabs = QTabWidget()
        structure_views_tabs.setDocumentMode(True)

        section_editor_tab = QWidget()
        section_editor_layout = QVBoxLayout(section_editor_tab)
        section_editor_layout.setContentsMargins(8, 8, 8, 8)
        section_editor_layout.setSpacing(8)

        section_selector_row = QHBoxLayout()
        section_selector_row.addWidget(QLabel("Section"))
        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(280)
        self.section_combo.currentIndexChanged.connect(self.controller.on_section_changed)
        section_selector_row.addWidget(self.section_combo)
        section_add_button = QPushButton("Add Section")
        section_add_button.clicked.connect(self.controller.add_section_from_structure)
        section_selector_row.addWidget(section_add_button)
        section_remove_button = QPushButton("Remove Section")
        section_remove_button.clicked.connect(self.controller.remove_section_from_structure)
        section_selector_row.addWidget(section_remove_button)
        section_up_button = QPushButton("Move Up")
        section_up_button.clicked.connect(self.controller.move_section_up_from_structure)
        section_selector_row.addWidget(section_up_button)
        section_down_button = QPushButton("Move Down")
        section_down_button.clicked.connect(self.controller.move_section_down_from_structure)
        section_selector_row.addWidget(section_down_button)
        section_apply_button = QPushButton("Apply Section")
        section_apply_button.clicked.connect(self.controller.apply_section_from_structure)
        section_selector_row.addWidget(section_apply_button)
        section_selector_row.addStretch(1)
        section_editor_layout.addLayout(section_selector_row)

        section_form = QFormLayout()
        section_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        section_form.setHorizontalSpacing(12)
        section_form.setVerticalSpacing(8)
        self.section_name_input = QLineEdit()
        self.section_name_input.setMinimumHeight(30)
        self.section_name_input.setMinimumWidth(520)
        section_form.addRow("Name", self.section_name_input)
        self.section_description_input = QLineEdit()
        self.section_description_input.setMinimumHeight(30)
        self.section_description_input.setMinimumWidth(520)
        section_form.addRow("Description", self.section_description_input)
        self.section_type_combo = QComboBox()
        self.section_type_combo.addItem("single", "single")
        self.section_type_combo.addItem("repeating", "repeating")
        self.section_type_combo.setMinimumHeight(30)
        section_form.addRow("Section Type", self.section_type_combo)
        self.section_behavior_profile_input = QLineEdit()
        self.section_behavior_profile_input.setMinimumHeight(30)
        section_form.addRow("Behavior Profile", self.section_behavior_profile_input)
        self.section_default_max_rows_input = QLineEdit()
        self.section_default_max_rows_input.setMinimumHeight(30)
        section_form.addRow("Default Max Rows", self.section_default_max_rows_input)
        self.section_show_delete_combo = QComboBox()
        self.section_show_delete_combo.addItem("True", True)
        self.section_show_delete_combo.addItem("False", False)
        self.section_show_delete_combo.setMinimumHeight(30)
        section_form.addRow("Show Delete Button", self.section_show_delete_combo)
        self.section_delete_label_input = QLineEdit()
        self.section_delete_label_input.setMinimumHeight(30)
        section_form.addRow("Delete Button Label", self.section_delete_label_input)
        self.section_delete_tooltip_input = QLineEdit()
        self.section_delete_tooltip_input.setMinimumHeight(30)
        section_form.addRow("Delete Button Tooltip", self.section_delete_tooltip_input)
        self.section_require_confirm_combo = QComboBox()
        self.section_require_confirm_combo.addItem("False", False)
        self.section_require_confirm_combo.addItem("True", True)
        self.section_require_confirm_combo.setMinimumHeight(30)
        section_form.addRow("Require Delete Confirm", self.section_require_confirm_combo)
        section_form_container = QWidget()
        section_form_container_layout = QVBoxLayout(section_form_container)
        section_form_container_layout.setContentsMargins(0, 0, 0, 0)
        section_form_container_layout.setSpacing(0)
        section_form_container_layout.addLayout(section_form)
        section_form_container_layout.addStretch(1)

        section_editor_scroll_area = QScrollArea()
        section_editor_scroll_area.setWidgetResizable(True)
        section_editor_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        section_editor_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        section_editor_scroll_area.setWidget(section_form_container)
        section_editor_layout.addWidget(section_editor_scroll_area, 1)
        structure_views_tabs.addTab(section_editor_tab, "Section Editor")

        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        config_layout.setContentsMargins(8, 8, 8, 8)
        config_layout.setSpacing(8)

        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderLabels(["Config Node", "Value"])
        self.structure_tree.header().setStretchLastSection(True)
        config_layout.addWidget(self.structure_tree, 1)
        structure_views_tabs.addTab(config_tab, "Config Nodes")

        guardrails_tab = QWidget()
        guardrail_layout = QVBoxLayout(guardrails_tab)
        guardrail_layout.setContentsMargins(8, 8, 8, 8)
        guardrail_layout.setSpacing(8)
        self.guardrails_view = QPlainTextEdit()
        self.guardrails_view.setReadOnly(True)
        guardrail_layout.addWidget(self.guardrails_view, 1)
        structure_views_tabs.addTab(guardrails_tab, "Guardrails")

        validation_tab = QWidget()
        validation_layout = QVBoxLayout(validation_tab)
        validation_layout.setContentsMargins(8, 8, 8, 8)
        validation_layout.setSpacing(8)
        self.validation_summary_view = QPlainTextEdit()
        self.validation_summary_view.setReadOnly(True)
        validation_layout.addWidget(self.validation_summary_view, 1)
        structure_views_tabs.addTab(validation_tab, "Validation")

        structure_layout.addWidget(structure_views_tabs, 1)
        self.tabs.addTab(structure_tab, "Structure")

        summary_tab = QWidget()
        summary_layout = QFormLayout(summary_tab)
        self.field_count_value = QLabel("0")
        self.grid_shape_value = QLabel("0 x 0")
        self.dirty_value = QLabel("No")
        self.draft_dependency_value = QLabel("No pending draft dependencies")
        self.draft_dependency_value.setWordWrap(True)
        summary_layout.addRow("Header fields", self.field_count_value)
        summary_layout.addRow("Grid shape", self.grid_shape_value)
        summary_layout.addRow("Unsaved edits", self.dirty_value)
        summary_layout.addRow("Draft usage", self.draft_dependency_value)

        self.draft_dependency_details_view = QPlainTextEdit()
        self.draft_dependency_details_view.setReadOnly(True)
        self.draft_dependency_details_view.setMinimumHeight(110)
        summary_layout.addRow("Draft details", self.draft_dependency_details_view)

        self.snapshot_label_input = QLineEdit()
        self.snapshot_label_input.setPlaceholderText("Version label")
        summary_layout.addRow("Version label", self.snapshot_label_input)

        snapshot_actions = QHBoxLayout()
        snapshot_save_button = QPushButton("Save Version")
        snapshot_save_button.clicked.connect(self.controller.save_version_snapshot)
        snapshot_actions.addWidget(snapshot_save_button)
        snapshot_restore_button = QPushButton("Restore Latest")
        snapshot_restore_button.clicked.connect(self.controller.restore_latest_snapshot)
        snapshot_actions.addWidget(snapshot_restore_button)
        snapshot_actions.addStretch(1)
        summary_layout.addRow("Version actions", snapshot_actions)

        self.high_contrast_combo = QComboBox()
        self.high_contrast_combo.addItem("Off", False)
        self.high_contrast_combo.addItem("On", True)
        self.high_contrast_combo.currentIndexChanged.connect(self._on_high_contrast_changed)
        summary_layout.addRow("High Contrast", self.high_contrast_combo)

        self.font_profile_combo = QComboBox()
        self.font_profile_combo.addItem("Default", "default")
        self.font_profile_combo.addItem("Lexend (if installed)", "lexend")
        self.font_profile_combo.addItem("OpenDyslexic (if installed)", "dyslexia")
        self.font_profile_combo.currentIndexChanged.connect(self._on_font_profile_changed)
        summary_layout.addRow("Font Profile", self.font_profile_combo)

        self.tabs.addTab(summary_tab, "Summary")
        self.tabs.currentChanged.connect(self._handle_main_tab_changed)
        content_layout.addWidget(self.tabs, 1)

        content_layout.addStretch(1)
        scroll_area.setWidget(scroll_content)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self._apply_responsive_layout()
        self._configure_accessibility_semantics()
        self._configure_tab_order()
        self._configure_context_menus()
        self._configure_shortcuts()
        self._configure_table_navigation()
        self._apply_standard_density()

    def _apply_standard_density(self):
        if str(self.font_profile or "default").strip().lower() != "default":
            return
        compact_font = QFont(self._default_app_font)
        compact_font.setPixelSize(12)
        self.setFont(compact_font)

    def _build_standard_density_stylesheet(self):
        if str(self.font_profile or "default").strip().lower() != "default":
            return ""
        return (
            "QMainWindow#layoutManagerWindow, QMainWindow#layoutManagerWindow * { font-size: 12px; }"
            "QWidget#layoutManagerRoot, QWidget#layoutManagerRoot * { font-size: 12px; }"
            "QMainWindow#layoutManagerWindow QGroupBox, QWidget#layoutManagerRoot QGroupBox { font-size: 12px; font-weight: 600; }"
            "QMainWindow#layoutManagerWindow QGroupBox::title, QWidget#layoutManagerRoot QGroupBox::title { font-size: 12px; }"
            "QMainWindow#layoutManagerWindow QPushButton, QMainWindow#layoutManagerWindow QComboBox, QMainWindow#layoutManagerWindow QLineEdit, QMainWindow#layoutManagerWindow QPlainTextEdit, QMainWindow#layoutManagerWindow QTreeWidget, QMainWindow#layoutManagerWindow QTableWidget { font-size: 12px; }"
            "QMainWindow#layoutManagerWindow QHeaderView::section, QWidget#layoutManagerRoot QHeaderView::section { font-size: 12px; }"
            "QMainWindow#layoutManagerWindow QTabBar::tab, QWidget#layoutManagerRoot QTabBar::tab { font-size: 12px; }"
            "QMainWindow#layoutManagerWindow QPushButton, QWidget#layoutManagerRoot QPushButton { padding: 5px 10px; }"
        )

    def _apply_responsive_layout(self):
        geometry = self._available_screen_geometry()
        viewport_width = int(self.content_scroll_area.viewport().width() or 0)
        if geometry is not None:
            target_width = int(geometry.width() * 0.94)
        else:
            target_width = int(self.width() * 0.94)
        if viewport_width > 0:
            target_width = max(target_width, viewport_width)
        self.scroll_content.setMinimumWidth(max(1080, target_width))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _configure_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.controller.save_current)

        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._handle_escape)

        focus_form_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_form_shortcut.activated.connect(lambda: self.form_combo.setFocus())

        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self._focus_next_tab)

        previous_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        previous_tab_shortcut.activated.connect(self._focus_previous_tab)

    def _configure_table_navigation(self):
        self._navigable_tables = (
            self.header_fields_table,
            self.row_fields_table,
            self.mapping_table,
            self.header_preview_table,
        )
        for table_widget in self._navigable_tables:
            table_widget.installEventFilter(self)

    def _configure_authoring_table(self, table_widget):
        table_widget.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        table_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)

    def _build_excel_column_choices(self, max_column_number=260):
        choices = []
        max_count = max(int(max_column_number or 0), 0)
        for column_number in range(1, max_count + 1):
            value = column_number
            letters = []
            while value > 0:
                value, remainder = divmod(value - 1, 26)
                letters.append(chr(ord("A") + remainder))
            choices.append("".join(reversed(letters)))
        return choices

    def _dropdown_spec_for_cell(self, table_widget, column_index):
        if table_widget is self.header_fields_table:
            if column_index in (6, 9, 10):
                return {"options": ["false", "true"], "editable": False}
            if column_index == 8:
                return {"options": HEADER_ROLE_OPTIONS, "editable": True}
            if column_index == 11:
                return {"options": HEADER_WIDGET_OPTIONS, "editable": False}
            if column_index == 12:
                return {"options": STATE_OPTIONS, "editable": False}
            if column_index == 13:
                return {"options": OPTIONS_SOURCE_OPTIONS, "editable": True}
        if table_widget is self.row_fields_table:
            if column_index == 2:
                return {"options": ["entry", "display", "checkbutton", "combobox"], "editable": False}
            if column_index == 4:
                return {"options": ROW_ROLE_OPTIONS.get(self.current_row_section_name(), [""]), "editable": True}
            if column_index in (5, 6, 7, 8, 9, 10, 11):
                return {"options": ["false", "true"], "editable": False}
            if column_index == 13:
                return {"options": STICKY_OPTIONS, "editable": True}
            if column_index == 14:
                return {"options": STATE_OPTIONS, "editable": False}
            if column_index == 15:
                return {"options": OPTIONS_SOURCE_OPTIONS, "editable": True}
            if column_index == 16:
                return {"options": BOOTSTYLE_OPTIONS, "editable": True}
        if table_widget is self.mapping_table:
            if column_index == 1:
                return {"options": self._excel_column_choices, "editable": True}
            if column_index in (2, 3):
                return {"options": ["false", "true"], "editable": False}
            if column_index == 4:
                return {"options": ["value", "code_lookup", "stop_from_duration"], "editable": False}
            if column_index == 5:
                return {"options": ["value", "code_number", "duration_minutes", "bool_int", "minutes_label"], "editable": False}
        return None

    def _clear_table_cell_widgets(self, table_widget):
        for row_index in range(table_widget.rowCount()):
            for column_index in range(table_widget.columnCount()):
                if table_widget.cellWidget(row_index, column_index) is not None:
                    table_widget.removeCellWidget(row_index, column_index)

    def _set_combo_cell_value(self, table_widget, row_index, column_index, value, dropdown_spec):
        combo_widget = table_widget.cellWidget(row_index, column_index)
        if not isinstance(combo_widget, QComboBox):
            combo_widget = QComboBox(table_widget)
            table_widget.setCellWidget(row_index, column_index, combo_widget)
        options = [str(option) for option in dropdown_spec.get("options", [])]
        with QSignalBlocker(combo_widget):
            combo_widget.setEditable(bool(dropdown_spec.get("editable")))
            combo_widget.clear()
            combo_widget.addItems(options)
            text_value = str(value if value is not None else "")
            if combo_widget.isEditable():
                combo_widget.setEditText(text_value)
            else:
                normalized_value = text_value.strip().lower()
                match_index = combo_widget.findText(normalized_value, Qt.MatchFlag.MatchFixedString)
                if match_index < 0:
                    match_index = combo_widget.findText(text_value, Qt.MatchFlag.MatchFixedString)
                if match_index < 0:
                    match_index = 0
                combo_widget.setCurrentIndex(match_index)
        backing_item = table_widget.item(row_index, column_index)
        if backing_item is None:
            backing_item = QTableWidgetItem(text_value)
            table_widget.setItem(row_index, column_index, backing_item)
        else:
            backing_item.setText(text_value)

    def _set_plain_cell_value(self, table_widget, row_index, column_index, value):
        table_widget.removeCellWidget(row_index, column_index)
        item = QTableWidgetItem(str(value if value is not None else ""))
        table_widget.setItem(row_index, column_index, item)

    def eventFilter(self, watched, event):
        if watched in getattr(self, "_navigable_tables", ()) and event.type() == QEvent.Type.KeyPress:
            key_code = event.key()
            modifiers = event.modifiers()

            if self._table_is_editable(watched):
                if modifiers == Qt.KeyboardModifier.ControlModifier and key_code == Qt.Key.Key_C:
                    self._copy_table_selection(watched)
                    self.set_status("Copied selected table cells.")
                    return True

                if modifiers == Qt.KeyboardModifier.ControlModifier and key_code == Qt.Key.Key_X:
                    self._cut_table_selection(watched)
                    self.controller.mark_dirty()
                    self.set_status("Cut selected table cells.")
                    return True

                if modifiers == Qt.KeyboardModifier.ControlModifier and key_code == Qt.Key.Key_V:
                    self._paste_table_selection(watched)
                    self.controller.mark_dirty()
                    self.set_status("Pasted into selected table cells.")
                    return True

                if modifiers == Qt.KeyboardModifier.NoModifier and key_code in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                    self._delete_table_selection(watched)
                    self.controller.mark_dirty()
                    self.set_status("Cleared selected table cells.")
                    return True

                if modifiers == Qt.KeyboardModifier.ControlModifier and key_code in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._apply_table_changes(watched)
                    return True

            if modifiers == Qt.KeyboardModifier.ControlModifier and key_code in (
                Qt.Key.Key_Left,
                Qt.Key.Key_Right,
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
            ):
                if self._advance_table_cell(watched, key_code, step=5, wrap=False):
                    return True

            if modifiers == Qt.KeyboardModifier.AltModifier and key_code in (
                Qt.Key.Key_Left,
                Qt.Key.Key_Right,
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
            ):
                if self._advance_table_cell(watched, key_code, step=3, wrap=False):
                    return True

            if key_code in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and modifiers in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ShiftModifier,
            ):
                move_key = Qt.Key.Key_Down if modifiers == Qt.KeyboardModifier.NoModifier else Qt.Key.Key_Up
                if self._advance_table_cell(watched, move_key, step=1, wrap=True):
                    return True

        return super().eventFilter(watched, event)

    def _apply_table_changes(self, table_widget):
        if table_widget is self.header_fields_table:
            self.controller.apply_header_field_from_block()
            return
        if table_widget is self.row_fields_table:
            self.controller.apply_row_field_from_block()
            return
        if table_widget is self.mapping_table:
            self.controller.apply_mapping_from_import_export()
            return

    def _advance_table_cell(self, table_widget, key_code, step=1, wrap=False):
        row_count = int(table_widget.rowCount())
        column_count = int(table_widget.columnCount())
        if row_count <= 0 or column_count <= 0:
            return False

        row_index = int(table_widget.currentRow())
        column_index = int(table_widget.currentColumn())
        if row_index < 0:
            row_index = 0
        if column_index < 0:
            column_index = 0

        row_delta = 0
        column_delta = 0
        if key_code == Qt.Key.Key_Left:
            column_delta = -1
        elif key_code == Qt.Key.Key_Right:
            column_delta = 1
        elif key_code == Qt.Key.Key_Up:
            row_delta = -1
        elif key_code == Qt.Key.Key_Down:
            row_delta = 1
        else:
            return False

        target_row = row_index
        target_column = column_index
        for _ in range(max(int(step), 1)):
            candidate_row = target_row + row_delta
            candidate_column = target_column + column_delta

            if wrap:
                candidate_row %= row_count
                candidate_column %= column_count
            else:
                candidate_row = max(0, min(candidate_row, row_count - 1))
                candidate_column = max(0, min(candidate_column, column_count - 1))

            if candidate_row == target_row and candidate_column == target_column:
                break
            target_row = candidate_row
            target_column = candidate_column

        if target_row == row_index and target_column == column_index:
            return False

        table_widget.setCurrentCell(target_row, target_column)
        current_item = table_widget.currentItem()
        if current_item is not None:
            table_widget.scrollToItem(current_item, QTableWidget.ScrollHint.PositionAtCenter)
        self.set_status(f"Moved to table cell ({target_row + 1}, {target_column + 1}).")
        return True

    def _handle_escape(self):
        focused_widget = QApplication.focusWidget()
        if focused_widget is not None:
            focused_widget.clearFocus()
        self.set_status("Canceled current inline interaction.")

    def _focus_next_tab(self):
        tab_count = self.tabs.count()
        if tab_count <= 1:
            return
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % tab_count)

    def _focus_previous_tab(self):
        tab_count = self.tabs.count()
        if tab_count <= 1:
            return
        self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % tab_count)

    def _on_preview_cell_selected(self, row_index, column_index):
        fields = self._preview_cell_fields.get((row_index, column_index), [])
        if not fields:
            self.preview_metadata_view.setPlainText(f"Cell ({row_index}, {column_index}) has no mapped fields.")
            self.set_status(f"Preview cell ({row_index}, {column_index}) has no mapped fields.")
            return
        summary = ", ".join(
            str(field.get("label") or field.get("id") or "Field")
            for field in fields[:3]
        )
        overflow = len(fields) - 3
        if overflow > 0:
            summary = f"{summary} (+{overflow} more)"

        metadata_lines = [f"Cell: ({row_index}, {column_index})", f"Field count: {len(fields)}", ""]
        for field in fields:
            field_id = str(field.get("id") or "")
            field_label = str(field.get("label") or field_id or "Field")
            field_cell = str(field.get("cell") or "")
            field_role = str(field.get("role") or "")
            metadata_lines.append(f"- {field_label} [{field_id}]")
            if field_cell:
                metadata_lines.append(f"  cell: {field_cell}")
            if field_role:
                metadata_lines.append(f"  role: {field_role}")
        self.preview_metadata_view.setPlainText("\n".join(metadata_lines))
        self.set_status(f"Preview cell ({row_index}, {column_index}) fields: {summary}")

    def _configure_context_menus(self):
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._show_editor_context_menu)

        for table_widget in (
            self.header_fields_table,
            self.row_fields_table,
            self.mapping_table,
            self.header_preview_table,
        ):
            table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table_widget.customContextMenuRequested.connect(
                lambda position, target=table_widget: self._show_table_context_menu(target, position)
            )

        for tree_widget in (self.structure_tree, self.row_sections_tree):
            tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tree_widget.customContextMenuRequested.connect(
                lambda position, target=tree_widget: self._show_tree_context_menu(target, position)
            )

    def _configure_accessibility_semantics(self):
        self.form_combo.setAccessibleName("Stored forms selector")
        self.form_combo.setAccessibleDescription("Select a stored layout form to activate, duplicate, rename, or delete.")
        self.editor.setAccessibleName("Layout JSON editor")
        self.editor.setAccessibleDescription("Edit layout JSON directly. Supports standard text editing actions.")
        self.header_fields_table.setAccessibleName("Header fields table")
        self.row_fields_table.setAccessibleName("Row fields table")
        self.mapping_table.setAccessibleName("Import export mapping table")
        self.structure_tree.setAccessibleName("Layout structure tree")
        self.row_sections_tree.setAccessibleName("Row sections preview tree")
        self.high_contrast_combo.setAccessibleName("High contrast mode")
        self.high_contrast_combo.setAccessibleDescription("Toggle high contrast rendering for improved visibility.")
        self.font_profile_combo.setAccessibleName("Accessibility font profile")
        self.font_profile_combo.setAccessibleDescription("Select readable font overrides for accessibility support.")
        self.snapshot_label_input.setAccessibleName("Version snapshot label")

    def _configure_tab_order(self):
        self.setTabOrder(self.form_combo, self.editor)
        self.setTabOrder(self.editor, self.header_fields_table)
        self.setTabOrder(self.header_fields_table, self.row_section_combo)
        self.setTabOrder(self.row_section_combo, self.row_fields_table)
        self.setTabOrder(self.row_fields_table, self.mapping_section_combo)
        self.setTabOrder(self.mapping_section_combo, self.mapping_table)
        self.setTabOrder(self.mapping_table, self.section_combo)
        self.setTabOrder(self.section_combo, self.structure_tree)
        self.setTabOrder(self.structure_tree, self.snapshot_label_input)
        self.setTabOrder(self.snapshot_label_input, self.high_contrast_combo)
        self.setTabOrder(self.high_contrast_combo, self.font_profile_combo)

    def _on_high_contrast_changed(self, *_args):
        self.high_contrast_enabled = bool(self.high_contrast_combo.currentData())
        self._apply_theme()
        self.set_status(
            "High contrast mode enabled." if self.high_contrast_enabled else "High contrast mode disabled."
        )

    def _on_font_profile_changed(self, *_args):
        self.font_profile = str(self.font_profile_combo.currentData() or "default")
        self._apply_theme()
        self.set_status(f"Font profile set to {self.font_profile}.")

    def _resolve_font_family(self, preferred_families):
        families = set(QFontDatabase().families())
        for family_name in preferred_families:
            if family_name in families:
                return family_name
        return ""

    def _apply_font_profile(self):
        selected_profile = str(self.font_profile or "default").strip().lower()
        if selected_profile == "default":
            self.setFont(QFont(self._default_app_font))
            return

        if selected_profile == "lexend":
            family_name = self._resolve_font_family(["Lexend", "Segoe UI", "Arial"])
        else:
            family_name = self._resolve_font_family(["OpenDyslexic", "OpenDyslexicAlta", "Lexend", "Segoe UI", "Arial"])

        selected_font = QFont(self._default_app_font)
        if family_name:
            selected_font.setFamily(family_name)
        selected_font.setPointSize(max(int(selected_font.pointSize() or 10), 11))
        self.setFont(selected_font)

    def _build_accessibility_stylesheet(self):
        if not self.high_contrast_enabled:
            return ""
        return (
            "QWidget { background: #000000; color: #ffffff; }"
            "QLineEdit, QPlainTextEdit, QTableWidget, QTreeWidget, QComboBox {"
            " background: #000000; color: #ffffff; border: 2px solid #ffffff; }"
            "QPushButton { background: #000000; color: #ffffff; border: 2px solid #00ffff; }"
            "QPushButton:focus, QLineEdit:focus, QPlainTextEdit:focus, QTableWidget:focus, QTreeWidget:focus, QComboBox:focus {"
            " border: 3px dashed #ffff00; }"
            "QLabel#mutedLabel { color: #ffffff; font-weight: 600; }"
        )

    def _apply_theme(self):
        tokens = self.theme_tokens
        base_stylesheet = get_qt_stylesheet(theme_tokens=tokens)
        accessibility_stylesheet = self._build_accessibility_stylesheet()
        density_stylesheet = self._build_standard_density_stylesheet()
        stylesheet_parts = [base_stylesheet, accessibility_stylesheet, density_stylesheet]
        self.setStyleSheet("\n".join(part for part in stylesheet_parts if part))
        application = QApplication.instance()
        if application is not None:
            application.setPalette(get_qt_palette(theme_tokens=tokens))
        self._apply_font_profile()
        self._apply_standard_density()

    def set_theme_tokens(self, theme_tokens):
        self.theme_tokens = dict(theme_tokens or {})
        self._apply_theme()

    def _handle_editor_changed(self):
        if self._updating_editor:
            return
        self.controller.mark_dirty()

    def _handle_main_tab_changed(self, *_args):
        current_widget = self.tabs.currentWidget()
        if current_widget is not self.json_editor_tab:
            return
        self.finalize_block_table_edits()
        self.controller.sync_block_view_to_editor()

    def finalize_block_table_edits(self):
        for table_widget in (self.header_fields_table, self.row_fields_table, self.mapping_table):
            focus_widget = table_widget.focusWidget()
            if focus_widget is not None:
                focus_widget.clearFocus()
            table_widget.clearFocus()
        QApplication.processEvents()

    def set_editor_text(self, text):
        self._updating_editor = True
        self.editor.setPlainText(text)
        self._updating_editor = False

    def editor_text(self):
        return self.editor.toPlainText()

    def set_header_field_presets(self, presets):
        blocker = QSignalBlocker(self.header_field_preset_combo)
        self.header_field_preset_combo.clear()
        self.header_field_preset_combo.addItem("Select preset field...", "")
        for preset in presets or []:
            preset_id = str((preset or {}).get("id") or "").strip()
            if not preset_id:
                continue
            preset_label = str((preset or {}).get("label") or preset_id).strip() or preset_id
            preset_source = str((preset or {}).get("source") or "default").strip().lower()
            source_label = "Custom" if preset_source == "custom" else "Built-in"
            self.header_field_preset_combo.addItem(f"{preset_label} [{preset_id}] ({source_label})", preset_id)
        del blocker

    def current_header_field_preset_id(self):
        return str(self.header_field_preset_combo.currentData() or "").strip()

    def set_row_field_presets(self, presets):
        blocker = QSignalBlocker(self.row_field_preset_combo)
        self.row_field_preset_combo.clear()
        self.row_field_preset_combo.addItem("Select preset column...", "")
        for preset in presets or []:
            preset_id = str((preset or {}).get("id") or "").strip()
            if not preset_id:
                continue
            preset_label = str((preset or {}).get("label") or preset_id).strip() or preset_id
            preset_source = str((preset or {}).get("source") or "default").strip().lower()
            source_label = "Custom" if preset_source == "custom" else "Built-in"
            self.row_field_preset_combo.addItem(f"{preset_label} [{preset_id}] ({source_label})", preset_id)
        del blocker

    def current_row_field_preset_id(self):
        return str(self.row_field_preset_combo.currentData() or "").strip()

    def set_available_mapping_columns(self, column_names):
        blocker = QSignalBlocker(self.mapping_column_selector)
        self.mapping_column_selector.clear()
        for column_name in column_names or []:
            self.mapping_column_selector.addItem(str(column_name or ""))
        if self.mapping_column_selector.findText("") < 0:
            self.mapping_column_selector.insertItem(0, "")
        self.mapping_column_selector.setCurrentIndex(0)
        del blocker

    def current_mapping_column_choice(self):
        return str(self.mapping_column_selector.currentText() or "").strip()

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
            self.reason_label.setText(f"ERROR: {message}")
        elif message:
            self.reason_label.setText(f"INFO: {message}")

    def set_busy_state(self, active, message=""):
        if active:
            if message:
                self.status_bar.showMessage(str(message), 0)
            if not self._busy_cursor_active:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                self._busy_cursor_active = True
            return
        if self._busy_cursor_active:
            QApplication.restoreOverrideCursor()
            self._busy_cursor_active = False

    def set_import_export_progress(self, active, message=""):
        if active:
            self.import_export_status_label.setText(str(message or "Import/Export operation in progress..."))
            self.import_export_status_label.setVisible(True)
            self.set_busy_state(True, str(message or "Import/Export operation in progress..."))
            return
        self.import_export_status_label.setVisible(False)
        self.import_export_status_label.setText("")
        self.set_busy_state(False)

    def _table_is_editable(self, table_widget):
        return table_widget.editTriggers() != QTableWidget.EditTrigger.NoEditTriggers

    def _show_editor_context_menu(self, position):
        menu = self.editor.createStandardContextMenu()
        menu.exec(self.editor.mapToGlobal(position))

    def _show_table_context_menu(self, table_widget, position):
        menu = QMenu(table_widget)
        copy_action = menu.addAction("Copy")
        cut_action = menu.addAction("Cut")
        paste_action = menu.addAction("Paste")
        delete_action = menu.addAction("Delete")

        has_selection = bool(table_widget.selectedItems())
        is_editable = self._table_is_editable(table_widget)
        clipboard_text = QApplication.clipboard().text()

        copy_action.setEnabled(has_selection)
        cut_action.setEnabled(has_selection and is_editable)
        delete_action.setEnabled(has_selection and is_editable)
        paste_action.setEnabled(is_editable and bool(str(clipboard_text or "").strip()))

        selected_action = menu.exec(table_widget.viewport().mapToGlobal(position))
        if selected_action is copy_action:
            self._copy_table_selection(table_widget)
        elif selected_action is cut_action:
            self._cut_table_selection(table_widget)
        elif selected_action is paste_action:
            self._paste_table_selection(table_widget)
        elif selected_action is delete_action:
            self._delete_table_selection(table_widget)

    def _show_tree_context_menu(self, tree_widget, position):
        menu = QMenu(tree_widget)
        copy_action = menu.addAction("Copy")
        current_item = tree_widget.currentItem()
        copy_action.setEnabled(current_item is not None)
        selected_action = menu.exec(tree_widget.viewport().mapToGlobal(position))
        if selected_action is copy_action and current_item is not None:
            text_value = "\t".join(
                str(current_item.text(column_index) or "") for column_index in range(tree_widget.columnCount())
            )
            QApplication.clipboard().setText(text_value)

    def _copy_table_selection(self, table_widget):
        ranges = table_widget.selectedRanges()
        if not ranges:
            return
        rows = []
        for selected_range in ranges:
            for row_index in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                columns = []
                for column_index in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                    columns.append(self._cell_text(table_widget, row_index, column_index))
                rows.append("\t".join(columns))
        QApplication.clipboard().setText("\n".join(rows))

    def _cut_table_selection(self, table_widget):
        self._copy_table_selection(table_widget)
        self._delete_table_selection(table_widget)

    def _delete_table_selection(self, table_widget):
        for item in table_widget.selectedItems():
            row_index = item.row()
            column_index = item.column()
            dropdown_spec = self._dropdown_spec_for_cell(table_widget, column_index)
            if dropdown_spec is not None:
                default_value = ""
                if not dropdown_spec.get("editable"):
                    default_value = str((dropdown_spec.get("options") or [""])[0])
                self._set_table_text(table_widget, row_index, column_index, default_value)
                continue
            item.setText("")

    def _paste_table_selection(self, table_widget):
        clipboard_text = str(QApplication.clipboard().text() or "")
        if not clipboard_text:
            return
        row_index = table_widget.currentRow()
        column_index = table_widget.currentColumn()
        if row_index < 0:
            row_index = 0
        if column_index < 0:
            column_index = 0

        lines = clipboard_text.splitlines()
        for row_offset, line in enumerate(lines):
            target_row = row_index + row_offset
            if target_row >= table_widget.rowCount():
                break
            values = line.split("\t")
            for column_offset, value in enumerate(values):
                target_column = column_index + column_offset
                if target_column >= table_widget.columnCount():
                    break
                self._set_table_text(table_widget, target_row, target_column, str(value or ""))

    def set_dirty(self, dirty):
        self.dirty_value.setText("Yes" if dirty else "No")
        title_suffix = " *" if dirty else ""
        self.setWindowTitle(f"Layout Manager Qt{title_suffix}")

    def render_preview_grid(self, preview_grid):
        preview = dict(preview_grid or {})
        row_count = int(preview.get("max_row", 0)) + 1
        column_count = int(preview.get("max_col", 0)) + 1
        self._preview_cell_fields = {}
        self.header_preview_table.setUpdatesEnabled(False)
        self.row_sections_tree.setUpdatesEnabled(False)
        try:
            self.header_preview_table.clear()
            self.header_preview_table.setRowCount(max(row_count, 1))
            self.header_preview_table.setColumnCount(max(column_count, 1))
            self.header_preview_table.setHorizontalHeaderLabels([f"Col {index}" for index in range(max(column_count, 1))])

            for cell in preview.get("cells", []):
                row = int(cell.get("row", 0))
                col = int(cell.get("col", 0))
                fields_here = cell.get("fields") or []
                self._preview_cell_fields[(row, col)] = list(fields_here)
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
                section_item.setExpanded(False)
        finally:
            self.header_preview_table.setUpdatesEnabled(True)
            self.row_sections_tree.setUpdatesEnabled(True)

        self.field_count_value.setText(str(preview.get("field_count", 0)))
        self.grid_shape_value.setText(f"{row_count} x {column_count}")

        total_cells = max(row_count, 1) * max(column_count, 1)
        mapped_cells = len([key for key, values in self._preview_cell_fields.items() if values])
        self.preview_metadata_view.setPlainText(
            "\n".join(
                [
                    "Preview metadata overview",
                    f"Grid size: {row_count} x {column_count}",
                    f"Total cells: {total_cells}",
                    f"Cells with mapped fields: {mapped_cells}",
                    "",
                    "Select a preview cell to inspect field-level metadata.",
                ]
            )
        )

    def render_validation_summary(self, summary):
        payload = dict(summary or {})
        stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
        errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
        warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []

        lines = [
            f"Status: {'OK' if payload.get('ok') else 'Issues found'}",
            f"Total fields: {stats.get('total_fields', 0)}",
            f"Header fields: {stats.get('header_fields', 0)}",
            f"Production row fields: {stats.get('production_row_fields', 0)}",
            f"Downtime row fields: {stats.get('downtime_row_fields', 0)}",
            "",
            "Errors:",
        ]
        if errors:
            lines.extend([f"- {message}" for message in errors])
        else:
            lines.append("- None")

        lines.append("")
        lines.append("Warnings:")
        if warnings:
            lines.extend([f"- {message}" for message in warnings])
        else:
            lines.append("- None")

        self.validation_summary_view.setPlainText("\n".join(lines))

    def render_form_dependency_audit(self, audit):
        payload = dict(audit or {})
        dependent_drafts = payload.get("dependent_drafts") if isinstance(payload.get("dependent_drafts"), list) else []
        summary = str(payload.get("summary") or "No pending Form Loader drafts depend on this form.")
        self.draft_dependency_value.setText(summary)

        if dependent_drafts:
            detail_lines = []
            for draft in dependent_drafts:
                detail_lines.append(str(draft.get("filename") or "Unknown draft"))
                detail_lines.append(f"Saved: {draft.get('saved_at') or '--'}")
                detail_lines.append(f"Path: {draft.get('path') or '--'}")
                detail_lines.append("")
            self.draft_dependency_details_view.setPlainText("\n".join(detail_lines).rstrip())
        else:
            self.draft_dependency_details_view.setPlainText("No pending Form Loader drafts currently reference the selected form.")

    def _set_table_text(self, table_widget, row_index, column_index, value):
        dropdown_spec = self._dropdown_spec_for_cell(table_widget, column_index)
        if dropdown_spec is not None:
            self._set_combo_cell_value(table_widget, row_index, column_index, value, dropdown_spec)
            return
        self._set_plain_cell_value(table_widget, row_index, column_index, value)

    def _next_table_render_token(self, table_widget):
        table_key = id(table_widget)
        token_value = int(self._table_render_tokens.get(table_key, 0)) + 1
        self._table_render_tokens[table_key] = token_value
        return table_key, token_value

    def _render_table_rows_chunked(self, table_widget, row_count, row_renderer, chunk_size=64):
        table_key, token_value = self._next_table_render_token(table_widget)
        total_rows = max(int(row_count or 0), 0)
        table_widget.setUpdatesEnabled(False)
        self._clear_table_cell_widgets(table_widget)
        table_widget.clearContents()
        table_widget.setRowCount(total_rows)
        if total_rows == 0:
            table_widget.setUpdatesEnabled(True)
            return

        def _render_chunk(start_index):
            if self._table_render_tokens.get(table_key) != token_value:
                return
            end_index = min(start_index + max(int(chunk_size), 1), total_rows)
            for row_index in range(start_index, end_index):
                row_renderer(row_index)
            if end_index < total_rows:
                QTimer.singleShot(0, lambda: _render_chunk(end_index))
                return
            if self._table_render_tokens.get(table_key) == token_value:
                table_widget.setUpdatesEnabled(True)
                table_widget.viewport().update()

        if total_rows <= max(int(chunk_size), 1):
            _render_chunk(0)
            return
        QTimer.singleShot(0, lambda: _render_chunk(0))

    def _cache_key(self, payload):
        try:
            return json.dumps(payload, sort_keys=True, default=str)
        except Exception:
            return str(payload)

    def _cell_text(self, table_widget, row_index, column_index):
        cell_widget = table_widget.cellWidget(row_index, column_index)
        if isinstance(cell_widget, QComboBox):
            return str(cell_widget.currentText()).strip()
        item = table_widget.item(row_index, column_index)
        return str(item.text()).strip() if item is not None else ""

    def _selected_row_index(self, table_widget):
        selected_items = table_widget.selectedItems()
        if not selected_items:
            current_row = int(table_widget.currentRow())
            return current_row if current_row >= 0 else -1
        return selected_items[0].row()

    def selected_header_field_row_index(self):
        return self._selected_row_index(self.header_fields_table)

    def selected_row_field_row_index(self):
        return self._selected_row_index(self.row_fields_table)

    def selected_mapping_field_id(self):
        row_index = self._selected_row_index(self.mapping_table)
        if row_index < 0:
            return ""
        return self._cell_text(self.mapping_table, row_index, 0)

    def _mapping_name_to_row_section(self, mapping_name):
        normalized_mapping_name = str(mapping_name or "").strip()
        if normalized_mapping_name in self._mapping_to_row_section:
            return self._mapping_to_row_section[normalized_mapping_name]
        if normalized_mapping_name.endswith("_mapping"):
            return f"{normalized_mapping_name[:-8]}_row_fields"
        return "production_row_fields"

    def _build_repeating_section_bindings(self, config):
        sections = config.get("sections") if isinstance(config, dict) and isinstance(config.get("sections"), list) else []
        bindings = []
        seen_fields_keys = set()
        seen_mapping_keys = set()

        for section in sections:
            if not isinstance(section, dict):
                continue
            if str(section.get("section_type") or "single").strip().lower() != "repeating":
                continue
            fields_key = str(section.get("fields_key") or "").strip()
            mapping_key = str(section.get("mapping_key") or "").strip()
            if not fields_key or not mapping_key:
                continue
            if fields_key in seen_fields_keys or mapping_key in seen_mapping_keys:
                continue
            section_name = str(section.get("name") or section.get("id") or fields_key).strip() or fields_key
            bindings.append(
                {
                    "section_name": section_name,
                    "fields_key": fields_key,
                    "mapping_key": mapping_key,
                }
            )
            seen_fields_keys.add(fields_key)
            seen_mapping_keys.add(mapping_key)

        if bindings:
            return bindings

        return [
            {
                "section_name": "Production",
                "fields_key": "production_row_fields",
                "mapping_key": "production_mapping",
            },
            {
                "section_name": "Downtime",
                "fields_key": "downtime_row_fields",
                "mapping_key": "downtime_mapping",
            },
        ]

    def _refresh_repeating_section_selectors(self, config):
        current_row_section = str(self.row_section_combo.currentData() or "").strip()
        current_mapping_name = str(self.mapping_section_combo.currentData() or "").strip()
        bindings = self._build_repeating_section_bindings(config)

        self._row_section_to_mapping = {
            binding["fields_key"]: binding["mapping_key"]
            for binding in bindings
        }
        self._mapping_to_row_section = {
            binding["mapping_key"]: binding["fields_key"]
            for binding in bindings
        }

        row_blocker = QSignalBlocker(self.row_section_combo)
        mapping_blocker = QSignalBlocker(self.mapping_section_combo)
        self.row_section_combo.clear()
        self.mapping_section_combo.clear()
        for binding in bindings:
            section_name = str(binding.get("section_name") or binding.get("fields_key") or "Section")
            fields_key = str(binding.get("fields_key") or "")
            mapping_key = str(binding.get("mapping_key") or "")
            self.row_section_combo.addItem(f"{section_name} [{fields_key}]", fields_key)
            self.mapping_section_combo.addItem(f"{section_name} [{mapping_key}]", mapping_key)

        row_index = self.row_section_combo.findData(current_row_section)
        if row_index < 0:
            row_index = 0 if self.row_section_combo.count() > 0 else -1
        if row_index >= 0:
            self.row_section_combo.setCurrentIndex(row_index)

        mapping_index = self.mapping_section_combo.findData(current_mapping_name)
        if mapping_index < 0 and row_index >= 0:
            selected_row_section = str(self.row_section_combo.currentData() or "").strip()
            preferred_mapping = self._row_section_to_mapping.get(selected_row_section, "")
            mapping_index = self.mapping_section_combo.findData(preferred_mapping)
        if mapping_index < 0:
            mapping_index = 0 if self.mapping_section_combo.count() > 0 else -1
        if mapping_index >= 0:
            self.mapping_section_combo.setCurrentIndex(mapping_index)

        del row_blocker
        del mapping_blocker

    def current_row_section_name(self):
        current_value = str(self.row_section_combo.currentData() or "").strip()
        if current_value:
            return current_value
        if self.row_section_combo.count() > 0:
            return str(self.row_section_combo.itemData(0) or "production_row_fields")
        return "production_row_fields"

    def current_mapping_name(self):
        current_value = str(self.mapping_section_combo.currentData() or "").strip()
        if current_value:
            return current_value
        if self.mapping_section_combo.count() > 0:
            return str(self.mapping_section_combo.itemData(0) or "production_mapping")
        return "production_mapping"

    def render_block_authoring(self, config):
        self._refresh_repeating_section_selectors(config)
        header_fields = list(config.get("header_fields") or [])
        header_cache_key = self._cache_key(header_fields)
        if header_cache_key != self._header_fields_cache_key:
            self._header_fields_cache_key = header_cache_key

            def _render_header_row(row_index):
                field = header_fields[row_index]
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
                self._set_table_text(self.header_fields_table, row_index, 11, field.get("widget", "entry"))
                self._set_table_text(self.header_fields_table, row_index, 12, field.get("state", ""))
                self._set_table_text(self.header_fields_table, row_index, 13, field.get("options_source", ""))
                values = field.get("values") if isinstance(field.get("values"), list) else []
                self._set_table_text(
                    self.header_fields_table,
                    row_index,
                    14,
                    ", ".join(str(item).strip() for item in values if str(item).strip()),
                )
                id_item = self.header_fields_table.item(row_index, 0)
                if id_item is not None:
                    id_item.setData(Qt.ItemDataRole.UserRole, field.get("id", ""))

            self._render_table_rows_chunked(
                self.header_fields_table,
                len(header_fields),
                _render_header_row,
                chunk_size=48,
            )

        self.render_row_fields_authoring(config)

    def render_row_fields_authoring(self, config):
        section_name = self.current_row_section_name()
        row_fields = list(config.get(section_name) or [])
        row_cache_key = self._cache_key({"section": section_name, "fields": row_fields})
        if row_cache_key != self._row_fields_cache_key:
            self._row_fields_cache_key = row_cache_key

            def _render_row_field(row_index):
                field = row_fields[row_index]
                self._set_table_text(self.row_fields_table, row_index, 0, field.get("id", ""))
                self._set_table_text(self.row_fields_table, row_index, 1, field.get("label", ""))
                self._set_table_text(self.row_fields_table, row_index, 2, field.get("widget", "entry"))
                self._set_table_text(self.row_fields_table, row_index, 3, field.get("width", ""))
                self._set_table_text(self.row_fields_table, row_index, 4, field.get("role", ""))
                self._set_table_text(self.row_fields_table, row_index, 5, bool(field.get("readonly", False)))
                self._set_table_text(self.row_fields_table, row_index, 6, bool(field.get("derived", False)))
                self._set_table_text(self.row_fields_table, row_index, 7, bool(field.get("math_trigger", False)))
                self._set_table_text(self.row_fields_table, row_index, 8, bool(field.get("open_row_trigger", False)))
                self._set_table_text(self.row_fields_table, row_index, 9, bool(field.get("user_input", False)))
                self._set_table_text(self.row_fields_table, row_index, 10, bool(field.get("expand", False)))
                self._set_table_text(self.row_fields_table, row_index, 11, bool(field.get("bold", False)))
                self._set_table_text(self.row_fields_table, row_index, 12, field.get("default", ""))
                self._set_table_text(self.row_fields_table, row_index, 13, field.get("sticky", ""))
                self._set_table_text(self.row_fields_table, row_index, 14, field.get("state", ""))
                self._set_table_text(self.row_fields_table, row_index, 15, field.get("options_source", ""))
                self._set_table_text(self.row_fields_table, row_index, 16, field.get("bootstyle", ""))
                values = field.get("values") if isinstance(field.get("values"), list) else []
                self._set_table_text(self.row_fields_table, row_index, 17, ", ".join(str(item).strip() for item in values if str(item).strip()))
                id_item = self.row_fields_table.item(row_index, 0)
                if id_item is not None:
                    id_item.setData(Qt.ItemDataRole.UserRole, field.get("id", ""))

            self._render_table_rows_chunked(
                self.row_fields_table,
                len(row_fields),
                _render_row_field,
                chunk_size=36,
            )

    def render_import_export_authoring(self, config, metadata=None):
        self._refresh_repeating_section_selectors(config)
        self.template_path_input.setText(str(config.get("template_path") or ""))
        self.render_import_export_metadata(metadata)
        self.render_mapping_authoring(config)

    def render_import_export_metadata(self, metadata):
        payload = dict(metadata or {})
        production = payload.get("production") if isinstance(payload.get("production"), dict) else {}
        downtime = payload.get("downtime") if isinstance(payload.get("downtime"), dict) else {}
        workbook = payload.get("workbook") if isinstance(payload.get("workbook"), dict) else {}
        template_path = str(payload.get("template_path") or "").strip() or "(not set)"

        lines = [
            f"Template: {template_path}",
            (
                "Production: "
                f"fields={int(production.get('field_count', 0))}, "
                f"mapped={int(production.get('mapped_columns', 0))}, "
                f"start_row={int(production.get('start_row', 1))}, "
                f"max_rows={int(production.get('max_rows', 25))}"
            ),
            (
                "Downtime: "
                f"fields={int(downtime.get('field_count', 0))}, "
                f"mapped={int(downtime.get('mapped_columns', 0))}, "
                f"start_row={int(downtime.get('start_row', 1))}, "
                f"max_rows={int(downtime.get('max_rows', 25))}"
            ),
        ]
        workbook_mode = str(workbook.get("mode") or "none")
        if workbook.get("exists"):
            lines.append(
                "Workbook: "
                f"mode={workbook_mode}, "
                f"sheets={int(workbook.get('sheet_count', 0))}, "
                f"sampled_rows={int(workbook.get('sampled_rows', 0))}, "
                f"non_empty_rows={int(workbook.get('non_empty_rows', 0))}"
            )
            sheet_names = workbook.get("sheet_names") if isinstance(workbook.get("sheet_names"), list) else []
            if sheet_names:
                lines.append(f"Workbook sheets: {', '.join(str(sheet_name) for sheet_name in sheet_names[:5])}")
        elif template_path != "(not set)":
            lines.append(f"Workbook: unavailable ({workbook_mode})")
        self.import_export_metadata_label.setText("\n".join(lines))

    def render_mapping_authoring(self, config):
        mapping_name = self.current_mapping_name()
        mapping = config.get(mapping_name) if isinstance(config.get(mapping_name), dict) else {}
        self.mapping_start_row_input.setText(str(mapping.get("start_row", 1)))
        self.mapping_max_rows_input.setText(str(mapping.get("max_rows", 25)))
        row_section_name = self._mapping_name_to_row_section(mapping_name)
        row_fields = list(config.get(row_section_name) or [])
        columns = mapping.get("columns") if isinstance(mapping.get("columns"), dict) else {}

        mapping_cache_key = self._cache_key(
            {
                "mapping_name": mapping_name,
                "start_row": mapping.get("start_row", 1),
                "max_rows": mapping.get("max_rows", 25),
                "row_fields": row_fields,
                "columns": columns,
            }
        )
        if mapping_cache_key != self._mapping_cache_key:
            self._mapping_cache_key = mapping_cache_key

            def _render_mapping_row(row_index):
                field = row_fields[row_index]
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

            self._render_table_rows_chunked(
                self.mapping_table,
                len(row_fields),
                _render_mapping_row,
                chunk_size=48,
            )

    def header_field_table_values(self):
        values = []
        for row_index in range(self.header_fields_table.rowCount()):
            item = self.header_fields_table.item(row_index, 0)
            values.append(
                {
                    "_original_id": str(item.data(Qt.ItemDataRole.UserRole) or "").strip() if item is not None else "",
                    "id": self._cell_text(self.header_fields_table, row_index, 0),
                    "label": self._cell_text(self.header_fields_table, row_index, 1),
                    "row": self._cell_text(self.header_fields_table, row_index, 2),
                    "col": self._cell_text(self.header_fields_table, row_index, 3),
                    "cell": self._cell_text(self.header_fields_table, row_index, 4),
                    "width": self._cell_text(self.header_fields_table, row_index, 5),
                    "readonly": self._cell_text(self.header_fields_table, row_index, 6),
                    "default": self._cell_text(self.header_fields_table, row_index, 7),
                    "role": self._cell_text(self.header_fields_table, row_index, 8),
                    "import_enabled": self._cell_text(self.header_fields_table, row_index, 9),
                    "export_enabled": self._cell_text(self.header_fields_table, row_index, 10),
                    "widget": self._cell_text(self.header_fields_table, row_index, 11),
                    "state": self._cell_text(self.header_fields_table, row_index, 12),
                    "options_source": self._cell_text(self.header_fields_table, row_index, 13),
                    "values": self._cell_text(self.header_fields_table, row_index, 14),
                }
            )
        return values

    def row_field_table_values(self):
        values = []
        for row_index in range(self.row_fields_table.rowCount()):
            item = self.row_fields_table.item(row_index, 0)
            values.append(
                {
                    "_original_id": str(item.data(Qt.ItemDataRole.UserRole) or "").strip() if item is not None else "",
                    "id": self._cell_text(self.row_fields_table, row_index, 0),
                    "label": self._cell_text(self.row_fields_table, row_index, 1),
                    "widget": self._cell_text(self.row_fields_table, row_index, 2),
                    "width": self._cell_text(self.row_fields_table, row_index, 3),
                    "role": self._cell_text(self.row_fields_table, row_index, 4),
                    "readonly": self._cell_text(self.row_fields_table, row_index, 5),
                    "derived": self._cell_text(self.row_fields_table, row_index, 6),
                    "math_trigger": self._cell_text(self.row_fields_table, row_index, 7),
                    "open_row_trigger": self._cell_text(self.row_fields_table, row_index, 8),
                    "user_input": self._cell_text(self.row_fields_table, row_index, 9),
                    "expand": self._cell_text(self.row_fields_table, row_index, 10),
                    "bold": self._cell_text(self.row_fields_table, row_index, 11),
                    "default": self._cell_text(self.row_fields_table, row_index, 12),
                    "sticky": self._cell_text(self.row_fields_table, row_index, 13),
                    "state": self._cell_text(self.row_fields_table, row_index, 14),
                    "options_source": self._cell_text(self.row_fields_table, row_index, 15),
                    "bootstyle": self._cell_text(self.row_fields_table, row_index, 16),
                    "values": self._cell_text(self.row_fields_table, row_index, 17),
                }
            )
        return values

    def selected_header_field_id(self):
        row_index = self._selected_row_index(self.header_fields_table)
        if row_index < 0:
            return ""
        item = self.header_fields_table.item(row_index, 0)
        if item is None:
            return ""
        original_id = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        return original_id or self._cell_text(self.header_fields_table, row_index, 0)

    def selected_header_field_values(self):
        row_index = self._selected_row_index(self.header_fields_table)
        if row_index < 0:
            return None
        return {
            "id": self._cell_text(self.header_fields_table, row_index, 0),
            "label": self._cell_text(self.header_fields_table, row_index, 1),
            "row": self._cell_text(self.header_fields_table, row_index, 2),
            "col": self._cell_text(self.header_fields_table, row_index, 3),
            "cell": self._cell_text(self.header_fields_table, row_index, 4),
            "width": self._cell_text(self.header_fields_table, row_index, 5),
            "readonly": self._cell_text(self.header_fields_table, row_index, 6),
            "default": self._cell_text(self.header_fields_table, row_index, 7),
            "role": self._cell_text(self.header_fields_table, row_index, 8),
            "import_enabled": self._cell_text(self.header_fields_table, row_index, 9),
            "export_enabled": self._cell_text(self.header_fields_table, row_index, 10),
            "widget": self._cell_text(self.header_fields_table, row_index, 11),
            "state": self._cell_text(self.header_fields_table, row_index, 12),
            "options_source": self._cell_text(self.header_fields_table, row_index, 13),
            "values": self._cell_text(self.header_fields_table, row_index, 14),
        }

    def selected_row_field_id(self):
        row_index = self._selected_row_index(self.row_fields_table)
        if row_index < 0:
            return ""
        item = self.row_fields_table.item(row_index, 0)
        if item is None:
            return ""
        original_id = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        return original_id or self._cell_text(self.row_fields_table, row_index, 0)

    def selected_row_field_values(self):
        row_index = self._selected_row_index(self.row_fields_table)
        if row_index < 0:
            return None
        return {
            "id": self._cell_text(self.row_fields_table, row_index, 0),
            "label": self._cell_text(self.row_fields_table, row_index, 1),
            "widget": self._cell_text(self.row_fields_table, row_index, 2),
            "width": self._cell_text(self.row_fields_table, row_index, 3),
            "role": self._cell_text(self.row_fields_table, row_index, 4),
            "readonly": self._cell_text(self.row_fields_table, row_index, 5),
            "derived": self._cell_text(self.row_fields_table, row_index, 6),
            "math_trigger": self._cell_text(self.row_fields_table, row_index, 7),
            "open_row_trigger": self._cell_text(self.row_fields_table, row_index, 8),
            "user_input": self._cell_text(self.row_fields_table, row_index, 9),
            "expand": self._cell_text(self.row_fields_table, row_index, 10),
            "bold": self._cell_text(self.row_fields_table, row_index, 11),
            "default": self._cell_text(self.row_fields_table, row_index, 12),
            "sticky": self._cell_text(self.row_fields_table, row_index, 13),
            "state": self._cell_text(self.row_fields_table, row_index, 14),
            "options_source": self._cell_text(self.row_fields_table, row_index, 15),
            "bootstyle": self._cell_text(self.row_fields_table, row_index, 16),
            "values": self._cell_text(self.row_fields_table, row_index, 17),
        }

    def template_path_value(self):
        return str(self.template_path_input.text()).strip()

    def version_label_value(self):
        return str(self.snapshot_label_input.text() or "").strip()

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
        self.structure_tree.setUpdatesEnabled(False)
        self.structure_tree.clear()
        self.render_section_editor(config)

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

        try:
            for key, value in (config or {}).items():
                add_node(None, key, value)
        finally:
            self.structure_tree.setUpdatesEnabled(True)

        self.guardrails_view.setPlainText(json.dumps(guardrails or {}, indent=2))

    def render_section_editor(self, config):
        config_data = dict(config or {})
        sections = [section for section in config_data.get("sections", []) if isinstance(section, dict)]
        selected_section_id = self.current_section_id()
        blocker = QSignalBlocker(self.section_combo)
        self.section_combo.clear()
        for section in sections:
            section_id = str(section.get("id") or "")
            section_name = str(section.get("name") or section_id or "Section")
            self.section_combo.addItem(f"{section_name} [{section_id}]", section_id)
        if selected_section_id:
            section_index = self.section_combo.findData(selected_section_id)
            if section_index >= 0:
                self.section_combo.setCurrentIndex(section_index)
        del blocker
        self._render_selected_section_values(sections)

    def _render_selected_section_values(self, sections):
        current_section_id = self.current_section_id()
        current_section = next((section for section in sections if section.get("id") == current_section_id), None)
        if not isinstance(current_section, dict):
            self.section_name_input.setText("")
            self.section_description_input.setText("")
            self.section_behavior_profile_input.setText("")
            self.section_default_max_rows_input.setText("")
            self.section_delete_label_input.setText("")
            self.section_delete_tooltip_input.setText("")
            return
        self.section_name_input.setText(str(current_section.get("name") or ""))
        self.section_description_input.setText(str(current_section.get("description") or ""))
        section_type = str(current_section.get("section_type") or "single")
        section_type_index = self.section_type_combo.findData(section_type)
        if section_type_index >= 0:
            self.section_type_combo.setCurrentIndex(section_type_index)
        self.section_behavior_profile_input.setText(str(current_section.get("behavior_profile") or ""))
        self.section_default_max_rows_input.setText(str(current_section.get("default_max_rows") or ""))

        delete_policy = current_section.get("delete_row_policy") if isinstance(current_section.get("delete_row_policy"), dict) else {}
        show_delete = bool(delete_policy.get("show_delete_button", True))
        show_index = self.section_show_delete_combo.findData(show_delete)
        if show_index >= 0:
            self.section_show_delete_combo.setCurrentIndex(show_index)
        require_confirm = bool(delete_policy.get("require_delete_confirmation", False))
        confirm_index = self.section_require_confirm_combo.findData(require_confirm)
        if confirm_index >= 0:
            self.section_require_confirm_combo.setCurrentIndex(confirm_index)
        self.section_delete_label_input.setText(str(delete_policy.get("delete_button_label") or "X"))
        self.section_delete_tooltip_input.setText(str(delete_policy.get("delete_button_tooltip") or "Delete this row"))

    def current_section_id(self):
        return str(self.section_combo.currentData() or "")

    def set_section_selection(self, section_id):
        target_index = self.section_combo.findData(str(section_id or ""))
        if target_index >= 0:
            self.section_combo.setCurrentIndex(target_index)

    def selected_section_values(self):
        return {
            "name": str(self.section_name_input.text() or "").strip(),
            "description": str(self.section_description_input.text() or "").strip(),
            "section_type": str(self.section_type_combo.currentData() or "single"),
            "behavior_profile": str(self.section_behavior_profile_input.text() or "").strip(),
            "default_max_rows": str(self.section_default_max_rows_input.text() or "").strip(),
            "show_delete_button": self.section_show_delete_combo.currentData(),
            "delete_button_label": str(self.section_delete_label_input.text() or "").strip(),
            "delete_button_tooltip": str(self.section_delete_tooltip_input.text() or "").strip(),
            "require_delete_confirmation": self.section_require_confirm_combo.currentData(),
        }

    def prompt_text(self, title, label, default_text=""):
        text, accepted = QInputDialog.getText(self, title, label, QLineEdit.EchoMode.Normal, default_text)
        if not accepted:
            return None
        value = str(text).strip()
        return value or None

    def confirm(self, title, message):
        return QMessageBox.question(self, title, message) == QMessageBox.StandardButton.Yes

    def show_warning(self, title, message):
        QMessageBox.warning(self, title, message)

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
