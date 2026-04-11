
Production Logging Center is a desktop production support application for GLC operators. It is built with Python, Tkinter, and ttkbootstrap and can be packaged as a Windows executable or an Ubuntu Debian package.

## Build Targets

- `build.py` detects the host OS and supports two artifact targets: Windows `.exe` and Ubuntu `.deb`.
- On Windows, running `python build.py` in an interactive terminal now prompts for `Windows (.exe)` or `Ubuntu (.deb via WSL)`.
- Non-interactive invocations still default to the host-native target so existing automated rebuild flows keep working.
- `python build.py --target windows` forces the Windows EXE path.
- `python build.py --target ubuntu` forces the Ubuntu packaging path.
- `python build.py --target ubuntu --wsl-distro Ubuntu-24.04` uses a specific WSL distro when launching the Ubuntu build from Windows.
- Ubuntu packaging expects a Linux Python runtime with `Pillow` and `PyInstaller` available, plus `dpkg-deb` in the selected WSL or Ubuntu environment.
- When the repository lives on a Windows drive such as `D:\`, the selected WSL distro must also expose that drive under `/mnt/<drive-letter>` or the Ubuntu build will stop with a prerequisite error.
- Ubuntu artifacts are written under `dist/ubuntu/`.

## Two Working Modes

The project currently operates in two different forms:

- Source / Python mode: the app is run from the Python files in the repository.
- Packaged EXE mode: the app is run from the built standalone Windows executable.

These two forms do not have identical behavior. The Python version has access to the repository files and build tooling, while the EXE version is a packaged release with a more limited update path.


## Shared Capabilities

- Production Log workflow with draft save and reopen support.
- Production Log tracks shop orders, part numbers, and molds during shift entry.
- Production Log keeps a Total Molds header field in sync with the current production rows and includes it in workbook export.
- Automatic recovery snapshots for overwritten drafts.
- Excel export and import support for production sheet work.
- A footer-level Balance Downtime action that fills in missing downtime proportionally across existing downtime rows before export, with a fallback adjustment row when needed.
- Production and downtime sections keep one blank row open automatically while you enter the current shift.
- Exported workbooks can be opened in the default application for review, and the latest export can then be printed from the app once it has been checked.
- A derived target-time field in the header plus a live color-coded Ghost Time indicator in the footer so operators can see missing time in red and extra time in green while entering the sheet.
- Workbook-linked summary header import without overwriting formula cells on export.
- Layout Manager and Rate Manager tools.
- Shared viewport scrolling keeps wider modules usable in narrower windows instead of clipping the right side of the page.
- Backup / Recovery viewer for browsing and restoring draft snapshots and configuration backups.
- Settings management for export paths, theme selection, production defaults, editable downtime code labels, and per-module live-session persistence.
- Settings Manager now separates general settings from admin-only Developer & Admin tools for repository control, advanced packaged dev updates, external module override trust, and external module override management.
- Configurable page-transition fades, including the ability to tune the duration or disable them.
- Configurable toast notifications for non-blocking status messages.
- Automatic per-file external module overrides when a matching `.py` file exists in the external `the_golden_standard` folder and admin-controlled override trust is enabled.
- In-app help viewer and About screen.
- Help Center navigation now includes top-level guide chips, a Hidden Modules reference, and smaller User Guide section chips for module-specific reading.
- Bundled GPL license access from Help Center and About.
- Theme support with readability overrides, including the Martin Modern Light industrial preset for the shared shell.
- Rotated backup copies for settings, layout, and rate file saves.
- Hard-coded application icon assets with documented replacement steps.


## Data Safety And Recovery

- `settings.json`, `layout_config.json`, and `rates.json` now save through an atomic write path instead of direct overwrite-only writes.
- Each of those files keeps a local `.bak` recovery copy plus rotated recovery history under `data/backups`.
- Production Log drafts continue to save in `data/pending`, and overwritten drafts now keep recovery snapshots under `data/pending/history`.
- Backup / Recovery gives operators a single place to restore saved drafts, recovery snapshots, and JSON backup copies without using Windows Explorer.


## Compatibility Notes

- The current `layout_config.json` routes `target_time` through `header_fields`. Older local builds from before the config-driven Target Time change may not present that field correctly if they reuse the newer layout file.
- The current `settings.json` includes `persistent_modules`. Older builds ignore that key safely, but they do not preserve module state across navigation.


## Source / Python Mode

- Runs directly from the repository source files.
- Can use the local project structure, docs, templates, and module files directly.
- Can be rebuilt locally with `build.py` and PyInstaller.
- Prefers Logging Center's own local `.venv` for source-build runtime discovery before falling back to environment or system Python.
- Can be used to develop, test, and package new EXE releases.
- The Update Manager can now hand off from source mode by downloading the published packaged EXE into local `dist` and launching it.


## Packaged EXE Mode

- Runs as a standalone Windows executable built by PyInstaller.
- Intended for normal operator use outside the Python development environment.
- Does not have the same direct access to repository source files or local build tooling that the Python version has.
- Bundles the help documentation and `LICENSE.txt` for in-app access.
- Uses the Update Manager for packaged EXE release checks plus selectable module payload installs.
- Update checks default to the main repository URL and can be overridden or cleared from Security Admin.
- Uses local editable JSON files and external module override files beside the EXE when they exist.
- Packaged builds now use versioned EXE filenames so a newer build can download beside the current one, launch separately, and leave the older copy available until cleanup is confirmed.
- Local builds now keep the current EXE in `dist/` and archive up to 10 older versioned EXEs in `dist/Old_exe`.
- The footer update status bar now stays hidden unless an update job is actively running.
- Protected security administration now includes persisted non-secure mode, admin-only developer tools visibility, and a hardened vault reset flow with explicit confirmation and backup behavior.
- External Python override files can now be staged beside the app without executing until an admin explicitly enables override trust.

## Installed Ubuntu Package Mode

- The installed Debian package places the application bundle under `/opt/production-logging-center-glc`.
- User-writable runtime files for the installed Linux app are stored under `$XDG_DATA_HOME/production-logging-center-glc` when `XDG_DATA_HOME` is set.
- If `XDG_DATA_HOME` is not set, the installed Linux app stores runtime files under `~/.local/share/production-logging-center-glc`.
- This includes editable JSON files, pending drafts, backups, security data, and external override files used by the installed package.

## Update Manager Status

- The updater checks only the Dispatcher Core version in `main.py` as the master version.
- The current stable Dispatcher Core release is `2.0.4`.
- Two-part versions such as `1.07` trigger an executable update when greater than the local version.
- Three-part versions only trigger an executable update when the third number is even, such as `1.07.2`.
- Odd patch versions such as `1.07.1` are ignored.
- Update availability now also requires a matching published EXE artifact in `dist/`.
- Update Manager defaults to the main repository URL, and the Security Admin developer tools can override or clear it when needed.
- In Python/source mode, stable updates download the published EXE into local `dist` and launch it for handoff testing.
- In packaged EXE mode, stable updates download a versioned EXE beside the current copy, clear stale bundled-module overrides, launch the newer build, and let the newer build offer cleanup of older local EXEs.
- Packaged EXE mode also supports selected module payload installs from the `the_golden_standard/` package without rebuilding the EXE.
- Downloaded or user-supplied module payloads become active automatically for that module when the matching external override file exists.
- Update Manager can now check for available module payload restores at startup and show a toast notification when they are available.
- Update Manager can now install all available module and JSON payload restores in one pass.
- Packaged EXE mode can also restore tracked JSON files such as `layout_config.json` and `rates.json` from the repository copy with local backups preserved before overwrite.
- Packaged EXE mode can also restore the bundled Help Center markdown files and `LICENSE.txt` as one grouped documentation update.
- The updater status bar now mounts above the content viewport and successful module payload installs auto-hide after a short delay.
- `main.py` remains the Dispatcher Core boundary and still updates only through the stable EXE release path.
- `About System v1.0.7` remains the first module payload target for packaged update testing after the `2.0.4` EXE handoff.
- The Help Center now uses a modern single-page layout with top link navigation, a Hidden Modules guide, and section chips for User Guide module pages instead of notebook tabs.
