# Form Loader (production_log) JSON Architecture

## Purpose

This note describes the JSON contracts that Form Loader must consume and the current architectural direction for the PyQt6 runtime.

`Form Loader` is the preferred user-facing alias. The internal `production_log` file, module, and data-family names remain permanent compatibility identifiers.

The key rule is simple:

- The JSON payload emitted by Layout Manager is the JSON payload Form Loader must accept.
- There is not supposed to be a separate Form Loader-only layout dialect.
- If Layout Manager can create, duplicate, normalize, save, and activate a form, Form Loader should be able to load that form through the same contract without manual JSON edits.

This document is the maintainer reference for that contract. The help references remain useful, but the live normalization path in the model and service layers is the authoritative behavior source.

See also:

- `docs/help/form_definitions.md`
- `docs/help/layout_config.md`
- `docs/help/production_log_calculations.md`
- `docs/help/user_guide_layout_manager_form_authoring.md`
- `docs/Plans in Progress or not started/Production Log Upgrade, Layout-System Support, and Rename.md`

## Live State And Current Tranche Direction

The live tree already has the following pieces in place:

- `form_definitions.json` selects the active form and tracks stored custom forms.
- `layout_config.json` or `data/forms/<form_id>.json` already carries section metadata, field metadata, row schemas, workbook mappings, and repeating-row delete policy.
- `production_log_calculations.json` already carries the calculation profile.
- Draft metadata is already form-aware through stored `form_id` and `form_name` values.
- The runtime already understands section-level routing metadata and the supported behavior profiles `header`, `production`, and `downtime`.

The important gap is in the PyQt6 renderer shape:

- The live Form Loader Qt controller and view already consume normalized JSON-backed field configs.
- The live Form Loader Qt view now exposes the fixed top selector shell plus the section-driven body renderer needed to match the Layout Manager output contract.
- The first preferred-alias rollout is live in the runtime and help index surfaces.
- The internal `production_log` family remains permanent even though the runtime now prefers `Form Loader` and `Form Calculations` in user-facing text.

## Contract Priority

When there is a mismatch between documentation and live behavior, use this priority order:

1. `app/models/layout_manager_model.py::normalize_config()` and related authoring helpers define the canonical stored layout shape.
2. `app/models/production_log_model.py` defines the runtime acceptance and normalization path for Form Loader.
3. `app/data_handler_service.py` defines workbook import/export behavior for that accepted shape.
4. `docs/help/layout_config.md` and related help docs are secondary references and must be updated to match the implemented contract.

## Files And Ownership

- `build.py` bundles the layout JSON, calculations JSON, templates, and docs into packaged builds.
- `app/utils.py` resolves local external copies before bundled resources so runtime reads can use local overrides safely.
- `app/form_definition_registry.py` owns the form registry contract, active-form resolution, custom-form paths, and per-form backup locations.
- `app/layout_config_service.py` resolves the active form through `FormDefinitionRegistry` instead of assuming one hard-coded layout file.
- `app/models/layout_manager_model.py` is the authoring-side owner of normalized layout payloads. Its normalization path defines what Layout Manager saves and therefore what Form Loader must accept.
- `app/models/production_log_model.py` is the runtime owner of:
  - accepted layout normalization
  - default section and row-field fallbacks
  - default calculation settings and named formulas
  - role-aware field lookup and compatibility helpers
  - formula-aware runtime math such as production minutes, downtime minutes, ghost minutes, and efficiency
  - draft payload construction and draft persistence tagged with `form_id` and `form_name`
- `app/models/production_log_calculations_model.py` is the calculations editor model. It imports canonical defaults from `ProductionLogModel`, exposes editor metadata, normalizes through `ProductionLogModel`, and saves the active profile with backup.
- `app/controllers/production_log_qt_controller.py` owns Form Loader Qt orchestration, active-form rebuild behavior, draft handling, and module-level workflows.
- `app/views/production_log_qt_view.py` is the PyQt6 presentation layer that consumes model-supplied metadata and renders the Form Loader surface.
- `app/data_handler_service.py` owns workbook-facing behavior:
  - header normalization
  - shift-window and target-time reconstruction
  - row mapping resolution
  - import/export transforms
  - workbook export and import
  - restricted expression evaluation for named formulas
