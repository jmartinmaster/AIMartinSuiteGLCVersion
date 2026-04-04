# The Martin Suite User Guide

## What This Program Does

The Martin Suite is a floor-focused desktop application for recording Disamatic production, tracking downtime, managing standard production rates, and exporting the finished shift record into the plant Excel template.

The suite is built around four day-to-day jobs:

1. Fill out the current shift production log.
2. Save and recover draft work during the shift.
3. Maintain part-number rate values used for time and efficiency calculations.
4. Adjust the layout and settings without editing code.

## Main Areas Of The Program

### Production Log

Use Production Log to enter the current shift data.

- Header fields capture shift-level information such as date, cast date, shift, hours, goal MPH, and return counts.
- Production rows capture shop order, part number, and mold count.
- Downtime rows capture start time, stop time, code, and cause.
- Calculate All updates efficiency for the current shift.
- Save Draft stores the current work in `data/pending`.
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

The draft recovery area at the top of Production Log helps prevent lost work.

- Resume Latest loads the newest draft in `data/pending`.
- Browse Drafts opens the full pending-draft list.
- Delete Current Draft removes the active saved draft file.
- The status line shows the latest draft name, current draft name, dirty/saved state, and pending count.

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

Manual JSON editing is still possible, but the built-in editors are safer because they enforce more of the expected structure.

## JSON Reference

Use the other Help tabs for the detailed structure of each JSON file used by the application.