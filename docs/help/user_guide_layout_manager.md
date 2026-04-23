# Layout Manager

Use Layout Manager to control how the Production Log header and Excel mapping behave.

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
- Save writes the working layout to the local `layout_config.json`.
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

Changes made here affect both the Production Log form layout and the Excel import/export mapping.

## Create A Form

Use this flow to create a new stored form from your current editor state:

1. Open Layout Manager.
2. (Optional) Make your layout edits first in Block View or JSON Editor.
3. In the Stored Forms row at the top, click Create.
4. Enter a form name when prompted.
5. Enter an optional description.
6. Confirm the prompts.

The app creates a new form using the current in-editor layout, refreshes the form list, and shows a success toast.

To start from scratch instead of copying the current editor content:

1. In the Stored Forms row, click Create Blank.
2. Enter a form name and optional description.
3. The app creates a minimal scaffold form with required repeating-row seed fields and mapping keys so the form is immediately valid and editable.

Related form actions in the same row:

- Activate: Switches the active form to the selected stored form.
- Create Blank: Creates a new minimal scaffold form (empty header section and required repeating-row seed fields) so you can author the layout from scratch in Block View.
- Duplicate: Clones the selected form into a new named form.
- Rename: Changes the selected form name and description.
- Delete: Removes the selected stored form after confirmation.

For a full guided walkthrough and practical authoring patterns, open the Help Viewer section `Layout Manager: Form Creation and Editing`.

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
