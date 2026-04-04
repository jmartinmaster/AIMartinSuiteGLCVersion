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
- The header also shows a read-only Target Time field derived from shift hours so the team can see the total minutes they are balancing toward.
- Optional workbook-linked header fields can also display imported summary cells such as bond, percentages, and selected top-part values when they are configured in the layout.
- Production rows capture shop order, part number, and mold count.
- The footer shows a derived Ghost Time value based on the difference between shift time and the combined production-plus-downtime total.
- Ghost Time is an internal balancing aid in the app and is not expected to exist in imported or exported production logs.
- Downtime rows capture start time, stop time, code, and cause.
- Excel export converts downtime stop times into the template's total-minute downtime column, and import converts those minutes back into stop times in the form.
- Balance Downtime is shown directly in the Downtime Issues action row and redistributes the required downtime across existing downtime rows using their current durations as weights. If there is no recorded downtime yet, it falls back to a dedicated adjustment row.
- Calculate All updates efficiency for the current shift.
- Save Draft stores the current work in `data/pending`.
- Overwriting an existing draft keeps a recovery snapshot in `data/pending/history`.
- The draft status strip keeps quick actions for resuming the latest draft, opening the pending-draft list, and launching the full Backup / Recovery viewer.
- Export Excel writes the current session into the configured production template and can immediately open the workbook in the default application for review.
- Open Last Export reopens the most recent exported workbook so it can be checked again before printing.
- Print Last Export sends the reviewed workbook to the default application print action when you are ready to print it.
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
- Enable Screen Transitions turns the page-switch fade on or off.
- Transition Duration controls how long the page-switch fade runs, from `0` to `500` milliseconds.
- Auto Save Interval controls how often draft autosave runs.
- Toast Duration controls how long non-blocking status notifications stay visible.
- Default Shift Hours sets the default value loaded into the production form.
- Default Goal MPH sets the default shift target.
- Export settings control where generated Excel files are written.
- Edit Downtime Codes opens a scrollable dialog for renaming existing downtime code numbers and adding extra numeric codes used by the form and Excel import/export.
- Saving settings also keeps recovery copies under `data/backups/settings`.

### Backup / Recovery

Use Backup / Recovery to inspect saved drafts, recovery snapshots, and JSON backup files.

- Pending Drafts can be resumed directly into Production Log.
- Recovery Snapshots can be restored back into `data/pending` and opened immediately.
- Settings, layout, and rate backups can be restored back into their live JSON files.
- Open Selected File and Open Containing Folder help when you want to inspect recovery files directly in Windows.
- Selection reminders and restore-complete messages use toast notifications instead of blocking dialogs.
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
- Draft saves, imports, and exports now use toast notifications for routine success messages.

If you load a draft or import Excel while unsaved changes exist, the suite asks for confirmation before replacing the current session.

## Excel Import And Export Notes

- Export uses the template path stored in `layout_config.json`.
- If the sheet is not balanced, Export can prompt to auto-balance downtime before writing the workbook.
- After export, the workbook can be opened in the default application for review before using Print Last Export.
- Import reads Excel using the same mapping definitions and reconstructs downtime stop times from the template's total-minute column.
- Production-row import also detects workbook header labels so older logs that store Molds in column F and newer logs that store Molds in column G both load correctly.
- Header fields can be configured as import-only so formula-driven workbook cells can be shown in the app without being overwritten on export.
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

## App Icons

- The app icon files are hard-coded and documented in the App Icons help page.
- Use that page when you need to replace the EXE icon, runtime PNG icon sizes, or the source icon artwork files.

## License Access

- The full GNU GPL license text is available from the Help Center.
- The About screen also provides an Open License button.
- Packaged builds include `LICENSE.txt` so the license opens cleanly in Windows.