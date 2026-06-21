# Layout JSON and Runtime Reference

This page is the single reference for the layout JSON structure and the runtime vocabulary currently recognized by Layout Manager, Form Loader, and Form Calculations.

## JSON Editor Rule

- The JSON Editor now expects one full layout JSON object.
- Save does not recover partial sections from malformed JSON.
- If the JSON is invalid, Save fails and reports the syntax error.
- If the JSON is valid, Save writes the current editor text to disk.

## Required Top-Level Layout Keys

The full layout object must contain these top-level keys:

- `template_path`
- `export_prefix`
- `header_fields`
- `production_row_fields`
- `downtime_row_fields`
- `production_mapping`
- `downtime_mapping`
- `sections`

## sections[] Object Keys

Recognized section keys:

- `id`
- `name`
- `description`
- `fields_key`
- `section_type`
- `behavior_profile`
- `mapping_key`
- `default_max_rows`
- `delete_row_policy`

Recognized `section_type` values:

- `single`
- `repeating`

Behavior profiles with implemented runtime behavior today:

- `header`
- `production`
- `downtime`

Custom `behavior_profile` values can exist in the JSON, but runtime behavior outside the implemented profiles is limited until explicit support is added.

## header_fields[] Keys

Required per header field:

- `id`
- `label`
- `row`
- `col`

Recognized optional header-field keys:

- `width`
- `cell`
- `readonly`
- `default`
- `role`
- `import_enabled`
- `export_enabled`

Recognized historical/core header field ids:

- `date`
- `cast_date`
- `bond`
- `eff_pct`
- `shift`
- `hours`
- `target_time`
- `mtd_pct`
- `goal_mph`
- `total_molds`
- `ret_north`
- `start_time`
- `end_time`
- `ret_south`

Recognized header roles:

- `log_date`
- `cast_date`
- `bond`
- `efficiency_pct`
- `shift_number`
- `shift_hours`
- `target_time`
- `mtd_percentage`
- `goal_rate`
- `total_molds`
- `ret_north`
- `shift_start_time`
- `shift_end_time`
- `ret_south`

## production_row_fields[] and downtime_row_fields[] Keys

Required per row field:

- `id`
- `label`
- `widget`

Recognized optional row-field keys:

- `width`
- `role`
- `readonly`
- `derived`
- `math_trigger`
- `open_row_trigger`
- `user_input`
- `expand`
- `bold`
- `default`
- `sticky`
- `state`
- `options_source`
- `bootstyle`
- `values`

Recognized widget values:

- `entry`: Editable text input cell.
- `display`: Read-only text cell, strictly enforced to be non-editable by the user.
- `checkbutton`: Native interactive checkbox.
- `combobox`: Dropdown selection box.

Recognized historical/core production row field ids:

- `shop_order`
- `part_number`
- `rate_lookup`
- `rate_override_enabled`
- `molds`
- `time_calc`

Recognized production row roles:

- `job_order`
- `part_number`
- `rate_value`
- `rate_override_toggle`
- `mold_count`
- `duration_minutes`

Recognized historical/core downtime row field ids:

- `start`
- `stop`
- `code`
- `cause`
- `time_calc`

Recognized downtime row roles:

- `start_clock`
- `stop_clock`
- `downtime_code`
- `cause_text`
- `duration_minutes`

## Mapping Object Keys

Each mapping object recognizes:

- `start_row`
- `max_rows`
- `columns`

Each `columns` entry can be either a simple column string or an object with these keys:

- `column`
- `import_enabled`
- `export_enabled`
- `import_transform`
- `export_transform`

Recognized import transform values:

- `value`
- `code_lookup`
- `stop_from_duration`

Recognized export transform values:

- `value`
- `code_number`
- `duration_minutes`
- `bool_int`
- `minutes_label`

## Role Normalization Rules

Runtime role normalization currently does this:

- lowercase text
- spaces and hyphens become underscores
- invalid non-alphanumeric characters are removed
- repeated underscores collapse to one underscore

Examples:

- `Shift Number` -> `shift_number`
- `Goal-Rate` -> `goal_rate`
- `Duration Minutes Day` -> `duration_minutes_day`

## Form Loader Calculation Vocabulary

Layout JSON calculations metadata includes:

- `calculations.companion_relative_path`
- `calculations.section_profiles[]`
	- `section_id`
	- `requires_calculations`
	- `calculation_profile`

Save-time transition behavior:

- If a save introduces one or more `section_profiles` that transition from not-required to `requires_calculations=true`, Layout Manager prompts to open Form Calculations.
- Declining that prompt does not block save; it only skips automatic navigation.
- Accepting the prompt opens Form Calculations so formulas and display targets can be configured immediately for the affected sections.

Recognized calculation formula names:

- `production_minutes`
- `shift_total_minutes`
- `shift_start_time`
- `shift_end_time`
- `downtime_minutes`
- `downtime_stop_clock`
- `ghost_minutes`
- `efficiency_pct`

Recognized calculation setting keys in the active calculations profile include:

- `production_minutes_rounding`
- `shift_total_rounding`
- `missing_rate_fallback_mode`
- `missing_rate_fallback_value`
- `allow_overnight_downtime`
- `negative_ghost_mode`
- `default_balance_mix_pct`
- `formulas`

The shift-time defaults also come from the shared shift-time settings used by Form Loader and Data Handler.

## Authoring Notes

- If you add a new field id or role, Layout Manager can store it as long as the JSON is valid.
- Form Loader only performs special runtime behavior for the roles and behavior profiles it explicitly recognizes.
- If a new symbol should affect calculations, workbook import/export, or row behavior, it needs explicit runtime support in code.