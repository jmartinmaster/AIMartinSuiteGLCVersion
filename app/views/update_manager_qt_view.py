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

__module_name__ = "Update Manager Qt View"
__version__ = "1.3.0"

try:
    from PyQt6.QtCore import QTimer
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
        QStatusBar,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QApplication = None
    QComboBox = None
    QFormLayout = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QStatusBar = None
    QTextEdit = None
    QVBoxLayout = None
    QWidget = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_update_manager_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_update_manager_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Update Manager Qt session payload must be a JSON object.")
    return payload


class UpdateManagerQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.value_labels = {}
        self.payload_selector = None
        self.payload_name_label = None
        self.payload_path_label = None
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Update Manager"))
        self.resize(1060, 720)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        title_label = QLabel(str(self.payload.get("title") or "Update Manager"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "Qt sidecar bootstrap for Update Manager migration."))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        summary_group = QGroupBox("Current Update Snapshot")
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

        root_layout.addWidget(summary_group)

        payload_group = QGroupBox("Module Payload Restores (Slice 2)")
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
        check_payload_button.clicked.connect(self.controller.request_check_module_payload)
        payload_actions.addWidget(check_payload_button)
        apply_payload_button = QPushButton("Apply Selected Payload")
        apply_payload_button.clicked.connect(self.controller.request_apply_module_payload)
        payload_actions.addWidget(apply_payload_button)
        apply_all_payload_button = QPushButton("Apply All Payloads")
        apply_all_payload_button.clicked.connect(self.controller.request_apply_all_module_payloads)
        payload_actions.addWidget(apply_all_payload_button)
        payload_actions.addStretch(1)
        payload_layout.addRow(QLabel("Actions"), payload_actions)

        root_layout.addWidget(payload_group)

        documentation_group = QGroupBox("Documentation Payload Restores (Slice 3)")
        documentation_layout = QFormLayout(documentation_group)
        documentation_actions = QHBoxLayout()
        check_documentation_button = QPushButton("Check Documentation Restores")
        check_documentation_button.clicked.connect(self.controller.request_check_documentation_payload_updates)
        documentation_actions.addWidget(check_documentation_button)
        apply_documentation_button = QPushButton("Apply Documentation Restores")
        apply_documentation_button.clicked.connect(self.controller.request_apply_documentation_payload_updates)
        documentation_actions.addWidget(apply_documentation_button)
        documentation_actions.addStretch(1)
        documentation_layout.addRow(QLabel("Actions"), documentation_actions)
        root_layout.addWidget(documentation_group)

        advanced_group = QGroupBox("Advanced Source Jobs & Recovery (Slice 4)")
        advanced_layout = QFormLayout(advanced_group)
        advanced_actions = QHBoxLayout()
        start_advanced_button = QPushButton("Start Advanced Source Update")
        start_advanced_button.clicked.connect(self.controller.request_start_advanced_source_update)
        advanced_actions.addWidget(start_advanced_button)
        retry_source_button = QPushButton("Retry Source Job")
        retry_source_button.clicked.connect(self.controller.request_retry_source_job)
        advanced_actions.addWidget(retry_source_button)
        cleanup_source_button = QPushButton("Cleanup Source Job")
        cleanup_source_button.clicked.connect(self.controller.request_cleanup_source_job)
        advanced_actions.addWidget(cleanup_source_button)
        open_log_button = QPushButton("Open Build Log")
        open_log_button.clicked.connect(self.controller.request_open_source_build_log)
        advanced_actions.addWidget(open_log_button)
        advanced_actions.addStretch(1)
        advanced_layout.addRow(QLabel("Actions"), advanced_actions)
        root_layout.addWidget(advanced_group)

        note_group = QGroupBox("Migration Note")
        note_layout = QVBoxLayout(note_group)
        self.note_text = QTextEdit()
        self.note_text.setReadOnly(True)
        note_layout.addWidget(self.note_text)
        root_layout.addWidget(note_group, 1)

        controls = QHBoxLayout()
        check_button = QPushButton("Check Repository")
        check_button.clicked.connect(self.controller.check_repository)
        controls.addWidget(check_button)
        apply_button = QPushButton("Apply Stable Updates")
        apply_button.clicked.connect(self.controller.request_apply_stable_updates)
        controls.addWidget(apply_button)
        refresh_button = QPushButton("Refresh Snapshot")
        refresh_button.clicked.connect(self.controller.refresh_snapshot)
        controls.addWidget(refresh_button)
        controls.addStretch(1)
        root_layout.addLayout(controls)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

    def render_snapshot(self, snapshot):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        for key, label_widget in self.value_labels.items():
            label_widget.setText(str(snapshot.get(key, "-")))
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

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_update_manager_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2

    from app.controllers.update_manager_qt_controller import UpdateManagerQtController

    session_payload = load_update_manager_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = UpdateManagerQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/update_manager_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_update_manager_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
