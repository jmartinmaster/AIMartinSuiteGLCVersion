# Settings Manager

Use Settings Manager to configure application defaults.

- Theme controls the UI theme.
- Enable Screen Transitions turns the page-switch fade on or off.
- Transition Duration controls how long the page-switch fade runs, from `0` to `500` milliseconds.
- Auto Save Interval controls how often draft autosave runs.
- Toast Duration controls how long non-blocking status notifications stay visible.
- Default Shift Hours sets the default value loaded into the production form.
- Default Goal MPH sets the default shift target.
- Export settings control where generated Excel files are written.
- Persistent Modules lets you choose which main modules keep their live in-progress state when you navigate away and then return during the same app session.
- Edit Downtime Codes opens a scrollable dialog for renaming existing downtime code numbers and adding extra numeric codes used by the form and Excel import/export.
- Show Advanced Module Tools reveals the external module path and an editor that writes directly to override files in the external `modules` folder.
- Saving settings also keeps recovery copies under `data/backups/settings`.
- When a matching `.py` file exists in the external `modules` folder beside the app, that module is used first automatically; otherwise the bundled module stays in use.

## External Module Notes

- Advanced module editing writes only to the external override folder beside the app.
- Saving an override does not modify the bundled internal module copy.
- Removing an override returns that module to the bundled version on the next reload.
