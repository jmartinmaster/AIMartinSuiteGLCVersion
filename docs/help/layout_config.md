# layout_config.json Reference

`layout_config.json` is the default built-in form layout for the shipped Form Loader default form, currently named `Temp Form Title`.

Custom stored forms under `data/forms/<form_id>.json` use the same schema.

That shared schema matters:

- Layout Manager saves this contract.
- Form Loader loads this contract.
- There is not supposed to be a separate Form Loader-only layout format.

If Layout Manager can validate and save a form, Form Loader should be able to accept that form as input through the active form registry.

Calculation behavior such as rounding, missing-rate fallback, shift anchors, and downtime rollover is stored separately in `production_log_calculations.json`.

See also:

- `docs/help/form_definitions.md`
- `docs/help/production_log_calculations.md`
- `docs/help/user_guide_layout_manager_form_authoring.md`
- `docs/production_log_json_architecture.md`

## What This Layout Controls

The active layout controls four related parts of Form Loader:

1. The active form structure chosen through `form_definitions.json`.
2. The section order and section behavior shown in the form.
3. The field schema for header and repeating-row sections.
4. The Excel cell and column mapping used for import and export.

## Top-Level Structure

```json
{
  "template_path": "templates/disamatic_template.xlsx",
  "header_fields": [],
  "production_row_fields": [],
  "downtime_row_fields": [],
  "production_mapping": {},
  "downtime_mapping": {},
  "sections": []
}
```

Required top-level keys in the normalized contract:

- `template_path`
- `header_fields`
- `production_row_fields`
- `downtime_row_fields`
- `production_mapping`
- `downtime_mapping`
- `sections`

The shipped built-in form uses `layout_config.json`. Custom forms created from Layout Manager use `data/forms/<form_id>.json`. The same schema applies to both.

## template_path

- Type: string
- Purpose: Relative path to the Excel template used for export.
- Leave it blank if you want export to create a minimal workbook from the configured mappings instead of copying a template first.

## sections

- Type: array of objects
- Purpose: Defines the logical form sections, their rendering order, and their workbook-routing metadata.

Form Loader should treat `sections[]` order as the authoritative display order for supported sections.

Supported keys per section:

- `id`: stable section id
- `name`: visible section label
- `description`: optional helper text
- `fields_key`: which field array this section uses
- `section_type`: `single` or `repeating`
- `behavior_profile`: runtime behavior name such as `header`, `production`, or `downtime`
- `mapping_key`: workbook mapping section used by repeating sections
- `default_max_rows`: default row limit for repeating sections
- `delete_row_policy`: repeating-row delete behavior metadata

Current runtime-supported behavior profiles:

- `header`
- `production`
- `downtime`

Future profiles may appear in saved JSON, but they remain limited until the runtime explicitly supports them.

Example:

```json
{
  "id": "production",
  "name": "Production Rows",
  "fields_key": "production_row_fields",
  "section_type": "repeating",
  "behavior_profile": "production",
  "mapping_key": "production_mapping",
  "default_max_rows": 50,
  "delete_row_policy": {
    "show_delete_button": true,
    "delete_button_label": "X",
    "delete_button_tooltip": "Delete this row",
    "require_delete_confirmation": false
  }
}
```

## header_fields

- Type: array of objects
- Purpose: Defines the field schema used by the header section.

Required keys per field:

- `id`: internal field name
- `label`: visible label in the form
- `row`: UI row index within the header grid
- `col`: UI column index within the header grid

Optional keys per field:

- `width`: entry width hint in the UI
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

Import-only workbook summary fields are supported by combining `readonly: true` with `export_enabled: false`. This is useful for cells such as calculated percentages or formula-driven summary rows that you want to display in Form Loader without overwriting the workbook formula on export.

Recognized historical/core header field ids include:

- `date`
- `cast_date`
- `shift`
- `hours`
- `goal_mph`
- `total_molds`

Current built-in header field ids in the shipped default form:

- `date` -> role `log_date`
- `cast_date` -> role `cast_date`
- `bond` -> role `bond`
- `eff_pct` -> role `efficiency_pct`
- `shift` -> role `shift_number`
- `hours` -> role `shift_hours`
- `target_time` -> role `target_time`
- `mtd_pct` -> role `mtd_percentage`
- `goal_mph` -> role `goal_rate`
- `total_molds` -> role `total_molds`
- `ret_north` -> role `ret_north`
- `start_time` -> role `shift_start_time`
- `end_time` -> role `shift_end_time`
- `ret_south` -> role `ret_south`

