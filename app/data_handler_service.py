import json
import os
import re
import shutil
from datetime import date, datetime

import openpyxl

from app.downtime_codes import get_code_number, normalize_code_value
from app.utils import ensure_external_directory, external_path, local_or_resource_path, resource_path

__module_name__ = "Data Handler"
__version__ = "1.1.2"


class DataHandlerService:
    def __init__(self, config_name="layout_config.json"):
        self.config_path = local_or_resource_path(config_name)
        with open(self.config_path, "r", encoding="utf-8") as handle:
            self.config = json.load(handle)
        self.settings = self.load_settings()
        self.pending_dir = ensure_external_directory("data/pending")

    def load_settings(self):
        settings_path = external_path("settings.json")
        settings = {
            "export_directory": "exports",
            "organize_exports_by_date": True,
            "default_export_prefix": "Disamatic Production Sheet",
        }
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass
        return settings

    def parse_export_date(self, raw_date):
        date_text = str(raw_date or "").strip()
        if not date_text:
            return None
        for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%m%d%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_text, fmt)
            except ValueError:
                continue
        return None

    def format_cell_value(self, value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%m/%d/%Y")
        if isinstance(value, date):
            return value.strftime("%m/%d/%Y")
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        return value

    def format_header_value(self, field_id, value, number_format=None):
        formatted = self.format_cell_value(value)
        if isinstance(value, (int, float)) and number_format and "%" in str(number_format):
            return f"{value * 100:.0f}%"
        if field_id == "cast_date":
            text = str(formatted or "").strip()
            if not text:
                return ""
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                return digits.zfill(3)[-3:]
        return formatted

    def get_header_fields(self):
        return self.config.get("header_fields", [])

    def get_header_field_ids(self):
        return [field.get("id") for field in self.get_header_fields() if field.get("id")]

    def format_numeric_text(self, value, allow_decimal=False):
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            numeric_value = float(text)
        except Exception:
            return text
        if numeric_value.is_integer():
            return str(int(numeric_value))
        if allow_decimal:
            return f"{numeric_value:.2f}".rstrip("0").rstrip(".")
        return str(int(round(numeric_value)))

    def normalize_date_text(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        parsed = self.parse_export_date(text)
        if parsed is None:
            return text
        return parsed.strftime("%m/%d/%Y")

    def compute_target_time(self, raw_hours):
        try:
            total_minutes = int(round(float(raw_hours or 0) * 60))
        except Exception:
            return ""
        return f"{total_minutes} min" if total_minutes > 0 else ""

    def normalize_target_time_text(self, value):
        total_minutes = self.parse_total_minutes(value)
        if total_minutes is None or total_minutes <= 0:
            return ""
        return f"{total_minutes} min"

    def normalize_header_field_value(self, field_id, value, header_data=None):
        header_data = header_data or {}
        text = str(value or "").strip()
        if field_id == "date":
            return self.normalize_date_text(text)
        if field_id == "hours":
            return self.format_numeric_text(text, allow_decimal=True)
        if field_id in {"shift", "goal_mph", "ret_south", "ret_north", "total_molds"}:
            return self.format_numeric_text(text, allow_decimal=False)
        if field_id == "cast_date":
            computed = self.compute_cast_date(header_data.get("date"))
            return computed or self.format_header_value(field_id, text)
        if field_id == "target_time":
            computed = self.compute_target_time(header_data.get("hours"))
            return computed or self.normalize_target_time_text(text)
        return text

    def normalize_header_data(self, header_data):
        normalized = {}
        raw_header = {field_id: str(header_data.get(field_id, "") or "").strip() for field_id in self.get_header_field_ids()}
        for field_id in self.get_header_field_ids():
            if field_id in {"cast_date", "target_time"}:
                continue
            normalized[field_id] = self.normalize_header_field_value(field_id, raw_header.get(field_id, ""), {**raw_header, **normalized})
        if "cast_date" in raw_header:
            normalized["cast_date"] = self.normalize_header_field_value("cast_date", raw_header.get("cast_date", ""), {**raw_header, **normalized})
        if "target_time" in raw_header:
            normalized["target_time"] = self.normalize_header_field_value("target_time", raw_header.get("target_time", ""), {**raw_header, **normalized})
        return normalized

    def compute_cast_date(self, raw_date):
        parsed = self.parse_export_date(raw_date)
        if parsed is None:
            return ""
        return f"{parsed.timetuple().tm_yday:03}"

    def evaluate_formula_cell(self, workbook, worksheet, formula, cache=None):
        if not isinstance(formula, str) or not formula.startswith("="):
            return formula
        cache = cache if cache is not None else {}
        cache_key = (worksheet.title, formula)
        if cache_key in cache:
            return cache[cache_key]
        expression = formula[1:].strip()

        def resolve_reference(token):
            if "!" in token:
                sheet_name, cell_ref = token.split("!", 1)
                sheet_name = sheet_name.strip("'")
                target_ws = workbook[sheet_name]
            else:
                cell_ref = token
                target_ws = worksheet
            return self.resolve_import_cell_value(workbook, target_ws, cell_ref, cache)

        def replace_sum(match):
            args = [part.strip() for part in match.group(1).split(",") if part.strip()]
            total = 0
            for arg in args:
                if ":" in arg:
                    if "!" in arg:
                        sheet_name, cell_range = arg.split("!", 1)
                        target_ws = workbook[sheet_name.strip("'")]
                    else:
                        cell_range = arg
                        target_ws = worksheet
                    for row in target_ws[cell_range]:
                        for cell in row:
                            value = self.resolve_import_cell_value(workbook, target_ws, cell.coordinate, cache)
                            if isinstance(value, (int, float)):
                                total += value
                            elif value not in (None, ""):
                                try:
                                    total += float(value)
                                except Exception:
                                    pass
                else:
                    value = resolve_reference(arg)
                    if isinstance(value, (int, float)):
                        total += value
                    elif value not in (None, ""):
                        try:
                            total += float(value)
                        except Exception:
                            pass
            return str(total)

        expression = re.sub(r"SUM\(([^\)]*)\)", replace_sum, expression, flags=re.IGNORECASE)
        ref_pattern = re.compile(r"(?<![A-Z0-9_'])((?:'[^']+'!)?[A-Z]+\d+)")

        def replace_ref(match):
            token = match.group(1)
            value = resolve_reference(token)
            if value in (None, ""):
                return "0"
            if isinstance(value, str):
                try:
                    return str(float(value))
                except Exception:
                    return "0"
            return str(value)

        expression = ref_pattern.sub(replace_ref, expression)
        try:
            result = eval(expression, {"__builtins__": None}, {})
        except Exception:
            result = None
        cache[cache_key] = result
        return result

    def resolve_import_cell_value(self, workbook, worksheet, cell_ref, cache=None):
        cache = cache if cache is not None else {}
        cell = worksheet[cell_ref]
        value = cell.value
        if isinstance(value, str) and value.startswith("="):
            return self.evaluate_formula_cell(workbook, worksheet, value, cache)
        return value

    def normalize_time_value(self, value):
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return ""
        return digits.zfill(4)[-4:]

    def parse_total_minutes(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return max(0, int(value))
        text = str(value).strip()
        if not text:
            return None
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        return max(0, int(digits))

    def calculate_duration_minutes(self, start_value, stop_value):
        start_text = self.normalize_time_value(start_value)
        stop_text = self.normalize_time_value(stop_value)
        if len(start_text) != 4 or len(stop_text) != 4:
            return None
        start_minutes = int(start_text[:2]) * 60 + int(start_text[2:])
        stop_minutes = int(stop_text[:2]) * 60 + int(stop_text[2:])
        if stop_minutes < start_minutes:
            stop_minutes += 24 * 60
        return stop_minutes - start_minutes

    def calculate_stop_time(self, start_value, total_minutes_value):
        start_text = self.normalize_time_value(start_value)
        total_minutes = self.parse_total_minutes(total_minutes_value)
        if len(start_text) != 4 or total_minutes is None:
            return ""
        start_minutes = int(start_text[:2]) * 60 + int(start_text[2:])
        stop_minutes = (start_minutes + total_minutes) % (24 * 60)
        return f"{stop_minutes // 60:02}{stop_minutes % 60:02}"

    def get_export_directory(self, raw_date):
        base_dir = str(self.settings.get("export_directory", "exports") or "exports").strip() or "exports"
        target_dir = base_dir if os.path.isabs(base_dir) else external_path(base_dir)
        if self.settings.get("organize_exports_by_date", True):
            export_date = self.parse_export_date(raw_date)
            if export_date is not None:
                year_dir = os.path.join(target_dir, export_date.strftime("%Y"))
                legacy_month_dir = os.path.join(year_dir, export_date.strftime("%m"))
                month_folder = export_date.strftime("%m %B")
                target_dir = os.path.join(year_dir, month_folder)
                if os.path.isdir(legacy_month_dir) and not os.path.exists(target_dir):
                    os.makedirs(year_dir, exist_ok=True)
                    os.rename(legacy_month_dir, target_dir)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def calculate_formula(self, formula_str, data_context):
        try:
            for key, value in data_context.items():
                placeholder = "{" + key + "}"
                if placeholder in formula_str:
                    val = value if value and str(value).strip() else "0"
                    formula_str = formula_str.replace(placeholder, str(val))
            return eval(formula_str, {"__builtins__": None}, {})
        except Exception:
            return 0

    def get_production_column(self, column_map, key, fallback=None):
        value = column_map.get(key, fallback)
        text = str(value or "").strip()
        return text or None

    def normalize_header_label(self, value):
        return " ".join(str(value or "").strip().lower().split())

    def detect_production_columns(self, worksheet, configured_columns, start_row):
        resolved_columns = dict(configured_columns)
        header_row = max(1, int(start_row) - 1)
        label_map = {"shop order": "shop_order", "part number": "part_number", "molds": "molds"}
        for column_index in range(1, worksheet.max_column + 1):
            raw_value = worksheet.cell(row=header_row, column=column_index).value
            normalized = self.normalize_header_label(raw_value)
            field_name = label_map.get(normalized)
            if field_name:
                resolved_columns[field_name] = openpyxl.utils.get_column_letter(column_index)
        return resolved_columns

    def export_to_template(self, ui_data, shift, date_str):
        clean_date = date_str.replace("/", "")
        export_prefix = str(self.settings.get("default_export_prefix", "Disamatic Production Sheet") or "Disamatic Production Sheet").strip()
        filename = f"{export_prefix} {shift}{clean_date}.xlsx"
        target_path = os.path.join(self.get_export_directory(date_str), filename)
        full_template_path = resource_path(self.config["template_path"])
        shutil.copy(full_template_path, target_path)
        wb = openpyxl.load_workbook(target_path)
        ws = wb.active
        for field in self.config["header_fields"]:
            cell_coord = field.get("cell")
            val = ui_data["header"].get(field["id"])
            if cell_coord and field.get("export_enabled", True):
                cell = ws[cell_coord]
                from openpyxl.cell.cell import MergedCell
                if isinstance(cell, MergedCell):
                    for range_ in ws.merged_cells.ranges:
                        if cell_coord in range_:
                            ws.cell(range_.min_row, range_.min_col).value = val
                            break
                else:
                    cell.value = val
        p_map = self.config["production_mapping"]
        p_start = p_map["start_row"]
        p_cols = p_map["columns"]
        for index, row_data in enumerate(ui_data["production"]):
            current_row = p_start + index
            ws[f"{p_cols['shop_order']}{current_row}"] = row_data.get("shop_order")
            ws[f"{p_cols['part_number']}{current_row}"] = row_data.get("part_number")
            ws[f"{p_cols['molds']}{current_row}"] = row_data.get("molds")
        d_map = self.config["downtime_mapping"]
        d_start = d_map["start_row"]
        d_cols = d_map["columns"]
        for index, row_data in enumerate(ui_data["downtime"]):
            current_row = d_start + index
            short_code = get_code_number(row_data.get("code", ""))
            duration_minutes = self.calculate_duration_minutes(row_data.get("start"), row_data.get("stop"))
            if duration_minutes is None:
                duration_minutes = self.parse_total_minutes(str(row_data.get("time_calc", "")).replace(" min", ""))
            ws[f"{d_cols['start']}{current_row}"] = row_data.get("start")
            ws[f"{d_cols['stop']}{current_row}"] = duration_minutes
            ws[f"{d_cols['code']}{current_row}"] = short_code
            ws[f"{d_cols['cause']}{current_row}"] = row_data.get("cause")
        wb.save(target_path)
        return target_path

    def import_from_excel(self, file_path):
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        formula_workbook = openpyxl.load_workbook(file_path, data_only=False)
        worksheet = workbook.active
        formula_worksheet = formula_workbook.active
        formula_cache = {}
        data = {"header": {}, "production": [], "downtime": []}
        for field in self.config["header_fields"]:
            cell_coord = field.get("cell")
            if cell_coord and field.get("import_enabled", True):
                value = worksheet[cell_coord].value
                if value is None:
                    value = self.resolve_import_cell_value(formula_workbook, formula_worksheet, cell_coord, formula_cache)
                number_format = formula_worksheet[cell_coord].number_format if cell_coord else None
                data["header"][field["id"]] = self.format_header_value(field["id"], value, number_format)
        if not data["header"].get("cast_date"):
            data["header"]["cast_date"] = self.compute_cast_date(data["header"].get("date"))
        p_map = self.config["production_mapping"]
        p_cols = self.detect_production_columns(formula_worksheet, p_map["columns"], p_map["start_row"])
        for index in range(50):
            row_idx = p_map["start_row"] + index
            shop_order = worksheet[f"{p_cols['shop_order']}{row_idx}"].value
            if shop_order is None:
                shop_order = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{p_cols['shop_order']}{row_idx}", formula_cache)
            if not shop_order:
                break
            part_number = worksheet[f"{p_cols['part_number']}{row_idx}"].value
            if part_number is None:
                part_number = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{p_cols['part_number']}{row_idx}", formula_cache)
            molds = worksheet[f"{p_cols['molds']}{row_idx}"].value
            if molds is None:
                molds = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{p_cols['molds']}{row_idx}", formula_cache)
            data["production"].append(
                {
                    "shop_order": self.format_cell_value(shop_order),
                    "part_number": self.format_cell_value(part_number),
                    "molds": self.format_cell_value(molds),
                }
            )
        d_map = self.config["downtime_mapping"]
        d_cols = d_map["columns"]
        for index in range(25):
            row_idx = d_map["start_row"] + index
            start_time = worksheet[f"{d_cols['start']}{row_idx}"].value
            if start_time is None:
                start_time = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{d_cols['start']}{row_idx}", formula_cache)
            if not start_time:
                break
            raw_val = worksheet[f"{d_cols['code']}{row_idx}"].value
            if raw_val is None:
                raw_val = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{d_cols['code']}{row_idx}", formula_cache)
            full_code = normalize_code_value(raw_val)
            total_minutes = worksheet[f"{d_cols['stop']}{row_idx}"].value
            if total_minutes is None:
                total_minutes = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{d_cols['stop']}{row_idx}", formula_cache)
            cause = worksheet[f"{d_cols['cause']}{row_idx}"].value
            if cause is None:
                cause = self.resolve_import_cell_value(formula_workbook, formula_worksheet, f"{d_cols['cause']}{row_idx}", formula_cache)
            data["downtime"].append(
                {
                    "start": self.format_cell_value(start_time),
                    "stop": self.calculate_stop_time(start_time, total_minutes),
                    "code": full_code,
                    "cause": self.format_cell_value(cause),
                }
            )
        return data
