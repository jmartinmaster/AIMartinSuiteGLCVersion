# The Martin Suite (GLC Edition)

The Martin Suite is a comprehensive desktop application designed for logging Disamatic production and managing manufacturing rates. Built with Python, Tkinter, and `ttkbootstrap`, it provides a modern, dark-theme-friendly interface for floor operators and managers to track production efficiency, manage downtime, and interface directly with Excel reports.

## Features

* **Production Logging (Form 510-09):** Track shop orders, part numbers, and molds produced in real-time.
* **Downtime Tracking:** Log start/stop times and categorize issues (e.g., Machine Repairs, Pattern Changes, No Iron) with automatic time calculation.
* **Live Efficiency (EFF%) Metrics:** Automatically calculate shift efficiency based on target molds per hour (MPH) and shift duration.
* **Dynamic Rate Management:** Add, edit, or remove target rates for specific part numbers.
* **Excel Integration:** 
  * Export production logs to formatted Excel sheets.
  * Import existing Excel sheets to resume or edit logged data.
* **Layout Manager:** A built-in JSON editor to dynamically adjust the UI grid layout of the production form.
* **Theme & Settings Management:** Support for various `ttkbootstrap` themes and customizable default targets.
* **Hot-Swap Repacking:** Built-in utility to bake layout and rate changes directly into a portable standalone executable.

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

The Martin Suite is designed to be bundled into a portable `.exe` for deployment on factory floors without requiring a Python environment. To build the executable, run the included build script:

```bash
python build.py
```

The compiled executable will be located in the `dist/` directory.

## License

Copyright (C) 2026 Jamie Martin

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0**.