`cast_date` is special. It stays readonly, does not keep a default value, and is normally derived from the entered date.

## Semantic Roles

Header, production-row, and downtime-row fields can carry an optional `role` string.

The role tells the runtime what a field means, even if you later rename the field id for layout or persistence reasons. Current shipped configs still keep the legacy ids, but the runtime resolves key behaviors by `role` first and falls back to the historical id when an older config omits it.

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

- `production_row_fields` defines the field schema used by production repeating sections.
- `downtime_row_fields` defines the field schema used by downtime repeating sections.
- The runtime uses the field arrays referenced by `sections[].fields_key`.
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
- `bootstyle`: style hint for display-focused fields
- `role`: optional semantic identifier used by runtime math, import/export transforms, and future schema evolution
- `lookup_source`: named lookup source used by supported runtime lookups
- `lookup_key_role`: role name used as the lookup key
- `override_toggle_role`: role used to identify a related override toggle field
- `toggle_target_role`: role used to identify which field a toggle affects
- `cell`: optional workbook-linked cell metadata for supported scenarios
- `import_enabled`: opt out of import for the field
- `export_enabled`: opt out of export for the field

The current runtime prefers `role` and falls back to built-in ids for backward compatibility.

## production_row_fields

- Type: array of objects
- Purpose: Defines the production row schema used by production repeating sections.

Recognized historical/core production row field ids include:

- `shop_order`
- `part_number`
- `rate_lookup`
- `rate_override_enabled`
- `molds`
- `time_calc`

Current built-in production row field ids in the shipped default form:

- `shop_order` -> role `job_order`
- `part_number` -> role `part_number`
- `rate_lookup` -> role `rate_value`
- `rate_override_enabled` -> role `rate_override_toggle`
- `molds` -> role `mold_count`
- `time_calc` -> role `duration_minutes`

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
- Purpose: Defines the downtime row schema used by downtime repeating sections.

Recognized historical/core downtime row field ids include:

- `start`
- `stop`
- `code`
- `cause`
- `time_calc`

Current built-in downtime row field ids in the shipped default form:

- `start` -> role `start_clock`
- `stop` -> role `stop_clock`
- `code` -> role `downtime_code`
- `cause` -> role `cause_text`
- `time_calc` -> role `duration_minutes`

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

Required workbook coverage follows the required core roles for the section, not just the historical field ids.

Structure:

```json
{
  "start_row": 19,
  "max_rows": 50,
  "columns": {
    "shop_order": { "column": "A" },
    "part_number": { "column": "E" },
    "molds": { "column": "G" }
  }
}
```

Column entries can be either simple strings or object-form mappings.

Supported object-form keys:

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

Structure:

```json
{
  "start_row": 6,
  "max_rows": 50,
  "columns": {
    "start": { "column": "A" },
    "stop": { "column": "B" },
    "code": { "column": "C" },
    "cause": { "column": "D" }
  }
}
```

Downtime mappings can also use the object form shown above. Legacy string entries still default to the current workbook behavior:

- `code` exports as the short numeric code and imports back as the full code label.
- `stop` exports as duration minutes and imports back as a stop clock value derived from `start` plus the workbook minutes.

## Layout Schema vs Rules Profile

Keep these two files distinct:

- The active layout file, either `layout_config.json` or `data/forms/<form_id>.json`, controls what the Form Loader form renders and how workbook columns are mapped.
- `production_log_calculations.json` controls calculation rules such as rounding modes, shift anchor handling, fallback rate behavior, overnight downtime, and default balance mix.

If a change affects what fields exist, how sections are ordered, or how workbook mappings are routed, it belongs in the active layout file. If it affects how values are calculated, normalized, or interpreted, it belongs in `production_log_calculations.json`.

## Recommended Editing Path

Use Layout Manager first for:

- section order and section behavior
- header layout
- production row schema
- downtime row schema
- workbook mapping
- stored-form management

Use Form Calculations for rule and formula behavior.

Raw JSON editing is still available when you need attributes that are easier to adjust directly, but Layout Manager is safer because it validates the shared contract before saving.
