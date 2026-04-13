# layout_config.json Reference

`layout_config.json` controls three related parts of Production Log:

1. The placement and behavior of header fields.
2. The schema for production rows and downtime rows.
3. The Excel cell and column mapping used for import and export.

Calculation behavior such as rounding, missing-rate fallback, shift anchors, and downtime rollover is stored separately in `production_log_calculations.json`.

See also:

- `production_log_calculations.json` runtime rules reference: `docs/help/production_log_calculations.md`
- Maintainer architecture note: `docs/production_log_json_architecture.md`

## Top-Level Structure

```json
{
  "template_path": "templates/disamatic_template.xlsx",
  "header_fields": [],
  "production_row_fields": [],
  "downtime_row_fields": [],
  "production_mapping": {},
  "downtime_mapping": {}
}
```

Required top-level keys:

- `template_path`
- `header_fields`
- `production_row_fields`
- `downtime_row_fields`
- `production_mapping`
- `downtime_mapping`

## template_path

- Type: string
- Purpose: Relative path to the Excel template used for export.
- Leave it blank if you want export to create a minimal workbook from the configured mappings instead of copying a template first.

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
- `role`: optional semantic name used by the runtime so behavior can follow meaning instead of a fixed field id

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

## Semantic Roles

Header, production-row, and downtime-row fields can carry an optional `role` string.

The role tells the runtime what a field means, even if you later rename the field id for layout or persistence reasons. Current shipped configs still keep the legacy ids, but the runtime now resolves key behaviors by `role` first and falls back to the historical id when an older config omits it.

Examples of header roles:

- `log_date`
- `cast_date`
- `shift_number`
- `shift_hours`
- `goal_rate`
- `total_molds`
- `shift_start_time`
- `shift_end_time`
- `target_time`

Examples of production-row roles:

- `job_order`
- `part_number`
- `rate_value`
- `rate_override_toggle`
- `mold_count`
- `duration_minutes`

Examples of downtime-row roles:

- `start_clock`
- `stop_clock`
- `downtime_code`
- `cause_text`
- `duration_minutes`

Rules for roles:

- A role should appear at most once within a given section.
- Core runtime roles are protected in Layout Manager even if you restyle or reorder the field.
- Older configs can omit `role`; Logging Center auto-assigns built-in roles for the shipped core ids.
- Custom fields can leave `role` blank until they need special runtime meaning.

## Row Schema Overview

- `production_row_fields` defines the inputs and derived fields shown on each production line.
- `downtime_row_fields` defines the inputs and derived fields shown on each downtime line.
- The order of entries in each array is the order used by the Production Log UI.
- Layout Manager can reorder, restyle, and extend these arrays without editing raw JSON.

## Supported Row-Field Attributes

Required keys per row field:

- `id`: internal field name used by the UI and persistence layer
- `label`: visible label or column heading
- `widget`: one of `entry`, `display`, `checkbutton`, or `combobox`

Optional keys:

- `width`: display width for the widget
- `readonly`: marks the field as non-editable in the form
- `default`: default value applied when a row is created
- `derived`: marks a field that is calculated or populated from other values
- `open_row_trigger`: if `true`, entering a value here can trigger creation of the next blank row
- `user_input`: marks fields expected to be entered by the operator
- `state`: widget state override, typically used with comboboxes
- `options_source`: named option list source for widgets such as downtime code comboboxes
- `expand`: allows the widget to stretch with the row layout
- `sticky`: grid alignment hint used by the row renderer
- `bold`: applies stronger text styling where supported
- `bootstyle`: ttkbootstrap style hint for display-focused fields
- `role`: optional semantic identifier used by runtime math, import/export transforms, and future schema evolution

The current runtime prefers `role` and falls back to the built-in ids for backward compatibility. Layout Manager still prevents removing the protected core fields while the migration remains compatible with older local configs.

## production_row_fields

- Type: array of objects
- Purpose: Defines the production row schema shown beneath the header form.

Protected core production row fields:

- `shop_order`
- `part_number`
- `rate_lookup`
- `rate_override_enabled`
- `molds`
- `time_calc`

Example:

```json
{
  "id": "molds",
  "label": "Molds",
  "widget": "entry",
  "width": 8,
  "open_row_trigger": true,
  "user_input": true
}
```

## downtime_row_fields

- Type: array of objects
- Purpose: Defines the downtime row schema shown in the downtime section.

Protected core downtime row fields:

- `start`
- `stop`
- `code`
- `cause`
- `time_calc`

Example:

```json
{
  "id": "time_calc",
  "label": "Minutes",
  "widget": "display",
  "width": 9,
  "readonly": true,
  "derived": true,
  "bold": true,
  "bootstyle": "info"
}
```

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

Column entries can also be objects when you need import/export transforms or per-column toggles:

```json
{
  "start_row": 19,
  "max_rows": 50,
  "columns": {
    "shop_order": { "column": "A" },
    "time_calc": {
      "column": "H",
      "import_enabled": false,
      "export_transform": "minutes_label"
    }
  }
}
```

Supported column object keys:

- `column`: Excel column letter
- `import_enabled`: set to `false` to skip reading the workbook column
- `export_enabled`: set to `false` to skip writing the workbook column
- `import_transform`: optional transform name used while importing
- `export_transform`: optional transform name used while exporting

If you keep the short string form, Logging Center applies the legacy defaults automatically.

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

Mapping requirements follow semantic roles, not just historical ids. The shipped config still uses the legacy field ids, but the validator now checks that the section provides the required core roles for workbook import/export.

Recommended editing path:

- Use Layout Manager for field order, labels, widths, widget types, and semantic roles.
- Use Production Log Calculations for rounding, shift timing, fallback behavior, ghost-time handling, and named formulas.

Downtime mappings can also use the object form shown above. Legacy string entries still default to the current workbook behavior:

- `code` exports as the short numeric code and imports back as the full code label.
- `stop` exports as duration minutes and imports back as a stop clock value derived from `start` plus the workbook minutes.

## Layout Schema vs Rules Profile

Keep these two files distinct:

- `layout_config.json`: controls what the Production Log UI renders and how workbook columns are mapped.
- `production_log_calculations.json`: controls calculation rules such as rounding modes, shift anchor handling, fallback rate behavior, overnight downtime, and default balance mix.

If a change affects what fields exist or how they are presented, it belongs in `layout_config.json`. If it affects how values are calculated, normalized, or interpreted, it belongs in `production_log_calculations.json`.

## Recommended Editing Path

Use Layout Manager first for header layout, production row schema, downtime row schema, and workbook mapping. Use Production Log Calculations for rule and formula behavior. Raw JSON editing is still available when you need attributes that are easier to adjust directly.