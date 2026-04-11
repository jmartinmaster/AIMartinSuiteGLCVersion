# Changelog

This changelog tracks the main branch release line for Production Logging Center (GLC Edition).

Version headings below are aligned to the current `2.x` release line used by Dispatcher Core. Earlier work has been grouped into practical release milestones so the shipped feature history is easier to follow without rewriting older module version markers.

## [2.1.0] - 2026-04-10

### Changed

- Completed a full architectural refactor of the entire application codebase following workspace migration.
- Separated all modules into a strict MVC layout with dedicated `app/controllers/`, `app/models/`, and `app/views/` subdirectories; each feature area (About, Help Viewer, Layout Manager, Production Log, Rate Manager, Recovery Viewer, Settings Manager, Update Manager) now has its own isolated controller, model, and view file.
- Extracted data-access logic into a dedicated `DataHandlerService` class (`data_handler_service.py`) with `DataHandler` kept as a thin subclass shim for backwards compatibility.
- Extracted layout configuration persistence into a standalone `LayoutConfigService` class (`layout_config_service.py`).
- Extracted security access-control enforcement into a standalone `SecurityService` class (`security_service.py`) so the vault and session logic in `security.py` remains focused on authentication state.
- Moved security constants, role definitions, access-right maps, and data-class definitions into a dedicated `models/security_model.py` so they are importable without pulling in any Tk or vault logic.
- Extracted update runtime state into `UpdateCoordinator` (`update_state.py`) and update widget bindings into `UpdateStateBindings` (`update_bindings.py`).
- Reduced all top-level app-package entry points (`about.py`, `help_viewer.py`, `layout_manager.py`, `production_log.py`, `rate_manager.py`, `recovery_viewer.py`, `settings_manager.py`, `update_manager.py`) to thin controller-delegation wrappers with no business logic.
- Verified clean import graph across all 54 source files with no circular dependencies and no broken references after the refactor.

## [2.0.4] - 2026-04-10

### Changed

- Promoted Dispatcher Core to stable version `2.0.4` for the external override trust hardening pass and release-polish follow-up.
- Carried the recent theme refresh into the MVC runtime by restoring the Martin Modern Light preset, Martin shell styling tokens, and non-reloading theme application for the shared app shell.
- Added the Total Molds Production Log header field to the MVC runtime, keeping it synchronized with production rows for draft persistence and workbook export.
- Hardened Layout Manager teardown so delayed preview callbacks and page switches do not leave behind stale widget access during unload.
- Added a separate admin-only external override trust toggle so Python override files can exist beside the app without executing until explicitly trusted.
- Changed dispatcher module loading so inactive external overrides no longer take precedence over bundled modules.
- Updated Update Manager payload messaging and local metadata checks so inactive override files are treated as staged artifacts rather than active live module state.
- Added a release regression checklist artifact and refreshed shipped docs to match the staged-versus-trusted override model.
- Verified source-mode startup and targeted runtime trust-boundary checks on Linux; packaged Windows EXE validation remains a manual checklist item.

## [2.0.2] - 2026-04-10

### Changed

- Promoted Dispatcher Core to stable version `2.0.2` for the completed security/admin trust-boundary stage.
- Moved repository controls, advanced packaged dev-update controls, and external module override editing into an admin-only Developer & Admin surface that stays hidden without an authenticated admin session.
- Added persisted advanced packaged dev-update gating and made Update Manager respect the configured repository URL.
- Added persisted non-secure mode administration plus startup state warning through the security flow.
- Hardened vault administration with a destructive reset path that now requires explicit confirmation, typed `RESET`, current-password re-entry, backup creation, non-secure-mode disable, and admin-session invalidation.
- Updated the Help Center and README so shipped guidance reflects the admin-only security and developer-control model.

## [2.0.0] - 2026-04-10

### Changed

- Promoted Dispatcher Core to stable version `2.0.0` for the newest-main integration finish pass.
- Moved the global updater banner above the main content viewport so active update state stays visible while scrolling page content.
- Added dispatcher-owned delayed clearing for successful payload and documentation completion banners so success state clears automatically without hiding warning or error states.
- Flattened Settings Manager into the shared shell viewport so the module whitelist controls no longer sit inside a nested scrolling region.
- Completed the low-risk newest-main parity wave with whitelist controls, developer logging, build icon sync, preserved runtime-state scrubbing, and updater UX cleanup in the current MVC runtime.

