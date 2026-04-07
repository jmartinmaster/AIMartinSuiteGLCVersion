# Production Log

Use Production Log to enter the current shift data.

- Header fields capture shift-level information such as date, cast date, shift, hours, goal MPH, and return counts.
- The header includes a read-only Target Time field derived from shift hours, saved with the draft header data, and routed through the layout config for workbook export/import.
- Optional workbook-linked header fields can also display imported summary cells such as bond, percentages, and selected top-part values when they are configured in the layout.
- Production rows capture shop order, part number, the active rate, a per-line override toggle for temporary corrections, and mold count.
- Production Log automatically keeps one blank production row and one blank downtime row open while you type so you do not need separate add-row buttons during normal entry.
- The footer shows a derived Ghost Time value based on the difference between shift time and the combined production-plus-downtime total.
- Ghost Time shows missing time in red and extra time in green.
- Ghost Time is an internal balancing aid in the app and is not expected to exist in imported or exported production logs.
- Downtime rows capture start time, stop time, code, and cause.
- Excel export converts downtime stop times into the template's total-minute downtime column, and import converts those minutes back into stop times in the form.
- Balance Downtime is shown in the footer action row and redistributes only missing downtime across existing downtime rows using their current durations as weights. If there is no recorded downtime yet, it falls back to a dedicated adjustment row.
- If the sheet is already over shift, Balance Downtime stops and asks you to review or remove downtime manually instead of subtracting downtime automatically.
- Calculate All updates efficiency for the current shift.
- Save Draft stores the current work in `data/pending`.
- Overwriting an existing draft keeps a recovery snapshot in `data/pending/history`.
- The draft status strip keeps quick actions for resuming the latest draft, opening the pending-draft list, and launching the full Backup / Recovery viewer.
- Export Excel writes the current session into the configured production template and can immediately open the workbook in the default application for review.
- Open Last Export reopens the most recent exported workbook so it can be checked again before printing.
- Print Last Export sends the reviewed workbook to the default application print action when you are ready to print it.
- Import Excel loads an existing workbook back into the form.

## Draft Recovery Notes

- Resume Latest loads the newest draft in `data/pending`.
- Pending Drafts opens a focused list of active draft files.
- Backup / Recovery provides the full restore workspace for recovery snapshots and JSON backups.
- Delete Current Draft removes the active saved draft file.
- The status line shows the latest draft name, current draft name, dirty/saved state, pending count, and recovery count.
- Draft saves, imports, and exports use toast notifications for routine success messages.

If you load a draft or import Excel while unsaved changes exist, Logging Center asks for confirmation before replacing the current session.

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
