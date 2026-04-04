# Changelog

This changelog tracks the main branch release line for The Martin Suite (GLC Edition).

Version headings below are aligned to the current `1.0.x` release line used by Dispatcher Core. Earlier work has been grouped into practical release milestones so the shipped feature history is easier to follow without rewriting older module version markers.

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