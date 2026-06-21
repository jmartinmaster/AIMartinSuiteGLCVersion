# Layout Manager

Use the **Layout Manager** to customize form layouts, field properties, and Excel
mappings for the **Form Loader**.

The interface is divided into six main tabs to keep editing clean and organized.

---

## The Six Main Tabs

1. **JSON Editor**: For editing the raw layout code directly (advanced users).
2. **Block View**: The safest visual editor for adding, removing, and reordering fields.
   - **Header Fields**: Manage shift-level fields (e.g. dates, hours).
   - **Row Fields**: Manage production and downtime table columns.
3. **Import / Export**: Configure how form fields map to Excel columns.
   - **Template Path**: Select the Excel spreadsheet template.
   - **Row Mapping**: Define which field goes to which Excel cell/column.
   - **Status**: View a summary of active columns and row counts.
4. **Preview**: Verify field placements and layout metadata.
   - **Header Preview**: Visual grid showing where header fields will appear.
   - **Row Sections**: Inspect table configurations.
   - **Metadata**: Technical details about cell positions and grid coverage.
5. **Structure**: Edit form behavior and rules.
   - **Section Editor**: Add, remove, or reorder table sections.
   - **Config Nodes**: Technical structure overview.
   - **Guardrails** & **Validation**: Check for errors or warnings in the layout.
6. **Summary**: Save/restore versions and access readability options.

---

## Basic Controls

- **Reload Current**: Discard unsaved edits and reload the active layout.
- **Load Default**: Load the factory-default layout template.
- **Format JSON**: Clean up indentation in the **JSON Editor**.
- **Validate JSON**: Scan the layout for syntax or structure errors.
- **Save**: Write changes to the form file (Default: `layout_config.json`, or a
  custom form file under `data/forms/`).
- **Undo / Redo**: Move backward or forward through your recent edits.

> **Pro Tip:** Toggling a field's **User Input** setting automatically turns off
> its **Derived** setting (and vice versa) to prevent contradictory options.

---

## Form Actions

At the top of the window, you can manage custom forms:
- **Activate**: Set the selected layout as the active form for the app.
- **Create**: Create a new stored form copying your current editor layout.
- **Create Blank**: Create a new blank layout template from scratch.
- **Duplicate**: Clone the selected form into a new layout.
- **Rename**: Change a form's name and description.
- **Delete**: Permanently remove the selected custom form.

---

## Using the Section Editor

Navigate to `Structure > Section Editor` to manage form sections:
- **Add / Remove Section**: Create new tables or delete custom ones.
- **Move Up / Down**: Change the order of sections in the Form Loader.
- **Section Type**: Choose **Single** (one block of fields) or **Repeating** (table rows).
- **Behavior Profile**: Set roles like `header`, `production`, or `downtime`.
- **Row Deletion Policy**: Enable or disable delete buttons and confirmations.

---

## Reusable Presets and Bulk Actions

In `Block View`, you can speed up your workflow:
- **Add Preset Field / Column**: Insert pre-configured fields directly into your layout.
- **Bulk Rename**: Rename multiple fields at once.
- **Bulk Delete Match**: Search and delete multiple fields matching a keyword.
- **Bulk Convert Widget**: Change multiple field widget types (e.g. entry to checkbox).

---

## Version Snapshots

Protect your layout edits in the **Summary** tab:
1. Enter a name in the **Version** box.
2. Click **Save Version** to save a snapshot.
3. Click **Restore Latest** to roll back if a change goes wrong.

---

## Keyboard Shortcuts

- `Ctrl + S`: Quick Save
- `Escape`: Clear active focus
- `Ctrl + L`: Focus the **Stored Forms** selector
- `Ctrl + Tab` / `Ctrl + Shift + Tab`: Cycle through tabs
- `Enter` / `Shift + Enter`: Move down or up one row in tables
- `Alt + Arrow keys`: Move focus 3 cells in that direction
- `Ctrl + Arrow keys`: Move focus 5 cells in that direction

---

## Accessibility Settings

In the **Summary** tab:
- **High Contrast**: Toggles higher contrast for text and focus outlines.
- **Font Profile**: Switch between **Default**, **Lexend**, or **OpenDyslexic**.
- State messages include written `INFO` or `ERROR` prefixes rather than relying on color alone.
