# Layout Manager

Use Layout Manager to control how the Production Log header and Excel mapping behave.

Layout Manager has two editor tabs: Block View and JSON Editor.

- Block View is the safer editor for moving fields and updating mapping values.
- JSON Editor is the advanced editor for full-file changes.
- Reload Current reloads the editable local layout file.
- Load Default restores the packaged baseline layout into the editor.
- Format JSON rewrites the current layout with consistent indentation.
- Validate JSON checks the current layout before you save it.
- Update Preview refreshes the live grid preview of the current header layout.
- Save to File writes the working layout to the local `layout_config.json`.
- Saving also keeps recovery copies under `data/backups/layouts`.
- Protected header field ids are `date`, `cast_date`, `shift`, `hours`, `goal_mph`, and `total_molds`.
- `Ctrl+S` triggers save.

Changes made here affect both the Production Log form layout and the Excel import/export mapping.

## Preview Notes

- The preview grid shows configured header positions, not live worksheet data.
- Read-only fields such as Cast Date stay read-only even if they are repositioned.
- Layout changes are picked up immediately by the Python app and by packaged builds that use the external local file.
