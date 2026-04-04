# The Martin Suite (GLC Edition)
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

# The Martin Suite (GLC Edition)
# Copyright (C) 2026 Jamie Martin
# ... [License text omitted for brevity] ...

import openpyxl
import json
import os
import shutil
import sys

__module_name__ = "Data Handler"
__version__ = "1.0.1"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class DataHandler:
    def __init__(self, config_name="layout_config.json"):
        # Use resource_path to find the config file inside the build
        self.config_path = resource_path(config_name)
        
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        
        # User data folders stay in the local directory (not internal to the exe)
        self.pending_dir = "data/pending"
        os.makedirs(self.pending_dir, exist_ok=True)
        
        self.settings_path = os.path.join(os.path.abspath("."), "settings.json")
        self.settings = {}
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    self.settings = json.load(f)
            except: pass
    def calculate_formula(self, formula_str, data_context):
    # """
        #Takes a string like '{molds} * 0.95' and replaces {molds} 
        #With the actual value from the UI entries.
        #"""
        try:
            # Replace placeholders {id} with actual values from data_context
            for key, value in data_context.items():
                placeholder = "{" + key + "}"
                if placeholder in formula_str:
                    # Default to 0 if the field is empty
                    val = value if value and str(value).strip() else "0"
                    formula_str = formula_str.replace(placeholder, str(val))
            
            # Clean the string for safety and evaluate
            # We only allow numbers and basic math operators
            return eval(formula_str, {"__builtins__": None}, {})
        except Exception as e:
            print(f"Math Error in formula '{formula_str}': {e}")
            return 0
    def export_to_template(self, ui_data, shift, date_str):
        clean_date = date_str.replace("/", "")
        prefix = self.settings.get("default_export_prefix", "Disamatic Production Sheet")
        filename = f"{prefix} {shift}{clean_date}.xlsx"
        
        base_export_dir = self.settings.get("export_directory", "exports")
        
        if self.settings.get("organize_exports_by_date", True) and "/" in date_str:
            try:
                parts = date_str.split("/")
                if len(parts) == 3:
                    year, month = parts[2], parts[0]
                    base_export_dir = os.path.join(base_export_dir, year, month)
            except Exception as e:
                print(f"Date parse error: {e}")

        target_path = os.path.join(base_export_dir, filename)
        os.makedirs(base_export_dir, exist_ok=True)

        # CRITICAL: Use resource_path for the template path defined in your JSON
        # If your JSON says "templates/production.xlsx", this finds it in the build
        full_template_path = resource_path(self.config['template_path'])
        
        shutil.copy(full_template_path, target_path)
        wb = openpyxl.load_workbook(target_path)
        ws = wb.active

        # 1. Map Header
        for field in self.config['header_fields']:
            cell_coord = field.get('cell')
            val = ui_data['header'].get(field['id'])
            if cell_coord:
                try:
                    is_merged = False
                    for range_ in ws.merged_cells.ranges:
                        if cell_coord in range_:
                            ws.cell(range_.min_row, range_.min_col).value = val
                            is_merged = True
                            break
                    if not is_merged:
                        ws[cell_coord].value = val
                except Exception as e:
                    print(f"Error mapping header {field['id']}: {e}")

        # 2. Map Production Rows
        p_map = self.config['production_mapping']
        p_start = p_map['start_row']
        for i, row_data in enumerate(ui_data['production']):
            curr_row = p_start + i
            for col_key, col_letter in p_map['columns'].items():
                if col_key in row_data:
                    ws[f"{col_letter}{curr_row}"] = row_data.get(col_key)

        # 3. Map Downtime Rows
        d_map = self.config['downtime_mapping']
        d_start = d_map['start_row']
        d_cols = d_map['columns']

        for i, row_data in enumerate(ui_data['downtime']):
            curr_row = d_start + i
            for col_key, col_letter in d_cols.items():
                if col_key == 'code':
                    full_code = row_data.get('code', "")
                    short_code = full_code.split(" ")[0] if full_code else ""
                    ws[f"{col_letter}{curr_row}"] = short_code
                elif col_key in row_data:
                    ws[f"{col_letter}{curr_row}"] = row_data.get(col_key)

        wb.save(target_path)
        return target_path

    # ... [import_from_excel method remains the same] ...

    # Import Production
    def import_from_excel(self, file_path):
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            
            data = {"header": {}, "production": [], "downtime": []}

            # 1. UI Lookup for Downtime Codes
            dt_lookup = {
                "1": "1 Misc Reason for Down Time", "2": "2 Machine Repairs",
                "3": "3 AMC, SBC, Shakeout Problem", "4": "4 Pattern Change",
                "5": "5 Pattern Repair", "6": "6 No Iron Due to Cupola",
                "7": "7 No Iron Due to Transfer", "8": "8 Auto Pour Problems",
                "9": "9 Inoculator Problems", "10": "10 No Sand"
            }

            # 2. Import Header (Date, Shift, etc.)
            for field in self.config['header_fields']:
                cell_coord = field.get('cell')
                if cell_coord:
                    data["header"][field['id']] = ws[cell_coord].value

            # 3. Import Production Lines dynamically
            p_map = self.config['production_mapping']
            p_cols = p_map['columns']
            
            # We need a primary key to know when to stop looking. We'll use the first column defined.
            primary_col_key = list(p_cols.keys())[0] if p_cols else None
            
            if primary_col_key:
                for i in range(50): # Check up to 50 rows
                    row_idx = p_map['start_row'] + i
                    primary_val = ws[f"{p_cols[primary_col_key]}{row_idx}"].value
                    
                    if not primary_val:
                        break
                    
                    row_data = {}
                    for col_key, col_letter in p_cols.items():
                        row_data[col_key] = ws[f"{col_letter}{row_idx}"].value
                    data["production"].append(row_data)

            # 4. Import Downtime dynamically
            d_map = self.config['downtime_mapping']
            d_cols = d_map['columns']
            primary_col_key = list(d_cols.keys())[0] if d_cols else None
            
            if primary_col_key:
                for i in range(25): # Check up to 25 downtime rows
                    row_idx = d_map['start_row'] + i
                    primary_val = ws[f"{d_cols[primary_col_key]}{row_idx}"].value
                    
                    if not primary_val:
                        break

                    row_data = {}
                    for col_key, col_letter in d_cols.items():
                        raw_val = ws[f"{col_letter}{row_idx}"].value
                        if col_key == 'code':
                            raw_str = str(raw_val).strip() if raw_val else ""
                            # Code conversion: UI needs "1 Misc..." but Excel only has "1"
                            row_data[col_key] = dt_lookup.get(raw_str, raw_str)
                        else:
                            row_data[col_key] = raw_val

                    data["downtime"].append(row_data)

            return data