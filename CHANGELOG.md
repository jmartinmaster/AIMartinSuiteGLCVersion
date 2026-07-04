# Changelog

This changelog tracks the main branch release line for Production Logging Center (GLC Edition).

Version headings below are aligned to the current `2.x` release line used by Dispatcher Core. Earlier work has been grouped into practical release milestones so the shipped feature history is easier to follow without rewriting older module version markers.

## [2.4.5] - 2026-07-04

### Changed

- **About manifest completeness**:
  - Improved module-version manifest assembly in About so the runtime list remains stable and complete when loading module metadata.
- **Update Manager URL handling hardening**:
  - Kept repository artifact URL resolution tolerant of encoded/quoted path edge cases to prevent malformed remote EXE lookup paths.
- **Version alignment**:
  - Bumped Dispatcher Core to `2.4.5` and incremented affected app module versions for the post-`2.4.4` merge set.

## [2.4.4] - 2026-07-03

### Added

- **Programmatic Accessibility Sweep**:
  - Programmatically set `setAccessibleName` and `setAccessibleDescription` on all interactive buttons, inputs, checklists, table widgets, tab views, and trees across all 8 PyQt6 views.
  - Implemented dynamic header field accessibility labels mapped directly from active JSON form layouts.

### Changed

- **Update Manager URL Quote Stripping**:
  - Stripped single (`'`) and double (`"`) quotes from repository URLs, preventing invalid address errors and restoring update functionality.
- **Form Loader Resilient Fallback**:
  - Configured Form Loader to gracefully fall back to the default shipped form layout (`layout_config.json`) if the selected custom layout is missing or corrupted, preventing application crashes.
- **Documentation Restructuring**:
  - Moved stale/finished documentation files to `docs/Completed Plans/` and updated timelines and version markers in active runbooks.

## [2.4.3] - 2026-06-24

### Added

- **Generic Options Sources**:
  - Added dynamic options source registration, loading, and saving to `app/downtime_codes.py` (storing custom dropdown code lists under `data/forms/op_source/`).
  - Added a dedicated "Options Sources" management layout in Layout Manager UI to create, edit, reorder, and delete custom options lists.
  - Integrated custom options sources lookups into Form Loader comboboxes and checkboxes.
  - Configured Excel import/export value transformations to format codes and descriptions dynamically based on options source configurations in `data_handler_service.py`.
- **Librarian MCP Memory Profiling & Anti-Pattern Presets**:
  - Implemented live Python memory profiling (`profile_memory` tool using `tracemalloc`) in the Project Librarian MCP server for heap statistics and comparisons.
  - Implemented anti-pattern presets configuration (`anti_pattern_search` tool) to define and run workspace searches.
  - Added background thread startup of the Librarian MCP server in `launcher.py` under the `AIMARTIN_START_LIBRARIAN` flag.
- **Form Loader UI Polish**:
  - Replaced the simple "Save Draft" button with a dropdown action menu, adding a "Clear Current Form" utility.

## [2.4.2] - 2026-06-22

### Added

- **Crash Monitoring & Recovery Integration**:
  - Created `app/crash_handler.py` supporting parent-child supervision of the main application process.
  - Implemented crash logging, diagnostic reports (saved to `latest_crash.txt`), and interactive PyQt6 relaunch options.
  - Added crash history viewing and deletion to Settings Manager Developer Tools.
- **Notification Center**:
  - Added a permanent clickable status bar badge indicating notification counts and displaying a historical log modal on click.
- **Layout Manager Comparison & Scanning Tools**:
  - Integrated JSON unified diff layouts, compare reference tabs, and Excel-based keyword scanning in Layout Manager to analyze missing semantic fields.

### Changed

- **Launcher Version Bump**: Bumped Dispatcher Core version to `2.4.2`.
- **Disabled Auto Missing Field Injection**: Bypassed automatic field injection prompts upon form activation to prevent intrusive modal alerts.

## [2.4.1] - 2026-06-22

### Added

