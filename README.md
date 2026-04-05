# AIMartinSuiteGLCVersion

The Martin Suite is a desktop production support application for GLC operators. It is built with Python, Tkinter, and ttkbootstrap and is packaged for Windows with PyInstaller.

## Two Working Modes

The project currently operates in two different forms:

- Source / Python mode: the app is run from the Python files in the repository.
- Packaged EXE mode: the app is run from the built standalone Windows executable.

These two forms do not have identical behavior. The Python version has access to the repository files and build tooling, while the EXE version is a packaged release with a more limited update path.

## Shared Capabilities

- Production Log workflow with draft save and reopen support.
- Production Log tracks shop orders, part numbers, and molds during shift entry.
- Automatic recovery snapshots for overwritten drafts.
- Excel export and import support for production sheet work.
- A footer-level Balance Downtime action that fills in missing downtime proportionally across existing downtime rows before export, with a fallback adjustment row when needed.
- Production and downtime sections keep one blank row open automatically while you enter the current shift.
- Exported workbooks can be opened in the default application for review, and the latest export can then be printed from the app once it has been checked.
- A derived target-time field in the header plus a live color-coded Ghost Time indicator in the footer so operators can see missing time in red and extra time in green while entering the sheet.
- Workbook-linked summary header import without overwriting formula cells on export.
- Layout Manager and Rate Manager tools.
- Backup / Recovery viewer for browsing and restoring draft snapshots and configuration backups.
- Settings management for export paths, theme selection, production defaults, and editable downtime code labels.
- Configurable page-transition fades, including the ability to tune the duration or disable them.
- Configurable toast notifications for non-blocking status messages.
- In-app help viewer and About screen.
- Bundled GPL license access from Help Center and About.
- Theme support with readability overrides.
- Rotated backup copies for settings, layout, and rate file saves.
- Hard-coded application icon assets with documented replacement steps.

## Data Safety And Recovery

- `settings.json`, `layout_config.json`, and `rates.json` now save through an atomic write path instead of direct overwrite-only writes.
- Each of those files keeps a local `.bak` recovery copy plus rotated recovery history under `data/backups`.
- Production Log drafts continue to save in `data/pending`, and overwritten drafts now keep recovery snapshots under `data/pending/history`.
- Backup / Recovery gives operators a single place to restore saved drafts, recovery snapshots, and JSON backup copies without using Windows Explorer.

## Source / Python Mode

- Runs directly from the repository source files.
- Can use the local project structure, docs, templates, and module files directly.
- Can be rebuilt locally with `build.py` and PyInstaller.
- Can be used to develop, test, and package new EXE releases.
- The Update Manager can now hand off from source mode by downloading the published packaged EXE into local `dist` and launching it.

## Packaged EXE Mode

- Runs as a standalone Windows executable built by PyInstaller.
- Intended for normal operator use outside the Python development environment.
- Does not have the same direct access to repository source files or local build tooling that the Python version has.
- Bundles the help documentation and `LICENSE.txt` for in-app access.
- Uses the Update Manager for packaged EXE release checks plus selectable module payload installs.
- Packaged builds now use versioned EXE filenames so a newer build can download beside the current one, launch separately, and leave the older copy available until cleanup is confirmed.

## Update Manager Status

- The updater checks only the Dispatcher Core version in `main.py` as the master version.
- The current stable Dispatcher Core release is `1.2.6`.
- Two-part versions such as `1.07` trigger an executable update when greater than the local version.
- Three-part versions only trigger an executable update when the third number is even, such as `1.07.2`.
- Odd patch versions such as `1.07.1` are ignored.
- Update availability now also requires a matching published EXE artifact in `dist/`.
- In Python/source mode, stable updates download the published EXE into local `dist` and launch it for handoff testing.
- In packaged EXE mode, stable updates download a versioned EXE beside the current copy, launch the newer build, and let the newer build offer cleanup of older local EXEs.
- Packaged EXE mode also supports selected module payload installs from the `modules/` package without rebuilding the EXE.
- `main.py` remains the Dispatcher Core boundary and still updates only through the stable EXE release path.
- `About System v1.0.4` is the first planned module payload target for packaged update testing after the `1.2.6` EXE handoff.
