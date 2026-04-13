# production_log_calculations.json Reference

`production_log_calculations.json` controls runtime behavior for Production Log calculations.

This file is separate from `layout_config.json` on purpose:

- `layout_config.json` controls what the UI renders and how workbook columns are mapped.
- `production_log_calculations.json` controls how values are interpreted, rounded, normalized, and calculated.

See also:

- Layout/schema reference: `docs/help/layout_config.md`
- Maintainer architecture note: `docs/production_log_json_architecture.md`

## Top-Level Structure

```json
{
  "production_minutes_rounding": "floor",
  "shift_total_rounding": "nearest",
  "missing_rate_fallback_mode": "header_goal",
  "missing_rate_fallback_value": 240.0,
  "shift_1_anchor_mode": "start",
  "shift_1_reference_time": "0600",
  "shift_2_anchor_mode": "midpoint",
  "shift_2_reference_time": "1800",
  "shift_3_anchor_mode": "end",
  "shift_3_reference_time": "0600",
  "allow_overnight_downtime": true,
  "negative_ghost_mode": "allow_negative",
  "default_balance_mix_pct": 100.0,
  "formulas": {}
}
```

## Behavior Rules

- `production_minutes_rounding`: `floor`, `nearest`, or `ceil`
- `shift_total_rounding`: `floor`, `nearest`, or `ceil`
- `missing_rate_fallback_mode`: `header_goal`, `fixed_value`, or `no_fallback`
- `missing_rate_fallback_value`: numeric MPH used when fallback mode is `fixed_value`
- `shift_1_anchor_mode`, `shift_2_anchor_mode`, `shift_3_anchor_mode`: `start`, `midpoint`, or `end`
- `shift_1_reference_time`, `shift_2_reference_time`, `shift_3_reference_time`: `HHMM`
- `allow_overnight_downtime`: if `true`, downtime can roll across midnight
- `negative_ghost_mode`: `allow_negative` or `clamp_zero`
- `default_balance_mix_pct`: default weighted downtime balance percentage

## Named Formulas

The `formulas` object contains named expressions used by the live Production Log runtime and by workbook import/export transforms.

Current formula names:

- `production_minutes`
- `shift_total_minutes`
- `shift_start_time`
- `shift_end_time`
- `downtime_minutes`
- `downtime_stop_clock`
- `ghost_minutes`
- `efficiency_pct`

Example:

```json
{
  "formulas": {
    "production_minutes": "round_minutes((molds / rate) * 60, production_minutes_rounding)",
    "shift_total_minutes": "round_minutes(hours * 60, shift_total_rounding)",
    "shift_start_time": "format_clock(default_start_minutes)",
    "shift_end_time": "format_clock(default_end_minutes)",
    "downtime_minutes": "if_value(stop_minutes < start_minutes, if_value(allow_overnight_downtime, (stop_minutes + day_minutes) - start_minutes, invalid_value), stop_minutes - start_minutes)",
    "downtime_stop_clock": "format_clock(default_stop_minutes)",
    "ghost_minutes": "shift_total_minutes - production_total_minutes - downtime_total_minutes",
    "efficiency_pct": "if_value((hours <= 0) or (goal_rate <= 0), 0, (total_molds / (hours * goal_rate)) * 100)"
  }
}
```

## Formula Context

The runtime passes different values to each formula depending on what is being calculated.

Common values available to formulas:

- `production_minutes_rounding`
- `shift_total_rounding`
- `allow_overnight_downtime`
- `day_minutes`
- `invalid_value`

Formula-specific context values:

- `production_minutes`: `molds`, `rate`
- `shift_total_minutes`: `hours`
- `shift_start_time`: `shift_anchor_mode`, `anchor_minutes`, `shift_total_minutes`, `default_start_minutes`, `default_end_minutes`
- `shift_end_time`: `shift_anchor_mode`, `anchor_minutes`, `shift_total_minutes`, `default_start_minutes`, `default_end_minutes`
- `downtime_minutes`: `start_minutes`, `stop_minutes`
- `downtime_stop_clock`: `start_minutes`, `duration_minutes`, `default_stop_minutes`
- `ghost_minutes`: `shift_total_minutes`, `production_total_minutes`, `downtime_total_minutes`
- `efficiency_pct`: `total_molds`, `hours`, `goal_rate`

## Formula Helpers

These helper functions are available inside formula expressions:

- `if_value(condition, true_value, false_value)`
- `round_minutes(value, rounding_mode)`
- `max_value(...)`
- `min_value(...)`
- `abs_value(value)`
- `float_value(value, fallback)`
- `int_value(value, fallback)`
- `format_clock(value, fallback)`

## Supported Formula Syntax

Formula expressions are intentionally restricted.

Allowed building blocks:

- Numeric, string, boolean, and `null`-style constants
- Named context values listed above
- Arithmetic operators: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Boolean operators: `and`, `or`, `not`
- Direct calls to the documented helper functions only

Not allowed:

- Attribute access
- Imports
- Indexing or subscripting
- Comprehensions
- Lambdas or arbitrary Python function calls

If a formula uses unsupported syntax or references an unknown name, Logging Center falls back to the default behavior for that calculation.

## Recommended Editing Path

Use Production Log Calculations for normal edits. It loads the active profile, previews the resolved behavior, and writes a backup before saving.

Use Layout Manager when you need to change field order, widget types, workbook mappings, or semantic `role` values.