- **Collapsible Diagnostics**: Nest 20 diagnostic, configuration, and job fields inside a collapsible `QTreeWidget` with automated height adjustment to prevent wasting vertical screen space.
- **Categorized Payload Tabs**: Organized the module updates view into a `QTabWidget` with four categories: User Facing, Admin, Dev, and Back End modules.
- **Content-Based Update Fallback**: Implemented a fallback update comparison that matches the raw code content of local and remote Python files when their version strings are unversioned (`"Unknown"`).
- **Metadata Definitions**: Declared `__module_name__` and `__version__` tags in `app/app_identity.py`, `app/app_platform.py`, `app/update_bindings.py`, and `app/update_state.py` for correct indexing.
- **Visual Progress Indicator**: Integrated an indeterminate `QProgressBar` in the Update Manager's Runtime Status layout that dynamically displays and animates during background operations.
- **Session Notification History**: Implemented in-RAM logging for all runtime alerts and toast notifications shown during the session.
- **Status Bar Notification Center**: Added a permanent, clickable `Notifications (X)` badge on the right side of the main status bar that triggers a scrollable history modal.
- **Improved Toast Readability**: Expanded toast width bounds (320-500px) and padded internal right margins to prevent text clipping and awkward word wraps.

### Changed

- **UI Layout Optimization**: Relocated the action buttons (Check Repository, Apply Stable Updates, Refresh Status) from the bottom of the Update Manager view to the top.
- **Direct Launcher Version Check**: Directed the core update manager to check `launcher.py` instead of `main.py` for repository version strings, fixing `"Remote version unreadable"` and `"Unknown"` version errors.
- **Launcher Version Bump**: Bumped Dispatcher Core version to `2.4.1` in `launcher.py` and `launcher-HPLaptop.py`.
- **Module Version Bumps**: Bumped Update Manager to `2.1.7` in `app/update_manager.py` and `app/models/update_manager_model.py`.

## [2.4.0] - 2026-06-21

### Added

- **Multi-Format Export Dropdown**:
  - Replaced the "Save Excel" button with a split dropdown button (`QToolButton`), allowing operators to save logs as Excel Workbooks (`.xlsx`), plain text dumps (`.txt`), or Word Documents (`.doc`).
  - Added plain-text summary layout exporter (`_generate_text_dump`) with dynamically aligned column formatting.
  - Added Word Document template layout exporter (`_generate_word_dump`) using custom inline CSS styles for tight page layout and line-heights, optimizing print formatting and saving paper.
- **Unified Document Import**:
  - Replaced the "Import Excel" button with a unified "Import Document" button that parses all three exported formats (Excel, Text, and Word/HTML) and restores the data back into the form fields.
  - Implemented a zero-dependency HTML parser (`WordDumpParser`) to extract headers and tables from exported Word Documents.
  - Implemented character offset parser for plain text files to dynamically detect column boundaries.
- **Form Layout Export Prefix Support**:
  - Moved the configuration of the export prefix out of global settings and into individual layout configuration JSON files (`export_prefix`).
  - Added automated fallback logic to use the active form name as the default prefix when `export_prefix` is omitted or empty.
  - Added visual prompts and folder selector dialogs for blank export prefixes.

### Changed

- **Launcher Version Bump**:
  - Promoted Dispatcher Core to stable version `2.4.0`.
- **Module Version Bumps**:
  - Bumped Form Loader Qt Controller to `1.4.0`.
  - Bumped Form Loader Qt View to `1.4.0`.
  - Bumped Data Handler Service to `1.2.0`.

## [2.3.2] - 2026-06-20

### Added

- **Interactive Task Board**:
  - Implemented the Task Board UI pane in the Project Librarian dashboard, supporting dropdown selection of markdown checklist files.
  - Implemented list creation, item addition, and dynamic checklist status toggling directly from the Web UI.
  - Added checklist sorting to place lists with active/incomplete tasks at the top, and empty or fully-completed checklists at the bottom.
  - Added new REST API endpoints (`/api/tasks`, `/api/tasks/create`, `/api/tasks/add`, and `/api/tasks/toggle`).
- **Index Browser and Full-Code View**:
  - Configured full-file source loading with line numbering, active tab routing, and line highlighting in the Web UI.
- **Server Self-Termination**:
  - Added a "Terminate Server" option in the Web UI.
  - Added the `/api/server/terminate` endpoint to gracefully shutdown the background Project Librarian server.
- **Developer Verification Checklist**:
  - Added `docs/verification_checklist.md` to track verification tasks.

### Changed

- **Launcher Version Bump**:
  - Promoted Dispatcher Core to `2.3.2`.

## [2.3.0] - 2026-06-20

### Added

- **Form Wizard**:
  - Implemented `FormWizardModel`, `FormWizardQtController`, and `FormWizardQtView` providing a step-by-step wizard for configuring new custom forms.
  - Integrated "Create Blank Form Wizard" dialog (`BlankFormWizardDialog`) in Layout Manager to bootstrap header, production, and downtime sections with default schemas.
