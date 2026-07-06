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
from PyQt6.QtWidgets import (
    QDialog,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QMessageBox,
    QFileDialog,
)

from app.models.form_wizard_model import FormWizardModel
from app.views.form_wizard_qt_view import FormWizardQtView

__module_name__ = "Form Wizard Controller"
__version__ = "2.5.0"


def _to_int(val, fallback=0):
    try:
        if val is None:
            return fallback
        return int(float(val))
    except (ValueError, TypeError):
        return fallback


class FormWizardQtController:
    def __init__(self, parent_view=None):
        self.model = FormWizardModel()
        self.view = FormWizardQtView(parent_view)
        
        self.current_page = 0
        self.total_pages = 4
        
        # Track the active section keys
        self.active_single_key = None
        self.active_repeating_key = None
        
        # Output values
        self.created_form_id = None
        self.created_form_name = None
        
        self._bind_events()
        self._load_model_to_views()

    def exec(self):
        result = self.view.exec()
        return result == QDialog.DialogCode.Accepted

    def _bind_events(self):
        self.view.next_clicked_hook = self.next_page
        self.view.back_clicked_hook = self.back_page
        self.view.import_form_btn.clicked.connect(self.import_layout_json)
        
        # Page 2: Sections buttons
        self.view.add_section_btn.clicked.connect(self.add_section_row)
        self.view.remove_section_btn.clicked.connect(self.remove_section_row)
        self.view.move_section_up_btn.clicked.connect(lambda: self.move_section_row(-1))
        self.view.move_section_down_btn.clicked.connect(lambda: self.move_section_row(1))
        self.view.load_default_sections_btn.clicked.connect(self.reset_sections_to_default)
        
        # Page 3: Single Section events
        self.view.single_section_combo.currentIndexChanged.connect(self.on_single_section_changed)
        self.view.add_header_btn.clicked.connect(self.add_header_row)
        self.view.remove_header_btn.clicked.connect(self.remove_header_row)
        self.view.load_default_headers_btn.clicked.connect(self.load_preset_headers)
        
        # Page 4: Repeating Section events
        self.view.repeating_section_combo.currentIndexChanged.connect(self.on_repeating_section_changed)
        self.view.add_column_btn.clicked.connect(self.add_repeating_row)
        self.view.remove_column_btn.clicked.connect(self.remove_repeating_row)
        self.view.load_default_columns_btn.clicked.connect(self.load_preset_columns)

    def _load_model_to_views(self):
        # Page 1 values
        self.view.name_edit.setText(self.model.form_name)
        self.view.desc_edit.setText(self.model.description)
        self.view.template_edit.setText(self.model.template_path)
        self.view.export_prefix_edit.setText(self.model.export_prefix)
        
        # Page 2 values
        self.populate_sections_table()
        
        # Page 3 values
        self.populate_single_section_combo()
        
        # Page 4 combo and initial table
        self.populate_repeating_section_combo()

    # --- Navigation ---
    def next_page(self):
        if not self.validate_current_page():
            return
            
        self.save_current_page_to_model()
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            if self.current_page == 2:
                self.populate_single_section_combo()
            elif self.current_page == 3:
                self.populate_repeating_section_combo()
            self.view.update_navigation(self.current_page, self.total_pages)
        else:
            # Final submit
            self.create_form()

    def back_page(self):
        self.save_current_page_to_model()
        if self.current_page > 0:
            self.current_page -= 1
            self.view.update_navigation(self.current_page, self.total_pages)

    # --- Page 1 Save & Validation ---
    def validate_current_page(self):
        if self.current_page == 0:
            name = self.view.name_edit.text().strip()
            if not name:
                self.view.show_warning("Validation Error", "Form Name is required.")
                return False
            # Check form name availability
            try:
                existing_forms = self.model.service.list_forms()
                existing_names = {str(f.get("name") or "").lower().strip() for f in existing_forms}
                if name.lower().strip() in existing_names:
                    self.view.show_warning("Validation Error", f"A form with name '{name}' already exists.")
                    return False
            except Exception:
                pass
        elif self.current_page == 1:
            sections = self.get_sections_from_table()
            if not sections:
                self.view.show_warning("Validation Error", "At least one section is required.")
                return False
            # Check section ID uniqueness
            seen = set()
            for s in sections:
                sid = s["id"]
                if sid in seen:
                    self.view.show_warning("Validation Error", f"Duplicate Section ID '{sid}' is not allowed.")
                    return False
                seen.add(sid)
        return True

    def save_current_page_to_model(self):
        if self.current_page == 0:
            self.model.form_name = self.view.name_edit.text().strip()
            self.model.description = self.view.desc_edit.text().strip()
            self.model.template_path = self.view.template_edit.text().strip()
            self.model.export_prefix = self.view.export_prefix_edit.text().strip()
        elif self.current_page == 1:
            self.model.set_sections(self.get_sections_from_table())
        elif self.current_page == 2:
            if self.active_single_key:
                self.model.set_single_fields(self.active_single_key, self.get_headers_from_table())
        elif self.current_page == 3:
            if self.active_repeating_key:
                self.model.set_repeating_fields(self.active_repeating_key, self.get_repeating_fields_from_table())

    # --- Page 2: Sections ---
    def populate_sections_table(self):
        table = self.view.sections_table
        table.setRowCount(0)
        for s in self.model.get_sections():
            r = table.rowCount()
            table.insertRow(r)
            
            table.setItem(r, 0, QTableWidgetItem(s.get("id", "")))
            table.setItem(r, 1, QTableWidgetItem(s.get("name", "")))
            
            type_combo = QComboBox()
            type_combo.addItems(["single", "repeating"])
            type_combo.setCurrentText(s.get("section_type", "single"))
            table.setCellWidget(r, 2, type_combo)
            
            table.setItem(r, 3, QTableWidgetItem(s.get("behavior_profile", "")))

    def get_sections_from_table(self):
        sections = []
        table = self.view.sections_table
        for r in range(table.rowCount()):
            id_item = table.item(r, 0)
            name_item = table.item(r, 1)
            type_combo = table.cellWidget(r, 2)
            profile_item = table.item(r, 3)
            
            sec_id = id_item.text().strip() if id_item else ""
            if not sec_id:
                continue
                
            sec_name = name_item.text().strip() if name_item else sec_id.replace("_", " ").title()
            sec_type = type_combo.currentText() if type_combo else "single"
            profile = profile_item.text().strip() if profile_item else sec_id
            
            sections.append({
                "id": sec_id,
                "name": sec_name,
                "fields_key": f"{sec_id}_fields" if sec_type == "single" else f"{sec_id}_row_fields",
                "mapping_key": f"{sec_id}_mapping" if sec_type == "repeating" else None,
                "section_type": sec_type,
                "behavior_profile": profile,
            })
        return sections

    def add_section_row(self):
        table = self.view.sections_table
        r = table.rowCount()
        table.insertRow(r)
        
        table.setItem(r, 0, QTableWidgetItem(f"custom_section_{r+1}"))
        table.setItem(r, 1, QTableWidgetItem(f"Custom Section {r+1}"))
        
        type_combo = QComboBox()
        type_combo.addItems(["single", "repeating"])
        type_combo.setCurrentText("single")
        table.setCellWidget(r, 2, type_combo)
        
        table.setItem(r, 3, QTableWidgetItem("custom"))

    def remove_section_row(self):
        table = self.view.sections_table
        selected = table.selectedRanges()
        if not selected:
            self.view.show_warning("Error", "Select a section row to remove.")
            return
        row = selected[0].topRow()
        table.removeRow(row)

    def move_section_row(self, direction):
        table = self.view.sections_table
        selected = table.selectedRanges()
        if not selected:
            return
        row = selected[0].topRow()
        new_row = row + direction
        if new_row < 0 or new_row >= table.rowCount():
            return
            
        # Swap rows
        for col in range(table.columnCount()):
            item_curr = table.item(row, col)
            item_new = table.item(new_row, col)
            
            # swap items
            text_curr = item_curr.text() if item_curr else ""
            text_new = item_new.text() if item_new else ""
            table.setItem(row, col, QTableWidgetItem(text_new))
            table.setItem(new_row, col, QTableWidgetItem(text_curr))
            
            # swap widgets (combox)
            widget_curr = table.cellWidget(row, col)
            widget_new = table.cellWidget(new_row, col)
            if widget_curr or widget_new:
                combo_curr_text = widget_curr.currentText() if isinstance(widget_curr, QComboBox) else "single"
                combo_new_text = widget_new.currentText() if isinstance(widget_new, QComboBox) else "single"
                
                new_combo = QComboBox()
                new_combo.addItems(["single", "repeating"])
                new_combo.setCurrentText(combo_curr_text)
                
                curr_combo = QComboBox()
                curr_combo.addItems(["single", "repeating"])
                curr_combo.setCurrentText(combo_new_text)
                
                table.setCellWidget(new_row, col, new_combo)
                table.setCellWidget(row, col, curr_combo)
                
        table.selectRow(new_row)

    def reset_sections_to_default(self):
        if self.view.confirm("Reset Sections", "Reset sections layout to default values? This clears custom edits on this step."):
            self.model.load_defaults()
            self.populate_sections_table()

    # --- Page 3: Single Section Fields ---
    def populate_single_section_combo(self):
        single_sections = [
            s for s in self.model.get_sections()
            if (s.get("section_type") or "single") == "single"
        ]
        
        combo = self.view.single_section_combo
        combo.blockSignals(True)
        combo.clear()
        
        for ss in single_sections:
            if not ss.get("fields_key"):
                if ss.get("id") == "header":
                    ss["fields_key"] = "header_fields"
                else:
                    ss["fields_key"] = f"{ss.get('id')}_fields"
            combo.addItem(f"{ss.get('name', 'Section')} ({ss.get('id', '')})", ss["fields_key"])
            
        combo.blockSignals(False)
        
        if single_sections:
            self.on_single_section_changed(0)
            
    def on_single_section_changed(self, index):
        if self.active_single_key:
            self.model.set_single_fields(self.active_single_key, self.get_headers_from_table())
            
        if index < 0 or index >= self.view.single_section_combo.count():
            self.active_single_key = None
            self.view.headers_table.setRowCount(0)
            return
            
        self.active_single_key = self.view.single_section_combo.itemData(index)
        self.populate_headers_table()

    def populate_headers_table(self):
        if not self.active_single_key:
            return
        table = self.view.headers_table
        table.setRowCount(0)
        for h in self.model.get_single_fields(self.active_single_key):
            self.add_header_row_to_table(
                h.get("id", ""),
                h.get("label", ""),
                h.get("row", 0),
                h.get("col", 0),
                h.get("width", 12),
                h.get("cell", ""),
                h.get("widget", "entry"),
                h.get("role", "")
            )

    def add_header_row_to_table(self, field_id="", label="", row=0, col=0, width=12, cell="", widget_type="entry", role=""):
        table = self.view.headers_table
        r = table.rowCount()
        table.insertRow(r)
        
        table.setItem(r, 0, QTableWidgetItem(field_id))
        table.setItem(r, 1, QTableWidgetItem(label))
        
        row_spin = QSpinBox()
        row_spin.setValue(_to_int(row))
        table.setCellWidget(r, 2, row_spin)
        
        col_spin = QSpinBox()
        col_spin.setValue(_to_int(col))
        table.setCellWidget(r, 3, col_spin)
        
        width_spin = QSpinBox()
        width_spin.setMaximum(24)
        width_spin.setValue(_to_int(width))
        table.setCellWidget(r, 4, width_spin)
        
        table.setItem(r, 5, QTableWidgetItem(cell))
        
        widget_combo = QComboBox()
        widget_combo.addItems(["entry", "combobox"])
        widget_combo.setCurrentText(widget_type)
        table.setCellWidget(r, 6, widget_combo)
        
        role_combo = QComboBox()
        role_combo.addItems(["", "shift_date", "shift_code", "operator_name", "shift_leader", "production_line", "goal_mph", "shift_hours"])
        role_combo.setCurrentText(role)
        table.setCellWidget(r, 7, role_combo)

    def get_headers_from_table(self):
        fields = []
        table = self.view.headers_table
        for r in range(table.rowCount()):
            fid_item = table.item(r, 0)
            lbl_item = table.item(r, 1)
            row_spin = table.cellWidget(r, 2)
            col_spin = table.cellWidget(r, 3)
            width_spin = table.cellWidget(r, 4)
            cell_item = table.item(r, 5)
            widget_combo = table.cellWidget(r, 6)
            role_combo = table.cellWidget(r, 7)
            
            fid = fid_item.text().strip() if fid_item else ""
            if not fid:
                continue
                
            lbl = lbl_item.text().strip() if lbl_item else fid.replace("_", " ").title()
            row_val = row_spin.value() if row_spin else 0
            col_val = col_spin.value() if col_spin else 0
            width_val = width_spin.value() if width_spin else 12
            cell_val = cell_item.text().strip() if cell_item else ""
            widget_val = widget_combo.currentText() if widget_combo else "entry"
            role_val = role_combo.currentText() if role_combo else ""
            
            field_config = {
                "id": fid,
                "label": lbl,
                "row": row_val,
                "col": col_val,
                "width": width_val,
                "cell": cell_val,
                "widget": widget_val,
            }
            if role_val:
                field_config["role"] = role_val
                
            fields.append(field_config)
        return fields

    def add_header_row(self):
        r = self.view.headers_table.rowCount()
        self.add_header_row_to_table(field_id=f"header_field_{r+1}", label=f"Header Field {r+1}")

    def remove_header_row(self):
        table = self.view.headers_table
        selected = table.selectedRanges()
        if not selected:
            return
        table.removeRow(selected[0].topRow())

    def load_preset_headers(self):
        default_config = self.model.layout_manager._get_default_config_template()
        preset_headers = default_config.get("header_fields", [])
        
        # Append only non-existing ones
        existing_ids = {f["id"] for f in self.get_headers_from_table()}
        for ph in preset_headers:
            if ph.get("id") not in existing_ids:
                self.add_header_row_to_table(
                    ph.get("id", ""),
                    ph.get("label", ""),
                    ph.get("row", 0),
                    ph.get("col", 0),
                    ph.get("width", 12),
                    ph.get("cell", ""),
                    ph.get("widget", "entry"),
                    ph.get("role", "")
                )

    # --- Page 4: Repeating Columns ---
    def populate_repeating_section_combo(self):
        # Save current table first if active
        if self.active_repeating_key:
            self.model.set_repeating_fields(self.active_repeating_key, self.get_repeating_fields_from_table())
            
        # Gather all repeating sections configured on Page 2
        sections = self.get_sections_from_table()
        repeating_sections = [s for s in sections if s["section_type"] == "repeating"]
        
        combo = self.view.repeating_section_combo
        combo.blockSignals(True)
        combo.clear()
        
        for rs in repeating_sections:
            combo.addItem(f"{rs['name']} ({rs['id']})", rs["fields_key"])
            
        combo.blockSignals(False)
        
        if repeating_sections:
            self.active_repeating_key = repeating_sections[0]["fields_key"]
            self.populate_repeating_table(self.active_repeating_key)
        else:
            self.active_repeating_key = None
            self.view.repeating_table.setRowCount(0)

    def on_repeating_section_changed(self, index):
        if index < 0:
            return
        # Save old
        if self.active_repeating_key:
            self.model.set_repeating_fields(self.active_repeating_key, self.get_repeating_fields_from_table())
            
        self.active_repeating_key = self.view.repeating_section_combo.itemData(index)
        self.populate_repeating_table(self.active_repeating_key)

    def populate_repeating_table(self, fields_key):
        table = self.view.repeating_table
        table.setRowCount(0)
        for rf in self.model.get_repeating_fields(fields_key):
            self.add_repeating_row_to_table(
                rf.get("id", ""),
                rf.get("label", ""),
                rf.get("widget", "entry"),
                rf.get("width", 12),
                rf.get("role", "")
            )

    def add_repeating_row_to_table(self, col_id="", label="", widget_type="entry", width=12, role=""):
        table = self.view.repeating_table
        r = table.rowCount()
        table.insertRow(r)
        
        table.setItem(r, 0, QTableWidgetItem(col_id))
        table.setItem(r, 1, QTableWidgetItem(label))
        
        widget_combo = QComboBox()
        widget_combo.addItems(["entry", "display", "checkbutton", "combobox"])
        widget_combo.setCurrentText(widget_type)
        table.setCellWidget(r, 2, widget_combo)
        
        width_spin = QSpinBox()
        width_spin.setMaximum(50)
        width_spin.setValue(_to_int(width))
        table.setCellWidget(r, 3, width_spin)
        
        role_combo = QComboBox()
        role_combo.addItems([
            "", "shop_order", "part_number", "rate_lookup", "rate_override_enabled",
            "mold_count", "duration_minutes", "start_time", "stop_time", "downtime_code", "downtime_cause"
        ])
        role_combo.setCurrentText(role)
        table.setCellWidget(r, 4, role_combo)

    def get_repeating_fields_from_table(self):
        fields = []
        table = self.view.repeating_table
        for r in range(table.rowCount()):
            cid_item = table.item(r, 0)
            lbl_item = table.item(r, 1)
            widget_combo = table.cellWidget(r, 2)
            width_spin = table.cellWidget(r, 3)
            role_combo = table.cellWidget(r, 4)
            
            cid = cid_item.text().strip() if cid_item else ""
            if not cid:
                continue
                
            lbl = lbl_item.text().strip() if lbl_item else cid.replace("_", " ").title()
            widget_val = widget_combo.currentText() if widget_combo else "entry"
            width_val = width_spin.value() if width_spin else 12
            role_val = role_combo.currentText() if role_combo else ""
            
            field_config = {
                "id": cid,
                "label": lbl,
                "widget": widget_val,
                "width": width_val,
            }
            if role_val:
                field_config["role"] = role_val
                
            fields.append(field_config)
        return fields

    def add_repeating_row(self):
        if not self.active_repeating_key:
            return
        r = self.view.repeating_table.rowCount()
        self.add_repeating_row_to_table(col_id=f"col_field_{r+1}", label=f"Column Field {r+1}")

    def remove_repeating_row(self):
        table = self.view.repeating_table
        selected = table.selectedRanges()
        if not selected:
            return
        table.removeRow(selected[0].topRow())

    def load_preset_columns(self):
        if not self.active_repeating_key:
            return
            
        # Determine profile based on active repeating key
        # Find section behavior profile from sections list
        sections = self.get_sections_from_table()
        target_profile = "production"
        for s in sections:
            if s.get("fields_key") == self.active_repeating_key:
                target_profile = s.get("behavior_profile", "production")
                break
                
        default_config = self.model.layout_manager._get_default_config_template()
        
        # Load production or downtime row fields based on profile
        source_key = "production_row_fields" if "production" in target_profile.lower() else "downtime_row_fields"
        preset_cols = default_config.get(source_key, [])
        
        existing_ids = {c["id"] for c in self.get_repeating_fields_from_table()}
        for pc in preset_cols:
            if pc.get("id") not in existing_ids:
                self.add_repeating_row_to_table(
                    pc.get("id", ""),
                    pc.get("label", ""),
                    pc.get("widget", "entry"),
                    pc.get("width", 12),
                    pc.get("role", "")
                )

    # --- Form Creation Trigger ---
    def create_form(self):
        name = self.model.form_name
        description = self.model.description
        
        try:
            form_info = self.model.create_form(name, description=description, activate=False)
            self.created_form_id = form_info.get("id")
            self.created_form_name = form_info.get("name", name)
            self.view.accept()
        except Exception as exc:
            self.view.show_warning("Form Creation Failed", f"An error occurred: {exc}")

    def import_layout_json(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, "Import Form Layout JSON", "", "JSON Files (*.json)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                import json
                config = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self.view, "Import Error", f"Failed to parse JSON file:\n{exc}")
            return
            
        try:
            missing_data = self.model.layout_manager.detect_missing_standard_fields(config)
            has_missing_header = len(missing_data.get("header", [])) > 0
            has_missing_prod = len(missing_data.get("production", [])) > 0
            has_missing_down = len(missing_data.get("downtime", [])) > 0
            
            metadata_check = missing_data.get("metadata", {})
            name_missing = metadata_check.get("name_missing")
            desc_missing = metadata_check.get("description_missing")
            
            if has_missing_header or has_missing_prod or has_missing_down or name_missing or desc_missing:
                suggestions = self.model.layout_manager.get_missing_fields_suggestions(config, file_path)
                from app.views.layout_manager_qt_view import InjectMissingFieldsDialog
                dialog = InjectMissingFieldsDialog(self.view, missing_fields=missing_data, suggestions=suggestions)
                if dialog.exec():
                    result = dialog.get_values()
                    metadata = result.get("metadata", {})
                    fields_to_inject = result.get("fields", [])
                    
                    config = self.model.layout_manager.inject_fields_into_config(config, fields_to_inject)
                    
                    if metadata.get("export_prefix"):
                        config["export_prefix"] = metadata.get("export_prefix")
                    name = metadata.get("name")
                    description = metadata.get("description")
                else:
                    name = None
                    description = None
            else:
                import os
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                clean_name = base_name.replace("_", " ").replace("-", " ").title()
                name = clean_name
                description = f"Imported from {os.path.basename(file_path)}"
        except Exception as exc:
            QMessageBox.critical(self.view, "Import Error", f"Error checking missing fields:\n{exc}")
            return
            
        self.model.form_name = name or config.get("export_prefix") or ""
        self.model.description = description or ""
        self.model.template_path = config.get("template_path", "")
        self.model.export_prefix = config.get("export_prefix", "")
        
        self.model.sections = config.get("sections", [])
        self.model.single_sections.clear()
        self.model.repeating_sections.clear()
        
        for section in self.model.sections:
            section_type = section.get("section_type") or "single"
            fields_key = section.get("fields_key")
            if section_type == "repeating":
                self.model.repeating_sections[fields_key] = config.get(fields_key, [])
            elif section_type == "single":
                self.model.single_sections[fields_key] = config.get(fields_key, [])
                
        self._load_model_to_views()