- `app/controllers/layout_manager_qt_controller.py` and `app/views/layout_manager_qt_view.py` are the primary authoring surfaces for the layout JSON that Form Loader consumes.

## Canonical JSON Contracts

The runtime is split across three JSON contracts:

- `form_definitions.json`: chooses the active form definition and tracks custom forms.
- `layout_config.json` or `data/forms/<form_id>.json`: defines the active form layout, section behavior, field schemas, and workbook mappings.
- `production_log_calculations.json`: defines calculation rules and named formulas.

### Form Registry Contract

The form registry contract identifies which layout file is active.

Each stored form record uses the normalized shape below:

- `id`
- `name`
- `description`
- `layout_relative_path`
- `layout_path_mode`
- `built_in`

The registry payload also stores `active_form_id` and `schema_version`.

### Layout Config Contract

Form Loader should accept the same normalized layout payload that Layout Manager saves.

The top-level keys expected by the normalized contract are:

- `template_path`
- `header_fields`
- `production_row_fields`
- `downtime_row_fields`
- `production_mapping`
- `downtime_mapping`
- `sections`

Blank forms created by `LayoutManagerModel.build_blank_form_config()` use this same shape. That means Form Loader must accept:

- the shipped default layout
- custom stored forms created from current state
- blank forms created from the Layout Manager scaffold
- duplicated forms
- forms with reordered sections and reordered fields

### Section Contract

`sections[]` is the canonical routing and rendering contract for the form body.

Each section can define:

- `id`
- `name`
- `description`
- `fields_key`
- `section_type`
- `behavior_profile`
- `mapping_key`
- `default_max_rows`
- `delete_row_policy`

Form Loader must treat section order in `sections[]` as authoritative for rendering order.

The current implemented behavior profiles are:

- `header`
- `production`
- `downtime`

Future profiles may appear in saved JSON. At present they are accepted at schema level but remain warning-capable no-ops until explicit runtime behavior is added.

### Field Contract

`header_fields`, `production_row_fields`, and `downtime_row_fields` define the field schema referenced by the sections.

Form Loader must accept Layout Manager output that includes the normalized field metadata used today, including:

- structural identity such as `id`, `label`, `row`, and `col`
- semantic behavior such as `role`, `readonly`, `derived`, `default`, and `user_input`
- widget behavior such as `widget`, `width`, `state`, `options_source`, `expand`, `sticky`, `bold`, and `bootstyle`
- row behavior such as `open_row_trigger`
- lookup and override metadata such as `lookup_source`, `lookup_key_role`, `override_toggle_role`, and `toggle_target_role`
- workbook participation metadata such as `cell`, `import_enabled`, and `export_enabled`

The runtime resolves behavior by semantic `role` first and falls back to legacy field ids for older configs.

### Mapping Contract

`production_mapping` and `downtime_mapping` define workbook routing for repeating rows.

Each mapping can define:

- `start_row`
- `max_rows`
- `columns`

Each column entry can be either a simple column letter or an object-form mapping that includes:

- `column`
- `import_enabled`
- `export_enabled`
- `import_transform`
- `export_transform`

Form Loader must accept the normalized mapping output that Layout Manager saves, including transform metadata that `DataHandlerService` already understands.

### Calculation Profile Contract

The calculation profile remains separate from layout authoring.

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

If a change affects runtime formula meaning or default normalization, it belongs in `ProductionLogModel` first.

## Acceptance Rules For Form Loader

Form Loader should treat Layout Manager output as accepted input under these rules:

1. Any config that survives `LayoutManagerModel.normalize_config()` and validation is valid Form Loader input.
2. Form Loader must not require a second Form Loader-specific translation format after a form is saved.
3. Section ordering comes from `sections[]`, not from hard-coded UI ordering.
4. Section routing comes from `behavior_profile`, `fields_key`, and `mapping_key`, not from fixed assumptions about only one shipped layout file.
5. Repeating-section delete behavior comes from `delete_row_policy` when the section type is `repeating`.
6. Runtime-sensitive behavior should resolve by `role` first and use legacy field ids only for compatibility fallback.
7. Blank forms and duplicated forms created by Layout Manager must load through the same acceptance path as the default shipped form.
8. Unsupported future behavior profiles must fail safely with warnings rather than partial silent execution.

## Form Registry Flow

