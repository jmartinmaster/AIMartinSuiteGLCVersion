# Layout Manager

Use Layout Manager to control the active form contract that Form Loader consumes, including sections, field schemas, and Excel mapping behavior.

Layout Manager has six top-level tabs: JSON Editor, Block View, Import / Export, Preview, Structure, and Summary.

The JSON Editor is in its own dedicated tab so raw layout editing is easier to read and review without sharing horizontal space.

Large multi-pane workflows are flattened into inner tabs so editing surfaces do not fight for reserved height inside one viewport:

- Block View: `Header Fields`, `Row Fields`
- Import / Export: `Template Path`, `Row Mapping`, `Status`
- Preview: `Header Preview`, `Row Sections`, `Metadata`
- Structure: `Section Editor`, `Config Nodes`, `Guardrails`, `Validation`

- Block View is the safer editor for field ordering and field-property changes.
- Import / Export is for workbook-oriented template and mapping operations.
- Preview is for placement checks, row-section inspection, and preview metadata review.
- Structure is for section behavior, config-node inspection, guardrails, and validation.
- JSON Editor is the advanced editor for full-file changes.
- Summary contains version snapshots plus accessibility options.
- Reload Current reloads the editable local layout file.
- Load Default restores the packaged baseline layout into the editor.
- Format JSON rewrites the current layout with consistent indentation.
- Validate JSON checks the current layout before you save it.
- Save writes the working layout to the active form file. For the built-in default form that is `layout_config.json`. For custom stored forms that is `data/forms/<form_id>.json`.
- After a successful Save, Layout Manager checks calculations metadata transitions. If one or more sections now require calculations setup, a confirmation dialog offers to open Form Calculations immediately.
- If you choose `Yes`, Layout Manager asks the host shell to open `Form Calculations` so you can configure formulas and display targets for the newly-required sections.
- If you choose `No`, Save still completes normally and you can open Form Calculations later from navigation.
- Save now accepts only valid full-layout JSON. If the JSON is malformed, Save fails with a syntax error instead of extracting partial sections.
- When Save succeeds from the JSON Editor and no visible Block View / Import / Export / Section Editor changes alter the layout, the file is written from the current editor text instead of being rebuilt from hidden defaults.
- When Save detects visible Block View, Import / Export, or Section Editor edits that have not been manually applied yet, those edits are now auto-applied before the file is written.
- Reloading or activating a form now opens the JSON Editor with the saved file text for that form instead of a regenerated JSON dump.
- Undo and Redo let you step backward or forward through recent layout edits.
- `Ctrl+S` triggers Save from anywhere in the Layout Manager window.
- `Escape` clears the current inline focus interaction.
- Keyboard shortcuts:
  - `Ctrl+S` save
  - `Escape` clear current inline focus interaction
  - `Ctrl+L` focus stored form selector
  - `Ctrl+Tab` / `Ctrl+Shift+Tab` cycle Layout Manager tabs
  - `Enter` / `Shift+Enter` move down or up one row in active table
  - `Alt+Arrow` move three cells in the selected direction
  - `Ctrl+Arrow` move five cells in the selected direction

Changes made here affect both the active Form Loader form layout and the Excel import/export mapping for that same form.

## Create A Form

Use this flow to create a new stored form from your current editor state:

1. Open Layout Manager.
2. (Optional) Make your layout edits first in Block View or JSON Editor.
3. In the Stored Forms row at the top, click Create.
4. Enter a form name when prompted.
5. Enter an optional description.
6. Confirm the prompts.

The app creates a new form using the current in-editor layout, refreshes the form list, and shows a success toast. That saved form uses the same schema Form Loader reads through the active form registry.

In the dedicated Qt Layout Manager runtime, the new stored form is selected in the Stored Forms list but does not replace the currently loaded active form until you click `Activate`.

To start from scratch instead of copying the current editor content:

