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
from app.downtime_codes import get_code_options
from app.theme_manager import get_qt_palette, get_qt_stylesheet

__module_name__ = "Form Loader Qt View"
__version__ = "1.3.6"

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PYQT6_AVAILABLE = True


def is_production_log_qt_runtime_available():
    return PYQT6_AVAILABLE


class ProductionLogQtView(QMainWindow):
    ROW_ACTION_COLUMN = 0
    SECTION_NAME_DEFAULTS = {
        "header": "Header Fields",
        "production": "Production Rows",
        "downtime": "Downtime Rows",
    }
    REPEATING_SECTION_MIN_HEIGHTS = {
        "production": 260,
        "downtime": 240,
    }

    def __init__(
        self,
        controller,
        payload,
        sections,
        header_fields,
        production_fields,
        downtime_fields,
        row_delete_policies=None,
        parent_widget=None,
    ):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self.sections = [dict(section) for section in list(sections or []) if isinstance(section, dict)]
        self.header_fields = list(header_fields or [])
        self.production_fields = list(production_fields or [])
        self.downtime_fields = list(downtime_fields or [])
        self.section_field_configs = {
            "header": self.header_fields,
            "production": self.production_fields,
            "downtime": self.downtime_fields,
        }
        self.section_info_by_profile = self._build_section_info_by_profile()
        self.row_delete_policies = dict(row_delete_policies or {})
        self.header_widgets = {}
        self.repeating_sections = {}
        self.action_buttons = []
        self.production_table = None
        self.downtime_table = None
        self.has_unsaved_changes = False
        self.last_saved_signature = None
        self.last_export_path = None
        self._suspend_dirty_tracking = False
        self._build_ui()
        self.apply_theme(theme_tokens=self.theme_tokens)
        if self.embedded:
            self._attach_to_parent_container(parent_widget)
        self._wire_live_edit_handlers()

        if not self.embedded:
            self.command_timer = QTimer(self)
            self.command_timer.setInterval(700)
            self.command_timer.timeout.connect(self.controller.poll_commands)
            self.command_timer.start()

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(int(getattr(self.controller, "auto_save_interval_ms", 300000) or 300000))
        self.auto_save_timer.timeout.connect(self.controller.auto_save)
        self.auto_save_timer.start()

        self._live_recalculate_timer = QTimer(self)
        self._live_recalculate_timer.setSingleShot(True)
        self._live_recalculate_timer.setInterval(300)
        self._live_recalculate_timer.timeout.connect(self._run_live_recalculate)

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

    def _available_screen_geometry(self, widget=None):
        target = widget or self
        window_handle = getattr(target, "windowHandle", lambda: None)()
        screen = window_handle.screen() if window_handle is not None else None
        if screen is None and hasattr(target, "screen"):
            try:
                screen = target.screen()
            except Exception:
                screen = None
        application = QApplication.instance()
        if screen is None and application is not None:
            screen = application.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _fit_window_to_screen(self, widget, requested_width, requested_height, padding=48):
        geometry = self._available_screen_geometry(widget)
        if geometry is None:
            widget.resize(requested_width, requested_height)
            return
        max_width = max(720, geometry.width() - int(padding))
        max_height = max(540, geometry.height() - int(padding))
        widget.resize(min(int(requested_width), max_width), min(int(requested_height), max_height))

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Form Loader"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self._fit_window_to_screen(self, 1240, 840)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(central_widget)
        scroll_area.setWidgetResizable(True)
        self.content_scroll_area = scroll_area
        root_layout.addWidget(scroll_area, 1)

        scroll_content = QWidget(scroll_area)
        scroll_content.setMinimumWidth(1120)
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "Form Loader"))
        title_label.setObjectName("pageTitle")
        content_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "PyQt6 Form Loader editor"))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        content_layout.addWidget(subtitle_label)

        self.form_name_label = QLabel("Active Form: --")
        content_layout.addWidget(self.form_name_label)

        selector_group = QGroupBox("Form Selector", central_widget)
        selector_layout = QHBoxLayout(selector_group)
        selector_layout.setContentsMargins(8, 8, 8, 8)
        selector_layout.setSpacing(8)
        selector_layout.addWidget(QLabel("Stored Form"))

        self.form_selector_combo = QComboBox(selector_group)
        self.form_selector_combo.setMinimumWidth(280)
        selector_layout.addWidget(self.form_selector_combo, 1)

        activate_form_button = QPushButton("Switch Form", selector_group)
        activate_form_button.clicked.connect(self.controller.activate_selected_form)
        selector_layout.addWidget(activate_form_button)
        content_layout.addWidget(selector_group)

        self._build_dynamic_sections(content_layout)

        self.draft_status_label = QLabel("Drafts: 0 | Recovery: 0 | Latest: None")
        self.draft_status_label.setObjectName("mutedLabel")
        content_layout.addWidget(self.draft_status_label)

        metrics_layout = QHBoxLayout()
        self.efficiency_label = QLabel("EFF%: 0.00")
        self.ghost_label = QLabel("Ghost Time: 0 min")
        metrics_layout.addWidget(self.efficiency_label)
        metrics_layout.addWidget(self.ghost_label)
        metrics_layout.addStretch(1)
        content_layout.addLayout(metrics_layout)

        content_layout.addStretch(1)
        content_layout.addWidget(self._build_action_panel(scroll_content))
        scroll_area.setWidget(scroll_content)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Form Loader window ready.", 5000)

    def _build_section_info_by_profile(self):
        section_info_by_profile = {}
        for section in self.sections:
            behavior_profile = str(section.get("behavior_profile") or section.get("id") or "").strip().lower()
            if not behavior_profile or behavior_profile in section_info_by_profile:
                continue
            normalized_section = dict(section)
            normalized_section["behavior_profile"] = behavior_profile
            normalized_section["name"] = self._normalize_section_name(behavior_profile, section)
            normalized_section["description"] = str(section.get("description") or "")
            section_info_by_profile[behavior_profile] = normalized_section
        return section_info_by_profile

    def _normalize_section_name(self, section_id, section_info=None):
        if isinstance(section_info, dict):
            candidate = str(section_info.get("name") or section_info.get("id") or "").strip()
            if candidate:
                return candidate
        return self.SECTION_NAME_DEFAULTS.get(section_id, "Section")

    def _get_section_info(self, section_id, section_info=None):
        resolved_section_id = str(section_id or "").strip().lower()
        info = dict(self.section_info_by_profile.get(resolved_section_id) or {})
        if isinstance(section_info, dict):
            info.update(section_info)
        info["behavior_profile"] = resolved_section_id
        info["name"] = self._normalize_section_name(resolved_section_id, info)
        info["description"] = str(info.get("description") or "")
        if not str(info.get("section_type") or "").strip():
            info["section_type"] = "single" if resolved_section_id == "header" else "repeating"
        return info

    def _get_section_display_name(self, section_id):
        return str(self._get_section_info(section_id).get("name") or "Section")

    def _get_section_field_configs(self, section_id):
        return list(self.section_field_configs.get(str(section_id or "").strip().lower()) or [])

    def _register_repeating_section(self, section_id, table, field_configs, section_name):
        resolved_section_id = str(section_id or "").strip().lower()
        self.repeating_sections[resolved_section_id] = {
            "table": table,
            "field_configs": list(field_configs or []),
            "section_name": str(section_name or self._get_section_display_name(resolved_section_id)),
        }
        if resolved_section_id == "production":
            self.production_table = table
        elif resolved_section_id == "downtime":
            self.downtime_table = table

    def _get_repeating_section_runtime(self, section_id):
        return self.repeating_sections.get(str(section_id or "").strip().lower()) or {}

    def _get_section_table(self, section_id):
        runtime_info = self._get_repeating_section_runtime(section_id)
        table = runtime_info.get("table")
        if table is not None:
            return table
        resolved_section_id = str(section_id or "").strip().lower()
        if resolved_section_id == "production":
            return self.production_table
        if resolved_section_id == "downtime":
            return self.downtime_table
        return None

    def _build_dynamic_sections(self, content_layout):
        rendered_profiles = set()
        for section in self.sections:
            section_type = str(section.get("section_type") or "single").strip().lower()
            behavior_profile = str(section.get("behavior_profile") or section.get("id") or "").strip().lower()
            section_name = str(section.get("name") or section.get("id") or "Section").strip() or "Section"

            if behavior_profile in rendered_profiles:
                self._add_unsupported_section_notice(
                    content_layout,
                    section_name,
                    f"Section profile '{behavior_profile}' is declared more than once and only one instance is currently supported.",
                )
                continue

            if behavior_profile == "header" and section_type == "single":
                rendered_profiles.add(behavior_profile)
                self._build_header_section(content_layout, self._get_section_info("header", section))
                continue

            if behavior_profile == "production" and section_type == "repeating":
                rendered_profiles.add(behavior_profile)
                self._build_repeating_section(content_layout, "production", section)
                continue

            if behavior_profile == "downtime" and section_type == "repeating":
                rendered_profiles.add(behavior_profile)
                self._build_repeating_section(content_layout, "downtime", section)
                continue

            self._add_unsupported_section_notice(
                content_layout,
                section_name,
                f"Section profile '{behavior_profile or 'unknown'}' with type '{section_type or 'unknown'}' is not yet rendered in Form Loader.",
            )

    def _create_action_button(self, title, callback, enabled=True):
        button = QPushButton(str(title or "Action"))
        button.setMinimumHeight(40)
        button.clicked.connect(callback)
        button.setEnabled(bool(enabled))
        self.action_buttons.append(button)
        return button

    def _build_action_group(self, title, buttons, parent):
        group = QGroupBox(str(title or "Actions"), parent)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(8, 8, 8, 8)
        group_layout.setSpacing(8)
        for button in buttons:
            group_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
        group_layout.addStretch(1)
        return group

    def _update_action_button_widths(self):
        if not self.action_buttons:
            return
        target_width = max(button.sizeHint().width() for button in self.action_buttons)
        for button in self.action_buttons:
            button.setFixedWidth(target_width)

    def _build_action_panel(self, parent):
        action_panel = QGroupBox("Workspace Actions", parent)
        action_panel_layout = QGridLayout(action_panel)
        action_panel_layout.setContentsMargins(10, 10, 10, 10)
        action_panel_layout.setHorizontalSpacing(12)
        action_panel_layout.setVerticalSpacing(12)

        draft_group = self._build_action_group(
            "Draft Workflow",
            [
                self._create_action_button("Save Draft", self.controller.save_draft),
                self._create_action_button("Refresh Draft Lists", self.controller.refresh_draft_lists),
                self._create_action_button("Pending Drafts", self.controller.open_pending_dialog),
                self._create_action_button("Open Pending Folder", self.controller.open_pending_folder),
            ],
            action_panel,
        )

        recovery_group = self._build_action_group(
            "Recovery",
            [
                self._create_action_button("Recovery Snapshots", self.controller.open_recovery_dialog),
                self._create_action_button("Open Recovery Folder", self.controller.open_recovery_folder),
            ],
            action_panel,
        )

        self.open_export_button = self._create_action_button("Open Last Export", self.controller.open_last_exported_file, enabled=False)
        self.print_export_button = self._create_action_button(
            "Print Last Export",
            self.controller.print_last_exported_file,
            enabled=False,
        )
        workbook_group = self._build_action_group(
            "Workbook",
            [
                self._create_action_button("Import Excel", self.controller.import_from_excel_ui),
                self._create_action_button("Export Excel", self.controller.export_to_excel),
                self.open_export_button,
                self.print_export_button,
            ],
            action_panel,
        )

        tools_group = self._build_action_group(
            "Calculations & Tools",
            [
                self._create_action_button("Calculate", self.controller.calculate_metrics),
                self._create_action_button("Balance Downtime", self.controller.balance_downtime_to_shift),
            ],
            action_panel,
        )

        action_panel_layout.addWidget(draft_group, 0, 0)
        action_panel_layout.addWidget(recovery_group, 0, 1)
        action_panel_layout.addWidget(tools_group, 0, 2)
        action_panel_layout.addWidget(workbook_group, 0, 3)
        action_panel_layout.setColumnStretch(0, 1)
        action_panel_layout.setColumnStretch(1, 1)
        action_panel_layout.setColumnStretch(2, 1)
        action_panel_layout.setColumnStretch(3, 1)
        return action_panel

    def _add_section_heading(self, content_layout, title, description=None):
        title_label = QLabel(str(title or "Section"))
        title_label.setObjectName("sectionTitle")
        content_layout.addWidget(title_label)
        if str(description or "").strip():
            description_label = QLabel(str(description or ""))
            description_label.setObjectName("mutedLabel")
            description_label.setWordWrap(True)
            content_layout.addWidget(description_label)

    def _build_header_section(self, content_layout, section_info):
        section_info = self._get_section_info("header", section_info)
        section_name = str(section_info.get("name") or self._get_section_display_name("header"))
        description = str(section_info.get("description") or "")
        self._add_section_heading(content_layout, section_name, description)

        header_group = QGroupBox(section_name)
        header_layout = QGridLayout(header_group)
        header_layout.setHorizontalSpacing(12)
        header_layout.setVerticalSpacing(8)
        max_grid_col = 0
        for field in self._get_section_field_configs("header"):
            field_id = str(field.get("id") or "").strip()
            if not field_id:
                continue
            label_text = str(field.get("label") or field_id.replace("_", " ").title())
            grid_row = int(field.get("row") or 0)
            grid_col = int(field.get("col") or 0)
            max_grid_col = max(max_grid_col, grid_col + 1)

            field_widget = self._create_header_field_widget(field, header_group)

            label_widget = QLabel(label_text + ":", header_group)
            self.header_widgets[field_id] = field_widget
            header_layout.addWidget(label_widget, grid_row, grid_col)
            header_layout.addWidget(field_widget, grid_row, grid_col + 1)

        for column_index in range(max_grid_col + 2):
            if column_index % 2 == 1:
                header_layout.setColumnStretch(column_index, 1)
            else:
                header_layout.setColumnStretch(column_index, 0)
        content_layout.addWidget(header_group)

    def _header_field_options(self, field):
        options = []
        raw_values = field.get("values")
        if isinstance(raw_values, list):
            for raw_value in raw_values:
                value_text = str(raw_value or "").strip()
                if value_text and value_text not in options:
                    options.append(value_text)
        elif isinstance(raw_values, str):
            for raw_value in raw_values.split(","):
                value_text = str(raw_value or "").strip()
                if value_text and value_text not in options:
                    options.append(value_text)

        options_source = str(field.get("options_source") or "").strip().lower()
        if options_source == "downtime_codes":
            for raw_value in get_code_options():
                value_text = str(raw_value or "").strip()
                if value_text and value_text not in options:
                    options.append(value_text)
        return options

    def _create_header_field_widget(self, field, parent):
        configured_width = int(field.get("width") or 0)
        widget_name = str(field.get("widget") or "entry").strip().lower() or "entry"
        state_name = str(field.get("state") or "").strip().lower()
        default_text = str(field.get("default") or "")

        if widget_name == "combobox":
            field_widget = QComboBox(parent)
            field_widget.addItems(self._header_field_options(field))
            is_editable = state_name == "normal"
            if not state_name and bool(field.get("readonly")):
                is_editable = False
            field_widget.setEditable(is_editable)
            if configured_width > 0:
                field_widget.setMinimumWidth(max(90, configured_width * 10))
            if state_name == "disabled":
                field_widget.setEnabled(False)
            self._set_header_widget_value(field_widget, default_text)
            return field_widget

        field_widget = QLineEdit(default_text, parent)
        if bool(field.get("readonly")) or state_name == "readonly":
            field_widget.setReadOnly(True)
        if state_name == "disabled":
            field_widget.setEnabled(False)
        if configured_width > 0:
            field_widget.setMinimumWidth(max(90, configured_width * 10))
        return field_widget

    def _set_header_widget_value(self, widget, value):
        text_value = str(value or "")
        if isinstance(widget, QComboBox):
            if widget.isEditable():
                widget.setEditText(text_value)
                return
            match_index = widget.findText(text_value, Qt.MatchFlag.MatchFixedString)
            if match_index < 0:
                widget.addItem(text_value)
                match_index = widget.count() - 1
            widget.setCurrentIndex(match_index)
            return
        widget.setText(text_value)

    def _create_repeating_table(self, field_configs):
        table = QTableWidget()
        table.setColumnCount(len(field_configs) + 1)
        table.setHorizontalHeaderLabels([""] + self._field_labels(field_configs))
        table.setColumnWidth(self.ROW_ACTION_COLUMN, 36)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        return table

    def _build_repeating_section(self, content_layout, section_id, section_info=None):
        section_info = self._get_section_info(section_id, section_info)
        section_name = str(section_info.get("name") or self._get_section_display_name(section_id))
        description = str(section_info.get("description") or "")
        field_configs = self._get_section_field_configs(section_id)
        self._add_section_heading(content_layout, section_name, description)
        table = self._create_repeating_table(field_configs)
        table.setMinimumHeight(self.REPEATING_SECTION_MIN_HEIGHTS.get(section_id, 240))
        self._register_repeating_section(section_id, table, field_configs, section_name)
        content_layout.addWidget(table)

        actions_layout = QHBoxLayout()
        add_button = QPushButton("Add Row")
        remove_button = QPushButton("Remove Selected")
        add_button.clicked.connect(lambda _checked=False, current_section_id=section_id: self._focus_open_section(current_section_id))
        remove_button.clicked.connect(
            lambda _checked=False, current_section_id=section_id: self._remove_selected_section_row(current_section_id)
        )
        actions_layout.addWidget(add_button)
        actions_layout.addWidget(remove_button)
        actions_layout.addStretch(1)
        content_layout.addLayout(actions_layout)

    def _add_unsupported_section_notice(self, content_layout, section_name, message):
        self._add_section_heading(content_layout, section_name)
        notice_label = QLabel(str(message or "This section is not currently rendered."))
        notice_label.setObjectName("mutedLabel")
        notice_label.setWordWrap(True)
        content_layout.addWidget(notice_label)

    def apply_theme(self, theme_tokens=None):
        if isinstance(theme_tokens, dict):
            self.theme_tokens = dict(theme_tokens)
        self.setStyleSheet(get_qt_stylesheet(theme_tokens=self.theme_tokens))
        self._update_action_button_widths()
        application = QApplication.instance()
        if application is not None:
            application.setPalette(get_qt_palette(theme_tokens=self.theme_tokens))

    def _wire_live_edit_handlers(self):
        for widget in self.header_widgets.values():
            if isinstance(widget, QComboBox):
                try:
                    widget.currentTextChanged.connect(self._queue_live_recalculate)
                except Exception:
                    pass
                try:
                    widget.currentTextChanged.connect(self.controller.on_header_field_focus_out)
                except Exception:
                    pass
                continue
            try:
                widget.textChanged.connect(self._queue_live_recalculate)
            except Exception:
                continue
            try:
                widget.editingFinished.connect(self.controller.on_header_field_focus_out)
            except Exception:
                pass
        if self.production_table is not None:
            try:
                self.production_table.itemChanged.connect(self._handle_production_item_changed)
            except Exception:
                pass
        if self.downtime_table is not None:
            try:
                self.downtime_table.itemChanged.connect(self._handle_downtime_item_changed)
            except Exception:
                pass

    def _handle_production_item_changed(self, _item):
        self._handle_table_item_changed(self.production_table, self.production_fields)

    def _handle_downtime_item_changed(self, _item):
        self._handle_table_item_changed(self.downtime_table, self.downtime_fields)

    def _handle_table_item_changed(self, table, field_configs):
        self._ensure_open_row(table, field_configs)
        self._refresh_row_action_buttons(table, field_configs)
        self._queue_live_recalculate()

    def _queue_live_recalculate(self, *_args):
        if not self._suspend_dirty_tracking:
            self.mark_dirty()
        if self._live_recalculate_timer.isActive():
            self._live_recalculate_timer.stop()
        self._live_recalculate_timer.start()

    def _run_live_recalculate(self):
        self.controller.calculate_metrics(silent=True)

    def _field_labels(self, field_configs):
        labels = []
        for field in field_configs:
            label_text = str(field.get("label") or field.get("id") or "").strip()
            labels.append(label_text or "Field")
        return labels

    def _field_column_offset(self):
        return self.ROW_ACTION_COLUMN + 1

    def _first_editable_column(self, field_configs):
        for column_index, field in enumerate(field_configs, start=self._field_column_offset()):
            if not bool(field.get("readonly")) and not bool(field.get("derived")):
                return column_index
        return self._field_column_offset()

    def _row_has_content(self, table, field_configs, row_index):
        if table is None:
            return False
        for column_index, field in enumerate(field_configs, start=self._field_column_offset()):
            if bool(field.get("derived")):
                continue
            item = table.item(row_index, column_index)
            if item is not None and str(item.text() or "").strip():
                return True
        return False

    def _table_field_configs(self, table):
        section_id = self._table_section_id(table)
        if not section_id:
            return []
        runtime_info = self._get_repeating_section_runtime(section_id)
        field_configs = runtime_info.get("field_configs")
        if field_configs:
            return list(field_configs)
        return self._get_section_field_configs(section_id)

    def _table_section_id(self, table):
        for section_id, runtime_info in self.repeating_sections.items():
            if runtime_info.get("table") is table:
                return section_id
        if table is self.production_table:
            return "production"
        if table is self.downtime_table:
            return "downtime"
        return ""

    def _get_row_delete_policy(self, table):
        section_id = self._table_section_id(table)
        policy = self.row_delete_policies.get(section_id) if isinstance(self.row_delete_policies, dict) else {}
        if not isinstance(policy, dict):
            policy = {}
        return {
            "show_delete_button": bool(policy.get("show_delete_button", True)),
            "delete_button_label": str(policy.get("delete_button_label") or "X").strip() or "X",
            "delete_button_tooltip": str(policy.get("delete_button_tooltip") or "Delete this row").strip()
            or "Delete this row",
            "require_delete_confirmation": bool(policy.get("require_delete_confirmation", False)),
        }

    def set_row_delete_policies(self, row_delete_policies):
        self.row_delete_policies = dict(row_delete_policies or {})
        for runtime_info in self.repeating_sections.values():
            table = runtime_info.get("table")
            field_configs = list(runtime_info.get("field_configs") or [])
            if table is not None:
                self._refresh_row_action_buttons(table, field_configs)

    def _refresh_row_action_buttons(self, table, field_configs):
        if table is None:
            return
        policy = self._get_row_delete_policy(table)
        show_delete_button = bool(policy.get("show_delete_button", True))
        delete_button_label = str(policy.get("delete_button_label") or "X")
        delete_button_tooltip = str(policy.get("delete_button_tooltip") or "Delete this row")
        require_delete_confirmation = bool(policy.get("require_delete_confirmation", False))
        for row_index in range(table.rowCount()):
            if not show_delete_button:
                table.setCellWidget(row_index, self.ROW_ACTION_COLUMN, None)
                continue
            delete_button = QPushButton(delete_button_label)
            delete_button.setMaximumWidth(26)
            delete_button.setToolTip(delete_button_tooltip)
            delete_button.clicked.connect(
                lambda _checked=False, current_table=table, current_row=row_index, requires_confirm=require_delete_confirmation: self._remove_table_row(
                    current_table,
                    current_row,
                    require_confirmation=requires_confirm,
                )
            )
            table.setCellWidget(row_index, self.ROW_ACTION_COLUMN, delete_button)

    def _ensure_open_row(self, table, field_configs):
        if table is None:
            return
        table.blockSignals(True)
        try:
            row_index = table.rowCount() - 1
            while row_index >= 0:
                if not self._row_has_content(table, field_configs, row_index) and row_index != table.rowCount() - 1:
                    table.removeRow(row_index)
                row_index -= 1
            if table.rowCount() == 0 or self._row_has_content(table, field_configs, table.rowCount() - 1):
                self._append_row(table, field_configs)
        finally:
            table.blockSignals(False)

    def _focus_open_row(self, table, field_configs):
        if table is None:
            return
        self._ensure_open_row(table, field_configs)
        self._refresh_row_action_buttons(table, field_configs)
        if table.rowCount() <= 0:
            return
        row_index = table.rowCount() - 1
        column_index = self._first_editable_column(field_configs)
        table.setCurrentCell(row_index, column_index)
        item = table.item(row_index, column_index)
        if item is not None:
            table.editItem(item)

    def _set_table_rows(self, table, field_configs, rows):
        if table is None:
            return
        table.blockSignals(True)
        table.setRowCount(0)
        for row_data in rows:
            self._append_row(table, field_configs, row_data=row_data)
        self._ensure_open_row(table, field_configs)
        self._refresh_row_action_buttons(table, field_configs)
        table.blockSignals(False)

    def _append_row(self, table, field_configs, row_data=None):
        if table is None:
            return
        row_data = dict(row_data or {})
        row_index = table.rowCount()
        table.insertRow(row_index)
        for column_index, field in enumerate(field_configs, start=self._field_column_offset()):
            field_id = str(field.get("id") or "").strip()
            item_value = str(row_data.get(field_id, field.get("default") or ""))
            table_item = QTableWidgetItem(item_value)
            if bool(field.get("readonly")) or bool(field.get("derived")):
                table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row_index, column_index, table_item)

    def _field_index_map(self, field_configs):
        mapping = {}
        for column_index, field in enumerate(field_configs, start=self._field_column_offset()):
            field_id = str(field.get("id") or "").strip()
            if field_id:
                mapping[field_id] = column_index
        return mapping

    def set_table_field_value(self, section_name, row_index, field_id, value):
        normalized_section_name = str(section_name or "").strip().lower()
        table = self._get_section_table(normalized_section_name)
        field_map = self._field_index_map(self._get_section_field_configs(normalized_section_name))
        if table is None:
            return
        column_index = field_map.get(str(field_id or "").strip())
        if column_index is None:
            return
        if row_index < 0 or row_index >= table.rowCount():
            return
        item = table.item(row_index, column_index)
        if item is None:
            item = QTableWidgetItem("")
            table.setItem(row_index, column_index, item)
        table.blockSignals(True)
        item.setText(str(value or ""))
        table.blockSignals(False)

    def set_header_field_value(self, field_id, value):
        field_key = str(field_id or "").strip()
        if not field_key:
            return
        widget = self.header_widgets.get(field_key)
        if widget is None:
            return
        widget.blockSignals(True)
        self._set_header_widget_value(widget, value)
        widget.blockSignals(False)

    def ask_import_file_path(self):
        file_path, _selected = QFileDialog.getOpenFileName(
            self,
            "Import Form Loader Workbook",
            "",
            "Excel Workbooks (*.xlsx *.xlsm *.xls);;All Files (*)",
        )
        return str(file_path or "").strip()

    def set_metrics(self, efficiency, ghost_minutes):
        self.efficiency_label.setText(f"EFF%: {float(efficiency):.2f}")
        self.ghost_label.setText(f"Ghost Time: {int(ghost_minutes)} min")

    def _collect_rows(self, table, field_configs):
        if table is None:
            return []
        rows = []
        for row_index in range(table.rowCount()):
            row_payload = {}
            has_content = False
            for column_index, field in enumerate(field_configs, start=self._field_column_offset()):
                field_id = str(field.get("id") or "").strip()
                if not field_id:
                    continue
                item = table.item(row_index, column_index)
                value = str(item.text()) if item is not None else ""
                row_payload[field_id] = value
                if not bool(field.get("derived")) and value.strip():
                    has_content = True
            if has_content:
                rows.append(row_payload)
        return rows

    def collect_form_data(self):
        header_payload = {}
        for field_id, widget in self.header_widgets.items():
            if isinstance(widget, QComboBox):
                header_payload[field_id] = str(widget.currentText())
            else:
                header_payload[field_id] = str(widget.text())
        return {
            "header": header_payload,
            "production": self._collect_rows(self._get_section_table("production"), self._get_section_field_configs("production")),
            "downtime": self._collect_rows(self._get_section_table("downtime"), self._get_section_field_configs("downtime")),
        }

    def set_form_data(self, header_payload, production_rows, downtime_rows):
        header_payload = dict(header_payload or {})
        self._suspend_dirty_tracking = True
        for field_id, widget in self.header_widgets.items():
            widget.blockSignals(True)
            self._set_header_widget_value(widget, header_payload.get(field_id, ""))
            widget.blockSignals(False)
        self._set_table_rows(
            self._get_section_table("production"),
            self._get_section_field_configs("production"),
            list(production_rows or []),
        )
        self._set_table_rows(
            self._get_section_table("downtime"),
            self._get_section_field_configs("downtime"),
            list(downtime_rows or []),
        )
        self._suspend_dirty_tracking = False

    def set_form_name(self, form_name):
        self.form_name_label.setText(f"Active Form: {str(form_name or '--')}")

    def set_form_options(self, forms, selected_form_id=None):
        combo = getattr(self, "form_selector_combo", None)
        if combo is None:
            return
        previous_block_state = combo.blockSignals(True)
        combo.clear()
        for form_info in forms:
            form_name = str(form_info.get("name") or form_info.get("id") or "Unnamed Form")
            combo.addItem(form_name, form_info.get("id"))
        if selected_form_id:
            match_index = combo.findData(selected_form_id)
            if match_index >= 0:
                combo.setCurrentIndex(match_index)
        combo.blockSignals(previous_block_state)

    def current_form_id(self):
        combo = getattr(self, "form_selector_combo", None)
        if combo is None:
            return None
        return combo.currentData()

    def _focus_open_section(self, section_id):
        normalized_section_id = str(section_id or "").strip().lower()
        self._focus_open_row(
            self._get_section_table(normalized_section_id),
            self._get_section_field_configs(normalized_section_id),
        )

    def _remove_selected_section_row(self, section_id):
        normalized_section_id = str(section_id or "").strip().lower()
        table = self._get_section_table(normalized_section_id)
        if table is None:
            return
        selection_model = table.selectionModel()
        if selection_model is None:
            return
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return
        require_confirmation = bool(self._get_row_delete_policy(table).get("require_delete_confirmation", False))
        self._remove_table_row(table, int(selected_rows[0].row()), require_confirmation=require_confirmation)

    def set_draft_status(self, pending_count, recovery_count, latest_name):
        latest_text = str(latest_name or "None")
        self.draft_status_label.setText(
            f"Drafts: {int(pending_count)} | Recovery: {int(recovery_count)} | Latest: {latest_text}"
        )

    def _add_production_row(self):
        self._focus_open_section("production")

    def _remove_selected_production_row(self):
        self._remove_selected_section_row("production")

    def _add_downtime_row(self):
        self._focus_open_section("downtime")

    def _remove_selected_downtime_row(self):
        self._remove_selected_section_row("downtime")

    def _remove_table_row(self, table, row_index, require_confirmation=False):
        if row_index < 0 or row_index >= table.rowCount():
            return
        if require_confirmation:
            section_name = self._get_section_display_name(self._table_section_id(table))
            if not self.ask_yes_no("Delete Row", f"Delete selected {section_name} row?"):
                return
        field_configs = self._table_field_configs(table)
        table.blockSignals(True)
        table.removeRow(row_index)
        table.blockSignals(False)
        self._ensure_open_row(table, field_configs)
        self._refresh_row_action_buttons(table, field_configs)
        self.mark_dirty()
        self._queue_live_recalculate()

    def show_pending_dialog(self, pending_drafts):
        dialog = QDialog(self)
        dialog.setWindowTitle("Pending Drafts")
        self._fit_window_to_screen(dialog, 900, 420)
        layout = QVBoxLayout(dialog)

        table = QTableWidget(dialog)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Draft", "Form", "Date", "Shift", "Saved At"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(pending_drafts))
        for row_index, record in enumerate(pending_drafts):
            table.setItem(row_index, 0, QTableWidgetItem(str(record.get("filename") or "")))
            table.setItem(row_index, 1, QTableWidgetItem(str(record.get("form_name") or "")))
            table.setItem(row_index, 2, QTableWidgetItem(str(record.get("date") or "")))
            table.setItem(row_index, 3, QTableWidgetItem(str(record.get("shift") or "")))
            table.setItem(row_index, 4, QTableWidgetItem(str(record.get("saved_at") or "")))
        layout.addWidget(table)

        button_box = QDialogButtonBox(dialog)
        load_button = button_box.addButton("Load Selected", QDialogButtonBox.ButtonRole.AcceptRole)
        delete_button = button_box.addButton("Delete Selected", QDialogButtonBox.ButtonRole.DestructiveRole)
        close_button = button_box.addButton(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)

        def load_selected_draft():
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                self.show_info("Form Loader", "Select a pending draft first.")
                return
            selected_index = int(selected_rows[0].row())
            if selected_index < 0 or selected_index >= len(pending_drafts):
                return
            self.controller.load_draft_path(str(pending_drafts[selected_index].get("path") or ""))
            dialog.accept()

        def delete_selected_draft():
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                self.show_info("Delete Draft", "Select a pending draft first.")
                return
            selected_index = int(selected_rows[0].row())
            if selected_index < 0 or selected_index >= len(pending_drafts):
                return
            draft_record = pending_drafts[selected_index]
            draft_path = str(draft_record.get("path") or "")
            draft_name = str(draft_record.get("filename") or "selected draft")
            if not self.ask_yes_no("Delete Draft", f"Delete {draft_name}?"):
                return
            if self.controller.delete_draft_file(draft_path):
                dialog.accept()
                self.controller.open_pending_dialog()

        load_button.clicked.connect(load_selected_draft)
        delete_button.clicked.connect(delete_selected_draft)
        close_button.clicked.connect(dialog.reject)
        table.itemDoubleClicked.connect(lambda _item: load_selected_draft())
        dialog.exec()

    def show_recovery_dialog(self, recovery_snapshots):
        dialog = QDialog(self)
        dialog.setWindowTitle("Recovery Snapshots")
        self._fit_window_to_screen(dialog, 900, 440)
        layout = QVBoxLayout(dialog)

        table = QTableWidget(dialog)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Snapshot", "Form", "Date", "Shift", "Saved At"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(recovery_snapshots))
        for row_index, record in enumerate(recovery_snapshots):
            table.setItem(row_index, 0, QTableWidgetItem(str(record.get("filename") or "")))
            table.setItem(row_index, 1, QTableWidgetItem(str(record.get("form_name") or "")))
            table.setItem(row_index, 2, QTableWidgetItem(str(record.get("date") or "")))
            table.setItem(row_index, 3, QTableWidgetItem(str(record.get("shift") or "")))
            table.setItem(row_index, 4, QTableWidgetItem(str(record.get("saved_at") or "")))
        layout.addWidget(table)

        button_box = QDialogButtonBox(dialog)
        restore_button = button_box.addButton("Restore Selected To Form", QDialogButtonBox.ButtonRole.AcceptRole)
        open_recovery_viewer_button = button_box.addButton("Open Recovery Viewer", QDialogButtonBox.ButtonRole.ActionRole)
        close_button = button_box.addButton(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)

        def restore_selected_snapshot():
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                self.show_info("Form Loader", "Select a recovery snapshot first.")
                return
            selected_index = int(selected_rows[0].row())
            if selected_index < 0 or selected_index >= len(recovery_snapshots):
                return
            snapshot_path = str(recovery_snapshots[selected_index].get("path") or "")
            self.controller.restore_snapshot_to_form(snapshot_path)
            dialog.accept()

        def open_recovery_viewer_for_selected_snapshot():
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                self.controller.request_open_recovery(snapshot_path=None)
                return
            selected_index = int(selected_rows[0].row())
            if selected_index < 0 or selected_index >= len(recovery_snapshots):
                self.controller.request_open_recovery(snapshot_path=None)
                return
            snapshot_path = str(recovery_snapshots[selected_index].get("path") or "")
            self.controller.request_open_recovery(snapshot_path=snapshot_path)

        restore_button.clicked.connect(restore_selected_snapshot)
        open_recovery_viewer_button.clicked.connect(open_recovery_viewer_for_selected_snapshot)
        close_button.clicked.connect(dialog.reject)
        table.itemDoubleClicked.connect(lambda _item: restore_selected_snapshot())
        dialog.exec()

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def show_toast(self, title, message, bootstyle=None):
        self.controller.show_toast(title, message, bootstyle)

    def mark_dirty(self):
        self.has_unsaved_changes = True

    def mark_clean(self, data=None):
        serializer = getattr(self.controller, "serialize_ui_data", None)
        if callable(serializer):
            self.last_saved_signature = serializer(data or self.collect_form_data())
        self.has_unsaved_changes = False

    def confirm_discard_unsaved_changes(self):
        if not self.has_unsaved_changes:
            return True
        return self.ask_yes_no("Unsaved Changes", "You have unsaved changes in the current session. Continue and discard them?")

    def ask_yes_no(self, title, message):
        return QMessageBox.question(
            self,
            str(title or "Confirm"),
            str(message or ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

    def ask_form_switch_action(self, current_form_name, target_form_name):
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Switch Form")
        dialog.setText(f"Switch from {str(current_form_name or 'the current form')} to {str(target_form_name or 'the selected form')}?")
        dialog.setInformativeText(
            "You have entered data in the current form. Save a draft before switching, discard the current form data, or cancel the switch."
        )
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
        result = dialog.exec()
        if result == QMessageBox.StandardButton.Save:
            return "save"
        if result == QMessageBox.StandardButton.Discard:
            return "discard"
        return "cancel"

    def set_status(self, message):
        self.status_bar.showMessage(str(message), 5000)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
