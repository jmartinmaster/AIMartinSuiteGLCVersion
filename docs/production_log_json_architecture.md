# Production Log JSON Architecture

## Purpose

This note describes the current JSON-driven Production Log architecture for maintainers.

The runtime is now split across a form registry plus two JSON contracts:

- `form_definitions.json` chooses the active form definition and tracks custom forms.
- `layout_config.json` or `data/forms/<form_id>.json` defines the active form layout, row schemas, and workbook mappings.
- `production_log_calculations.json` defines calculation rules and named formulas.

The existing help references explain each file individually. This document covers the ownership split, runtime flow, import/export behavior, and the current evaluator boundaries.

See also:

- `docs/help/form_definitions.md`
- `docs/help/layout_config.md`
- `docs/help/production_log_calculations.md`

## Files And Ownership

- `build.py` bundles the layout JSON, the calculations JSON, the templates folder, and the docs folder into packaged builds.
- `app/utils.py` resolves local external copies before bundled resources, so runtime reads can use a local override when it exists and fall back to the bundled copy otherwise.
- `app/form_definition_registry.py` owns the form registry contract, active-form resolution, custom-form file paths, and per-form backup locations.
- `app/layout_config_service.py` now resolves the active form through `FormDefinitionRegistry` instead of assuming one hardcoded layout file.
- `app/models/production_log_model.py` is the runtime owner of:
  - default calculation settings and named formulas
  - default production and downtime row schemas
  - normalization of loaded layout and calculation payloads
  - formula-aware runtime math such as production minutes, downtime minutes, ghost minutes, and efficiency
  - draft payload construction and draft persistence, now tagged with `form_id` and `form_name`
- `app/models/production_log_calculations_model.py` is the calculations editor model. It imports the canonical defaults from `ProductionLogModel`, exposes editor metadata, normalizes through `ProductionLogModel`, and saves the active profile with backup.
- `app/data_handler_service.py` owns workbook-facing behavior:
  - header normalization
  - shift-window and target-time reconstruction
  - row mapping resolution
  - import/export transforms
  - workbook export and import
  - restricted expression evaluation for named formulas
- `app/views/production_log_view.py` is the JSON-driven renderer for the Production Log screen. It reloads layout config, renders header fields, renders production and downtime rows dynamically, and exposes import/export actions.
- `app/views/layout_manager_view.py` now exposes a form selector and a `Create Form From Current` action so a saved editor state can become a new form definition.

## Form Registry Flow

1. `FormDefinitionRegistry` loads or seeds `form_definitions.json`.
2. The registry resolves the active form to either:
  - `layout_config.json` for the shipped default form, or
  - `data/forms/<form_id>.json` for a custom form.
3. `LayoutConfigService`, `ProductionLogModel`, and `DataHandlerService` all resolve the active layout through that registry.
4. When Layout Manager activates a different form, the dispatcher notifies open modules that implement `on_active_form_changed()`.
5. Production Log auto-saves dirty work to a draft, then rebuilds itself against the new active form.

## Runtime Flow

1. `ProductionLogModel` resolves the active form through `form_definitions.json`.
2. It loads the active layout config and merges any missing production and downtime row fields back onto the built-in defaults so required core row IDs remain present even when the config is partial.
3. `ProductionLogModel` loads `production_log_calculations.json`, normalizes allowed values, and restores missing named formulas from its built-in defaults.
4. `ProductionLogView` asks the model for section field configs and renders:
   - header controls from `header_fields`
   - production rows from `production_row_fields`
   - downtime rows from `downtime_row_fields`
5. The runtime now normalizes optional semantic `role` metadata for header fields and row fields. Core controller/view behavior resolves by role first and falls back to the historical field ids so older local configs still load safely.
6. `DataHandlerService` uses the active calculation settings whenever it normalizes header values, derives shift windows, converts downtime values, and moves data into or out of workbooks.

## Calculation Profile Ownership

The canonical calculation defaults live in `app/models/production_log_model.py`, not in the calculations editor.

The current named formulas are:

- `production_minutes`
- `shift_total_minutes`
- `shift_start_time`
- `shift_end_time`
- `downtime_minutes`
- `downtime_stop_clock`
- `ghost_minutes`
- `efficiency_pct`

The calculations editor model exposes those rules through metadata-driven editor sections called `Behavior Rules`, `Shift Timing`, and `Named Formulas`. Saving writes the normalized profile to the external calculations file and creates a rotating backup.

The practical ownership rule is:

- If the change is about default formulas, default rule values, normalization, or runtime meaning, it belongs in `ProductionLogModel` first.
- If the change is about presenting those values in the editor, it belongs in `ProductionLogCalculationsModel`.

## Import And Export Behavior

Workbook import and export are owned by `app/data_handler_service.py`.

### Export

- Header export uses the `header_fields` cell mappings from `layout_config.json`.
- Production and downtime export use `production_mapping` and `downtime_mapping`.
- Row mappings can be either simple column letters or object-form mappings with:
  - `column`
  - `import_enabled`
  - `export_enabled`
  - `import_transform`
  - `export_transform`
- The current default transforms include downtime code-number export/import lookup and downtime duration-minute export with stop-clock reconstruction on import.

Blank-template export is supported. If `template_path` resolves to an existing workbook, export copies that template first. If `template_path` is blank or does not resolve, `DataHandlerService` creates a new workbook with a single active sheet titled `Production Log` and writes the configured header and row mappings into it.

### Import

- Import opens the workbook twice: once for resolved values and once for raw formulas.
- Header fields are read through their configured cells.
- Production rows and downtime rows are read through their configured mappings.
- Production import also attempts to auto-detect the `shop_order`, `part_number`, and `molds` columns from the row above the configured start row.
- When a mapped cell is empty in the resolved workbook view, the importer can still evaluate a narrow subset of workbook formulas by resolving cell references and `SUM(...)` expressions before evaluating the resulting arithmetic expression.

This keeps import formula-aware for simple mapped sheets without trying to implement full Excel-calculation parity.

## Restricted Formula Evaluator

Named formulas no longer run through raw Python evaluation.

Instead, `app/data_handler_service.py` routes formula text through `app/safe_expression.py`, which parses the expression as an AST and evaluates only a restricted set of nodes.

Allowed runtime formula building blocks:

- constants
- named context values
- arithmetic operators
- comparisons
- boolean operators
- unary operators
- direct calls to approved helper functions

The current helper set includes:

- `if_value`
- `round_minutes`
- `max_value`
- `min_value`
- `abs_value`
- `float_value`
- `int_value`
- `format_clock`

The evaluator rejects unsupported constructs such as:

- attribute access
- arbitrary function calls
- imports
- subscripting
- comprehensions
- lambdas

If evaluation fails or a formula references an unknown name, the caller falls back to a supplied default result. That fallback behavior is part of the current safety model.

This restricted evaluator applies to the named formulas in `production_log_calculations.json`. Workbook-formula import is related but separate: it only supports resolved workbook values plus a limited `SUM` and cell-reference arithmetic path.

## Current Constraints

- Semantic roles now cover the main runtime-sensitive fields, but backward compatibility still depends on the legacy ids as a fallback path for older local configs.
- The current form registry only supports create and activate flows. It does not yet provide rename, duplicate, or delete management for custom forms.
- Some header field IDs still carry built-in model logic even though the fields are declared in JSON. In the current runtime, `cast_date`, `start_time`, `end_time`, and `target_time` are normalized from other header values rather than treated as plain free-text fields.
- Workbook-formula import is intentionally limited. It should be treated as compatibility support for simple mapped sheets, not as a general Excel formula engine.

## Recommended Next Maintainer Steps

1. Keep extending role-based behavior to any remaining runtime paths before introducing field-id-changing custom schemas.
2. Keep recomputing derived values on load rather than treating stored derived labels as authoritative draft data.
3. Treat Ubuntu packaging as a distinct validation path under WSL, because Debian package staging permissions differ from the Windows-mounted workspace semantics.