- **Enhanced JSON Editor in Layout Manager**:
  - Replaced standard text editors with custom `LineNumberPlainTextEdit` to add line numbers and active-line highlighting.
  - Implemented auto-saving and JSON validation on tab switches to prevent switching if code contains invalid syntax.

### Changed

- **Generic Form Loader Layout Handling**:
  - Refactored `ProductionLogQtController` to dynamically load form sections and layouts from generic schema configurations (`set_form_data(payload)`) rather than hardcoding fields.
  - Updated `DataHandlerService` to supply default schemas for production and downtime rows if not specified in the custom JSON.
- **Documentation and UI Assets**:
  - Fully audited and updated Help Center documentation (`docs/help/`) to reflect new Form Wizard and Layout Manager additions.
  - Updated application icons (`assets/icons/`).

## [2.2.7] - 2026-06-19

### Changed

- Audited and updated Help Center documentation files (`user_guide_production_log.md`, `user_guide_layout_manager.md`, `layout_config.md`, `layout_json_and_runtime_reference.md`, `rates_json.md`) to align with current features.
- Fixed Layout Manager save-bypass bug where normalized in-memory configuration comparisons would bypass saving edits to disk.
- Added support for `checkbutton` widget type in repeating rows of Form Loader, rendering it as a native checkbox widget.
- Added readonly enforcement for `display` widget types in repeating rows.
- Implemented dynamic rate-clearing on part number change to automatically trigger recalculation and fresh rate lookups.
- Added override toggling behavior to make the rate cell editable only when the rate override checkbutton is checked.
- Wrapped table item change events in signal blocking to prevent infinite recursion loop bugs.
- Fixed open-row growth logic to check actual widget values and ignore readonly, derived, display, and checkbox/textbox default values, ensuring blank row insertion only occurs on new content.
- Added Browse buttons to each Deferred Runtime Path Override field in Settings Manager Developer Tools, allowing users to select folders via the system directory picker instead of typing paths manually.
- Added `browse_runtime_path(override_key)` to `SettingsManagerQtController` following the established `browse_export_dir` delegation pattern.
- Added `ask_for_runtime_path_directory(override_key)` and `set_runtime_path_override(override_key, path)` view helpers to `SettingsManagerQtView` for controller-delegated directory browsing.
- Incremented individual module version numbers for all files modified in the last 24 hours.

### Fixed

- Resolved infinite loop recursion when changing QTableWidget item flags and values.

## [2.2.4] - 2026-06-12

### Changed

- Promoted Dispatcher Core to `2.2.4` for field-testing readiness after the security policy follow-up.
- Added support for password-optional `general` vaults while keeping `admin` and `developer` vaults password-required.
- Updated Security Admin save flows so password prompts are required only when the selected vault policy requires a password.
- Added a Security Admin UI toggle to explicitly require or remove a password for `general` vaults.
- Kept non-secure-mode auto-provisioning of a fallback `general_default` vault and surfaced its generated credentials when created.

### Notes

- `2.2.4` is an even patch field-testing checkpoint intended for broader runtime validation.
- Validation passed through targeted `py_compile` and problems-panel checks for touched security and settings modules.

## [2.2.3] - 2026-06-12

### Changed

- Promoted Dispatcher Core to `2.2.3` as the current source-side development checkpoint for the multi-form save payload, Layout Manager and Form Loader workflow refinements, and version-marker hygiene pass.
- Adjusted Form Loader multi-file form save behavior so the stored-form payload correctly captures all sections and fields for the full form contract.
- Continued Layout Manager and Form Loader workflow improvements across stored-form selection, layout normalization, section editing, and form management actions.
- Updated Security Service authorization flow so privileged module rights (`security:*`, `developer:*`) now trigger rights-based authentication checks instead of relying only on the protected-module list.
- Updated Security Service authorization flow so all mapped user-facing modules enforce access rights, with non-secure mode bypass limited to an admin-selected module list.
- Removed native security-device verification from vault login flows and moved to password-only vault authentication.
- Enforced password complexity for all vault roles: minimum 8 characters, at least 2 uppercase letters, and at least 1 special character from `!@#$%^&*().`.
- Added developer-only runtime support for updating role default rights while keeping admin sessions read-only for role-default policy changes.
- Added missing `__module_name__` and `__version__` markers to `layout_manager_model.py`, `recovery_viewer_model.py`, `settings_manager_model.py`, and `layout_config_service.py`.
- Bumped version markers across all touched controllers, models, views, and service modules to reflect the current source state.
- Refreshed multi-user migration documentation to reflect implemented vault/session/rights architecture and capture remaining policy decisions needed for full rollout.

