# Changelog

This changelog tracks the main branch release line for The Martin Suite (GLC Edition).

Version headings below are aligned to the current `1.x` release line used by Dispatcher Core. Earlier work has been grouped into practical release milestones so the shipped feature history is easier to follow without rewriting older module version markers.

## [1.1] - 2026-04-04

### Changed

- Promoted Dispatcher Core to stable version `1.1`.
- Aligned export folder handling with the Settings toggle so organized exports are written into year folders with month subfolders under the configured base export directory.
- Fixed downtime Excel import/export so the UI keeps using stop times while the template column stores total downtime minutes.
- Added import-only and export-only header field support so workbook summary cells can be shown in Production Log without overwriting formulas on export.
- Extended the default layout with additional workbook-linked header fields including bond, percentages, pattern-change count, and top-part summary values.
- Corrected the downtime code map so code 8 is AMC/SBC/Shakeout and code 9 is Pattern Change across both the UI and Excel import.
- Added a Settings dialog for editing downtime code labels, with overrides stored in `settings.json` and applied immediately to Production Log.
- Made the downtime code editor scrollable, allowed adding extra numeric codes beyond the defaults, and explicitly kept the internal helper out of the sidebar.
- Added a Balance Downtime action in Production Log that redistributes required downtime across existing downtime rows by weighted duration before export, with a dedicated adjustment row as fallback.
- Added a visible Target Time field in the Production Log header, a derived Ghost Time indicator in the footer, and a dedicated Downtime action row so Balance Downtime stays visible during entry.
- Hardened Production Log import so production columns are detected from real workbook headers, which keeps older `F = Molds` logs and newer `G = Molds` logs loading correctly while keeping Ghost internal to the app's balancing workflow.

### Notes

- Updated the touched module version markers for the stable `1.1` release, including Production Log, Data Handler, and Settings Manager.

## [1.0.8] - 2026-04-04

### Added

- Added rotated backup copies for `settings.json`, `layout_config.json`, and `rates.json` saves.
- Added recovery snapshots for overwritten Production Log drafts.
- Added recovery snapshot browsing alongside the active pending-draft list.
- Added a Backup / Recovery viewer for restoring drafts and configuration backups.
- Added a shared persistence helper to keep JSON saves atomic and backup-aware.

### Changed

- Switched settings and rate saves to atomic JSON writes.
- Switched layout saves to the shared backup-aware persistence helper.
- Kept the persistence helper internal and out of the sidebar module list.
- Trimmed Production Log so it keeps draft actions in place while the full restore workflow lives in Backup / Recovery.
- Simplified Update Manager into a compact Dispatcher Core release check.
- Replaced routine informational popups with toast notifications and added a configurable toast duration setting.
- Promoted Dispatcher Core to stable version `1.0.8` for the recovery and UI cleanup release.

## [1.0.6] - 2026-04-04

### Added

- Added Update Manager to the main branch for packaged executable update checks.
- Added `LICENSE.txt` as the packaged user-facing GPL copy.
- Added `LICENSE_HEADER.txt` as the canonical source header reference.

### Changed

- Switched packaging to the spec-driven onefile PyInstaller workflow.
- Bundled modules, help docs, templates, JSON data, and `LICENSE.txt` into the packaged EXE.
- Exposed the GPL license from the Help Center and About screen.
- Updated README and help documentation to explain source mode vs packaged EXE mode.
- Replaced short GPL header markers with the full GPL header block in touched source files.

### Notes

- Packaged EXE self-replacement remains experimental and may still require manual replacement during update testing.

## [1.0.5] - 2026-04-04

### Added

- Added in-app help documentation covering the user guide and JSON reference files.

### Changed

- Expanded packaging support so help documentation ships with the application.
- Improved overall help and guidance coverage for operators using the production tools.

## [1.0.4] - 2026-04-04

### Added

- Added live theme preview support.
- Expanded the layout block editor workflow.

### Changed

- Improved layout editing behavior and general layout manager usability.
- Improved draft recovery and save/reopen behavior in Production Log.
- Cleaned up theme readability for better day-to-day use.

## [1.0.3] - 2026-04-04

### Changed

- Improved rate and layout manager UX.
- Stabilized the layout editor workflow.
- Improved the build workflow used to package Windows releases.

## [1.0.2] - 2026-04-04

### Added

- Added the splash screen module with support for a custom PNG logo.

## [1.0.1] - 2026-04-04

### Added

- Added the repository GPL license file and tightened licensing compliance.

### Changed

- Brought project documentation and distribution materials in line with GPLv3 requirements.

## [1.0.0] - 2026-04-04

### Added

- Initial release of The Martin Suite (GLC Edition).
- Production Log workflow for shift entry and export handling.
- Dynamic export organization and settings-driven defaults.
- Rate Manager and Layout Manager modules.
- Settings, menus, Excel-oriented data handling, and the core dispatcher workflow.