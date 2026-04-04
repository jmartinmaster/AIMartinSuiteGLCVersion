# The Martin Suite User Guide

## What This Program Does

The Martin Suite is a floor-focused desktop application for recording Disamatic production, tracking downtime, managing standard production rates, and exporting the finished shift record into the plant Excel template.

The suite is built around four day-to-day jobs:

1. Fill out the current shift production log.
2. Save and recover draft work during the shift.
3. Maintain part-number rate values used for time and efficiency calculations.
4. Adjust the layout and settings without editing code.

It also includes a packaged-release Update Manager and direct access to the GPL license from the Help Center and About screen.

## Main Areas Of The Program

### Production Log

Use Production Log to enter the current shift data.

- Header fields capture shift-level information such as date, cast date, shift, hours, goal MPH, and return counts.
- Production rows capture shop order, part number, and mold count.
- Downtime rows capture start time, stop time, code, and cause.
- Calculate All updates efficiency for the current shift.
- Save Draft stores the current work in `data/pending`.
- Overwriting an existing draft keeps a recovery snapshot in `data/pending/history`.
- The draft status strip keeps quick actions for resuming the latest draft, opening the pending-draft list, and launching the full Backup / Recovery viewer.
- Export Excel writes the current session into the configured production template.
- Import Excel loads an existing workbook back into the form.

### Rate Manager

Use Rate Manager to maintain molds-per-hour targets for part numbers.

- Select an existing part to load it into the editor.
- Update the part number or rate and save the change.
- Use Clear to reset the editor without deleting anything.
- Delete removes the selected rate entry.

These rates are used by the Production Log when calculating per-row time and overall shift efficiency.

### Layout Manager

Use Layout Manager to control how the Production Log header and Excel mapping behave.

- Block View is the safer editor for moving fields and updating mapping values.
- JSON Editor is the advanced editor for full-file changes.
- Reload Current reloads the editable local layout file.
- Load Default restores the packaged baseline layout into the editor.
- Save to File writes the working layout to the local `layout_config.json`.

Changes made here affect both the form layout and the Excel import/export mapping.

### Settings Manager

Use Settings Manager to configure application defaults.

- Theme controls the UI theme.
- Auto Save Interval controls how often draft autosave runs.
- Default Shift Hours sets the default value loaded into the production form.
- Default Goal MPH sets the default shift target.
- Export settings control where generated Excel files are written.
- Saving settings also keeps recovery copies under `data/backups/settings`.

### Backup / Recovery

Use Backup / Recovery to inspect saved drafts, recovery snapshots, and JSON backup files.

- Pending Drafts can be resumed directly into Production Log.
- Recovery Snapshots can be restored back into `data/pending` and opened immediately.
- Settings, layout, and rate backups can be restored back into their live JSON files.
- Open Selected File and Open Containing Folder help when you want to inspect recovery files directly in Windows.
- The internal persistence helper powers these saves, but it is intentionally hidden from the sidebar because it is not a user-facing tool.

### Update Manager

Use Update Manager to compare the local Dispatcher Core version with the repository release version.

- Check Repository compares the local Dispatcher version against the current branch version.
- The page is intentionally compact because the updater only evaluates Dispatcher Core, not every sidebar module.
- Two-part versions such as `1.07` can trigger an executable update when greater than the local version.
- Three-part versions only trigger updates when the third number is even, such as `1.07.2`.
- Odd patch versions such as `1.07.1` are ignored.
- In the Python/source workflow, updated EXEs are still best handled by rebuilding manually.
- In the packaged EXE workflow, automatic self-replacement is still experimental and may require manual EXE replacement.

## Typical Workflow

1. Open Production Log at the start of the shift.
2. Enter the date and shift information.
3. Add production rows as jobs are run.
4. Add downtime rows when stoppages occur.
5. Use Save Draft during the shift if you want a manual checkpoint.
6. Resume the latest draft later if the session is interrupted.
7. Use Calculate All to review efficiency.
8. Export Excel when the record is ready.

## Draft Recovery

The draft status area at the top of Production Log helps prevent lost work without duplicating the full recovery page.

- Resume Latest loads the newest draft in `data/pending`.
- Pending Drafts opens a focused list of active draft files.
- Backup / Recovery provides the full restore workspace for recovery snapshots and JSON backups.
- Delete Current Draft removes the active saved draft file.
- The status line shows the latest draft name, current draft name, dirty/saved state, pending count, and recovery count.

If you load a draft or import Excel while unsaved changes exist, the suite asks for confirmation before replacing the current session.

## Excel Import And Export Notes

- Export uses the template path stored in `layout_config.json`.
- Import reads Excel using the same mapping definitions.
- If exported values land in the wrong place, check the mapping docs and Layout Manager.

## Where To Edit JSON Files

- `layout_config.json`: use Layout Manager when possible.
- `settings.json`: use Settings Manager when possible.
- `rates.json`: use Rate Manager when possible.
- Draft files in `data/pending`: normally created and managed by Production Log.
- Recovery copies are stored under `data/backups` and `data/pending/history`.

When you save settings, layout, or rates through the built-in tools, the suite now keeps extra restore copies automatically.

Manual JSON editing is still possible, but the built-in editors are safer because they enforce more of the expected structure.

## JSON Reference

Use the other Help tabs for the detailed structure of each JSON file used by the application.

## License Access

- The full GNU GPL license text is available from the Help Center.
- The About screen also provides an Open License button.
- Packaged builds include `LICENSE.txt` so the license opens cleanly in Windows.