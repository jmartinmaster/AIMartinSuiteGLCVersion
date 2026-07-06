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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QWidget,
)

__module_name__ = "Form Wizard View"
__version__ = "2.5.0"


class FormWizardQtView(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Form Creation Wizard")
        self.resize(850, 650)
        self.setMinimumSize(800, 600)
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Header progress label
        self.progress_label = QLabel(self)
        self.progress_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #555555;")
        self.main_layout.addWidget(self.progress_label)
        
        # Stacked pages
        self.stack = QStackedWidget(self)
        self.main_layout.addWidget(self.stack)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        self.back_button = QPushButton("Back", self)
        self.next_button = QPushButton("Next", self)
        self.cancel_button = QPushButton("Cancel", self)
        
        bottom_layout.addWidget(self.cancel_button)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.back_button)
        bottom_layout.addWidget(self.next_button)
        self.main_layout.addLayout(bottom_layout)
        
        # Build pages
        self._build_page_basic_info()
        self._build_page_sections()
        self._build_page_single_fields()
        self._build_page_repeating_fields()
        
        # Event hooks (to be connected by controller)
        self.next_clicked_hook = None
        self.back_clicked_hook = None
        self.cancel_clicked_hook = None
        self.browse_template_hook = None
        
        # Action button connections
        self.next_button.clicked.connect(self._on_next_clicked)
        self.back_button.clicked.connect(self._on_back_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
        self.update_navigation(0, 4)

    def update_navigation(self, current_index, total_pages):
        self.stack.setCurrentIndex(current_index)
        self.progress_label.setText(f"Step {current_index + 1} of {total_pages}: {self._get_step_name(current_index)}")
        self.back_button.setEnabled(current_index > 0)
        if current_index == total_pages - 1:
            self.next_button.setText("Create Form")
        else:
            self.next_button.setText("Next")

    def _get_step_name(self, index):
        names = [
            "General Form Info",
            "Configure Form Sections",
            "Define Header Fields (Single Section)",
            "Define Columns (Repeating Sections)"
        ]
        if index < len(names):
            return names[index]
        return ""

    def _on_next_clicked(self):
        if self.next_clicked_hook:
            self.next_clicked_hook()

    def _on_back_clicked(self):
        if self.back_clicked_hook:
            self.back_clicked_hook()

    def _on_cancel_clicked(self):
        if self.cancel_clicked_hook:
            self.cancel_clicked_hook()
        else:
            self.reject()

    # --- Page 1: Basic Info ---
    def _build_page_basic_info(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 8, 0, 0)
        
        self.import_form_btn = QPushButton("Import Existing Form Layout JSON...", page)
        self.import_form_btn.setStyleSheet("font-weight: bold; height: 28px;")
        layout.addWidget(self.import_form_btn)
        
        form_group = QGroupBox("Form Identity")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(8)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Injection Molding Log")
        form_layout.addRow("Form Name *", self.name_edit)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("e.g. Logs parts, molds, and downtime codes")
        form_layout.addRow("Description", self.desc_edit)
        
        self.export_prefix_edit = QLineEdit()
        self.export_prefix_edit.setPlaceholderText("e.g. Injection Molding Log")
        form_layout.addRow("Export Filename Prefix", self.export_prefix_edit)
        
        layout.addWidget(form_group)
        
        template_group = QGroupBox("Excel Export Template Association (Optional)")
        template_layout = QHBoxLayout(template_group)
        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText("e.g. templates/molding_template.xlsx")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        template_layout.addWidget(self.template_edit)
        template_layout.addWidget(self.browse_button)
        layout.addWidget(template_group)
        
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _on_browse_clicked(self):
        if self.browse_template_hook:
            self.browse_template_hook()
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Excel Template", "", "Excel Workbooks (*.xlsx *.xlsm)"
            )
            if file_path:
                self.template_edit.setText(file_path)

    # --- Page 2: Sections Configuration ---
    def _build_page_sections(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 8, 0, 0)
        
        instructions = QLabel("Select which sections you want to include in this layout. You can also define custom sections.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        self.sections_table = QTableWidget(0, 4)
        self.sections_table.setHorizontalHeaderLabels(["Section ID", "Section Name", "Type", "Behavior Profile"])
        self.sections_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sections_table)
        
        button_row = QHBoxLayout()
        self.add_section_btn = QPushButton("Add Custom Section")
        self.remove_section_btn = QPushButton("Remove Section")
        self.move_section_up_btn = QPushButton("Move Up")
        self.move_section_down_btn = QPushButton("Move Down")
        self.load_default_sections_btn = QPushButton("Reset to Defaults")
        
        button_row.addWidget(self.add_section_btn)
        button_row.addWidget(self.remove_section_btn)
        button_row.addSpacing(16)
        button_row.addWidget(self.move_section_up_btn)
        button_row.addWidget(self.move_section_down_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.load_default_sections_btn)
        layout.addLayout(button_row)
        
        self.stack.addWidget(page)

    # --- Page 3: Single Section Fields Configuration ---
    def _build_page_single_fields(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 8, 0, 0)
        
        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("Select Single Section to Design:"))
        self.single_section_combo = QComboBox()
        self.single_section_combo.setMinimumWidth(220)
        combo_row.addWidget(self.single_section_combo)
        combo_row.addStretch(1)
        layout.addLayout(combo_row)
        
        self.headers_table = QTableWidget(0, 8)
        self.headers_table.setHorizontalHeaderLabels([
            "Field ID *", "Label", "Row", "Col", "Width", "Excel Cell", "Widget Type", "Semantic Role"
        ])
        self.headers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.headers_table)
        
        button_row = QHBoxLayout()
        self.add_header_btn = QPushButton("Add Field")
        self.remove_header_btn = QPushButton("Remove Selected Field")
        self.load_default_headers_btn = QPushButton("Add Standard Presets")
        
        button_row.addWidget(self.add_header_btn)
        button_row.addWidget(self.remove_header_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.load_default_headers_btn)
        layout.addLayout(button_row)
        
        self.stack.addWidget(page)

    # --- Page 4: Repeating Section Columns ---
    def _build_page_repeating_fields(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 8, 0, 0)
        
        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("Select Section to Design:"))
        self.repeating_section_combo = QComboBox()
        self.repeating_section_combo.setMinimumWidth(220)
        combo_row.addWidget(self.repeating_section_combo)
        combo_row.addStretch(1)
        layout.addLayout(combo_row)
        
        self.repeating_table = QTableWidget(0, 5)
        self.repeating_table.setHorizontalHeaderLabels([
            "Column ID *", "Header Label", "Widget Type", "Width", "Semantic Role"
        ])
        self.repeating_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.repeating_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.repeating_table)
        
        button_row = QHBoxLayout()
        self.add_column_btn = QPushButton("Add Column")
        self.remove_column_btn = QPushButton("Remove Selected Column")
        self.load_default_columns_btn = QPushButton("Load Standard Columns")
        
        button_row.addWidget(self.add_column_btn)
        button_row.addWidget(self.remove_column_btn)
        button_row.addStretch(1)
        button_row.addWidget(self.load_default_columns_btn)
        layout.addLayout(button_row)
        
        self.stack.addWidget(page)

    # --- Utility UI dialogs ---
    def show_warning(self, title, message):
        QMessageBox.warning(self, title, message)

    def confirm(self, title, message):
        return QMessageBox.question(self, title, message) == QMessageBox.StandardButton.Yes
