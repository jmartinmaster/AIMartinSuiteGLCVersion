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

__module_name__ = "Settings Manager Qt View"
__version__ = "1.4.0"

try:
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QCheckBox,
        QCheckBox,
        QComboBox,
        QFormLayout,
        QGroupBox,
        QHeaderView,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QAbstractItemView = None
    QApplication = None
    QCheckBox = None
    QComboBox = None
    QFormLayout = None
    QGroupBox = None
    QHeaderView = None
    QHBoxLayout = None
    QInputDialog = None
    QLabel = None
    QLineEdit = None
    QListWidget = None
    QListWidgetItem = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QSpinBox = None
    QStatusBar = None
    QTableWidget = None
    QTableWidgetItem = None
    QTextEdit = None
    Qt = None
    QVBoxLayout = None
    QWidget = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_settings_manager_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_settings_manager_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Settings Manager Qt session payload must be a JSON object.")
    return payload


class SettingsManagerQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.value_labels = {}
        self.theme_combo = None
        self.export_directory_input = None
        self.toast_duration_spin = None
        self.auto_save_spin = None
        self.transition_enabled_checkbox = None
        self.transition_duration_spin = None
        self.organize_exports_checkbox = None
        self.module_whitelist_list = None
        self.persistent_modules_list = None
        self.downtime_codes_table = None
        self.security_admin_group = None
        self.security_session_label = None
        self.security_note_label = None
        self.security_vault_list = None
        self.security_vault_name_input = None
        self.security_role_combo = None
        self.security_enabled_checkbox = None
        self.security_password_rule_label = None
        self.security_non_secure_checkbox = None
        self.security_rights_checkboxes = {}
        self.security_role_defaults = {}
        self._security_state = {}
        self.developer_admin_group = None
        self.developer_repository_input = None
        self.developer_advanced_checkbox = None
        self.developer_trust_checkbox = None
        self.developer_status_label = None
        self._suspend_change_signal = False
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Settings Manager"))
        self.resize(1140, 820)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        title_label = QLabel(str(self.payload.get("title") or "Settings Manager"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Qt sidecar bootstrap for Settings Manager migration."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        summary_group = QGroupBox("Current Settings Snapshot")
        summary_form = QFormLayout(summary_group)

        for key, label in [
            ("theme", "Theme"),
            ("security_summary", "Security Session"),
            ("section_mode", "Section Mode"),
            ("module_whitelist", "Module Whitelist"),
            ("persistent_modules", "Persistent Modules"),
            ("external_override_trust", "External Override Trust"),
            ("security_admin_visible", "Security Admin Visible"),
            ("developer_admin_visible", "Developer Admin Visible"),
        ]:
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.value_labels[key] = value_label
            summary_form.addRow(QLabel(label), value_label)

        root_layout.addWidget(summary_group)

        editable_group = QGroupBox("Core Settings (Slice 1)")
        editable_layout = QFormLayout(editable_group)

        self.theme_combo = QComboBox()
        self.theme_combo.currentIndexChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Theme"), self.theme_combo)

        self.export_directory_input = QLineEdit()
        self.export_directory_input.textChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Export Directory"), self.export_directory_input)

        self.organize_exports_checkbox = QCheckBox("Organize exports by date")
        self.organize_exports_checkbox.stateChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Export Organization"), self.organize_exports_checkbox)

        self.toast_duration_spin = QSpinBox()
        self.toast_duration_spin.setRange(1, 120)
        self.toast_duration_spin.valueChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Toast Duration (sec)"), self.toast_duration_spin)

        self.auto_save_spin = QSpinBox()
        self.auto_save_spin.setRange(1, 240)
        self.auto_save_spin.valueChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Auto Save Interval (min)"), self.auto_save_spin)

        self.transition_enabled_checkbox = QCheckBox("Enable screen transitions")
        self.transition_enabled_checkbox.stateChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Transitions"), self.transition_enabled_checkbox)

        self.transition_duration_spin = QSpinBox()
        self.transition_duration_spin.setRange(0, 500)
        self.transition_duration_spin.valueChanged.connect(self._on_form_changed)
        editable_layout.addRow(QLabel("Transition Duration (ms)"), self.transition_duration_spin)

        module_lists_row = QHBoxLayout()
        self.module_whitelist_list = QListWidget()
        self.module_whitelist_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.module_whitelist_list.itemSelectionChanged.connect(self._on_form_changed)
        self.persistent_modules_list = QListWidget()
        self.persistent_modules_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.persistent_modules_list.itemSelectionChanged.connect(self._on_form_changed)
        module_lists_row.addWidget(self.module_whitelist_list)
        module_lists_row.addWidget(self.persistent_modules_list)
        editable_layout.addRow(QLabel("Module Lists"), module_lists_row)

        root_layout.addWidget(editable_group)

        downtime_group = QGroupBox("Downtime Codes (Slice 2)")
        downtime_layout = QVBoxLayout(downtime_group)
        downtime_hint = QLabel(
            "Edit numeric downtime codes inline. Imports and exports use these code numbers."
        )
        downtime_hint.setWordWrap(True)
        downtime_layout.addWidget(downtime_hint)

        self.downtime_codes_table = QTableWidget(0, 2)
        self.downtime_codes_table.setHorizontalHeaderLabels(["Code", "Label"])
        self.downtime_codes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.downtime_codes_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.downtime_codes_table.verticalHeader().setVisible(False)
        self.downtime_codes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.downtime_codes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.downtime_codes_table.itemChanged.connect(self._on_form_changed)
        downtime_layout.addWidget(self.downtime_codes_table)

        downtime_actions = QHBoxLayout()
        add_code_button = QPushButton("Add Code")
        add_code_button.clicked.connect(self.controller.add_next_downtime_code_row)
        downtime_actions.addWidget(add_code_button)
        reset_codes_button = QPushButton("Reset Defaults")
        reset_codes_button.clicked.connect(self.controller.reset_downtime_codes_to_defaults)
        downtime_actions.addWidget(reset_codes_button)
        apply_codes_button = QPushButton("Apply Codes")
        apply_codes_button.clicked.connect(self.controller.apply_downtime_codes)
        downtime_actions.addWidget(apply_codes_button)
        downtime_actions.addStretch(1)
        downtime_layout.addLayout(downtime_actions)

        root_layout.addWidget(downtime_group)

        self.security_admin_group = QGroupBox("Security Administration (Slice 3)")
        security_layout = QVBoxLayout(self.security_admin_group)

        self.security_session_label = QLabel("Session: Locked")
        self.security_session_label.setWordWrap(True)
        security_layout.addWidget(self.security_session_label)

        self.security_note_label = QLabel("Security admin tools require an active admin or developer session.")
        self.security_note_label.setWordWrap(True)
        security_layout.addWidget(self.security_note_label)

        security_editor_layout = QHBoxLayout()

        self.security_vault_list = QListWidget()
        self.security_vault_list.itemSelectionChanged.connect(self.controller.load_selected_security_vault)
        security_editor_layout.addWidget(self.security_vault_list, 1)

        security_form_container = QWidget()
        security_form = QFormLayout(security_form_container)

        self.security_vault_name_input = QLineEdit()
        self.security_vault_name_input.textChanged.connect(self._on_form_changed)
        security_form.addRow(QLabel("Vault Name"), self.security_vault_name_input)

        self.security_role_combo = QComboBox()
        self.security_role_combo.addItems(["general", "admin", "developer"])
        self.security_role_combo.currentTextChanged.connect(self.controller.on_security_role_selected)
        security_form.addRow(QLabel("Role"), self.security_role_combo)

        self.security_enabled_checkbox = QCheckBox("Enabled")
        self.security_enabled_checkbox.stateChanged.connect(self._on_form_changed)
        security_form.addRow(QLabel("Vault Status"), self.security_enabled_checkbox)

        self.security_password_rule_label = QLabel("Password rule: not set")
        self.security_password_rule_label.setWordWrap(True)
        security_form.addRow(QLabel("Password Rule"), self.security_password_rule_label)

        rights_container = QWidget()
        rights_layout = QVBoxLayout(rights_container)
        rights_layout.setContentsMargins(0, 0, 0, 0)
        rights_layout.setSpacing(4)
        security_form.addRow(QLabel("Access Rights"), rights_container)
        self.security_rights_container = rights_container
        self.security_rights_layout = rights_layout

        self.security_non_secure_checkbox = QCheckBox("Persistently bypass protected-module authentication")
        self.security_non_secure_checkbox.stateChanged.connect(self._on_form_changed)
        security_form.addRow(QLabel("Security Mode"), self.security_non_secure_checkbox)

        security_actions_row_1 = QHBoxLayout()
        new_vault_button = QPushButton("New Vault")
        new_vault_button.clicked.connect(self.controller.start_new_security_vault)
        security_actions_row_1.addWidget(new_vault_button)
        role_defaults_button = QPushButton("Role Defaults")
        role_defaults_button.clicked.connect(self.controller.apply_selected_security_role_defaults)
        security_actions_row_1.addWidget(role_defaults_button)
        save_vault_button = QPushButton("Save Vault")
        save_vault_button.clicked.connect(self.controller.save_current_security_vault)
        security_actions_row_1.addWidget(save_vault_button)
        save_reset_vault_button = QPushButton("Save + Reset Password")
        save_reset_vault_button.clicked.connect(lambda: self.controller.save_current_security_vault(reset_password=True))
        security_actions_row_1.addWidget(save_reset_vault_button)
        security_actions_row_1.addStretch(1)
        security_form.addRow(QLabel("Vault Actions"), security_actions_row_1)

        security_actions_row_2 = QHBoxLayout()
        rotate_password_button = QPushButton("Rotate Password")
        rotate_password_button.clicked.connect(self.controller.rotate_selected_security_vault_password)
        security_actions_row_2.addWidget(rotate_password_button)
        delete_vault_button = QPushButton("Delete Vault")
        delete_vault_button.clicked.connect(self.controller.delete_selected_security_vault)
        security_actions_row_2.addWidget(delete_vault_button)
        save_security_mode_button = QPushButton("Save Security Mode")
        save_security_mode_button.clicked.connect(self.controller.save_current_security_mode)
        security_actions_row_2.addWidget(save_security_mode_button)
        security_actions_row_2.addStretch(1)
        security_form.addRow(QLabel("Mode Actions"), security_actions_row_2)

        security_editor_layout.addWidget(security_form_container, 2)
        security_layout.addLayout(security_editor_layout)
        root_layout.addWidget(self.security_admin_group)

        self.developer_admin_group = QGroupBox("Developer & Admin Tools (Slice 4)")
        developer_layout = QFormLayout(self.developer_admin_group)

        self.developer_repository_input = QLineEdit()
        self.developer_repository_input.textChanged.connect(self._on_form_changed)
        developer_layout.addRow(QLabel("Update Repository URL"), self.developer_repository_input)

        self.developer_advanced_checkbox = QCheckBox("Enable advanced dev update actions")
        self.developer_advanced_checkbox.stateChanged.connect(self._on_form_changed)
        developer_layout.addRow(QLabel("Advanced Dev Updates"), self.developer_advanced_checkbox)

        self.developer_trust_checkbox = QCheckBox("Enable external module override trust")
        self.developer_trust_checkbox.stateChanged.connect(self._on_form_changed)
        developer_layout.addRow(QLabel("Override Trust"), self.developer_trust_checkbox)

        self.developer_status_label = QLabel("-")
        self.developer_status_label.setWordWrap(True)
        developer_layout.addRow(QLabel("External Modules"), self.developer_status_label)

        save_developer_button = QPushButton("Save Developer Settings")
        save_developer_button.clicked.connect(self.controller.save_current_developer_admin_settings)
        developer_layout.addRow(QLabel("Actions"), save_developer_button)

        root_layout.addWidget(self.developer_admin_group)

        note_group = QGroupBox("Migration Note")
        note_layout = QVBoxLayout(note_group)
        self.note_text = QTextEdit()
        self.note_text.setReadOnly(True)
        note_layout.addWidget(self.note_text)
        root_layout.addWidget(note_group, 1)

        controls = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.controller.save_settings)
        controls.addWidget(save_button)
        refresh_button = QPushButton("Refresh Snapshot")
        refresh_button.clicked.connect(self.controller.refresh_snapshot)
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        root_layout.addLayout(controls)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _on_form_changed(self):
        if self._suspend_change_signal:
            return
        self.controller.on_form_changed()

    def render_snapshot(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        for key, label_widget in self.value_labels.items():
            label_widget.setText(str(snapshot.get(key, "-")))
        self.note_text.setPlainText(str(snapshot.get("note") or ""))
        self.security_session_label.setText(f"Session: {snapshot.get('security_summary', 'Locked')}")
        self.security_admin_group.setVisible(bool(snapshot.get("security_admin_visible", False)))
        self.developer_admin_group.setVisible(bool(snapshot.get("developer_admin_visible", False)))
        self.status_bar.showMessage("Settings snapshot refreshed.", 4000)

    def _populate_module_list(self, widget, options, selected_names):
        widget.clear()
        selected_lookup = set(selected_names or [])
        for item in options or []:
            module_name = str(item.get("module_name") or "").strip()
            display_name = str(item.get("display_name") or module_name)
            if not module_name:
                continue
            list_item = QListWidgetItem(f"{display_name} ({module_name})")
            list_item.setData(0x0100, module_name)
            widget.addItem(list_item)
            list_item.setSelected(module_name in selected_lookup)

    def _selected_module_names(self, widget):
        selected_names = []
        for item in widget.selectedItems():
            module_name = str(item.data(0x0100) or "").strip()
            if module_name and module_name not in selected_names:
                selected_names.append(module_name)
        return selected_names

    def set_editable_settings(self, settings, theme_options, navigation_modules, persistable_modules):
        settings = settings if isinstance(settings, dict) else {}
        self._suspend_change_signal = True
        try:
            self.theme_combo.clear()
            selected_theme = str(settings.get("theme") or "")
            for option in theme_options or []:
                theme_key = str(option.get("key") or "").strip()
                theme_label = str(option.get("label") or theme_key)
                if not theme_key:
                    continue
                self.theme_combo.addItem(theme_label, theme_key)
            selected_index = self.theme_combo.findData(selected_theme)
            if selected_index < 0:
                selected_index = 0
            if selected_index >= 0:
                self.theme_combo.setCurrentIndex(selected_index)

            self.export_directory_input.setText(str(settings.get("export_directory") or ""))
            self.organize_exports_checkbox.setChecked(bool(settings.get("organize_exports_by_date", True)))
            self.toast_duration_spin.setValue(int(settings.get("toast_duration_sec", 5)))
            self.auto_save_spin.setValue(int(settings.get("auto_save_interval_min", 5)))
            self.transition_enabled_checkbox.setChecked(bool(settings.get("enable_screen_transitions", True)))
            self.transition_duration_spin.setValue(int(settings.get("screen_transition_duration_ms", 360)))

            self._populate_module_list(self.module_whitelist_list, navigation_modules, settings.get("module_whitelist", []))
            self._populate_module_list(self.persistent_modules_list, persistable_modules, settings.get("persistent_modules", []))
            self.set_downtime_code_rows(settings.get("downtime_codes", {}))
        finally:
            self._suspend_change_signal = False

    def get_form_values(self):
        return {
            "theme": str(self.theme_combo.currentData() or ""),
            "export_directory": self.export_directory_input.text().strip(),
            "organize_exports_by_date": bool(self.organize_exports_checkbox.isChecked()),
            "toast_duration_sec": int(self.toast_duration_spin.value()),
            "auto_save_interval_min": int(self.auto_save_spin.value()),
            "enable_screen_transitions": bool(self.transition_enabled_checkbox.isChecked()),
            "screen_transition_duration_ms": int(self.transition_duration_spin.value()),
            "module_whitelist": self._selected_module_names(self.module_whitelist_list),
            "persistent_modules": self._selected_module_names(self.persistent_modules_list),
        }

    def set_downtime_code_rows(self, code_map):
        code_map = code_map if isinstance(code_map, dict) else {}
        ordered_items = sorted(code_map.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else str(item[0]))
        self.downtime_codes_table.setRowCount(0)
        for code, label in ordered_items:
            self.add_downtime_code_row(str(code), str(label))

    def add_downtime_code_row(self, code, label):
        self.downtime_codes_table.blockSignals(True)
        try:
            row_index = self.downtime_codes_table.rowCount()
            self.downtime_codes_table.insertRow(row_index)
            self.downtime_codes_table.setItem(row_index, 0, QTableWidgetItem(str(code or "")))
            self.downtime_codes_table.setItem(row_index, 1, QTableWidgetItem(str(label or "")))
        finally:
            self.downtime_codes_table.blockSignals(False)

    def get_downtime_code_rows(self):
        rows = []
        for row_index in range(self.downtime_codes_table.rowCount()):
            code_item = self.downtime_codes_table.item(row_index, 0)
            label_item = self.downtime_codes_table.item(row_index, 1)
            rows.append(
                {
                    "code": str(code_item.text()).strip() if code_item else "",
                    "label": str(label_item.text()).strip() if label_item else "",
                }
            )
        return rows

    def _get_selected_vault_record(self):
        current_item = self.security_vault_list.currentItem()
        if current_item is None:
            return None
        return current_item.data(0x0100)

    def set_security_vault_form(self, vault_record):
        vault_record = vault_record if isinstance(vault_record, dict) else {}
        self._suspend_change_signal = True
        try:
            self.security_vault_name_input.setText(str(vault_record.get("vault_name") or ""))
            role = str(vault_record.get("role") or "general").strip().lower()
            role_index = self.security_role_combo.findText(role)
            if role_index < 0:
                role_index = 0
            self.security_role_combo.setCurrentIndex(role_index)
            self.security_enabled_checkbox.setChecked(bool(vault_record.get("enabled", True)))
            self.update_security_role_note()

            selected_rights = set(vault_record.get("rights") or [])
            for right_key, checkbox in self.security_rights_checkboxes.items():
                checkbox.setChecked(right_key in selected_rights)
        finally:
            self._suspend_change_signal = False

    def get_selected_security_vault_name(self):
        record = self._get_selected_vault_record()
        if not isinstance(record, dict):
            return ""
        return str(record.get("vault_name") or "")

    def clear_security_vault_selection(self):
        self.security_vault_list.clearSelection()

    def update_security_role_note(self):
        role = str(self.security_role_combo.currentText() or "general").strip().lower()
        if role == "general":
            self.security_password_rule_label.setText("General vaults do not require passwords.")
        elif role == "admin":
            self.security_password_rule_label.setText("Admin vaults require a password.")
        else:
            self.security_password_rule_label.setText("Developer vaults require a password and include all rights.")

    def apply_security_role_defaults(self):
        role = str(self.security_role_combo.currentText() or "general").strip().lower()
        defaults = set(self.security_role_defaults.get(role, []))
        if role == "developer":
            for checkbox in self.security_rights_checkboxes.values():
                checkbox.setChecked(True)
        else:
            for right_key, checkbox in self.security_rights_checkboxes.items():
                checkbox.setChecked(right_key in defaults)
        self._on_form_changed()

    def _configure_security_rights(self, access_rights):
        while self.security_rights_layout.count() > 0:
            item = self.security_rights_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.security_rights_checkboxes = {}

        for right in access_rights or []:
            right_key = str(right.get("key") or "").strip()
            right_label = str(right.get("label") or right_key)
            if not right_key:
                continue
            checkbox = QCheckBox(right_label)
            checkbox.setToolTip(str(right.get("description") or ""))
            checkbox.stateChanged.connect(self._on_form_changed)
            self.security_rights_layout.addWidget(checkbox)
            self.security_rights_checkboxes[right_key] = checkbox

    def configure_security_admin_panel(self, state, preferred_name=None):
        state = state if isinstance(state, dict) else {}
        self._security_state = state
        self.security_role_defaults = dict(state.get("role_defaults") or {})
        self._configure_security_rights(state.get("access_rights") or [])
        self.security_note_label.setText(str(state.get("session_summary") or "Locked"))

        self.security_vault_list.clear()
        preferred = str(preferred_name or "").strip()
        selected_row = -1
        for index, vault in enumerate(state.get("vaults") or []):
            vault_name = str(vault.get("vault_name") or "")
            role = str(vault.get("role") or "general")
            enabled_text = "enabled" if bool(vault.get("enabled", True)) else "disabled"
            list_item = QListWidgetItem(f"{vault_name} ({role}, {enabled_text})")
            list_item.setData(0x0100, vault)
            self.security_vault_list.addItem(list_item)
            if preferred and vault_name == preferred:
                selected_row = index

        if selected_row < 0 and self.security_vault_list.count() > 0:
            selected_row = 0
        if selected_row >= 0:
            self.security_vault_list.setCurrentRow(selected_row)
            self.set_security_vault_form(self._get_selected_vault_record())
        else:
            self.set_security_vault_form(None)

        self._suspend_change_signal = True
        try:
            self.security_non_secure_checkbox.setChecked(bool(state.get("non_secure_mode", False)))
        finally:
            self._suspend_change_signal = False

    def get_security_non_secure_mode(self):
        return bool(self.security_non_secure_checkbox.isChecked())

    def get_security_vault_payload(self, reset_password=False):
        selected = self._get_selected_vault_record() or {}
        rights = [
            right_key
            for right_key, checkbox in self.security_rights_checkboxes.items()
            if checkbox.isChecked()
        ]
        return {
            "existing_name": str(selected.get("vault_name") or "").strip() or None,
            "vault_name": self.security_vault_name_input.text().strip(),
            "role": str(self.security_role_combo.currentText() or "general").strip().lower(),
            "enabled": bool(self.security_enabled_checkbox.isChecked()),
            "rights": rights,
            "reset_password": bool(reset_password),
        }

    def configure_developer_admin_tools(self, state):
        state = state if isinstance(state, dict) else {}
        self._suspend_change_signal = True
        try:
            self.developer_repository_input.setText(str(state.get("update_repository_url") or ""))
            self.developer_advanced_checkbox.setChecked(bool(state.get("enable_advanced_dev_updates", False)))
            self.developer_trust_checkbox.setChecked(bool(state.get("enable_external_override_trust", False)))
            self.developer_status_label.setText(str(state.get("external_modules_status") or "-"))
        finally:
            self._suspend_change_signal = False

    def get_developer_admin_settings_values(self):
        return {
            "update_repository_url": self.developer_repository_input.text().strip(),
            "enable_advanced_dev_updates": bool(self.developer_advanced_checkbox.isChecked()),
            "enable_external_override_trust": bool(self.developer_trust_checkbox.isChecked()),
        }

    def ask_for_password_pair(self, title, message):
        first_value, first_ok = QInputDialog.getText(self, title, message, QLineEdit.EchoMode.Password)
        if not first_ok:
            return None
        second_value, second_ok = QInputDialog.getText(self, title, "Re-enter password:", QLineEdit.EchoMode.Password)
        if not second_ok:
            return None
        if first_value != second_value:
            self.show_error(title, "Passwords did not match.")
            return None
        if not str(first_value or "").strip():
            self.show_error(title, "Password cannot be blank.")
            return None
        return str(first_value)

    def ask_yes_no(self, title, message):
        response = QMessageBox.question(self, title, message)
        return response == QMessageBox.StandardButton.Yes

    def show_toast(self, title, message, _bootstyle=None):
        combined = f"{title}: {message}" if title else str(message or "")
        self.status_bar.showMessage(combined, 5000)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_settings_manager_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2

    from app.controllers.settings_manager_qt_controller import SettingsManagerQtController

    session_payload = load_settings_manager_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = SettingsManagerQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/settings_manager_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_settings_manager_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