## [1.5.6] - 2026-04-05

### Changed

- Promoted Dispatcher Core to stable version `1.5.6` for the grouped documentation restore and Help menu issue-report release.
- Updated `Data Handler` to version `1.1.2` for export-folder naming cleanup under configured base export directories.
- Changed organized exports to use `YYYY/MM MonthName` month folders under the selected base export directory.
- Added automatic migration so a legacy `YYYY/MM` export folder is renamed in place to `YYYY/MM MonthName` when that export month is used.
- Added grouped documentation restores in Update Manager so Help Center markdown files and `LICENSE.txt` can be refreshed without rebuilding the EXE or choosing individual doc files.
- Added a `Report A Problem` Help menu action that opens the GitHub issue creation page.

## [1.5.4] - 2026-04-05

### Changed

- Promoted Dispatcher Core to stable version `1.5.4` for the updater notification and packaged handoff cleanup release.
- Added default-on startup checks for module payload updates, with a one-time legacy fallback when the new preference has not been saved yet.
- Added toast notifications when repository payload restores are available so packaged operators do not need to open Update Manager first.
- Added an `Install All Available Payloads` action in Update Manager to apply all module and JSON payload restores in one pass.
- Cleared stale external module override files before launching downloaded or rebuilt packaged executables so EXE handoff uses the newly bundled modules.

### Notes

- Newer settings files may now include `enable_module_update_notifications`. Older builds can ignore this key safely, but they will not provide the new startup payload check behavior.

## [1.5.2] - 2026-04-05

### Changed

- Promoted Dispatcher Core to stable version `1.5.2` for the shared module viewport scrolling update.
- Added horizontal overflow support to the main dispatcher content canvas so wide pages such as Production Log and Layout Manager scroll instead of clipping content in narrower windows.
- Added shared horizontal mouse-wheel support with `Shift + Mouse Wheel` for the main module viewport.
- Updated the local build flow to archive older versioned EXEs under `dist/Old_exe` and retain up to 10 older builds automatically.

### Notes

- The current `layout_config.json` now expects the config-driven `target_time` header field. Older local builds from before that change may not handle the newer layout file correctly.
- The newer `settings.json` `persistent_modules` entry is safe for older builds to ignore, but those builds will not restore live module state across navigation.

## [1.5.0] - 2026-04-05

### Changed

- Promoted Dispatcher Core to stable version `1.5.0` for the runtime-control and module-source selection release.
- Added settings-controlled module persistence so selected tools can keep their live in-progress state across navigation within the current app session.
- Changed source-build runtime resolution to prefer the suite's own `.venv` before environment-variable or system Python fallbacks.
- Changed external module loading to automatic per-file fallback so a matching file in the external `modules` folder is used first and bundled modules remain active everywhere else.
- Updated About so loaded module entries can show `(external)` when the live module came from the external `modules` folder, even when its version matches the bundled copy.
- Routed Production Log header values through shared normalization so header edits, JSON drafts, and Excel import/export stay formatted consistently, including derived `Target Time`.
- Refactored Production Log UI construction into smaller section builders for safer ongoing edits.
- Added a hidden advanced module editor in Settings so external override files can be reviewed, created, updated, or removed intentionally from the app.
- Hid the footer update status bar whenever the updater is idle and only surface it while an update job is actually active.
- Expanded payload restores so packaged builds can restore tracked JSON files such as `layout_config.json` and `rates.json` from the repository copy while preserving local backups.
- Refreshed the Help Center into a single-page layout with top link navigation, improved readability, and horizontal scrolling for smaller windows.
- Removed the unused `example_modules.py` placeholder so future modules can be added intentionally as needed.

## [1.2.6] - 2026-04-04

### Changed

- Promoted Dispatcher Core to stable version `1.2.6` for the packaged EXE handoff and module-payload release.
- Added a dispatcher-owned persistent update coordinator so the Update Manager can retain release-check state and reopen the same live session.
- Updated packaged releases to preserve side-by-side EXE handoff while keeping Dispatcher Core updates tied to `main.py` and published EXE artifacts.
- Expanded packaged updates so selectable module payloads from `the_golden_standard/` can be downloaded and installed without rebuilding the EXE.
- Prepared `About System v1.0.4` as the first post-EXE module payload target for packaged update verification.

## [1.2.4] - 2026-04-04

### Changed

