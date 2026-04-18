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
__version__ = "1.1.0"

try:
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtWidgets import (
        QAbstractItemView,
        QApplication,
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
    QDialog = None
    QDialogButtonBox = None
    QFileDialog = None
    QGridLayout = None
    QGroupBox = None
    QHBoxLayout = None
    QLabel = None
    QLineEdit = None
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
    def __init__(self, controller, payload, header_fields, production_fields, downtime_fields):
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not installed in the active Python environment.")
        super().__init__()
        self.controller = controller
        self.payload = dict(payload or {})
        self.header_fields = list(header_fields or [])
        self.production_fields = list(production_fields or [])
        self.downtime_fields = list(downtime_fields or [])
        self.header_widgets = {}
        self._build_ui()
        self._wire_live_edit_handlers()

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

    def _build_ui(self):
        self.setWindowTitle(str(self.payload.get("window_title") or "Production Log"))
        self.resize(1240, 840)

        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title_label = QLabel(str(self.payload.get("title") or "Production Log"))
        title_label.setObjectName("pageTitle")
        root_layout.addWidget(title_label)

        subtitle_label = QLabel(str(self.payload.get("subtitle") or "PyQt6 Production Log editor"))
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setWordWrap(True)
        root_layout.addWidget(subtitle_label)

        self.form_name_label = QLabel("Active Form: --")
        root_layout.addWidget(self.form_name_label)

        header_group = QGroupBox("Header", central_widget)
        header_layout = QGridLayout(header_group)
        header_layout.setHorizontalSpacing(12)
        header_layout.setVerticalSpacing(8)
        max_grid_col = 0
        for field in self.header_fields:
            field_id = str(field.get("id") or "").strip()
            if not field_id:
                continue
            label_text = str(field.get("label") or field_id.replace("_", " ").title())
            grid_row = int(field.get("row") or 0)
            grid_col = int(field.get("col") or 0)
            max_grid_col = max(max_grid_col, grid_col + 1)

            field_widget = QLineEdit(str(field.get("default") or ""), header_group)
            if bool(field.get("readonly")):
                field_widget.setReadOnly(True)
            configured_width = int(field.get("width") or 0)
            if configured_width > 0:
                # Approximate Tk character-width hints in pixels for Qt line edits.
                field_widget.setMinimumWidth(max(90, configured_width * 10))

            label_widget = QLabel(label_text + ":", header_group)
            self.header_widgets[field_id] = field_widget
            header_layout.addWidget(label_widget, grid_row, grid_col)
            header_layout.addWidget(field_widget, grid_row, grid_col + 1)

        for column_index in range(max_grid_col + 2):
            if column_index % 2 == 1:
                header_layout.setColumnStretch(column_index, 1)
            else:
                header_layout.setColumnStretch(column_index, 0)
        root_layout.addWidget(header_group)

        controls_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh Draft Lists")
        refresh_button.clicked.connect(self.controller.refresh_draft_lists)
        controls_layout.addWidget(refresh_button)

        save_button = QPushButton("Save Draft")
        save_button.clicked.connect(self.controller.save_draft)
        controls_layout.addWidget(save_button)

        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self.controller.calculate_metrics)
        controls_layout.addWidget(calculate_button)

        export_button = QPushButton("Export Excel")
        export_button.clicked.connect(self.controller.export_to_excel)
        controls_layout.addWidget(export_button)

        import_button = QPushButton("Import Excel")
        import_button.clicked.connect(self.controller.import_from_excel_ui)
        controls_layout.addWidget(import_button)

        pending_button = QPushButton("Pending Drafts")
        pending_button.clicked.connect(self.controller.open_pending_dialog)
        controls_layout.addWidget(pending_button)

        recovery_button = QPushButton("Recovery Snapshots")
        recovery_button.clicked.connect(self.controller.open_recovery_dialog)
        controls_layout.addWidget(recovery_button)

        open_pending_button = QPushButton("Open Pending Folder")
        open_pending_button.clicked.connect(self.controller.open_pending_folder)
        controls_layout.addWidget(open_pending_button)

        open_recovery_button = QPushButton("Open Recovery Folder")
        open_recovery_button.clicked.connect(self.controller.open_recovery_folder)
        controls_layout.addWidget(open_recovery_button)

        controls_layout.addStretch(1)
        root_layout.addLayout(controls_layout)

        production_title = QLabel("Production Rows")
        production_title.setObjectName("sectionTitle")
        root_layout.addWidget(production_title)

        self.production_table = QTableWidget()
        self.production_table.setColumnCount(len(self.production_fields))
        self.production_table.setHorizontalHeaderLabels(self._field_labels(self.production_fields))
        self.production_table.horizontalHeader().setStretchLastSection(True)
        self.production_table.verticalHeader().setVisible(False)
        self.production_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.production_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        root_layout.addWidget(self.production_table)

        production_actions = QHBoxLayout()
        add_production_button = QPushButton("Add Production Row")
        add_production_button.clicked.connect(self._add_production_row)
        production_actions.addWidget(add_production_button)
        remove_production_button = QPushButton("Remove Selected")
        remove_production_button.clicked.connect(self._remove_selected_production_row)
        production_actions.addWidget(remove_production_button)
        production_actions.addStretch(1)
        root_layout.addLayout(production_actions)

        downtime_title = QLabel("Downtime Rows")
        downtime_title.setObjectName("sectionTitle")
        root_layout.addWidget(downtime_title)

        self.downtime_table = QTableWidget()
        self.downtime_table.setColumnCount(len(self.downtime_fields))
        self.downtime_table.setHorizontalHeaderLabels(self._field_labels(self.downtime_fields))
        self.downtime_table.horizontalHeader().setStretchLastSection(True)
        self.downtime_table.verticalHeader().setVisible(False)
        self.downtime_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.downtime_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        root_layout.addWidget(self.downtime_table)

        downtime_actions = QHBoxLayout()
        add_downtime_button = QPushButton("Add Downtime Row")
        add_downtime_button.clicked.connect(self._add_downtime_row)
        downtime_actions.addWidget(add_downtime_button)
        remove_downtime_button = QPushButton("Remove Selected")
        remove_downtime_button.clicked.connect(self._remove_selected_downtime_row)
        downtime_actions.addWidget(remove_downtime_button)
        downtime_actions.addStretch(1)
        root_layout.addLayout(downtime_actions)

        self.draft_status_label = QLabel("Drafts: 0 | Recovery: 0 | Latest: None")
        self.draft_status_label.setObjectName("mutedLabel")
        root_layout.addWidget(self.draft_status_label)

        metrics_layout = QHBoxLayout()
        self.efficiency_label = QLabel("EFF%: 0.00")
        self.ghost_label = QLabel("Ghost Time: 0 min")
        metrics_layout.addWidget(self.efficiency_label)
        metrics_layout.addWidget(self.ghost_label)
        metrics_layout.addStretch(1)
        root_layout.addLayout(metrics_layout)

        self.setCentralWidget(central_widget)
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Production Log Qt window ready.", 5000)

    def _wire_live_edit_handlers(self):
        for widget in self.header_widgets.values():
            try:
                widget.textChanged.connect(self._queue_live_recalculate)
            except Exception:
                continue
        try:
            self.production_table.itemChanged.connect(self._queue_live_recalculate)
        except Exception:
            pass
        try:
            self.downtime_table.itemChanged.connect(self._queue_live_recalculate)
        except Exception:
            pass

    def _queue_live_recalculate(self, *_args):
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

    def _set_table_rows(self, table, field_configs, rows):
        table.blockSignals(True)
        table.setRowCount(0)
        for row_data in rows:
            self._append_row(table, field_configs, row_data=row_data)
        table.blockSignals(False)

    def _append_row(self, table, field_configs, row_data=None):
        row_data = dict(row_data or {})
        row_index = table.rowCount()
        table.insertRow(row_index)
        for column_index, field in enumerate(field_configs):
            field_id = str(field.get("id") or "").strip()
            item_value = str(row_data.get(field_id, field.get("default") or ""))
            table_item = QTableWidgetItem(item_value)
            if bool(field.get("readonly")) or bool(field.get("derived")):
                table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row_index, column_index, table_item)

    def _field_index_map(self, field_configs):
        mapping = {}
        for column_index, field in enumerate(field_configs):
            field_id = str(field.get("id") or "").strip()
            if field_id:
                mapping[field_id] = column_index
        return mapping

    def set_table_field_value(self, section_name, row_index, field_id, value):
        if section_name == "production":
            table = self.production_table
            field_map = self._field_index_map(self.production_fields)
        else:
            table = self.downtime_table
            field_map = self._field_index_map(self.downtime_fields)
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

    def ask_import_file_path(self):
        file_path, _selected = QFileDialog.getOpenFileName(
            self,
            "Import Production Log Workbook",
            "",
            "Excel Workbooks (*.xlsx *.xlsm *.xls);;All Files (*)",
        )
        return str(file_path or "").strip()

    def set_metrics(self, efficiency, ghost_minutes):
        self.efficiency_label.setText(f"EFF%: {float(efficiency):.2f}")
        self.ghost_label.setText(f"Ghost Time: {int(ghost_minutes)} min")

    def _collect_rows(self, table, field_configs):
        rows = []
        for row_index in range(table.rowCount()):
            row_payload = {}
            has_content = False
            for column_index, field in enumerate(field_configs):
                field_id = str(field.get("id") or "").strip()
                if not field_id:
                    continue
                item = table.item(row_index, column_index)
                value = str(item.text()) if item is not None else ""
                row_payload[field_id] = value
                if value.strip():
                    has_content = True
            if has_content:
                rows.append(row_payload)
        return rows

    def collect_form_data(self):
        header_payload = {}
        for field_id, widget in self.header_widgets.items():
            header_payload[field_id] = str(widget.text())
        return {
            "header": header_payload,
            "production": self._collect_rows(self.production_table, self.production_fields),
            "downtime": self._collect_rows(self.downtime_table, self.downtime_fields),
        }

    def set_form_data(self, header_payload, production_rows, downtime_rows):
        header_payload = dict(header_payload or {})
        for field_id, widget in self.header_widgets.items():
            widget.blockSignals(True)
            widget.setText(str(header_payload.get(field_id, "")))
            widget.blockSignals(False)
        self._set_table_rows(self.production_table, self.production_fields, list(production_rows or []))
        self._set_table_rows(self.downtime_table, self.downtime_fields, list(downtime_rows or []))

    def set_form_name(self, form_name):
        self.form_name_label.setText(f"Active Form: {str(form_name or '--')}")

    def set_draft_status(self, pending_count, recovery_count, latest_name):
        latest_text = str(latest_name or "None")
        self.draft_status_label.setText(
            f"Drafts: {int(pending_count)} | Recovery: {int(recovery_count)} | Latest: {latest_text}"
        )

    def _add_production_row(self):
        self._append_row(self.production_table, self.production_fields)

    def _remove_selected_production_row(self):
        selected_rows = self.production_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        self.production_table.removeRow(int(selected_rows[0].row()))

    def _add_downtime_row(self):
        self._append_row(self.downtime_table, self.downtime_fields)

    def _remove_selected_downtime_row(self):
        selected_rows = self.downtime_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        self.downtime_table.removeRow(int(selected_rows[0].row()))

    def show_pending_dialog(self, pending_drafts):
        dialog = QDialog(self)
        dialog.setWindowTitle("Pending Drafts")
        dialog.resize(900, 420)
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
                self.show_info("Production Log", "Select a pending draft first.")
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
        dialog.resize(900, 440)
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
                self.show_info("Production Log", "Select a recovery snapshot first.")
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

    def ask_yes_no(self, title, message):
        return QMessageBox.question(
            self,
            str(title or "Confirm"),
            str(message or ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

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
