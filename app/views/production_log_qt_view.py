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

__module_name__ = "Production Log Qt View"
__version__ = "1.0.0"

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    PYQT6_AVAILABLE = True
except ImportError:
    QAbstractItemView = None
    QApplication = None
    QFormLayout = None
    QHBoxLayout = None
    QLabel = None
    QMainWindow = object
    QMessageBox = None
    QPushButton = None
    QStatusBar = None
    QTableWidget = None
    QTableWidgetItem = None
    QVBoxLayout = None
    QWidget = None
    QTimer = None
    PYQT6_AVAILABLE = False


def is_production_log_qt_runtime_available():
    return PYQT6_AVAILABLE


def load_production_log_qt_session(session_path):
    with open(session_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Production Log Qt session payload must be a JSON object.")
    return payload


class ProductionLogQtView(QMainWindow):
    def __init__(self, controller, payload):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.value_labels = {}
        self.pending_drafts = []
        self.recovery_snapshots = []
        self._build_ui()

        self.command_timer = QTimer(self)
        self.command_timer.setInterval(700)
        self.command_timer.timeout.connect(self.controller.poll_commands)
        self.command_timer.start()

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Production Log"))
        self.resize(980, 620)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "Production Log"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(
            str(
                self.payload.get("subtitle")
                or "Qt sidecar bootstrap summary for Production Log while Tk workflow parity is in progress."
            )
        )
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        self.form_name_label = QLabel("Active Form: --")
        root_layout.addWidget(self.form_name_label)

        summary_form = QFormLayout()
        for key, title in (
            ("pending_draft_count", "Pending Drafts"),
            ("recovery_snapshot_count", "Recovery Snapshots"),
            ("latest_draft_name", "Latest Draft"),
            ("dt_code_count", "Downtime Codes"),
        ):
            value_label = QLabel("--")
            value_label.setObjectName("summaryValue")
            self.value_labels[key] = value_label
            summary_form.addRow(f"{title}:", value_label)
        root_layout.addLayout(summary_form)

        controls_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh Snapshot")
        refresh_button.clicked.connect(self.controller.refresh_snapshot)
        controls_layout.addWidget(refresh_button)

        open_pending_button = QPushButton("Open Pending Folder")
        open_pending_button.clicked.connect(self.controller.open_pending_folder)
        controls_layout.addWidget(open_pending_button)

        open_recovery_button = QPushButton("Open Recovery Folder")
        open_recovery_button.clicked.connect(self.controller.open_recovery_folder)
        controls_layout.addWidget(open_recovery_button)

        controls_layout.addStretch(1)
        root_layout.addLayout(controls_layout)

        pending_title = QLabel("Pending Drafts")
        pending_title.setObjectName("sectionTitle")
        root_layout.addWidget(pending_title)

        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(5)
        self.pending_table.setHorizontalHeaderLabels(["Draft", "Form", "Date", "Shift", "Saved At"])
        self.pending_table.horizontalHeader().setStretchLastSection(True)
        self.pending_table.verticalHeader().setVisible(False)
        self.pending_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.pending_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.pending_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pending_table.itemDoubleClicked.connect(self._on_pending_table_double_clicked)
        root_layout.addWidget(self.pending_table)

        pending_actions = QHBoxLayout()
        load_draft_button = QPushButton("Load Selected Draft")
        load_draft_button.clicked.connect(self._request_load_selected_draft)
        pending_actions.addWidget(load_draft_button)
        pending_actions.addStretch(1)
        root_layout.addLayout(pending_actions)

        recovery_title = QLabel("Recovery Snapshots")
        recovery_title.setObjectName("sectionTitle")
        root_layout.addWidget(recovery_title)

        self.recovery_table = QTableWidget()
        self.recovery_table.setColumnCount(5)
        self.recovery_table.setHorizontalHeaderLabels(["Snapshot", "Form", "Date", "Shift", "Saved At"])
        self.recovery_table.horizontalHeader().setStretchLastSection(True)
        self.recovery_table.verticalHeader().setVisible(False)
        self.recovery_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.recovery_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recovery_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.recovery_table.itemDoubleClicked.connect(self._on_recovery_table_double_clicked)
        root_layout.addWidget(self.recovery_table)

        recovery_actions = QHBoxLayout()
        open_recovery_button = QPushButton("Open Recovery Viewer")
        open_recovery_button.clicked.connect(self._request_open_recovery_viewer)
        recovery_actions.addWidget(open_recovery_button)
        open_snapshot_button = QPushButton("Open Recovery Viewer For Selected Snapshot")
        open_snapshot_button.clicked.connect(self._request_open_recovery_for_selected)
        recovery_actions.addWidget(open_snapshot_button)
        restore_snapshot_button = QPushButton("Restore Selected Snapshot To Host Form")
        restore_snapshot_button.clicked.connect(self._request_restore_selected_snapshot)
        recovery_actions.addWidget(restore_snapshot_button)
        recovery_actions.addStretch(1)
        root_layout.addLayout(recovery_actions)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Production Log Qt window ready.", 5000)

    def render_snapshot(self, snapshot):
        snapshot = dict(snapshot or {})
        self.form_name_label.setText(f"Active Form: {snapshot.get('form_name') or '--'}")
        for key, label in self.value_labels.items():
            label.setText(str(snapshot.get(key) or "--"))
        self.pending_drafts = list(snapshot.get("pending_drafts") or [])
        self.recovery_snapshots = list(snapshot.get("recovery_snapshots") or [])
        self._refresh_pending_table()
        self._refresh_recovery_table()
        self.status_bar.showMessage("Snapshot refreshed.", 5000)

    def _refresh_pending_table(self):
        self.pending_table.setRowCount(len(self.pending_drafts))
        for row_index, record in enumerate(self.pending_drafts):
            self.pending_table.setItem(row_index, 0, QTableWidgetItem(str(record.get("filename") or "")))
            self.pending_table.setItem(row_index, 1, QTableWidgetItem(str(record.get("form_name") or "")))
            self.pending_table.setItem(row_index, 2, QTableWidgetItem(str(record.get("date") or "")))
            self.pending_table.setItem(row_index, 3, QTableWidgetItem(str(record.get("shift") or "")))
            self.pending_table.setItem(row_index, 4, QTableWidgetItem(str(record.get("saved_at") or "")))

    def _refresh_recovery_table(self):
        self.recovery_table.setRowCount(len(self.recovery_snapshots))
        for row_index, record in enumerate(self.recovery_snapshots):
            self.recovery_table.setItem(row_index, 0, QTableWidgetItem(str(record.get("filename") or "")))
            self.recovery_table.setItem(row_index, 1, QTableWidgetItem(str(record.get("form_name") or "")))
            self.recovery_table.setItem(row_index, 2, QTableWidgetItem(str(record.get("date") or "")))
            self.recovery_table.setItem(row_index, 3, QTableWidgetItem(str(record.get("shift") or "")))
            self.recovery_table.setItem(row_index, 4, QTableWidgetItem(str(record.get("saved_at") or "")))

    def _selected_pending_record(self):
        selected_rows = self.pending_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        selected_index = int(selected_rows[0].row())
        if selected_index < 0 or selected_index >= len(self.pending_drafts):
            return None
        return self.pending_drafts[selected_index]

    def _selected_recovery_record(self):
        selected_rows = self.recovery_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        selected_index = int(selected_rows[0].row())
        if selected_index < 0 or selected_index >= len(self.recovery_snapshots):
            return None
        return self.recovery_snapshots[selected_index]

    def _request_load_selected_draft(self):
        record = self._selected_pending_record()
        if record is None:
            self.show_info("Production Log", "Select a pending draft first.")
            return
        self.controller.request_load_draft(record.get("path"))

    def _request_open_recovery_viewer(self):
        self.controller.request_open_recovery(snapshot_path=None)

    def _request_open_recovery_for_selected(self):
        record = self._selected_recovery_record()
        if record is None:
            self.show_info("Production Log", "Select a recovery snapshot first.")
            return
        self.controller.request_open_recovery(snapshot_path=record.get("path"))

    def _request_restore_selected_snapshot(self):
        record = self._selected_recovery_record()
        if record is None:
            self.show_info("Production Log", "Select a recovery snapshot first.")
            return
        self.controller.request_restore_snapshot(record.get("path"))

    def _on_pending_table_double_clicked(self, _item):
        self._request_load_selected_draft()

    def _on_recovery_table_double_clicked(self, _item):
        self._request_restore_selected_snapshot()

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def set_status(self, message):
        self.status_bar.showMessage(str(message), 5000)

    def closeEvent(self, event):
        self.controller.handle_close()
        super().closeEvent(event)


def run_production_log_qt_session(session_path):
    if not PYQT6_AVAILABLE:
        print("PyQt6 is not installed in the active Python environment.", file=sys.stderr)
        return 2

    from app.controllers.production_log_qt_controller import ProductionLogQtController

    session_payload = load_production_log_qt_session(session_path)
    application = create_qt_application(theme_tokens=session_payload.get("theme_tokens") or {})
    controller = ProductionLogQtController(session_payload)
    controller.show()
    return application.exec()


def main(argv=None):
    argv = list(argv or sys.argv)
    if len(argv) < 2:
        print("Usage: python app/views/production_log_qt_view.py <session.json>", file=sys.stderr)
        return 2
    return run_production_log_qt_session(argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