- Promoted Dispatcher Core to stable version `1.2.4` for the versioned packaged updater release.
- Switched packaged builds to versioned EXE names such as `TheMartinSuite_GLC_v1.2.4.exe`.
- Updated the build flow so preserved versioned EXEs can coexist in `dist` during side-by-side update testing.
- Reworked packaged updates so the newer EXE downloads beside the current one, launches separately, and leaves the older copy available for testing until cleanup is confirmed.
- Extended the updater so source-mode checks now require a published EXE artifact and can download and launch that packaged EXE for handoff testing.
- Added startup detection so newer packaged builds can offer removal of older local EXE versions after side-by-side update testing.

## [1.2.2] - 2026-04-04

### Changed

- Promoted Dispatcher Core to stable version `1.2.2` for the Production Log rate visibility and override release.
- Added a visible per-line rate field in Production Log so operators can confirm the active rate used for each production row.
- Added a per-line temporary override toggle so an incorrect looked-up rate can be corrected for the current row without changing `rates.json`.
- Hardened Production Log rate matching so part numbers still resolve when they differ by case, spacing, or leading-zero formatting.

## [1.2] - 2026-04-04

### Changed

- Promoted Dispatcher Core to stable version `1.2` for the Production Log workflow polish release.
- Restored the splash screen footer so copyright and GPL license text remain visible even when the logo is present.
- Replaced manual Production Log add-row buttons with automatic keep-one-open row behavior for both production and downtime entry.
- Moved Balance Downtime into the main footer action row.
- Updated Ghost Time so missing time is highlighted in red, extra time is highlighted in green, and over-shift cases require manual downtime removal instead of automatic subtraction.

## [1.1.4] - 2026-04-04

### Added

- Added configurable screen-transition controls so the app fade can be tuned or disabled without editing code.
- Added a dedicated App Icons help page describing the hard-coded runtime and packaging icon pipeline.
- Added the source icon artwork files to the tracked asset set alongside the generated icon sizes.

### Changed

- Promoted Dispatcher Core to stable version `1.1.4` after strengthening the default screen fade so module transitions are visibly noticeable out of the box.
- Kept internal helpers such as `utils` and `app_logging` hidden inside the app navigation while allowing the VS Code explorer to show working files normally.
- Added missing version markers to the remaining internal helper modules so version reporting stays complete.
- Expanded the packaged asset bundle so the icon source artwork ships with the rest of the documented icon files.

## [1.1.2] - 2026-04-04

### Changed

- Promoted Dispatcher Core to stable version `1.1.2` after the stricter post-Gemini cleanup pass.
- Removed module reloads from theme preview and theme save so settings changes stop hard-refreshing the active page.
- Added a short fade transition around module switches to reduce visible flashing during screen changes.
- Added lightweight dispatcher-level exception logging for icon setup, preload failures, module load failures, and startup theme reads.
- Updated Settings Manager to use the stable `1.1.2` module marker for the anti-flash theme behavior changes.

### Notes

- This even patch release is intended to remain eligible for the packaged EXE update gate.

## [1.1.1] - 2026-04-04

### Changed

- Advanced Dispatcher Core to development version `1.1.1` for the shared path helper cleanup checkpoint.
- Centralized bundled-versus-local path resolution through a shared helper module and compatibility shim.
- Added review-first export follow-up actions so the latest workbook can be opened and printed separately after validation.
- Completed the remaining path-helper cleanup in layout backup handling and tightened broad exception fallbacks in Production Log.

### Notes

- This odd patch release is intended as a development checkpoint and is ignored by the packaged EXE update gate.

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
- Routed the Production Log Target Time field through `header_fields` so it now saves in draft JSON and participates in the normal workbook header mapping.
- Added a Settings option for keeping selected modules live across navigation so returning to a chosen module restores the same in-progress UI state during the current app session.
- Changed source-build runtime discovery to prefer the suite's own `.venv` before environment-variable or system Python fallbacks.
- Added a Settings-controlled External Module Overrides switch so downloaded or user-supplied files in the external `modules` folder can be activated explicitly instead of always taking precedence.
- Updated About so modules currently loaded from the external `modules` folder are marked with `(external)` even when the version number matches the bundled copy.
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

- Initial release of Production Logging Center (GLC Edition).
- Production Log workflow for shift entry and export handling.
- Dynamic export organization and settings-driven defaults.
- Rate Manager and Layout Manager modules.
- Settings, menus, Excel-oriented data handling, and the core dispatcher workflow.