### Notes

- `2.2.3` is an odd patch development checkpoint and is not intended to be treated as a packaged stable-update target.
- Validation passed through `Validate Changed UI Modules` and targeted `py_compile` checks on the touched Python files.

## [2.2.1] - 2026-04-23

### Changed

- Promoted Dispatcher Core to `2.2.1` as the current source-side development checkpoint for the stored-form compatibility pass, section-driven Form Loader work, and release-documentation refresh.
- Fixed Form Loader repeating-row auto-growth in the PyQt6 runtime by treating only user-entry/open-row-trigger fields as row content when deciding whether to append or prune rows.
- Removed the unintended extra `Time` display column from the active `production_logging_center_copy` form definition to keep the production row table aligned with the intended operator workflow.
- Added user-facing documentation notes that ADA-aligned accessibility improvements are in progress, are being integrated gradually, and welcome suggestions or contribution support.
- Rebuilt the live `production_log` PyQt6 surface around a stored-form selector plus section-driven rendering for the supported `header`, `production`, and `downtime` behavior profiles.
- Added guarded active-form switching so local and external form changes now share the same save, discard, or cancel flow, reset the selector cleanly on cancel, and keep draft metadata aligned with the active form.
- Renamed user-facing runtime labels from `Production Log` / `Production Log Calculations` to `Form Loader` / `Form Calculations` while intentionally keeping the internal `production_log` family and workbook fallback sheet title compatibility-stable.
- Changed the built-in default form identity to `temp_form_title` / `Temp Form Title` and added alias-backed compatibility for older `production_logging_center` references in stored form state and drafts.
- Expanded Layout Manager authoring so stored-form selection, full-layout JSON saves, preset-field insertion, richer table editing, mapping assignment, and form-management actions work against the same layout contract Form Loader consumes.
- Tightened layout normalization and save behavior so malformed JSON fails fast, current editor text can be saved directly when appropriate, and the runtime no longer silently rebuilds removed sections or fields during normalization.
- Updated Recovery Viewer, Help Viewer, security labels, module registry text, contributor instructions, root README guidance, and current help/runbook docs to reflect the preferred `Form Loader` / `Form Calculations` aliases.

### Notes

- `2.2.1` is an odd patch development checkpoint and is not intended to be treated as a packaged stable-update target.
- Focused validation passed through `Validate Changed UI Modules`, repeated `scripts/run_production_log_smoke.py`, targeted `py_compile`, and markdown problems-panel checks for the touched docs.

## [2.1.5] - 2026-04-12

### Changed

- Promoted Dispatcher Core to `2.1.5` as the current source-side development checkpoint for the privileged-navigation, Production Log refresh, and grouped module-payload pass.
- Added dedicated protected sidebar pages for `Security Admin`, `Developer Tools`, `Internal Code Editor`, and `Production Log Calculations`, with File-menu sign-in and gatekeeper session propagation through the dispatcher shell.
- Updated Settings Manager to keep general application settings in the standard page while exposing security and developer administration through dedicated privileged surfaces.
- Refined Production Log pending-draft behavior so delete confirmation stays parented above the selector window, refresh can redraw header-derived values, and Start Time / End Time remain exportable computed header fields driven by Shift and Hours.
- Expanded Update Manager and external override handling so module payload installs can stage grouped MVC file sets while still presenting as a single module payload.
- Added an external data registry and dispatcher-owned background data-request worker so shared JSON payload discovery, fallback resolution, and startup cache warmup no longer rely on scattered path handling across models.
- Added multi-form layout ownership and active-form-aware layout loading through the form-definition and layout-config services, allowing Create Form groundwork to move beyond a single hardcoded layout source.
- Expanded Layout Manager so create and duplicate form flows can collect descriptions, optionally activate the new form immediately, and edit normalized section metadata for header, production, and downtime sections.
- Split Layout Manager workbook-facing controls into a dedicated `Import / Export` tab, moved template-path editing out of raw JSON-only workflow, and kept Block View focused on schema and field structure updates.
- Made Layout Manager preview less coordinate-first by emphasizing visible field labels while retaining detailed edit metadata in tooltips, and fixed split-surface selection scrolling so each tab scrolls its own canvas correctly.
- Added a lightweight local project librarian CLI that reuses the AST symbol index, catalogs searchable repo text locally, records git-change snapshots, and supports an in-memory REPL for faster repeated lookups.
- Hardened workbook import and export routing so section metadata, field-level toggles, mapping-column toggles, and stale-mapping pruning are enforced through bounded header, production, and downtime profiles, with unsupported future profiles skipped safely and surfaced as warnings.
- Moved Production Log further toward section-aware runtime helpers so row collection, repopulation, open-row behavior, and active-form refresh flows rely less on direct production-versus-downtime list access.
- Refreshed Help Center documentation and module version markers to match the current shell, security, updater, and Production Log behavior.