1. `FormDefinitionRegistry` loads or seeds `form_definitions.json`.
2. The registry resolves the active form to either:
   - `layout_config.json` for the shipped default form, or
   - `data/forms/<form_id>.json` for a custom form.
3. `LayoutConfigService`, `ProductionLogModel`, and `DataHandlerService` all resolve the active layout through that registry.
4. When Layout Manager activates a different form, the dispatcher notifies open modules that implement `on_active_form_changed()`.
5. Form Loader uses that same active-form contract for local selector changes and external active-form changes.

## Runtime Flow

1. `ProductionLogModel` resolves the active form through `form_definitions.json`.
2. It loads the active layout config and normalizes sections, header fields, row fields, mappings, and compatibility defaults.
3. It loads `production_log_calculations.json`, normalizes allowed values, and restores missing named formulas from built-in defaults.
4. `ProductionLogQtController` and `ProductionLogQtView` consume the normalized contract for the live Form Loader surface.
5. The live runtime now uses the fixed top form-selector shell plus a dynamic body rendered from `sections[]` order.
6. Draft payloads continue to store `form_id` and `form_name` so the runtime can safely reload the correct form context.
7. Form changes with entered data use the guarded prompt flow defined in the current tranche plan: prompt, optionally save, and reload the selected form blank if the switch proceeds.

## Import And Export Behavior

Workbook import and export are owned by `app/data_handler_service.py`.

### Export

- Header export uses the configured header field cell mappings from the accepted layout payload.
- Repeating-row export uses the active section contract to resolve the repeating profiles implemented today.
- The shipped layout still maps production and downtime through `production_mapping` and `downtime_mapping`, but the routing source is the accepted layout contract rather than a single hard-coded layout file assumption.
- If a form declares an unsupported future profile in `sections`, export skips that section safely and records a warning.

Blank-template export is supported. If `template_path` resolves to an existing workbook, export copies that template first. If `template_path` is blank or does not resolve, `DataHandlerService` creates a new workbook with a single active sheet titled `Production Log` and writes the configured header and row mappings into it. That workbook sheet title remains intentionally compatibility-stable even though the runtime prefers the `Form Loader` alias.

### Import

- Import opens the workbook twice: once for resolved values and once for raw formulas.
- Header fields are read through their configured cells.
- Repeating rows are routed through the active layout section contract for implemented profiles.
- Production import still attempts to auto-detect the `shop_order`, `part_number`, and `molds` columns from the row above the configured start row.
- When a mapped cell is empty in the resolved workbook view, the importer can still evaluate a narrow subset of workbook formulas by resolving cell references and `SUM(...)` expressions before evaluating the resulting arithmetic expression.
- If a form declares an unsupported future profile in `sections`, import skips that section safely and records a warning.

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

## Current Support Boundary

- Semantic roles cover the main runtime-sensitive fields, but backward compatibility still depends on legacy ids as a fallback path for older local configs.
- The import/export and runtime-rendering contract is section-driven for implemented profiles, but only `header`, `production`, and `downtime` have runtime behavior today.
- The live PyQt6 Form Loader view now mirrors the supported Layout Manager section contract for the implemented profiles.
- Some header field ids still carry built-in model logic even though the fields are declared in JSON. In the current runtime, values such as `cast_date`, `start_time`, `end_time`, and `target_time` are normalized from other header values rather than treated as plain free-text fields.
- Workbook-formula import is intentionally limited. It should be treated as compatibility support for simple mapped sheets, not as a general Excel formula engine.
- The first preferred-alias rollout is complete in the live runtime, while permanent internal `production_log` identifiers remain unchanged.

## Recommended Maintainer Rules

1. When Layout Manager normalization changes, update Form Loader acceptance behavior and docs in the same effort.
2. Do not introduce a second Form Loader-only JSON layout dialect.
3. Keep extending role-based behavior before depending on field-id-changing custom schemas.
4. Keep recomputing derived values on load rather than treating stored derived labels as authoritative draft data.
5. If a new behavior profile is added in Layout Manager, update all of the following together:
   - `LayoutManagerModel` normalization and validation
   - `ProductionLogModel` acceptance and routing helpers
   - `ProductionLogQtController` and `ProductionLogQtView`
   - `DataHandlerService` import/export routing
   - validation coverage and documentation
6. Treat `docs/help/layout_config.md` as a consumer-facing summary, not the sole contract source, until it is fully aligned with the live section-driven runtime.
