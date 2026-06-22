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
__version__ = "1.8.2"

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
    QFileDialog,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QTabWidget,
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
        self.theme_status_label = None
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
        self.security_password_required_checkbox = None
        self.security_password_rule_label = None
        self.security_non_secure_checkbox = None
        self.security_non_secure_modules_list = None
        self.security_save_role_defaults_button = None
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
        self.developer_runtime_settings_path_label = None
        self.developer_runtime_override_inputs = {}
        self.developer_runtime_override_access_labels = {}
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
        self.theme_combo.currentIndexChanged.connect(self.controller.preview_selected_theme)
        theme_row = QWidget()
        theme_row_layout = QHBoxLayout(theme_row)
        theme_row_layout.setContentsMargins(0, 0, 0, 0)
        theme_row_layout.addWidget(self.theme_combo, 1)
        revert_theme_button = QPushButton("Revert Preview")
        revert_theme_button.clicked.connect(self.controller.revert_theme_preview)
        theme_row_layout.addWidget(revert_theme_button)
        editable_layout.addRow(QLabel("Theme"), theme_row)

        self.theme_status_label = QLabel("Current theme: -")
        self.theme_status_label.setWordWrap(True)
        editable_layout.addRow(QLabel("Theme Status"), self.theme_status_label)

        self.export_directory_input = QLineEdit()
        self.export_directory_input.textChanged.connect(self._on_form_changed)
        export_row = QWidget()
        export_row_layout = QHBoxLayout(export_row)
        export_row_layout.setContentsMargins(0, 0, 0, 0)
        export_row_layout.addWidget(self.export_directory_input, 1)
        browse_export_button = QPushButton("Browse")
        browse_export_button.clicked.connect(self.controller.browse_export_dir)
        export_row_layout.addWidget(browse_export_button)
        editable_layout.addRow(QLabel("Export Directory"), export_row)

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

        module_lists_row = QWidget()
        module_lists_layout = QHBoxLayout(module_lists_row)
        module_lists_layout.setContentsMargins(0, 0, 0, 0)
        module_lists_layout.setSpacing(10)

        whitelist_column = QWidget()
        whitelist_layout = QVBoxLayout(whitelist_column)
        whitelist_layout.setContentsMargins(0, 0, 0, 0)
        whitelist_layout.setSpacing(4)
        whitelist_layout.addWidget(QLabel("Navigation Modules"))
        self.module_whitelist_list = QListWidget()
        self.module_whitelist_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.module_whitelist_list.itemSelectionChanged.connect(self._on_form_changed)
        whitelist_layout.addWidget(self.module_whitelist_list)

        persistent_column = QWidget()
        persistent_layout = QVBoxLayout(persistent_column)
        persistent_layout.setContentsMargins(0, 0, 0, 0)
        persistent_layout.setSpacing(4)
        persistent_layout.addWidget(QLabel("Persistent Modules"))
        self.persistent_modules_list = QListWidget()
        self.persistent_modules_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.persistent_modules_list.itemSelectionChanged.connect(self._on_form_changed)
        persistent_layout.addWidget(self.persistent_modules_list)

        module_lists_layout.addWidget(whitelist_column)
        module_lists_layout.addWidget(persistent_column)
        editable_layout.addRow(QLabel("Module Lists"), module_lists_row)

        content_layout.addWidget(self.editable_group)

        self.downtime_group = QGroupBox("Downtime Codes")
        downtime_layout = QVBoxLayout(self.downtime_group)
        downtime_hint = QLabel(
            "Edit downtime codes inline. Codes may be numeric or alphanumeric. Imports and exports use these code identifiers."
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

        self.security_password_required_checkbox = QCheckBox("Require Password")
        self.security_password_required_checkbox.stateChanged.connect(self._on_form_changed)
        security_form.addRow(QLabel("Password Requirement"), self.security_password_required_checkbox)

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

        self.security_non_secure_checkbox = QCheckBox("Enable persisted non-secure mode (for selected modules)")
        self.security_non_secure_checkbox.stateChanged.connect(self._on_form_changed)
        security_form.addRow(QLabel("Security Mode"), self.security_non_secure_checkbox)

        self.security_non_secure_modules_list = QListWidget()
        self.security_non_secure_modules_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.security_non_secure_modules_list.itemSelectionChanged.connect(self._on_form_changed)
        security_form.addRow(QLabel("Non-Secure Bypass Modules"), self.security_non_secure_modules_list)

        security_actions_row_1 = QHBoxLayout()
        new_vault_button = QPushButton("New Vault")
        new_vault_button.clicked.connect(self.controller.start_new_security_vault)
        security_actions_row_1.addWidget(new_vault_button)
        role_defaults_button = QPushButton("Role Defaults")
        role_defaults_button.clicked.connect(self.controller.apply_selected_security_role_defaults)
        security_actions_row_1.addWidget(role_defaults_button)
        self.security_save_role_defaults_button = QPushButton("Save Role Defaults")
        self.security_save_role_defaults_button.clicked.connect(self.controller.save_selected_security_role_defaults)
        security_actions_row_1.addWidget(self.security_save_role_defaults_button)
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
        developer_group_layout = QVBoxLayout(self.developer_admin_group)

        self.developer_tab_widget = QTabWidget()
        developer_group_layout.addWidget(self.developer_tab_widget)

        # Tab 1: Settings
        dev_settings_tab = QWidget()
        developer_layout = QFormLayout(dev_settings_tab)
        self.developer_tab_widget.addTab(dev_settings_tab, "Developer Settings")

        self.developer_access_label = QLabel("Admin or developer session required")
        self.developer_access_label.setWordWrap(True)
        developer_layout.addRow(QLabel("Developer & Admin"), self.developer_access_label)

        self.developer_note_label = QLabel(
            "Sign in from the File menu or Security tools to reveal privileged pages in the main navigation, including Internal Code Editor."
        )
        self.developer_note_label.setWordWrap(True)
        developer_layout.addRow(QLabel("Guidance"), self.developer_note_label)

        self.developer_repository_input = QLineEdit()
        self.developer_repository_input.textChanged.connect(self._on_form_changed)
        developer_layout.addRow(QLabel("Update Repository URL"), self.developer_repository_input)

        self.developer_advanced_checkbox = QCheckBox("Enable advanced dev update actions")
        self.developer_advanced_checkbox.stateChanged.connect(self._on_form_changed)
        developer_layout.addRow(QLabel("Advanced Dev Updates"), self.developer_advanced_checkbox)

        self.developer_trust_checkbox = QCheckBox("Enable external module override trust")
        self.developer_trust_checkbox.stateChanged.connect(self._on_form_changed)
        developer_layout.addRow(QLabel("Override Trust"), self.developer_trust_checkbox)

        self.developer_trust_note_label = QLabel(
            "Override files can exist beside the app without executing. Enable trust only when you intentionally want the app to load those external Python files."
        )
        self.developer_trust_note_label.setWordWrap(True)
        developer_layout.addRow(QLabel("Trust Guidance"), self.developer_trust_note_label)

        self.developer_status_label = QLabel("-")
        self.developer_status_label.setWordWrap(True)
        developer_layout.addRow(QLabel("External Modules"), self.developer_status_label)

        self.developer_runtime_settings_path_label = QLabel("-")
        self.developer_runtime_settings_path_label.setWordWrap(True)
        developer_layout.addRow(QLabel("Settings File"), self.developer_runtime_settings_path_label)

        runtime_paths_group = QGroupBox("Deferred Runtime Path Overrides")
        runtime_paths_layout = QFormLayout(runtime_paths_group)
        runtime_paths_hint = QLabel(
            "Set optional root overrides for runtime folders. Leave a field blank to use the default data/... location."
        )
        runtime_paths_hint.setWordWrap(True)
        runtime_paths_layout.addRow(runtime_paths_hint)

        self.developer_runtime_override_inputs = {}
        self.developer_runtime_override_access_labels = {}
        for override_key, override_label in [
            ("exports_root", "Exports Root"),
            ("forms_root", "Forms Root"),
            ("pending_root", "Pending Drafts Root"),
            ("backups_root", "Backups Root"),
            ("modules_root", "External Modules Root"),
            ("security_root", "Security Root"),
        ]:
            row_widget = QWidget()
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)

            input_row = QWidget()
            input_row_layout = QHBoxLayout(input_row)
            input_row_layout.setContentsMargins(0, 0, 0, 0)
            input_row_layout.setSpacing(4)

            path_input = QLineEdit()
            path_input.setPlaceholderText("Default (blank)")
            path_input.textChanged.connect(self._on_form_changed)
            input_row_layout.addWidget(path_input, 1)

            browse_button = QPushButton("Browse…")
            browse_button.setFixedWidth(72)
            _key = override_key
            browse_button.clicked.connect(lambda _checked=False, k=_key: self.controller.browse_runtime_path(k))
            input_row_layout.addWidget(browse_button)

            row_layout.addWidget(input_row)

            access_label = QLabel("-")
            access_label.setWordWrap(True)
            access_label.setObjectName("mutedLabel")
            row_layout.addWidget(access_label)

            runtime_paths_layout.addRow(QLabel(override_label), row_widget)
            self.developer_runtime_override_inputs[override_key] = path_input
            self.developer_runtime_override_access_labels[override_key] = access_label

        developer_layout.addRow(runtime_paths_group)

        self.developer_unlock_button = QPushButton("Unlock Developer Tools")
        self.developer_unlock_button.clicked.connect(self.controller.request_developer_admin_access)
        developer_layout.addRow(QLabel("Access"), self.developer_unlock_button)

        developer_shortcuts = QWidget()
        developer_shortcuts_layout = QHBoxLayout(developer_shortcuts)
        developer_shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        open_code_editor_button = QPushButton("Open Internal Code Editor")
        open_code_editor_button.clicked.connect(self.controller.open_internal_code_editor)
        developer_shortcuts_layout.addWidget(open_code_editor_button)
        developer_shortcuts_layout.addStretch(1)
        developer_layout.addRow(QLabel("Shortcuts"), developer_shortcuts)

        save_developer_button = QPushButton("Save Developer Settings")
        save_developer_button.clicked.connect(self.controller.save_current_developer_admin_settings)
        self.developer_save_button = save_developer_button
        developer_layout.addRow(QLabel("Actions"), save_developer_button)

        # Tab 2: Crash Reports
        crash_reports_tab = QWidget()
        crash_reports_layout = QVBoxLayout(crash_reports_tab)
        self.developer_tab_widget.addTab(crash_reports_tab, "Crash Reports")

        crash_select_layout = QHBoxLayout()
        crash_select_layout.setSpacing(10)
        crash_select_layout.addWidget(QLabel("Select Report:"))

        self.developer_crash_combo = QComboBox()
        self.developer_crash_combo.currentIndexChanged.connect(self._on_crash_report_selected)
        crash_select_layout.addWidget(self.developer_crash_combo, 1)

        self.developer_crash_refresh_button = QPushButton("Refresh")
        self.developer_crash_refresh_button.clicked.connect(self._on_crash_reports_refresh_clicked)
        crash_select_layout.addWidget(self.developer_crash_refresh_button)

        self.developer_crash_delete_button = QPushButton("Delete Report")
        self.developer_crash_delete_button.clicked.connect(self._on_crash_report_delete_clicked)
        crash_select_layout.addWidget(self.developer_crash_delete_button)

        crash_reports_layout.addLayout(crash_select_layout)

        self.developer_crash_viewer = QTextEdit()
        self.developer_crash_viewer.setReadOnly(True)
        self.developer_crash_viewer.setStyleSheet(
            "font-family: Consolas, Monaco, monospace; font-size: 9pt;"
        )
        crash_reports_layout.addWidget(self.developer_crash_viewer)

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

        self.security_admin_group.setVisible(True)
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
            self.set_theme_status(f"Current theme: {self.theme_combo.currentText() or '-'}")

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

    def set_theme_selection(self, theme_name):
        theme_name = str(theme_name or "").strip()
        self._suspend_change_signal = True
        try:
            selected_index = self.theme_combo.findData(theme_name)
            if selected_index >= 0:
                self.theme_combo.setCurrentIndex(selected_index)
        finally:
            self._suspend_change_signal = False

    def set_theme_status(self, message):
        if self.theme_status_label is not None:
            self.theme_status_label.setText(str(message or ""))
        self.status_bar.showMessage(str(message or ""), 4000)

    def set_export_directory(self, directory_path):
        self.export_directory_input.setText(str(directory_path or ""))

    def ask_for_export_directory(self):
        return str(QFileDialog.getExistingDirectory(self, "Select Export Directory", self.export_directory_input.text().strip() or "") or "").strip()

    def ask_for_runtime_path_directory(self, override_key):
        path_input = self.developer_runtime_override_inputs.get(override_key)
        start_dir = path_input.text().strip() if path_input is not None else ""
        return str(QFileDialog.getExistingDirectory(self, "Select Folder", start_dir) or "").strip()

    def set_runtime_path_override(self, override_key, directory_path):
        path_input = self.developer_runtime_override_inputs.get(override_key)
        if path_input is not None:
            path_input.setText(str(directory_path or ""))

    def set_downtime_code_rows(self, code_map):
        code_map = code_map if isinstance(code_map, dict) else {}

        def _code_sort_key(item):
            code_text = str(item[0])
            if code_text.isdigit():
                return (0, int(code_text))
            return (1, code_text)

        ordered_items = sorted(code_map.items(), key=_code_sort_key)
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
            self.security_password_required_checkbox.setChecked(bool(vault_record.get("password_required", True)))
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
        limit = self._security_state.get("role_limits", {}).get(role)
        if role in {"admin", "developer"}:
            self.security_password_required_checkbox.setChecked(True)
            self.security_password_required_checkbox.setEnabled(False)
            self.security_password_rule_label.setText(
                f"{role.title()} vaults require passwords. Rule: minimum 8 characters, at least 2 uppercase letters, and at least 1 special character from !@#$%^&*(). Limit: {limit}."
            )
            return

        self.security_password_required_checkbox.setEnabled(True)
        if self.security_password_required_checkbox.isChecked():
            self.security_password_rule_label.setText(
                f"General vault password is enabled. Rule: minimum 8 characters, at least 2 uppercase letters, and at least 1 special character from !@#$%^&*(). Limit: {limit}."
            )
        else:
            self.security_password_rule_label.setText(
                f"General vault password is disabled by policy. Limit: {limit}."
            )

    def apply_security_role_defaults(self):
        role = str(self.security_role_combo.currentText() or "general").strip().lower()
        defaults = set(self.security_role_defaults.get(role, []))
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
        can_manage_role_defaults = bool(state.get("can_manage_role_defaults", False))
        session_vault_name = str(state.get("session_vault_name") or "").strip()
        self.security_role_defaults = dict(state.get("role_defaults") or {})
        self._configure_security_rights(state.get("access_rights") or [])
        if can_manage_security:
            self.security_note_label.setText("Security administration is unlocked for the active admin or developer session.")
        else:
            self.security_note_label.setText(
                "Sign in with an admin or developer vault to edit vaults, passwords, and security mode from this page."
            )
        if self.security_form_container is not None:
            self.security_form_container.setEnabled(can_manage_security)
        if self.security_vault_list is not None:
            self.security_vault_list.setEnabled(can_manage_security)
        if self.security_non_secure_modules_list is not None:
            self.security_non_secure_modules_list.setEnabled(can_manage_security)
        if self.security_save_role_defaults_button is not None:
            self.security_save_role_defaults_button.setEnabled(can_manage_role_defaults)
        if self.security_unlock_button is not None:
            self.security_unlock_button.setText("Re-authenticate Security Admin" if can_manage_security else "Unlock Security Admin")

        self.security_non_secure_modules_list.clear()
        bypass_lookup = set(state.get("non_secure_bypass_modules") or [])
        for module_item in state.get("non_secure_bypass_options") or []:
            module_name = str(module_item.get("module_name") or "").strip()
            display_name = str(module_item.get("display_name") or module_name.replace("_", " ").title()).strip()
            if not module_name:
                continue
            list_item = QListWidgetItem(f"{display_name} ({module_name})")
            list_item.setData(0x0100, module_name)
            self.security_non_secure_modules_list.addItem(list_item)
            list_item.setSelected(module_name in bypass_lookup)

        self.security_vault_list.clear()
        preferred = str(preferred_name or "").strip() or session_vault_name
        selected_row = -1
        for index, vault in enumerate(state.get("vaults") or []):
            vault_name = str(vault.get("vault_name") or "")
            role = str(vault.get("role") or "general")
            enabled_text = "enabled" if bool(vault.get("enabled", True)) else "disabled"
            active_text = ", active" if session_vault_name and vault_name == session_vault_name else ""
            list_item = QListWidgetItem(f"{vault_name} ({role}, {enabled_text}{active_text})")
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

    def get_security_non_secure_bypass_modules(self):
        selected_names = []
        if self.security_non_secure_modules_list is None:
            return selected_names
        for item in self.security_non_secure_modules_list.selectedItems():
            module_name = str(item.data(0x0100) or "").strip()
            if module_name and module_name not in selected_names:
                selected_names.append(module_name)
        return selected_names

    def get_selected_security_role_name(self):
        return str(self.security_role_combo.currentText() or "general").strip().lower()

    def get_selected_security_rights(self):
        return [
            right_key
            for right_key, checkbox in self.security_rights_checkboxes.items()
            if checkbox.isChecked()
        ]

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
            "password_required": bool(self.security_password_required_checkbox.isChecked()),
            "rights": rights,
            "reset_password": bool(reset_password),
        }

    def configure_developer_admin_tools(self, state):
        state = state if isinstance(state, dict) else {}
        can_manage_developer = bool(state.get("can_manage_developer", False))
        session_summary = str(state.get("session_summary") or "Locked")
        section_mode = str(state.get("section_mode") or self.section_mode or "full")
        self._suspend_change_signal = True
        try:
            self.developer_access_label.setText(f"Session: {session_summary}")
            self.developer_repository_input.setText(str(state.get("update_repository_url") or ""))
            self.developer_advanced_checkbox.setChecked(bool(state.get("enable_advanced_dev_updates", False)))
            self.developer_trust_checkbox.setChecked(bool(state.get("enable_external_override_trust", False)))
            self.developer_status_label.setText(str(state.get("external_modules_status") or "-"))
            self.developer_runtime_settings_path_label.setText(str(state.get("runtime_settings_path") or "-"))
            self._set_runtime_path_override_state(state.get("runtime_path_overrides") or [], can_manage_developer)
            if section_mode == "developer_admin":
                note_text = "Privileged update and override settings now live on this dedicated page. Internal Code Editor remains a separate sidebar module."
            elif can_manage_developer:
                note_text = "Developer tools are unlocked for the active developer session."
            else:
                note_text = "Sign in from the File menu or Security tools to reveal privileged pages in the main navigation, including Internal Code Editor."
            self.developer_note_label.setText(note_text)
        finally:
            self._suspend_change_signal = False
        self.developer_repository_input.setEnabled(can_manage_developer)
        self.developer_advanced_checkbox.setEnabled(can_manage_developer)
        self.developer_trust_checkbox.setEnabled(can_manage_developer)
        if self.developer_save_button is not None:
            self.developer_save_button.setEnabled(can_manage_developer)
        if self.developer_unlock_button is not None:
            self.developer_unlock_button.setText("Re-authenticate Developer Tools" if can_manage_developer else "Unlock Developer Tools")

        # Update crash reports combobox
        crash_reports = state.get("crash_reports", [])
        self.developer_crash_combo.blockSignals(True)
        current_selection = self.developer_crash_combo.currentText()
        self.developer_crash_combo.clear()
        if crash_reports:
            self.developer_crash_combo.addItems(crash_reports)
            idx = self.developer_crash_combo.findText(current_selection)
            if idx >= 0:
                self.developer_crash_combo.setCurrentIndex(idx)
            else:
                self.developer_crash_combo.setCurrentIndex(0)
            self.developer_crash_delete_button.setEnabled(can_manage_developer)
        else:
            self.developer_crash_combo.addItem("No crash reports found")
            self.developer_crash_delete_button.setEnabled(False)
        self.developer_crash_combo.blockSignals(False)

        self.developer_crash_combo.setEnabled(can_manage_developer)
        self.developer_crash_viewer.setEnabled(can_manage_developer)
        self.developer_crash_refresh_button.setEnabled(can_manage_developer)

        # Load active report
        self._on_crash_report_selected()


    def get_runtime_path_overrides(self):
        return {
            key: widget.text().strip()
            for key, widget in self.developer_runtime_override_inputs.items()
            if widget is not None
        }

    def get_developer_admin_settings_values(self):
        runtime_overrides = self.get_runtime_path_overrides()
        return {
            "update_repository_url": self.developer_repository_input.text().strip(),
            "enable_advanced_dev_updates": bool(self.developer_advanced_checkbox.isChecked()),
            "enable_external_override_trust": bool(self.developer_trust_checkbox.isChecked()),
            "runtime_path_overrides": runtime_overrides,
        }

    def _set_runtime_path_override_state(self, runtime_path_overrides, can_manage_developer):
        entries = runtime_path_overrides if isinstance(runtime_path_overrides, list) else []
        entries_by_key = {
            str(entry.get("key") or "").strip(): entry
            for entry in entries
            if isinstance(entry, dict)
        }
        for override_key, path_input in self.developer_runtime_override_inputs.items():
            entry = entries_by_key.get(override_key, {})
            override_value = str(entry.get("override_value") or "")
            required_right = str(entry.get("required_right") or "")
            can_edit = bool(entry.get("can_edit", False) and can_manage_developer)
            default_path = str(entry.get("default_path") or "")
            effective_path = str(entry.get("effective_path") or "")

            path_input.setText(override_value)
            path_input.setEnabled(can_edit)

            access_label = self.developer_runtime_override_access_labels.get(override_key)
            if access_label is not None:
                if can_edit:
                    access_label.setText(f"Default: {default_path} | Effective: {effective_path}")
                else:
                    access_label.setText(
                        f"Read-only. Required right: {required_right or '-'} | Default: {default_path} | Effective: {effective_path}"
                    )

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
        password_text = str(first_value)
        special_characters = "!@#$%^&*()."
        if len(password_text) < 8:
            self.show_error(title, "Password must be at least 8 characters long.")
            return None
        if sum(1 for character in password_text if character.isupper()) < 2:
            self.show_error(title, "Password must include at least two uppercase letters.")
            return None
        if not any(character in special_characters for character in password_text):
            self.show_error(title, "Password must include at least one special character from !@#$%^&*().")
            return None
        return str(first_value)

    def ask_yes_no(self, title, message):
        response = QMessageBox.question(self, title, message)
        return response == QMessageBox.StandardButton.Yes

    def set_status(self, message):
        self.status_bar.showMessage(str(message or ""), 5000)

    def show_toast(self, title, message, _bootstyle=None):
        self.controller.show_toast(title, message, _bootstyle)

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

    def _on_crash_report_selected(self):
        filename = self.developer_crash_combo.currentText()
        if filename and filename != "No crash reports found":
            content = self.controller.load_crash_report(filename)
            self.developer_crash_viewer.setPlainText(content)
        else:
            self.developer_crash_viewer.setPlainText("No crash report selected.")

    def _on_crash_reports_refresh_clicked(self):
        self.controller.refresh_snapshot(initial=False)

    def _on_crash_report_delete_clicked(self):
        filename = self.developer_crash_combo.currentText()
        if not filename or filename == "No crash reports found":
            return
        if self.ask_yes_no("Delete Crash Report", f"Are you sure you want to delete {filename}?"):
            self.controller.delete_crash_report(filename)

