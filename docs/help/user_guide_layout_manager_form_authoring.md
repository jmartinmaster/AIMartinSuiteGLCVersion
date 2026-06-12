# Layout Manager: Form Creation and Editing

Use this guide for a practical start-to-finish authoring workflow when creating or editing stored forms.

The form saved here is the same layout contract that Form Loader loads through the active form registry.

## Quick Start Flow

1. Open Layout Manager.
2. Choose one path:
   - Create: start from your current editor state.
   - Create Blank: start from the minimal scaffold.
3. Enter form name and optional description.
4. Use `Block View` and `Structure > Section Editor` to shape fields and section behavior.
5. Use `Preview > Header Preview` and `Preview > Metadata` to verify placement and mapped metadata.
6. Use `Structure > Validation` to clear issues and warnings.
7. Save, then Activate the form when ready.

## Create vs Create Blank

- Create:
  - Best when you want to branch from an existing draft.
  - Copies current editor content into a new stored form.
- Create Blank:
  - Best when you want a net-new layout.
  - Creates a minimal valid scaffold with required repeating-row seed fields and mapping keys.

## Recommended Editing Order

1. `Structure > Section Editor`:
   - Define sections, section type, behavior profile, and repeating-row delete policy.
2. `Block View`:
   - `Header Fields`: edit header schema rows.
   - `Row Fields`: edit production or downtime row schemas.
   - Add/reorder header fields and row fields.
   - Apply field-level attributes (readonly, role, defaults, triggers, options source).
3. `Import / Export`:
   - `Template Path`: set the workbook path.
   - `Row Mapping`: confirm field-to-column mappings and transform settings.
   - `Status`: review template and mapping summary details.
4. `Preview`:
   - `Header Preview`: confirm visual placement.
   - `Row Sections`: inspect section and field structure.
   - `Metadata`: verify mapped field details and coverage.
5. `Structure > Validation`:
   - Resolve validation issues before save.

## Section Editor Tips

- Keep section ids stable once forms are in use.
- For repeating sections, set delete-row behavior intentionally:
  - Show Delete Button
  - Delete Button Label and Tooltip
  - Require Delete Confirm
- If a repeating section should participate in calculation workflows, ensure its calculations metadata profile marks `requires_calculations` as `true`.
- Save-time behavior: when a save introduces new required-calculation sections, Layout Manager prompts to open Form Calculations so setup can be completed immediately.
- Use Move Up / Move Down in `Structure > Section Editor` to finalize ordering before broad field edits.

## Row Field Tips

- Use role values for semantic behavior and future-proofing.
- Keep section keys, field ids, roles, widgets, and mapping transforms aligned with the syntax Layout Manager and Form Loader recognize.
- Use bulk actions to accelerate repetitive edits:
  - Bulk Rename
  - Bulk Delete Match
  - Bulk Convert Widget

## Preview Metadata Tips

- Click a cell in `Preview > Header Preview` to inspect mapped field details (id, label, cell, role).
- Use `Preview > Metadata` to verify overlap hotspots and missing placement.
- Treat preview as placement validation, not live worksheet data.

## Validation Summary Tips

- Use `Structure > Validation` after each structural change.
- Resolve errors first, then warnings.
- Common cleanup targets:
  - Duplicate ids or ambiguous labels
  - Invalid widget/type combinations
  - Missing mapping coverage for required fields
- Re-check validation after every structural change (section add/remove/reorder).

## Keyboard Workflow

- Ctrl+S: Save quickly from anywhere.
- Escape: Clear active inline focus.
- Ctrl+L: Jump focus to stored form selector.
- Ctrl+Tab / Ctrl+Shift+Tab: Cycle tabs.
- Enter / Shift+Enter: Move down/up one row in active table.
- Alt+Arrow: Move three cells in selected direction.
- Ctrl+Arrow: Move five cells in selected direction.

## Version Safety

- Use Summary tab snapshots before major restructuring:
  - Save Version with a clear label.
  - Restore Latest to recover quickly from bad edits.
- Snapshot before bulk operations and before section reorder passes.

## Common Pitfalls

- Editing mapping first before field ids/roles are stabilized.
- Renaming fields repeatedly without checking dependent mappings.
- Activating a form before preview and validation are clean.
- Skipping snapshot creation before large bulk edits.

## Completion Checklist

- Form created and named correctly.
- Section behavior and delete policy configured.
- Header and row fields reviewed for role and readonly correctness.
- Import/export mapping checked.
- Preview metadata checked for expected cell coverage.
- Validation Summary clear (or warnings accepted intentionally).
- Form saved, then activated.
