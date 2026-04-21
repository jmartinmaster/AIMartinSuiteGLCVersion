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
__module_name__ = "Settings Manager Qt View"
__version__ = "1.5.1"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PYQT6_AVAILABLE = True
class SettingsManagerQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
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
        self.security_form_container = None
        self.security_vault_name_input = None
        self.security_role_combo = None
        self.security_enabled_checkbox = None
        self.security_password_rule_label = None
        self.security_non_secure_checkbox = None
        self.security_unlock_button = None
        self.security_rights_checkboxes = {}
        self.security_role_defaults = {}
        self._security_state = {}
        self.section_mode = str(self.payload.get("section_mode") or "full")
        self.summary_group = None
        self.editable_group = None
        self.downtime_group = None
        self.developer_admin_group = None
        self.developer_repository_input = None
        self.developer_advanced_checkbox = None
        self.developer_trust_checkbox = None
        self.developer_status_label = None
        self.developer_unlock_button = None
        self.developer_save_button = None
        self.note_text = None
        self._suspend_change_signal = False
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
        self.setWindowTitle(str(self.payload.get("window_title") or "Settings Manager"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self._fit_window_to_screen(1180, 860)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(central_widget)
        scroll_area.setWidgetResizable(True)
        self.content_scroll_area = scroll_area
        root_layout.addWidget(scroll_area, 1)

        scroll_content = QWidget(scroll_area)
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(10)

        title_label = QLabel(str(self.payload.get("title") or "Settings Manager"))
        title_label.setObjectName("pageTitle")
        content_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Manage application settings and privileged administration."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        content_layout.addWidget(subtitle_label)

        self.summary_group = QGroupBox("Current Settings")
        summary_form = QFormLayout(self.summary_group)

        for key, label in [
            ("theme", "Theme"),
            ("security_summary", "Security Session"),
            ("section_mode", "Administration Scope"),
            ("module_whitelist", "Module Whitelist"),
            ("persistent_modules", "Persistent Modules"),
            ("external_override_trust", "External Override Trust"),
            ("security_admin_visible", "Security Tools Access"),
            ("developer_admin_visible", "Developer Tools Access"),
        ]:
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.value_labels[key] = value_label
            summary_form.addRow(QLabel(label), value_label)

        content_layout.addWidget(self.summary_group)

        self.editable_group = QGroupBox("Core Settings")
        editable_layout = QFormLayout(self.editable_group)

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

        content_layout.addWidget(self.editable_group)

        self.downtime_group = QGroupBox("Downtime Codes")
        downtime_layout = QVBoxLayout(self.downtime_group)
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

        content_layout.addWidget(self.downtime_group)

        self.security_admin_group = QGroupBox("Security Administration")
        security_layout = QVBoxLayout(self.security_admin_group)

        self.security_session_label = QLabel("Session: Locked")
        self.security_session_label.setWordWrap(True)
        security_layout.addWidget(self.security_session_label)

        self.security_note_label = QLabel("Security admin tools require an active admin or developer session.")
        self.security_note_label.setWordWrap(True)
        security_layout.addWidget(self.security_note_label)

        self.security_unlock_button = QPushButton("Unlock Security Admin")
        self.security_unlock_button.clicked.connect(self.controller.request_security_admin_access)
        security_layout.addWidget(self.security_unlock_button, 0, Qt.AlignmentFlag.AlignLeft)

        security_editor_layout = QHBoxLayout()

        self.security_vault_list = QListWidget()
        self.security_vault_list.itemSelectionChanged.connect(self.controller.load_selected_security_vault)
        security_editor_layout.addWidget(self.security_vault_list, 1)

        security_form_container = QWidget()
        self.security_form_container = security_form_container
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
        reset_security_button = QPushButton("Reset Security Storage")
        reset_security_button.clicked.connect(self.controller.reset_security_storage_from_ui)
        security_actions_row_2.addWidget(reset_security_button)
        save_security_mode_button = QPushButton("Save Security Mode")
        save_security_mode_button.clicked.connect(self.controller.save_current_security_mode)
        security_actions_row_2.addWidget(save_security_mode_button)
        security_actions_row_2.addStretch(1)
        security_form.addRow(QLabel("Mode Actions"), security_actions_row_2)

        security_editor_layout.addWidget(security_form_container, 2)
        security_layout.addLayout(security_editor_layout)
        content_layout.addWidget(self.security_admin_group)

        self.developer_admin_group = QGroupBox("Developer & Admin Tools")
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

        self.developer_unlock_button = QPushButton("Unlock Developer Tools")
        self.developer_unlock_button.clicked.connect(self.controller.request_developer_admin_access)
        developer_layout.addRow(QLabel("Access"), self.developer_unlock_button)

        save_developer_button = QPushButton("Save Developer Settings")
        save_developer_button.clicked.connect(self.controller.save_current_developer_admin_settings)
        self.developer_save_button = save_developer_button
        developer_layout.addRow(QLabel("Actions"), save_developer_button)

        content_layout.addWidget(self.developer_admin_group)

        controls = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.controller.save_settings)
        controls.addWidget(save_button)
        refresh_button = QPushButton("Refresh Settings")
        refresh_button.clicked.connect(self.controller.refresh_snapshot)
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        content_layout.addLayout(controls)
        content_layout.addStretch(1)

        scroll_area.setWidget(scroll_content)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

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

    def _on_form_changed(self):
        if self._suspend_change_signal:
            return
        self.controller.on_form_changed()

    def render_snapshot(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        for key, label_widget in self.value_labels.items():
            label_widget.setText(str(snapshot.get(key, "-")))
        if self.note_text is not None:
            self.note_text.setPlainText(str(snapshot.get("note") or ""))
        self.security_session_label.setText(f"Session: {snapshot.get('security_summary', 'Locked')}")
        self.apply_section_mode(snapshot)
        self.status_bar.showMessage("Settings snapshot refreshed.", 4000)

    def apply_section_mode(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        section_mode = str(snapshot.get("section_mode") or self.section_mode or "full")
        self.section_mode = section_mode

        self.summary_group.setVisible(True)
        self.editable_group.setVisible(section_mode == "full")
        self.downtime_group.setVisible(section_mode == "full")

        security_visible = bool(snapshot.get("security_admin_visible", False))
        developer_visible = bool(snapshot.get("developer_admin_visible", False))

        if section_mode == "security_admin":
            self.security_admin_group.setVisible(True)
            self.developer_admin_group.setVisible(False)
            self.setWindowTitle(str(self.payload.get("window_title") or "Security Admin - Production Logging Center"))
            return

        if section_mode == "developer_admin":
            self.security_admin_group.setVisible(False)
            self.developer_admin_group.setVisible(True)
            self.setWindowTitle(str(self.payload.get("window_title") or "Developer Tools - Production Logging Center"))
            return

        self.security_admin_group.setVisible(security_visible)
        self.developer_admin_group.setVisible(developer_visible)
        self.setWindowTitle(str(self.payload.get("window_title") or "Settings Manager - Production Logging Center"))

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
        selected_items = self.security_vault_list.selectedItems() if self.security_vault_list is not None else []
        if not selected_items:
            return None
        return selected_items[0].data(0x0100)

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

            selected_rights = set(vault_record.get("rights") or self.security_role_defaults.get(role, []))
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
        if self.security_vault_list is None:
            return
        self.security_vault_list.blockSignals(True)
        try:
            self.security_vault_list.clearSelection()
            self.security_vault_list.setCurrentItem(None)
        finally:
            self.security_vault_list.blockSignals(False)

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
        can_manage_security = bool(state.get("can_manage_security", False))
        self.security_role_defaults = dict(state.get("role_defaults") or {})
        self._configure_security_rights(state.get("access_rights") or [])
        if can_manage_security:
            self.security_note_label.setText("Security administration is unlocked for the active admin or developer session.")
        else:
            self.security_note_label.setText("Sign in with an admin or developer vault to edit vaults, passwords, and security mode.")
        if self.security_form_container is not None:
            self.security_form_container.setEnabled(can_manage_security)
        if self.security_vault_list is not None:
            self.security_vault_list.setEnabled(can_manage_security)
        if self.security_unlock_button is not None:
            self.security_unlock_button.setText("Re-authenticate Security Admin" if can_manage_security else "Unlock Security Admin")

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
        can_manage_developer = bool(state.get("can_manage_developer", False))
        self._suspend_change_signal = True
        try:
            self.developer_repository_input.setText(str(state.get("update_repository_url") or ""))
            self.developer_advanced_checkbox.setChecked(bool(state.get("enable_advanced_dev_updates", False)))
            self.developer_trust_checkbox.setChecked(bool(state.get("enable_external_override_trust", False)))
            status_text = str(state.get("external_modules_status") or "-")
            if not can_manage_developer:
                status_text = f"Developer tools are locked until a developer session is active.\n\n{status_text}"
            self.developer_status_label.setText(status_text)
        finally:
            self._suspend_change_signal = False
        self.developer_repository_input.setEnabled(can_manage_developer)
        self.developer_advanced_checkbox.setEnabled(can_manage_developer)
        self.developer_trust_checkbox.setEnabled(can_manage_developer)
        if self.developer_save_button is not None:
            self.developer_save_button.setEnabled(can_manage_developer)
        if self.developer_unlock_button is not None:
            self.developer_unlock_button.setText("Re-authenticate Developer Tools" if can_manage_developer else "Unlock Developer Tools")

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
        dispatcher = getattr(self.controller, "dispatcher", None)
        show_toast = getattr(dispatcher, "show_toast", None)
        if callable(show_toast):
            show_toast(title, message, _bootstyle)
        self.status_bar.showMessage(combined, 5000)

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

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
