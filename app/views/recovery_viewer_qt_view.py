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
__version__ = "1.0.1"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QGroupBox,
    QFormLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
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
        self._backup_policy_table = None
        self._backup_policy_enabled_checkbox = None
        self._backup_policy_interval_spin = None
        self._backup_policy_keep_spin = None
        self._backup_policy_draft_auto_spin = None
        self._backup_policy_history_keep_spin = None
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

        clean_drafts_button = QPushButton("Clean Drafts")
        clean_drafts_button.clicked.connect(self.controller.clean_drafts)
        controls_layout.addWidget(clean_drafts_button)

        clean_snapshots_button = QPushButton("Clean Snapshots")
        clean_snapshots_button.clicked.connect(self.controller.clean_snapshots)
        controls_layout.addWidget(clean_snapshots_button)

        clean_config_backups_button = QPushButton("Clean Config Backups")
        clean_config_backups_button.clicked.connect(self.controller.clean_backups)
        controls_layout.addWidget(clean_config_backups_button)

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
            if record_type == "config_backup":
                self.config_backup_tabs = QTabWidget()
                self._config_backup_subtab_definitions = (
                    ("settings", "Settings"),
                    ("layouts", "Form Layouts"),
                    ("form_definitions", "Form Definitions"),
                    ("rates", "Rates"),
                    ("calculations", "Form Calculations"),
                )
                self._config_backup_tables = {}
                self._config_backup_row_to_global_index = {}
                for sub_type, sub_label in self._config_backup_subtab_definitions:
                    table = self._create_table_widget()
                    self._config_backup_tables[sub_type] = table
                    self._config_backup_row_to_global_index[sub_type] = []
                    self.config_backup_tabs.addTab(table, sub_label)
                self.tabs.addTab(self.config_backup_tabs, tab_label)
            else:
                table = self._create_table_widget()
                self._tables_by_record_type[record_type] = table
                self._tab_row_to_global_index[record_type] = []
                self.tabs.addTab(table, tab_label)
        self.tabs.addTab(self._build_backup_policy_tab(), "Backup Policy")
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

    def _build_backup_policy_tab(self):
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        description = QLabel(
            "Control how long the shared backup system waits between copies, how many versions it keeps, and which targets remain protected."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        controls_group = QGroupBox("Global Backup Policy")
        controls_form = QFormLayout(controls_group)

        self._backup_policy_enabled_checkbox = QCheckBox("Enable shared backups")
        controls_form.addRow(QLabel("Enabled"), self._backup_policy_enabled_checkbox)

        self._backup_policy_interval_spin = QSpinBox()
        self._backup_policy_interval_spin.setRange(1, 240)
        self._backup_policy_interval_spin.setSuffix(" min")
        controls_form.addRow(QLabel("Config Backup Interval"), self._backup_policy_interval_spin)

        self._backup_policy_keep_spin = QSpinBox()
        self._backup_policy_keep_spin.setRange(1, 250)
        controls_form.addRow(QLabel("Config Backup Retention"), self._backup_policy_keep_spin)

        self._backup_policy_draft_auto_spin = QSpinBox()
        self._backup_policy_draft_auto_spin.setRange(1, 240)
        self._backup_policy_draft_auto_spin.setSuffix(" min")
        controls_form.addRow(QLabel("Draft Auto-Save Interval"), self._backup_policy_draft_auto_spin)

        self._backup_policy_history_keep_spin = QSpinBox()
        self._backup_policy_history_keep_spin.setRange(1, 250)
        controls_form.addRow(QLabel("Draft History Retention"), self._backup_policy_history_keep_spin)

        layout.addWidget(controls_group)

        targets_group = QGroupBox("Backup Targets")
        targets_layout = QVBoxLayout(targets_group)
        targets_hint = QLabel(
            "Each row mirrors a backup target that currently writes to disk. Disable a row to stop that target from producing versioned backups."
        )
        targets_hint.setWordWrap(True)
        targets_layout.addWidget(targets_hint)

        self._backup_policy_table = QTableWidget(0, 6)
        self._backup_policy_table.setHorizontalHeaderLabels(["Enabled", "Target", "Interval", "Keep", "Path", "Description"])
        self._backup_policy_table.verticalHeader().setVisible(False)
        self._backup_policy_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._backup_policy_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._backup_policy_table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self._backup_policy_table.horizontalHeader().setStretchLastSection(True)
        self._backup_policy_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._backup_policy_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._backup_policy_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._backup_policy_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._backup_policy_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._backup_policy_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        targets_layout.addWidget(self._backup_policy_table)

        target_actions = QHBoxLayout()
        reload_policy_button = QPushButton("Reload Policy")
        reload_policy_button.clicked.connect(self.controller.refresh_backup_policy)
        target_actions.addWidget(reload_policy_button)

        reset_policy_button = QPushButton("Reset Defaults")
        reset_policy_button.clicked.connect(self.controller.reset_backup_policy_defaults)
        target_actions.addWidget(reset_policy_button)

        clean_backups_button = QPushButton("Clean Config Backups")
        clean_backups_button.clicked.connect(self.controller.clean_backups)
        target_actions.addWidget(clean_backups_button)

        save_policy_button = QPushButton("Save Policy")
        save_policy_button.clicked.connect(self.controller.save_backup_policy)
        target_actions.addWidget(save_policy_button)

        target_actions.addStretch(1)
        targets_layout.addLayout(target_actions)
        layout.addWidget(targets_group, 1)
        return tab

    def set_backup_policy(self, policy, target_definitions):
        policy = dict(policy or {})
        target_definitions = list(target_definitions or [])
        if self._backup_policy_enabled_checkbox is not None:
            self._backup_policy_enabled_checkbox.setChecked(bool(policy.get("enabled", True)))
        if self._backup_policy_interval_spin is not None:
            self._backup_policy_interval_spin.setValue(int(policy.get("interval_min", 30) or 30))
        if self._backup_policy_keep_spin is not None:
            self._backup_policy_keep_spin.setValue(int(policy.get("keep_count", 12) or 12))
        if self._backup_policy_draft_auto_spin is not None:
            self._backup_policy_draft_auto_spin.setValue(int(policy.get("draft_auto_save_interval_min", 5) or 5))
        if self._backup_policy_history_keep_spin is not None:
            self._backup_policy_history_keep_spin.setValue(int(policy.get("draft_history_keep_count", 20) or 20))

        target_overrides = policy.get("target_overrides") if isinstance(policy.get("target_overrides"), dict) else {}
        table = self._backup_policy_table
        if table is None:
            return

        table.setRowCount(len(target_definitions))
        for row_index, definition in enumerate(target_definitions):
            override = target_overrides.get(definition.get("key"), {}) if isinstance(target_overrides, dict) else {}
            effective_enabled = bool(override.get("enabled", True))
            effective_interval = int(override.get("interval_min", policy.get("interval_min", 30)) or 30)
            effective_keep = int(override.get("keep_count", policy.get("keep_count", 12)) or 12)

            enabled_item = QTableWidgetItem()
            enabled_item.setFlags(enabled_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            enabled_item.setCheckState(Qt.CheckState.Checked if effective_enabled else Qt.CheckState.Unchecked)
            enabled_item.setData(Qt.ItemDataRole.UserRole, str(definition.get("key") or ""))
            table.setItem(row_index, 0, enabled_item)

            table.setItem(row_index, 1, QTableWidgetItem(str(definition.get("label") or definition.get("key") or "")))

            interval_item = QTableWidgetItem(str(effective_interval))
            table.setItem(row_index, 2, interval_item)

            keep_item = QTableWidgetItem(str(effective_keep))
            table.setItem(row_index, 3, keep_item)

            table.setItem(row_index, 4, QTableWidgetItem(str(definition.get("target_path") or "")))
            table.setItem(row_index, 5, QTableWidgetItem(str(definition.get("description") or "")))

        self._backup_policy_table.resizeRowsToContents()

    def get_backup_policy_values(self):
        policy = {
            "enabled": self._backup_policy_enabled_checkbox.isChecked() if self._backup_policy_enabled_checkbox is not None else True,
            "interval_min": self._backup_policy_interval_spin.value() if self._backup_policy_interval_spin is not None else 30,
            "keep_count": self._backup_policy_keep_spin.value() if self._backup_policy_keep_spin is not None else 12,
            "draft_auto_save_interval_min": self._backup_policy_draft_auto_spin.value() if self._backup_policy_draft_auto_spin is not None else 5,
            "draft_history_keep_count": self._backup_policy_history_keep_spin.value() if self._backup_policy_history_keep_spin is not None else 20,
            "target_overrides": {},
        }

        table = self._backup_policy_table
        if table is None:
            return policy

        for row_index in range(table.rowCount()):
            target_item = table.item(row_index, 0)
            if target_item is None:
                continue
            target_key = str(target_item.data(Qt.ItemDataRole.UserRole) or "").strip()
            enabled_item = table.item(row_index, 0)
            interval_item = table.item(row_index, 2)
            keep_item = table.item(row_index, 3)
            interval_value = policy["interval_min"]
            keep_value = policy["keep_count"]
            try:
                interval_value = max(1, int(str(interval_item.text()).strip())) if interval_item is not None else policy["interval_min"]
            except Exception:
                interval_value = policy["interval_min"]
            try:
                keep_value = max(1, int(str(keep_item.text()).strip())) if keep_item is not None else policy["keep_count"]
            except Exception:
                keep_value = policy["keep_count"]
            policy["target_overrides"][target_key] = {
                "enabled": bool(enabled_item.checkState() == Qt.CheckState.Checked) if enabled_item is not None else True,
                "interval_min": interval_value,
                "keep_count": keep_value,
            }
        return policy

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

    def _get_config_backup_subtab_category(self, record):
        kind = str(record.get("kind") or "").lower()
        if "settings" in kind:
            return "settings"
        elif "form definition" in kind:
            return "form_definitions"
        elif "rate" in kind:
            return "rates"
        elif "calculation" in kind:
            return "calculations"
        else:
            return "layouts"

    def refresh_table(self, records):
        records = list(records or [])
        # 1. Refresh non-config_backup tabs
        for tab_index, (record_type, _) in enumerate(self._tab_definitions):
            if record_type == "config_backup":
                continue
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

        # 2. Refresh config_backup subtabs
        config_backup_records = [
            (global_index, record)
            for global_index, record in enumerate(records)
            if str(record.get("record_type") or "") == "config_backup"
        ]
        
        # Categorize
        subtab_records = {sub_type: [] for sub_type, _ in self._config_backup_subtab_definitions}
        for global_index, record in config_backup_records:
            category = self._get_config_backup_subtab_category(record)
            if category in subtab_records:
                subtab_records[category].append((global_index, record))
                
        # Populate each subtab table
        for sub_index, (sub_type, sub_label) in enumerate(self._config_backup_subtab_definitions):
            table = self._config_backup_tables[sub_type]
            table_records = subtab_records[sub_type]
            row_to_global_index = []
            table.setRowCount(len(table_records))
            for row_index, (global_index, record) in enumerate(table_records):
                row_to_global_index.append(global_index)
                table.setItem(row_index, 0, QTableWidgetItem(str(record.get("kind") or "")))
                table.setItem(row_index, 1, QTableWidgetItem(str(record.get("name") or "")))
                table.setItem(row_index, 2, QTableWidgetItem(str(record.get("form_name") or "System")))
                table.setItem(row_index, 3, QTableWidgetItem(str(record.get("saved_at") or "")))
                table.setItem(row_index, 4, QTableWidgetItem(str(record.get("restore_target") or "")))
            self._config_backup_row_to_global_index[sub_type] = row_to_global_index
            self.config_backup_tabs.setTabText(sub_index, f"{sub_label} ({len(table_records)})")
            
        # Update the main "Config Backups" tab text with total count
        main_tab_index = 0
        for idx, (r_type, _) in enumerate(self._tab_definitions):
            if r_type == "config_backup":
                main_tab_index = idx
                break
        self.tabs.setTabText(main_tab_index, f"Config Backups ({len(config_backup_records)})")
        
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
        if record_type == "config_backup":
            sub_index = self.config_backup_tabs.currentIndex()
            if sub_index < 0:
                return None
            sub_type = self._config_backup_subtab_definitions[sub_index][0]
            table = self._config_backup_tables[sub_type]
            selected_rows = table.selectionModel().selectedRows()
            if not selected_rows:
                return None
            row_index = int(selected_rows[0].row())
            row_to_global_index = self._config_backup_row_to_global_index.get(sub_type) or []
            if row_index < 0 or row_index >= len(row_to_global_index):
                return None
            return int(row_to_global_index[row_index])
        else:
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
        if hasattr(self, "_config_backup_tables"):
            for table in self._config_backup_tables.values():
                table.clearSelection()
        if index is None:
            return
        global_index = int(index)
        if global_index < 0:
            return
        for tab_index, (record_type, _) in enumerate(self._tab_definitions):
            if record_type == "config_backup":
                continue
            row_to_global_index = self._tab_row_to_global_index.get(record_type) or []
            if global_index not in row_to_global_index:
                continue
            row_index = row_to_global_index.index(global_index)
            table = self._tables_by_record_type[record_type]
            self.tabs.setCurrentIndex(tab_index)
            table.selectRow(row_index)
            return
        if hasattr(self, "_config_backup_subtab_definitions"):
            for sub_index, (sub_type, _) in enumerate(self._config_backup_subtab_definitions):
                row_to_global_index = self._config_backup_row_to_global_index.get(sub_type) or []
                if global_index not in row_to_global_index:
                    continue
                row_index = row_to_global_index.index(global_index)
                table = self._config_backup_tables[sub_type]
                main_tab_index = 0
                for idx, (r_type, _) in enumerate(self._tab_definitions):
                    if r_type == "config_backup":
                        main_tab_index = idx
                        break
                self.tabs.setCurrentIndex(main_tab_index)
                self.config_backup_tabs.setCurrentIndex(sub_index)
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
