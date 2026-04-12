# layout_config.json Reference

`layout_config.json` controls two things:

1. The placement and behavior of Production Log header fields.
2. The Excel cell and column mapping used for import and export.

## Top-Level Structure

```json
{
  "template_path": "templates/disamatic_template.xlsx",
  "header_fields": [],
  "production_mapping": {},
  "downtime_mapping": {}
}
```

Required top-level keys:

- `template_path`
- `header_fields`
- `production_mapping`
- `downtime_mapping`

## template_path

- Type: string
- Purpose: Relative path to the Excel template used for export.

## header_fields

- Type: array of objects
- Purpose: Defines the header controls shown in Production Log.

Required keys per field:

- `id`: internal field name
- `label`: visible label in the form
- `row`: UI row index
- `col`: UI column index

Optional keys per field:

- `width`: entry width in the UI
- `cell`: Excel cell used for export/import
- `readonly`: if `true`, the field cannot be edited directly in the form
- `default`: default text loaded into the field
- `import_enabled`: set to `false` to leave the field out of Excel import while still keeping it in the form
- `export_enabled`: set to `false` to prevent exporting the field back into the workbook

Example:

```json
{
  "id": "goal_mph",
  "label": "Goal MPH",
  "row": 2,
  "col": 2,
  "width": 10,
  "cell": "G5",
  "default": "240"
}
```

Import-only workbook summary fields are supported by combining `readonly: true` with `export_enabled: false`. This is useful for cells such as calculated percentages or formula-driven summary rows that you want to display in Production Log without overwriting the workbook formula on export.

Protected core fields currently expected by Logging Center:

- `date`
- `cast_date`
- `shift`
- `hours`
- `goal_mph`
- `total_molds`

`cast_date` is special. It stays readonly, does not keep a default value, and is normally derived from the entered date.

## production_mapping

- Type: object
- Purpose: Maps production row fields into Excel.

Required keys:

- `start_row`
- `columns`

Required columns:

- `shop_order`
- `part_number`
- `molds`

Structure:

```json
{
  "start_row": 19,
  "columns": {
    "shop_order": "A",
    "part_number": "E",
    "molds": "G"
  }
}
```

## downtime_mapping

- Type: object
- Purpose: Maps downtime row fields into Excel.

Required keys:

- `start_row`
- `columns`

Required columns:

- `start`
- `stop`
- `code`
- `cause`

Structure:

```json
{
  "start_row": 6,
  "columns": {
    "start": "A",
    "stop": "B",
    "code": "C",
    "cause": "D"
  }
}
```

## Recommended Editing Path

Use Layout Manager first. It is safer than editing the JSON by hand and updates the preview as you work.