1. In the Stored Forms row, click Create Blank.
2. Enter a form name and optional description.
3. The app creates an empty layout scaffold with the standard top-level containers so you can author the form structure yourself.

That blank form is stored immediately, but it still requires `Activate` before the editor and Save target switch to it.

Related form actions in the same row:

- Activate: Switches the app-wide active form to the selected stored form.
- Create Blank: Creates a new minimal scaffold form (empty header section and required repeating-row seed fields) so you can author the layout from scratch in Block View.
- Duplicate: Clones the selected form into a new named form. The duplicate stays stored-only until you click `Activate`.
- Rename: Changes the selected form name and description.
- Delete: Removes the selected stored form after confirmation.

For a full guided walkthrough and practical authoring patterns, open the Help Viewer section `Layout Manager: Form Creation and Editing`.

For the current one-stop vocabulary reference, open `Layout JSON and Runtime Reference` in the Help Viewer.

## Preview Metadata

- Use `Preview > Header Preview` to inspect placement.
- Click a preview cell to report mapped field metadata in the status line.
- Use `Preview > Metadata` for field-level details (id, label, cell, role) and grid coverage summary.

## Validation Summary

- Use `Structure > Validation` to review live validation status, field-count stats, and current issues or warnings while authoring.

## Section Editor

Use `Structure > Section Editor` to manage section behavior metadata:

- Section: choose which section to edit.
- Add Section: create a new section definition in the layout.
- Remove Section: remove a selected custom section.
- Move Up / Move Down: reorder sections in the saved layout.
- Name and Description: update section labels and helper text.
- Section Type: set single or repeating.
- Behavior Profile: set routing profile (for example header, production, downtime).
- Default Max Rows: applies to repeating sections.
- Show Delete Button: enable or disable inline row delete button for repeating rows.
- Delete Button Label and Tooltip: customize inline button text and help text.
- Require Delete Confirm: prompt user before row deletion.
- Apply Section: save editor changes for the selected section into the current layout.

## Flattened Authoring Layout

- `Block View` uses inner tabs for `Header Fields` and `Row Fields` instead of stacked collapsible sections.
- `Import / Export` uses inner tabs for `Template Path`, `Row Mapping`, and `Status`.
- `Preview` uses inner tabs for `Header Preview`, `Row Sections`, and `Metadata`.
- `Structure` uses inner tabs for `Section Editor`, `Config Nodes`, `Guardrails`, and `Validation`.
- The old `Expand All` / `Collapse All` Block View controls are removed because those panes no longer stack vertically.

## Advanced Row Field Editing

Block View row field editing now supports the extended row-field properties used by runtime logic:

- math_trigger
- open_row_trigger
- user_input
- expand
- bold
- default
- sticky
- state
- options_source
- bootstyle
- values (for combobox fields)

Block View apply behavior:

- `Header Fields > Apply Selected` persists edits to `id`, `label`, position, widget, state, combobox options, and the remaining header-field properties.
- `Header Fields > Add Preset Field` inserts a predefined header field from either the built-in default layout or your custom `editor_presets.header_fields` list. If the preset carries a built-in header role that already exists in the live header list, the added copy is inserted with that role cleared so it can be saved immediately.
- `Row Fields > Apply Selected` persists edits to `id`, `label`, widget, and the remaining row-field properties.
- `Ctrl+Enter` on an editable table applies the selected row or current mapping.
- `Row Fields > Add Blank Field` inserts a new custom column after the current selection.
- `Row Fields > Add Preset Column` inserts a predefined Production or Downtime column from the built-in default layout or your custom `editor_presets.production_row_fields` / `editor_presets.downtime_row_fields` list.
- `Row Mapping > Assign Column` assigns the selected Excel column to the selected mapping row.
- `Row Mapping > Clear Selected` removes the selected mapping row's current column assignment.

Custom reusable presets can now be stored directly in the layout JSON:

