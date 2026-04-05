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

The module details now live under the smaller User Guide section chips in the Help Center so you can jump directly to the page you want instead of reading one long combined document.

- Overview: this page, for the broad workflow and shared notes.
- Production Log: shift entry, downtime balancing, drafts, and Excel import/export behavior.
- Rate Manager: part-number rate maintenance used by Production Log calculations.
- Layout Manager: header layout and workbook mapping editing.
- Settings Manager: defaults, theme behavior, persistence options, and advanced module tools.
- Backup / Recovery: draft recovery, backup restore, and recovery file handling.
- Update Manager: Dispatcher Core version checks, payload downloads, and build-runtime notes.

Use the top User Guide chip first, then use the half-sized section chips directly below it to switch between module guides.

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
- Export writes into the configured base export folder and, when date organization is enabled, uses `YYYY/MM MonthName` subfolders.
- If Export finds an older month folder such as `04`, it renames it to the newer format such as `04 April` before saving the workbook.
- If the sheet is missing time, Export can prompt to auto-balance downtime before writing the workbook.
- If the sheet is already over shift, review or remove downtime manually before export.
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
- Module entries shown as `(external)` in About are currently being loaded from the external `modules` folder instead of the bundled copy.
- Packaged builds include `LICENSE.txt` so the license opens cleanly in Windows.