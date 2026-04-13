# form_definitions.json Reference

`form_definitions.json` is the registry that tells Logging Center which form definitions exist and which one is currently active.

This file sits above the individual layout files:

- `form_definitions.json` decides which form is active.
- `layout_config.json` is the default built-in form layout.
- `data/forms/<form_id>.json` stores custom form layouts created from Layout Manager.

## Top-Level Structure

```json
{
  "schema_version": 1,
  "active_form_id": "production_logging_center",
  "forms": [
    {
      "id": "production_logging_center",
      "name": "Production Logging Center",
      "description": "Default form definition backed by layout_config.json",
      "layout_relative_path": "layout_config.json",
      "layout_path_mode": "local_or_resource",
      "built_in": true
    }
  ]
}
```

## Form Records

Each entry in `forms` describes one available form definition.

Supported keys:

- `id`: stable machine-readable identifier
- `name`: human-readable display name shown in Layout Manager and Production Log status surfaces
- `description`: optional maintainer note
- `layout_relative_path`: path to the layout JSON relative to the app’s external data root
- `layout_path_mode`: `local_or_resource` for the built-in default form, `external` for custom forms
- `built_in`: `true` for the shipped default form, `false` for custom forms

## Active Form Behavior

`active_form_id` controls which form definition is currently live.

When the active form changes:

- Layout Manager reloads the selected form definition unless it has unsaved edits.
- Production Log rebuilds itself against the new layout definition.
- If Production Log has unsaved work, it auto-saves a draft before rebuilding.

## Where Custom Forms Live

Custom forms created from Layout Manager are written to:

- `data/forms/<form_id>.json`

Backups for those custom layout files are written under:

- `data/backups/layouts/<form_id>/`

The shipped default form continues to use `layout_config.json` and its existing backup location.

## Recommended Editing Path

Use Layout Manager for normal form work:

1. Load the current form or the bundled default.
2. Edit the block view or JSON editor.
3. Use `Create Form From Current` to save the current editor state as a new form definition.
4. Use the form selector and `Activate` to switch the live form.
5. Use `Rename`, `Duplicate`, and `Delete` to manage custom form definitions without editing the registry by hand.

Built-in behavior:

- The shipped default form can be activated, previewed, and copied into a new custom form.
- The shipped default form cannot be renamed or deleted.
- Deleting the currently active custom form automatically switches the app back to the default built-in form.

Direct JSON edits are still supported, but Layout Manager is safer because it validates the structure before saving.