- Add an optional top-level `editor_presets` object.
- Supported preset lists are `header_fields`, `production_row_fields`, and `downtime_row_fields`.
- Each preset entry uses the same field-object shape as the matching live section, so your preset can carry default labels, roles, widget settings, combobox `values`, `options_source`, booleans, and other repeatable defaults.
- Presets appear in the Block View selectors with `Built-in` or `Custom` labels.
- Header roles are unique. Only one live header field may own a given non-empty role such as `shift_number` or `log_date`.

Bulk actions are available in Block View for the currently selected row-field section:

- Bulk Rename: replace label text across many row fields at once.
- Bulk Delete Match: remove non-protected row fields by id/label match text.
- Bulk Convert Widget: convert matching row-field widgets from one type to another.

## Version Snapshots

Use the Summary tab to capture and restore versions of a form layout:

1. Enter an optional Version label.
2. Click Save Version to persist a timestamped snapshot.
3. Click Restore Latest to load the most recent snapshot for the active form.

Snapshots are stored under local runtime data and are intended for quick layout history recovery.

## Right-Click Editing

Right-click menus support fast editing in JSON and table/tree surfaces:

- JSON Editor: standard text actions.
- Editable tables: Copy, Cut, Paste, Delete.
- Preview/Structure trees: Copy current row/node text.

Keyboard editing shortcuts for editable tables:

- `Ctrl+C`: Copy selected cells
- `Ctrl+X`: Cut selected cells
- `Ctrl+V`: Paste into the current cell/selection anchor
- `Delete` or `Backspace`: Clear selected cells
- `Ctrl+Enter`: Apply the selected row or current mapping

Dropdown-backed table cells are now used for known enumerated values:

- booleans such as `readonly`, `derived`, `import_enabled`, and `export_enabled`
- header-field `widget`, `state`, and `options_source`
- row-field `widget`
- header-field and row-field `role`
- row-field `sticky`, `state`, `options_source`, and `bootstyle`
- mapping `import_transform` and `export_transform`
- mapping `column` values through the Excel-column selector list

## Accessibility Options

Use the Summary tab accessibility controls to improve readability and keyboard operation:

- High Contrast: toggles high-contrast rendering for text, borders, and focus visuals.
- Font Profile: choose `Default`, `Lexend (if installed)`, or `OpenDyslexic (if installed)`.

Screen-reader and keyboard support improvements include:

- Accessible control names/descriptions for core form selector and editing surfaces.
- Explicit tab-order routing across editor, table, mapping, and structure controls.
- Status messaging now includes `INFO` or `ERROR` text prefixes so state is not color-only.

## Preview Notes

- `Preview > Header Preview` shows configured header positions, not live worksheet data.
- Clicking a preview grid cell reports mapped field metadata in the status line.
- `Preview > Row Sections` shows section/field structure details.
- `Preview > Metadata` shows preview metadata and coverage summary.
- Read-only fields such as Cast Date stay read-only even if they are repositioned.
- Layout changes are picked up immediately by the Python app and by packaged builds that use the external local file.

## Window Scaling

- Layout Manager now scales content width based on available screen and window size.
- On smaller screens, the top-level and inner-tab editor surfaces adapt to reduce clipping and improve readability.

## Import and Export Summary

- The `Import / Export > Status` tab shows a live summary surface for:
  - active template path,
  - production and downtime mapped-column counts,
  - start row and max rows for each mapping section.
- This metadata is cached per session for faster repeated refreshes while authoring mappings.
- Template workbook metadata is scanned in read-only streaming mode and kept in a bounded in-memory cache for repeated analysis in the same session.
- Workbook summary lines include detected sheet count and sampled row activity when the template file is available.

## Table Navigation Tips

- Use `Enter` for quick row-by-row review in the current table.
- Use `Shift+Enter` to reverse direction while staying in-table.
- Use `Alt+Arrow` for short acceleration across dense mapping tables.
- Use `Ctrl+Arrow` for longer jumps in wide tables with many columns.