### Notes

- `2.1.5` is an odd patch development checkpoint and is not intended to be treated as a packaged stable-update target.
- Known follow-up from packaged Ubuntu validation: `production_log_calculations` currently fails to load because `app.models.production_log_calculations_model` imports `DEFAULT_CALCULATION_SETTINGS` from `app.models.production_log_model`, but that constant is not present in the current module.

## [2.1.4] - 2026-04-11

### Changed

- Promoted Dispatcher Core to stable version `2.1.4` for the MVC cleanup and release-documentation refresh.
- Finished the Production Log MVC separation by moving draft persistence, balance state and distribution math, export/open/print actions, and refresh/delete orchestration into controller and model code while keeping the view UI-focused.
- Moved Recovery Viewer restore operations and Settings Manager normalization, downtime-code validation, backup persistence, and external module editor source loading into model-layer code.
- Extracted Update Manager repository parsing, payload scanning and install helpers, stable artifact checks, remote downloads, and source-build filesystem helpers into `app/models/update_manager_model.py`.
- Moved dispatcher shell runtime settings loading, external module override file operations, and obsolete EXE cleanup helpers into `AppModel`.
- Fixed Update Manager runtime repository refresh so it uses the configured repository URL and correctly manages its runtime-settings listener lifecycle.
- Updated release handoff, regression checklist, packaged Windows runbook, and feature-sweep notes to match the current `2.1.4` release state.

### Notes

- This even patch release is intended to remain eligible for the packaged EXE update gate.
- Source diagnostics and byte-compilation passed for the touched Python files; packaged Windows validation remains the final manual release check.

## [2.1.2] - 2026-04-11

### Changed

- Promoted Dispatcher Core to stable version `2.1.2` for the post-refactor runtime stabilization pass.
- Kept focused module launching at the application boundary through `launcher.py --module ...` so the MVC module wrappers remain thin controller delegates.
- Hardened source startup after the MVC split by fixing blank numeric settings handling in Production Log, restoring missing widget/config helpers, and repairing Layout Manager preview/editor initialization.
- Added a background managed-module preloader plus generation-based source invalidation so page switches stay warm while edited files still rebuild on the next visit.
- Corrected Dispatcher Core release metadata resolution so source rebuild/update flows read the canonical version from `launcher.py` instead of attempting to parse `main.py` for a local assignment.
- Refreshed README guidance and the release regression checklist to match the focused-launch workflow and hot-swap-aware preload behavior.

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

## [1.6.0] - 2026-04-07

### Changed

- Promoted Dispatcher Core to stable version `1.6.0` for workbook resource management, build system fix, and version bump.
- Moved update repository configuration and external module editing out of Settings Manager and into Security Admin as developer-only tools.
- Added a persisted non-secure mode so normal visible modules can open without vault prompts while developer tools remain protected behind developer login.
- Restricted developer-vault deletion so only an active developer session can remove a developer vault, including while non-secure mode is enabled.
- Updated the Security Admin dialog to support responsive scrolling, developer login, and the new non-secure mode toggle.
- Updated the update-status banner to mount above the content viewport and auto-hide successful module payload completion messages.
- Refreshed README and Help Center documentation to match the current security and updater workflows.
- Aligned the icon pipeline so packaged builds regenerate `icon.ico` and the runtime PNG icon set from the repository PNG artwork before packaging, while the app now applies the full PNG icon set plus Windows-native icon handles at startup.
- Restored the default Update Repository URL to the main GitHub repository so new main-branch settings and updater fallbacks point back to the published release source.

## [1.5.6] - 2026-04-05

### Changed

- Promoted Dispatcher Core to stable version `1.5.6` for the grouped documentation restore and Help menu issue-report release.
- Updated `Data Handler` to version `1.1.4` for workbook resource management and version bump.
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
- Changed source-build runtime resolution to prefer Logging Center's own `.venv` before environment-variable or system Python fallbacks.
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
- Switched packaged builds to versioned EXE names such as `ProductionLoggingCenter_GLC_v1.2.4.exe`.
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
- Changed source-build runtime discovery to prefer Logging Center's own `.venv` before environment-variable or system Python fallbacks.
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