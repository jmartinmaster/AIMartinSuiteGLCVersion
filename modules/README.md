# The Martin Suite (GLC Edition)

The Martin Suite is a desktop application for logging Disamatic production, managing rates, editing layout mappings, recovering saved work, and packaging a Windows executable release. Built with Python, Tkinter, and `ttkbootstrap`, it supports both source-based development and a packaged EXE workflow.

## Features

* **Production Logging (Form 510-09):** Track shop orders, part numbers, and molds produced in real-time.
* **Downtime Tracking:** Log start/stop times and categorize issues (e.g., Machine Repairs, Pattern Changes, No Iron) with automatic time calculation.
* **Live Efficiency (EFF%) Metrics:** Automatically calculate shift efficiency based on target molds per hour (MPH) and shift duration.
* **Dynamic Rate Management:** Add, edit, or remove target rates for specific part numbers.
* **Excel Integration:** 
  * Export production logs to formatted Excel sheets.
  * Import existing Excel sheets to resume or edit logged data.
  * Pull workbook summary header fields into Production Log without overwriting formula-driven cells on export.
  * Balance missing downtime against the shift total before export by redistributing time proportionally across existing downtime rows, with a dedicated adjustment row as fallback.
* **Continuous Row Entry:** Production and downtime sections automatically keep one blank row available so operators can continue typing without manually adding rows.
* **Ghost Time Feedback:** The footer highlights missing time in red and extra time in green while leaving overtime cleanup to the operator.
* **Draft Recovery & Restore:** Save drafts, retain recovery snapshots when drafts are overwritten, and restore them from the Backup / Recovery view.
* **Layout Manager:** A built-in JSON editor to dynamically adjust the UI grid layout of the production form.
* **Theme & Settings Management:** Support for curated readable themes, configurable production defaults, and editable downtime code labels.
* **Backup-Aware Saves:** Settings, rates, and layout writes keep `.bak` copies plus rotated backups under `data/backups`.
* **Toast Notifications:** Routine status messages are non-blocking and use a configurable toast duration.
* **Help & License Access:** Built-in Help Center navigation plus bundled GPL license access from Help and About.
* **Backup / Recovery Viewer:** Browse pending drafts, recovery snapshots, and configuration backups from inside the suite.
* **Update Manager:** Shows a compact Dispatcher Core release check and can target packaged EXE updates.

## Prerequisites

Ensure you have Python 3.12+ installed. You will need the following dependencies:

```bash
pip install ttkbootstrap openpyxl pyinstaller
```

## Running the Application

To run the application from the source code, execute the dispatcher core:

```bash
python main.py
```

## Building the Executable

The Martin Suite is designed to be bundled into a standalone `.exe` for deployment on factory floors without requiring a Python environment. To build the executable, run the included build script:

```bash
python build.py
```

The compiled executable will be located in the `dist/` directory as a versioned file such as `TheMartinSuite_GLC_v1.5.4.exe`. Older versioned EXEs are moved into `dist/Old_exe`, where up to 10 archived builds are retained in version order.

## Update Behavior

- Source / Python mode can inspect repository versions and hand off into the published packaged EXE by downloading it into local `dist`.
- Packaged EXE mode uses Dispatcher Core as the master version check.
- The current stable Dispatcher Core release is `1.5.4`.
- Two-part versions such as `1.07` are valid update targets.
- Three-part versions only update when the third number is even, such as `1.07.2`.
- Stable executable updates also require a matching published EXE artifact in `dist/`.
- Packaged EXE updates download a versioned EXE beside the current copy, clear stale bundled-module overrides, launch it, and let the newer build offer cleanup of older local EXEs.
- Packaged EXE mode can also install selected module payload overrides directly from `modules/` without rebuilding the EXE.
- Packaged EXE mode can check for available payload restores at startup and show a toast notification when they are found.
- Packaged EXE mode can also install all available module and JSON payload restores in one pass.
- Packaged EXE mode can also restore tracked JSON files such as `layout_config.json` and `rates.json` from the repository while preserving local backups.
- `main.py` remains outside that payload list and still moves only through the packaged EXE update path.
- The Help Center now uses a single-page document layout with top link navigation and horizontal scrolling for smaller windows.

## License

Copyright (C) 2026 Jamie Martin

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0**. See the `LICENSE.txt` file for the packaged user-facing copy and `LICENSE` for the repository copy.