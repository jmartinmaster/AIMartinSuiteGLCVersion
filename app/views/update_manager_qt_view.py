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
__module_name__ = "Update Manager Qt View"
__version__ = "2.5.1"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QAbstractItemView,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

PYQT6_AVAILABLE = True


def is_update_manager_qt_runtime_available():
    return PYQT6_AVAILABLE


def get_option_category(option):
    from app.module_registry import ModuleRegistry
    try:
        registry = ModuleRegistry()
        reg_mod = registry.get_module(option["key"])
        allowed_roles = reg_mod.get("allowed_roles", [])
        if "admin" in allowed_roles:
            return "admin"
        elif "developer" in allowed_roles:
            return "dev"
        elif reg_mod.get("navigation_visible"):
            return "user facing"
        else:
            return "back end"
    except Exception:
        # Fallback for options not in the module registry (like JSON config payloads)
        key = option.get("key", "")
        if key == "production_log_calculations":
            return "dev"
        elif key in ("layout_config", "form_definitions", "rates"):
            return "user facing"
        return "back end"


class UpdateManagerQtView(QMainWindow):
    def __init__(self, controller, payload, parent_widget=None):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__(parent_widget)
        self.controller = controller
        self.payload = dict(payload or {})
        self.theme_tokens = dict(self.payload.get("theme_tokens") or {})
        self.embedded = parent_widget is not None
        self.value_labels = {}
        self.target_name_label = None
        self.runtime_status_value_label = None
        self.payload_tabs = None
        self.tab_combos = {}
        self.payload_name_label = None
        self.payload_path_label = None
        self.payload_local_version_label = None
        self.payload_remote_version_label = None
        self.payload_status_label = None
        self.payload_checksum_label = None
        self.payload_note_label = None
        self.documentation_tracked_label = None
        self.documentation_remote_state_label = None
        self.documentation_status_label = None
        self.documentation_note_label = None
        self.advanced_enabled_label = None
        self.advanced_phase_label = None
        self.advanced_detail_label = None
        self.advanced_recovery_label = None
        self.advanced_build_log_label = None
        self.note_text = None
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
        self.setWindowTitle(str(self.payload.get("window_title") or "Update Manager"))
        if self.embedded:
            self.setMinimumSize(0, 0)
        else:
            self._fit_window_to_screen(1120, 820)

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

        title_label = QLabel(str(self.payload.get("title") or "Update Manager"))
        title_label.setObjectName("pageTitle")
        content_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Manage stable releases, payload restores, and advanced source updates."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        content_layout.addWidget(subtitle_label)

        # Relocated controls layout (Check Repository, Apply Stable Updates, Refresh Status buttons)
        controls = QHBoxLayout()
        check_button = QPushButton("Check Repository")
        check_button.clicked.connect(self.controller.check_for_updates)
        check_button.setAccessibleName("Check updates repository")
        check_button.setAccessibleDescription("Compares local release version with the remote updates repository.")
        controls.addWidget(check_button)
        apply_button = QPushButton("Apply Stable Updates")
        apply_button.clicked.connect(self.controller.apply_updates)
        apply_button.setAccessibleName("Apply stable updates")
        apply_button.setAccessibleDescription("Downloads and installs the latest stable release updates.")
        controls.addWidget(apply_button)
        downgrade_button = QPushButton("Downgrade to Stable")
        downgrade_button.clicked.connect(self.controller.apply_stable_downgrade)
        downgrade_button.setAccessibleName("Downgrade to stable")
        downgrade_button.setAccessibleDescription(
            "Downloads and installs the repository stable release even when it is older than the local build."
        )
        controls.addWidget(downgrade_button)
        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self.controller.refresh_snapshot)
        refresh_button.setAccessibleName("Refresh update manager status")
        refresh_button.setAccessibleDescription("Reloads local release versions and repository cache snapshot.")
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        content_layout.addLayout(controls)

        summary_group = QGroupBox("Current Update Status")
        summary_form = QFormLayout(summary_group)

        self.target_name_label = QLabel("Dispatcher Core")
        self.target_name_label.setObjectName("pageTitle")
        self.target_name_label.setWordWrap(True)
        summary_form.addRow(QLabel("Release Target"), self.target_name_label)

        self.local_version_label = QLabel("-")
        self.local_version_label.setWordWrap(True)
        self.value_labels["local_version"] = self.local_version_label
        summary_form.addRow(QLabel("Local Version"), self.local_version_label)

        self.repository_version_label = QLabel("-")
        self.repository_version_label.setWordWrap(True)
        self.value_labels["remote_version"] = self.repository_version_label
        summary_form.addRow(QLabel("Repository Version"), self.repository_version_label)

        self.status_label = QLabel("-")
        self.status_label.setWordWrap(True)
        self.value_labels["status"] = self.status_label
        summary_form.addRow(QLabel("Status"), self.status_label)

        # Collapsible Tree Widget for detailed/diagnostic information
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(2)
        self.tree_widget.setHeaderLabels(["Property", "Value"])
        self.tree_widget.setColumnWidth(0, 240)
        self.tree_widget.setMinimumHeight(64)
        self.tree_widget.setAccessibleName("Update manager diagnostics tree")
        self.tree_widget.setAccessibleDescription("Detailed overview of branch, repository configuration, job phases, and advanced logs.")

        # Root category item
        root_item = QTreeWidgetItem(self.tree_widget, ["Detailed Diagnostics & Configuration", ""])
        
        # Categories
        repo_cat = QTreeWidgetItem(root_item, ["Repository & Configuration", ""])
        job_cat = QTreeWidgetItem(root_item, ["Job Status & Summary", ""])
        payload_cat = QTreeWidgetItem(root_item, ["Modules & Documentation Overview", ""])
        adv_cat = QTreeWidgetItem(root_item, ["Advanced Source Operations", ""])

        self.tree_items = {
            "repository": QTreeWidgetItem(repo_cat, ["Repository", "-"]),
            "branch": QTreeWidgetItem(repo_cat, ["Branch", "-"]),
            "stable_artifact": QTreeWidgetItem(repo_cat, ["Stable Artifact", "-"]),
            "updates_configured": QTreeWidgetItem(repo_cat, ["Updates Configured", "-"]),
            "advanced_channel_enabled": QTreeWidgetItem(repo_cat, ["Advanced Channel Enabled", "-"]),
            "configuration_note": QTreeWidgetItem(repo_cat, ["Configuration Note", "-"]),
            
            "job_phase": QTreeWidgetItem(job_cat, ["Job Phase", "-"]),
            "job_detail": QTreeWidgetItem(job_cat, ["Job Detail", "-"]),
            "summary_note": QTreeWidgetItem(job_cat, ["Stable Summary", "-"]),
            
            "module_payloads": QTreeWidgetItem(payload_cat, ["Tracked Module Payloads", "-"]),
            "module_payload_selected": QTreeWidgetItem(payload_cat, ["Selected Module Payload", "-"]),
            "module_payload_path": QTreeWidgetItem(payload_cat, ["Selected Payload Path", "-"]),
            "documentation_payloads": QTreeWidgetItem(payload_cat, ["Tracked Documentation Payloads", "-"]),
            "documentation_remote_state": QTreeWidgetItem(payload_cat, ["Documentation Remote State", "-"]),
            "documentation_status": QTreeWidgetItem(payload_cat, ["Documentation Status", "-"]),
            "documentation_note": QTreeWidgetItem(payload_cat, ["Documentation Note", "-"]),
            
            "advanced_source_phase": QTreeWidgetItem(adv_cat, ["Advanced Source Phase", "-"]),
            "advanced_source_detail": QTreeWidgetItem(adv_cat, ["Advanced Source Detail", "-"]),
            "advanced_recovery_available": QTreeWidgetItem(adv_cat, ["Advanced Recovery Available", "-"]),
            "advanced_build_log": QTreeWidgetItem(adv_cat, ["Advanced Build Log", "-"]),
        }

        # Add tree items to value_labels
        for key, item in self.tree_items.items():
            self.value_labels[key] = item

        # Expand child categories, collapse root by default
        self.tree_widget.expandItem(repo_cat)
        self.tree_widget.expandItem(job_cat)
        self.tree_widget.expandItem(payload_cat)
        self.tree_widget.expandItem(adv_cat)
        self.tree_widget.collapseItem(root_item)

        # Wire up dynamic height adjustments
        self.tree_widget.itemExpanded.connect(self._adjust_tree_height)
        self.tree_widget.itemCollapsed.connect(self._adjust_tree_height)

        summary_form.addRow(QLabel("Diagnostics"), self.tree_widget)

        content_layout.addWidget(summary_group)

        # Module Payload Updates Group with Tab Widget
        payload_group = QGroupBox("Module Payload Updates")
        payload_layout = QFormLayout(payload_group)

        self.payload_tabs = QTabWidget()
        self.payload_tabs.setAccessibleName("Module payload updates tabs")
        self.payload_tabs.setAccessibleDescription("Switch categories between user-facing, admin, dev, and backend modules.")
        self.tab_combos = {}
        categories = [
            ("user facing", "User Facing Modules"),
            ("admin", "Admin Modules"),
            ("dev", "Dev Modules"),
            ("back end", "Back End Modules")
        ]
        for cat_key, cat_name in categories:
            tab_widget = QWidget()
            tab_layout = QHBoxLayout(tab_widget)
            tab_layout.setContentsMargins(0, 4, 0, 4)
            
            combo = QComboBox()
            combo.currentIndexChanged.connect(self._on_payload_selection_changed)
            combo.setAccessibleName(f"Select {cat_name} payload")
            combo.setAccessibleDescription(f"Select a specific module payload within the {cat_name} section.")
            tab_layout.addWidget(QLabel("Select Payload:"))
            tab_layout.addWidget(combo, 1)
            
            self.payload_tabs.addTab(tab_widget, cat_name)
            self.tab_combos[cat_key] = combo
            
        self.payload_tabs.currentChanged.connect(self._on_tab_changed)
        payload_layout.addRow(QLabel("Payload Sections"), self.payload_tabs)

        self.payload_name_label = QLabel("No payload selected")
        self.payload_name_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Module"), self.payload_name_label)

        self.payload_path_label = QLabel("Payload updates are not available.")
        self.payload_path_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Path"), self.payload_path_label)

        self.payload_local_version_label = QLabel("Unknown")
        self.payload_local_version_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Local State"), self.payload_local_version_label)

        self.payload_remote_version_label = QLabel("Not checked")
        self.payload_remote_version_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Repository State"), self.payload_remote_version_label)

        self.payload_status_label = QLabel("Pending")
        self.payload_status_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Status"), self.payload_status_label)

        self.payload_governance_label = QLabel("-")
        self.payload_governance_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Governance"), self.payload_governance_label)

        self.payload_checksum_label = QLabel("Not checked")
        self.payload_checksum_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Checksum"), self.payload_checksum_label)

        self.payload_note_label = QLabel("Select a payload to compare against the repository.")
        self.payload_note_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Note"), self.payload_note_label)

        payload_actions = QHBoxLayout()
        check_payload_button = QPushButton("Check Selected Payload")
        check_payload_button.clicked.connect(self.controller.check_module_payload_update)
        check_payload_button.setAccessibleName("Check selected module payload")
        check_payload_button.setAccessibleDescription("Check if the selected module has an override update in the repository.")
        payload_actions.addWidget(check_payload_button)
        apply_payload_button = QPushButton("Apply Selected Payload")
        apply_payload_button.clicked.connect(self.controller.apply_module_payload_update)
        apply_payload_button.setAccessibleName("Apply selected module payload")
        apply_payload_button.setAccessibleDescription("Downloads and copies the override version for the selected module.")
        payload_actions.addWidget(apply_payload_button)
        apply_all_payload_button = QPushButton("Apply All Payloads")
        apply_all_payload_button.clicked.connect(self.controller.apply_all_module_payload_updates)
        apply_all_payload_button.setAccessibleName("Apply all module payloads")
        apply_all_payload_button.setAccessibleDescription("Downloads and copies all available override modules from the repository.")
        payload_actions.addWidget(apply_all_payload_button)
        payload_actions.addStretch(1)
        payload_layout.addRow(QLabel("Actions"), payload_actions)

        content_layout.addWidget(payload_group)

        # Documentation Updates
        documentation_group = QGroupBox("Documentation Updates")
        documentation_layout = QFormLayout(documentation_group)

        self.documentation_tracked_label = QLabel("0 tracked file(s)")
        self.documentation_tracked_label.setWordWrap(True)
        documentation_layout.addRow(QLabel("Tracked Files"), self.documentation_tracked_label)

        self.documentation_remote_state_label = QLabel("Not checked")
        self.documentation_remote_state_label.setWordWrap(True)
        documentation_layout.addRow(QLabel("Repository State"), self.documentation_remote_state_label)

        self.documentation_status_label = QLabel("Pending")
        self.documentation_status_label.setWordWrap(True)
        documentation_layout.addRow(QLabel("Status"), self.documentation_status_label)

        self.documentation_note_label = QLabel("Check and apply grouped documentation restores from the repository.")
        self.documentation_note_label.setWordWrap(True)
        documentation_layout.addRow(QLabel("Note"), self.documentation_note_label)

        documentation_actions = QHBoxLayout()
        check_documentation_button = QPushButton("Check Documentation Restores")
        check_documentation_button.clicked.connect(self.controller.check_documentation_payload_updates)
        check_documentation_button.setAccessibleName("Check documentation updates")
        check_documentation_button.setAccessibleDescription("Checks for updated help documents or user guides in the repository.")
        documentation_actions.addWidget(check_documentation_button)
        apply_documentation_button = QPushButton("Apply Documentation Restores")
        apply_documentation_button.clicked.connect(self.controller.apply_documentation_payload_updates)
        apply_documentation_button.setAccessibleName("Apply documentation restores")
        apply_documentation_button.setAccessibleDescription("Restores all tracked help files to match the latest repository copy.")
        documentation_actions.addWidget(apply_documentation_button)
        documentation_actions.addStretch(1)
        documentation_layout.addRow(QLabel("Actions"), documentation_actions)
        content_layout.addWidget(documentation_group)

        # Advanced Source Operations
        advanced_group = QGroupBox("Advanced Source Operations")
        advanced_layout = QFormLayout(advanced_group)

        self.advanced_enabled_label = QLabel("No")
        self.advanced_enabled_label.setWordWrap(True)
        advanced_layout.addRow(QLabel("Channel Enabled"), self.advanced_enabled_label)

        self.advanced_phase_label = QLabel("idle")
        self.advanced_phase_label.setWordWrap(True)
        advanced_layout.addRow(QLabel("Source Phase"), self.advanced_phase_label)

        self.advanced_detail_label = QLabel("No update job is running.")
        self.advanced_detail_label.setWordWrap(True)
        advanced_layout.addRow(QLabel("Source Detail"), self.advanced_detail_label)

        self.advanced_recovery_label = QLabel("No")
        self.advanced_recovery_label.setWordWrap(True)
        advanced_layout.addRow(QLabel("Recovery Available"), self.advanced_recovery_label)

        self.advanced_build_log_label = QLabel("Not available")
        self.advanced_build_log_label.setWordWrap(True)
        advanced_layout.addRow(QLabel("Build Log"), self.advanced_build_log_label)

        advanced_actions = QHBoxLayout()
        start_advanced_button = QPushButton("Start Advanced Source Update")
        start_advanced_button.clicked.connect(self.controller.start_advanced_dev_update)
        start_advanced_button.setAccessibleName("Start advanced source update")
        start_advanced_button.setAccessibleDescription("Initiates an advanced dev update job to rebuild binaries from source.")
        advanced_actions.addWidget(start_advanced_button)
        retry_source_button = QPushButton("Retry Source Job")
        retry_source_button.clicked.connect(self.controller.retry_source_job)
        retry_source_button.setAccessibleName("Retry source job")
        retry_source_button.setAccessibleDescription("Retries the current step in the advanced dev updates pipeline.")
        advanced_actions.addWidget(retry_source_button)
        cleanup_source_button = QPushButton("Cleanup Source Job")
        cleanup_source_button.clicked.connect(self.controller.cleanup_source_job)
        cleanup_source_button.setAccessibleName("Cleanup source job")
        cleanup_source_button.setAccessibleDescription("Cleans up temporary files from the advanced updates build workspace.")
        advanced_actions.addWidget(cleanup_source_button)
        open_log_button = QPushButton("Open Build Log")
        open_log_button.clicked.connect(self.controller.open_source_build_log)
        open_log_button.setAccessibleName("Open source build log")
        open_log_button.setAccessibleDescription("Opens the raw developer build outputs log text.")
        advanced_actions.addWidget(open_log_button)
        advanced_actions.addStretch(1)
        advanced_layout.addRow(QLabel("Actions"), advanced_actions)
        content_layout.addWidget(advanced_group)

        # Rollback Manager
        rollback_group = QGroupBox("Rollback Manager")
        rollback_layout = QVBoxLayout(rollback_group)
        
        rollback_layout.addWidget(QLabel("Select a versioned backup payload to verify and revert to:"))
        
        self.rollback_table = QTableWidget()
        self.rollback_table.setColumnCount(4)
        self.rollback_table.setHorizontalHeaderLabels(["Backup Time", "Module Name", "Backup Version", "Status"])
        self.rollback_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rollback_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rollback_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rollback_layout.addWidget(self.rollback_table, 1)
        
        rollback_btn_layout = QHBoxLayout()
        self.rollback_restore_btn = QPushButton("Restore Selected Backup")
        self.rollback_restore_btn.clicked.connect(self._on_rollback_restore_clicked)
        rollback_btn_layout.addWidget(self.rollback_restore_btn)
        
        self.rollback_refresh_btn = QPushButton("Refresh Backups List")
        self.rollback_refresh_btn.clicked.connect(self._on_rollback_refresh_clicked)
        rollback_btn_layout.addWidget(self.rollback_refresh_btn)
        rollback_btn_layout.addStretch(1)
        
        rollback_layout.addLayout(rollback_btn_layout)
        content_layout.addWidget(rollback_group)

        # Runtime Status
        runtime_status_group = QGroupBox("Runtime Status")
        runtime_status_layout = QVBoxLayout(runtime_status_group)
        self.runtime_status_value_label = QLabel("Ready")
        self.runtime_status_value_label.setWordWrap(True)
        runtime_status_layout.addWidget(self.runtime_status_value_label)
        
        self.progress_bar = QProgressBar(runtime_status_group)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        self.progress_bar.setAccessibleName("Update progress indicator")
        self.progress_bar.setAccessibleDescription("Visual indicator showing active download or build operations.")
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #e2e8f0; border-radius: 3px; border: none; }"
            "QProgressBar::chunk { background-color: #0f7c8f; border-radius: 3px; }"
        )
        runtime_status_layout.addWidget(self.progress_bar)
        
        content_layout.addWidget(runtime_status_group)

        content_layout.addStretch(1)

        scroll_area.setWidget(scroll_content)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self._adjust_tree_height()

    def _adjust_tree_height(self):
        visible_count = 0
        def count_visible(item):
            nonlocal visible_count
            visible_count += 1
            if item.isExpanded():
                for i in range(item.childCount()):
                    count_visible(item.child(i))
                    
        for i in range(self.tree_widget.topLevelItemCount()):
            count_visible(self.tree_widget.topLevelItem(i))
            
        row_height = 24
        header_height = 30
        margin = 10
        total_height = header_height + (visible_count * row_height) + margin
        total_height = max(64, min(total_height, 450))
        self.tree_widget.setFixedHeight(total_height)

    def _on_tab_changed(self, index):
        cat_keys = ["user facing", "admin", "dev", "back end"]
        if 0 <= index < len(cat_keys):
            combo = self.tab_combos[cat_keys[index]]
            payload_key = str(combo.currentData() or "").strip()
            if payload_key:
                self.controller.on_payload_selection_changed(payload_key)

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

    def render_snapshot(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        self.target_name_label.setText(str(snapshot.get("target_name") or "Dispatcher Core"))
        for key, widget in self.value_labels.items():
            val_str = str(snapshot.get(key, "-"))
            if isinstance(widget, QLabel):
                widget.setText(val_str)
            elif isinstance(widget, QTreeWidgetItem):
                widget.setText(1, val_str)
                widget.setToolTip(1, val_str)
        if self.note_text is not None:
            self.note_text.setPlainText(str(snapshot.get("note") or ""))
        self.payload_name_label.setText(str(snapshot.get("module_payload_selected") or "No payload selected"))
        self.payload_path_label.setText(str(snapshot.get("module_payload_path") or "Payload updates are not available."))
        self.payload_local_version_label.setText(str(snapshot.get("module_payload_local_version") or "Unknown"))
        self.payload_remote_version_label.setText(str(snapshot.get("module_payload_remote_version") or "Not checked"))
        self.payload_status_label.setText(str(snapshot.get("module_payload_status") or "Pending"))
        self.payload_checksum_label.setText(str(snapshot.get("module_payload_checksum_status") or "Not checked"))
        self.payload_note_label.setText(str(snapshot.get("module_payload_note") or "Select a payload to compare against the repository."))
        self.documentation_tracked_label.setText(str(snapshot.get("documentation_payloads") or "0 tracked file(s)"))
        self.documentation_remote_state_label.setText(str(snapshot.get("documentation_remote_state") or "Not checked"))
        self.documentation_status_label.setText(str(snapshot.get("documentation_status") or "Pending"))
        self.documentation_note_label.setText(str(snapshot.get("documentation_note") or "Check and apply grouped documentation restores from the repository."))
        self.advanced_enabled_label.setText(str(snapshot.get("advanced_channel_enabled") or "No"))
        self.advanced_phase_label.setText(str(snapshot.get("advanced_source_phase") or "idle"))
        self.advanced_detail_label.setText(str(snapshot.get("advanced_source_detail") or "No update job is running."))
        self.advanced_recovery_label.setText(str(snapshot.get("advanced_recovery_available") or "No"))
        self.advanced_build_log_label.setText(str(snapshot.get("advanced_build_log") or "Not available"))
        runtime_status = str(snapshot.get("runtime_status") or "Ready")
        self.runtime_status_value_label.setText(runtime_status)
        self.status_bar.showMessage(runtime_status, 4000)

        status_lower = runtime_status.lower()
        is_running = False
        if (
            "downloading" in status_lower
            or "building" in status_lower
            or "rebuild" in status_lower
            or "preparing" in status_lower
            or "extracting" in status_lower
            or "staging" in status_lower
            or "installing" in status_lower
            or snapshot.get("advanced_source_phase", "idle") not in {"idle", "failed", "source_complete", "complete"}
        ):
            is_running = True
        self.progress_bar.setVisible(is_running)

    def set_module_payload_options(self, options, selected_key):
        options = options if isinstance(options, list) else []
        selected_key = str(selected_key or "")
        
        self.payload_tabs.blockSignals(True)
        for combo in self.tab_combos.values():
            combo.blockSignals(True)
            
        try:
            for combo in self.tab_combos.values():
                combo.clear()
                
            categorized_options = {
                "user facing": [],
                "admin": [],
                "dev": [],
                "back end": []
            }
            
            for option in options:
                cat = get_option_category(option)
                categorized_options[cat].append(option)
                
            for cat_key, cat_options in categorized_options.items():
                combo = self.tab_combos[cat_key]
                selected_index = -1
                for index, option in enumerate(cat_options):
                    key = str(option.get("key") or "").strip()
                    display = str(option.get("display") or key)
                    combo.addItem(display, key)
                    if key == selected_key:
                        selected_index = index
                if selected_index < 0 and combo.count() > 0:
                    selected_index = 0
                if selected_index >= 0:
                    combo.setCurrentIndex(selected_index)
                    
            selected_cat = None
            for option in options:
                if str(option.get("key") or "").strip() == selected_key:
                    selected_cat = get_option_category(option)
                    break
            
            if selected_cat is not None:
                cat_keys = ["user facing", "admin", "dev", "back end"]
                if selected_cat in cat_keys:
                    self.payload_tabs.setCurrentIndex(cat_keys.index(selected_cat))
        finally:
            self.payload_tabs.blockSignals(False)
            for combo in self.tab_combos.values():
                combo.blockSignals(False)

    def _on_payload_selection_changed(self):
        index = self.payload_tabs.currentIndex()
        cat_keys = ["user facing", "admin", "dev", "back end"]
        if 0 <= index < len(cat_keys):
            combo = self.tab_combos[cat_keys[index]]
            payload_key = str(combo.currentData() or "").strip()
            if payload_key:
                self.controller.on_payload_selection_changed(payload_key)

    def ask_yes_no(self, title, message):
        response = QMessageBox.question(self, title, message)
        return response == QMessageBox.StandardButton.Yes

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

    def _on_rollback_restore_clicked(self):
        selected_ranges = self.rollback_table.selectedRanges()
        if not selected_ranges:
            self.show_info("Rollback Manager", "Please select a backup to restore.")
            return
        row = selected_ranges[0].topRow()
        backup_dir = self.rollback_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        version = self.rollback_table.item(row, 2).text()
        if self.ask_yes_no("Restore Backup", f"Are you sure you want to revert to the backup version {version}? This will overwrite current files and trigger an app restart."):
            self.controller.restore_rollback(backup_dir)

    def _on_rollback_refresh_clicked(self):
        self.controller.refresh_rollback_list()

    def refresh_rollback_list(self, rollback_candidates):
        self.rollback_table.setRowCount(0)
        self.rollback_table.setRowCount(len(rollback_candidates))
        for row_idx, item in enumerate(rollback_candidates):
            time_str = item.get("timestamp_str") or item.get("dir_name")
            module_name = item.get("module_name") or "-"
            version = item.get("version") or "Unknown"
            status = "Verified" if item.get("verified") else "Mismatch/Unsigned"
            
            time_cell = QTableWidgetItem(time_str)
            time_cell.setData(Qt.ItemDataRole.UserRole, item.get("path"))
            
            self.rollback_table.setItem(row_idx, 0, time_cell)
            self.rollback_table.setItem(row_idx, 1, QTableWidgetItem(module_name))
            self.rollback_table.setItem(row_idx, 2, QTableWidgetItem(version))
            self.rollback_table.setItem(row_idx, 3, QTableWidgetItem(status))

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
