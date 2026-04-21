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
__version__ = "1.4.0"

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PYQT6_AVAILABLE = True


def is_update_manager_qt_runtime_available():
    return PYQT6_AVAILABLE


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
        self.payload_selector = None
        self.payload_name_label = None
        self.payload_path_label = None
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

        summary_group = QGroupBox("Current Update Status")
        summary_form = QFormLayout(summary_group)

        for key, label in [
            ("repository", "Repository"),
            ("branch", "Branch"),
            ("stable_artifact", "Stable Artifact"),
            ("updates_configured", "Updates Configured"),
            ("local_version", "Local Version"),
            ("remote_version", "Repository Version"),
            ("status", "Status"),
            ("job_phase", "Job Phase"),
            ("job_detail", "Job Detail"),
            ("summary_note", "Stable Summary"),
            ("module_payloads", "Tracked Module Payloads"),
            ("module_payload_selected", "Selected Module Payload"),
            ("module_payload_path", "Selected Payload Path"),
            ("documentation_payloads", "Tracked Documentation Payloads"),
            ("documentation_remote_state", "Documentation Remote State"),
            ("documentation_status", "Documentation Status"),
            ("documentation_note", "Documentation Note"),
            ("advanced_channel_enabled", "Advanced Channel Enabled"),
            ("advanced_source_phase", "Advanced Source Phase"),
            ("advanced_source_detail", "Advanced Source Detail"),
            ("advanced_recovery_available", "Advanced Recovery Available"),
            ("advanced_build_log", "Advanced Build Log"),
            ("configuration_note", "Configuration Note"),
        ]:
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.value_labels[key] = value_label
            summary_form.addRow(QLabel(label), value_label)

        content_layout.addWidget(summary_group)

        payload_group = QGroupBox("Module Payload Updates")
        payload_layout = QFormLayout(payload_group)

        self.payload_selector = QComboBox()
        self.payload_selector.currentIndexChanged.connect(self._on_payload_selection_changed)
        payload_layout.addRow(QLabel("Payload"), self.payload_selector)

        self.payload_name_label = QLabel("No payload selected")
        self.payload_name_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Module"), self.payload_name_label)

        self.payload_path_label = QLabel("Payload updates are not available.")
        self.payload_path_label.setWordWrap(True)
        payload_layout.addRow(QLabel("Path"), self.payload_path_label)

        payload_actions = QHBoxLayout()
        check_payload_button = QPushButton("Check Selected Payload")
        check_payload_button.clicked.connect(self.controller.check_module_payload_update)
        payload_actions.addWidget(check_payload_button)
        apply_payload_button = QPushButton("Apply Selected Payload")
        apply_payload_button.clicked.connect(self.controller.apply_module_payload_update)
        payload_actions.addWidget(apply_payload_button)
        apply_all_payload_button = QPushButton("Apply All Payloads")
        apply_all_payload_button.clicked.connect(self.controller.apply_all_module_payload_updates)
        payload_actions.addWidget(apply_all_payload_button)
        payload_actions.addStretch(1)
        payload_layout.addRow(QLabel("Actions"), payload_actions)

        content_layout.addWidget(payload_group)

        documentation_group = QGroupBox("Documentation Updates")
        documentation_layout = QFormLayout(documentation_group)
        documentation_actions = QHBoxLayout()
        check_documentation_button = QPushButton("Check Documentation Restores")
        check_documentation_button.clicked.connect(self.controller.check_documentation_payload_updates)
        documentation_actions.addWidget(check_documentation_button)
        apply_documentation_button = QPushButton("Apply Documentation Restores")
        apply_documentation_button.clicked.connect(self.controller.apply_documentation_payload_updates)
        documentation_actions.addWidget(apply_documentation_button)
        documentation_actions.addStretch(1)
        documentation_layout.addRow(QLabel("Actions"), documentation_actions)
        content_layout.addWidget(documentation_group)

        advanced_group = QGroupBox("Advanced Source Operations")
        advanced_layout = QFormLayout(advanced_group)
        advanced_actions = QHBoxLayout()
        start_advanced_button = QPushButton("Start Advanced Source Update")
        start_advanced_button.clicked.connect(self.controller.start_advanced_dev_update)
        advanced_actions.addWidget(start_advanced_button)
        retry_source_button = QPushButton("Retry Source Job")
        retry_source_button.clicked.connect(self.controller.retry_source_job)
        advanced_actions.addWidget(retry_source_button)
        cleanup_source_button = QPushButton("Cleanup Source Job")
        cleanup_source_button.clicked.connect(self.controller.cleanup_source_job)
        advanced_actions.addWidget(cleanup_source_button)
        open_log_button = QPushButton("Open Build Log")
        open_log_button.clicked.connect(self.controller.open_source_build_log)
        advanced_actions.addWidget(open_log_button)
        advanced_actions.addStretch(1)
        advanced_layout.addRow(QLabel("Actions"), advanced_actions)
        content_layout.addWidget(advanced_group)

        controls = QHBoxLayout()
        check_button = QPushButton("Check Repository")
        check_button.clicked.connect(self.controller.check_for_updates)
        controls.addWidget(check_button)
        apply_button = QPushButton("Apply Stable Updates")
        apply_button.clicked.connect(self.controller.apply_updates)
        controls.addWidget(apply_button)
        refresh_button = QPushButton("Refresh Status")
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

    def render_snapshot(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        for key, label_widget in self.value_labels.items():
            label_widget.setText(str(snapshot.get(key, "-")))
        if self.note_text is not None:
            self.note_text.setPlainText(str(snapshot.get("note") or ""))
        self.payload_name_label.setText(str(snapshot.get("module_payload_selected") or "No payload selected"))
        self.payload_path_label.setText(str(snapshot.get("module_payload_path") or "Payload updates are not available."))
        self.status_bar.showMessage("Update snapshot refreshed.", 4000)

    def set_module_payload_options(self, options, selected_key):
        options = options if isinstance(options, list) else []
        selected_key = str(selected_key or "")
        self.payload_selector.blockSignals(True)
        try:
            self.payload_selector.clear()
            selected_index = -1
            for index, option in enumerate(options):
                key = str(option.get("key") or "").strip()
                display = str(option.get("display") or key)
                self.payload_selector.addItem(display, key)
                if key == selected_key:
                    selected_index = index
            if selected_index < 0 and self.payload_selector.count() > 0:
                selected_index = 0
            if selected_index >= 0:
                self.payload_selector.setCurrentIndex(selected_index)
        finally:
            self.payload_selector.blockSignals(False)

    def _on_payload_selection_changed(self):
        payload_key = str(self.payload_selector.currentData() or "").strip()
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

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)
