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
- Manage Security opens the admin authentication flow for protected security tasks.
- The Developer & Admin tools row appears only during an active admin session.
- Saving settings also keeps recovery copies under `data/backups/settings`.
- When a matching `.py` file exists in the external `the_golden_standard` folder beside the app, that module is used first automatically; otherwise the bundled module stays in use.

## Security Notes

- Security administration lets an authenticated admin rotate the master password and enable or disable persisted non-secure mode.
- Non-secure mode is a global persisted setting intended only for controlled admin use because it bypasses protected-module authentication.
- Reset Vault is destructive and now requires explicit confirmation, typed `RESET`, and current-password re-entry before the stored master-password vault is removed.

## Developer And Admin Tools

- Developer & Admin tools are hidden from general users and appear only while an admin session is active.
- Repository URL editing and the Advanced Dev Updates toggle now live in this privileged area instead of the ordinary settings form.
- External module override editing also lives in this privileged area.
- External override trust is a separate privileged toggle. Override files can exist on disk without being executed until an admin explicitly enables trust.

## External Module Notes

- External module editing writes only to the external override folder beside the app.
- Saving an override does not modify the bundled internal module copy.
- Saving an override does not make it active by itself; the app only loads external overrides when admin-controlled override trust is enabled.
- Removing an override returns that module to the bundled version on the next reload.
