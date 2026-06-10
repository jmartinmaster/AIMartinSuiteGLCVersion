# PyQt6 Host Migration Master Plan

## Status
- Canonical migration record for the completed PyQt6 host-shell and module migration effort.
- Migration status: completed through Phase 12 in this checkout.
- Maintenance check (2026-06-10): status remains completed; current feature and documentation planning continues in active plan documents and `docs/PLANNING_INDEX.md`.
- Future feature and update planning should live outside this document; use this file as the architecture baseline and historical closeout record.
- Phase 0 COMPLETED.
- Phase 1 Part 1 COMPLETED: dispatcher contract groundwork landed for `get_ui(parent, dispatcher)`, lifecycle hooks, container-neutral active-module state, and explicit active-form signaling.
- Phase 1 Part 2 COMPLETED: the current Tk loader sequence is now split into reusable dispatcher lifecycle helpers so the Qt viewport path can mirror the same steps instead of re-implementing them ad hoc.
- Phase 1 Part 3 COMPLETED: Sections A-D are implemented and validated for the mixed in-process/sidecar migration state.
- Phase 1 Part 3 Section A COMPLETED: the PyQt6 shell now exposes a real shared viewport scaffold and satisfies the dispatcher shell/view contract.
- Phase 1 Part 3 Section B COMPLETED: `_load_module_in_active_viewport()` now routes by active backend and the dispatcher owns the PyQt6 shell startup path.
- Phase 1 Part 3 Section C COMPLETED: `about` now mounts in-process inside the shared Qt viewport without `QtModuleRuntimeManager` or `QtModuleBridgeView`.
- Phase 1 Part 3 Section D COMPLETED: the Qt-side phase-gate validator passes for navigation state, persistence, unload, theme, active-form, protected-module, and mixed-path coexistence checks.
- Phase 2 COMPLETED: the PyQt6 host shell now behaves like the real application shell from the validated mixed migration baseline.
- Phase 2 Section 1 COMPLETED: the PyQt6 host shell now presents viewport and separate-window module state as user-facing shell context instead of runtime-management scaffolding.
- Phase 2 Section 1A COMPLETED: shell chrome refactor landed with viewport-first layout, sidebar collapse, user-facing copy, and a compact module-session panel.
- Phase 2 Section 1B COMPLETED: separate-window controls are now contextual and appear only for active sidecar-backed modules.
- Phase 2 Section 1C COMPLETED: shell title, placeholder, and active-module messaging now reflect real main-workspace versus separate-window context.
- Phase 3 COMPLETED: host adapter and dispatcher routing now use shared dispatcher lifecycle helpers and normalized Qt fallback flow from the completed Phase 2 shell baseline.
- Phase 3 Section 3A COMPLETED: the PyQt6 host adapter now exposes real viewport resize, viewport size, and Qt mousewheel forwarding services for shared-viewport modules.
- Phase 3 Section 3B COMPLETED: remaining Tk-specific shell and load-path behavior has been moved out of the Dispatcher behind host-adapter and shell-view contracts.
- Phase 3 Section 3C COMPLETED: the Qt load path now uses the shared viewport-load lifecycle helpers, and the non-pilot Qt fallback follows the normalized dispatcher flow.
- Phase 4 COMPLETED: low-risk pilot migration now treats `about` as the completed reference and has finished both `help_viewer` and `recovery_viewer` as in-process PyQt6 pilots plus the dedicated Phase 4 validation gate.
- Phase 4 Section 4A COMPLETED: Help Viewer is now the first new Phase 4 in-viewport pilot on the PyQt6 host path while Tk fallback remains intact.
- Phase 4 Section 4A.1 COMPLETED: Help Viewer shim routing and Qt controller/view embedded-mode foundations are in place while the temporary sidecar path remains intact.
- Phase 4 Section 4A.2 COMPLETED: embedded Help Viewer now preserves active document state across theme refresh and lifecycle transitions without joining the active pilot set yet.
- Phase 4 Section 4A.3 COMPLETED: Help Viewer now loads in-process through the normal PyQt6 dispatcher path, and the phase gate validates Help Viewer restore plus mixed coexistence with a sidecar-backed module.
- Phase 4 Section 4B COMPLETED: Recovery Viewer now runs as the second in-process PyQt6 pilot, including Production Log handoff, active-form refresh, and Tk fallback preservation.
- Phase 4 Section 4B.1 COMPLETED: Recovery Viewer shim routing plus embedded Qt controller/view foundations are in place.
- Phase 4 Section 4B.2 COMPLETED: embedded Recovery Viewer action parity now covers refresh, open-file, open-folder, resume, and restore; restore operations remain synchronous for Phase 4 because the existing model path is bounded to local JSON backup writes.
- Phase 4 Section 4B.3 COMPLETED: embedded Recovery Viewer now preserves selection across hide/restore, refreshes on active-form changes, and reapplies theme state in-process.
- Phase 4 Section 4B.4 COMPLETED: `recovery_viewer` now loads through the normal PyQt6 dispatcher path instead of the sidecar fallback.
- Phase 4 Section 4C COMPLETED: validator coverage plus shown-window closeout checks are now green.
- Phase 4 Section 4C.1 COMPLETED: the phase gate now covers both in-viewport pilots, Recovery Viewer restore/selection persistence, mixed coexistence with a sidecar-backed module, and Recovery Viewer active-form refresh behavior.
- Phase 4 Section 4C.2 COMPLETED: compile, phase-gate, and shown-window PyQt6 smoke validation all passed, so Phase 4 is closed.

## Plan Governance
1. This is the canonical completed migration record for the PyQt6 host-shell effort.
2. Do not reopen or extend this document for routine feature planning, release planning, or unrelated enhancements.
3. Existing audits and older migration docs are reference inputs only.
4. Update this document only if migration-closeout facts need correction or if a future architecture effort explicitly supersedes part of this baseline.
5. Operational docs such as validation runbooks and release checklists remain separate because they are execution aids, not migration plans.

## Current State
- The launcher now starts the PyQt6 shell through the Dispatcher instead of bypassing dispatcher lifecycle setup.
- The PyQt6 host shell now satisfies the active shell/view contract directly: menu wiring, update-banner refresh, navigation population, timer callbacks, theme refresh, and close handling.
- The PyQt6 shell layout is now viewport-first and user-facing instead of runtime-diagnostics-first, with sidebar collapse support and a compact module-session panel.
- Separate-window actions are now contextual to active sidecar-backed modules instead of appearing as general shell controls.
- The shell window title, workspace placeholder, and active-module messaging now distinguish clearly between the main workspace and temporary separate-window modules.
- `PyQt6HostUiAdapter` now delegates shared-viewport resize binding and viewport size queries to the real Qt workspace and forwards Qt mousewheel events to scroll targets.
- The PyQt6 shell now emits viewport resize notifications when shell layout changes such as sidebar collapse, banner visibility, or viewport surface switches occur.
- `_load_module_in_active_viewport()` now routes through the live PyQt6 host path, and `layout_manager` remains the explicit dedicated-window exception through `app/layout_manager_dispatcher.py`.
- `about` is the first verified in-process Qt pilot module mounted inside the shared viewport.
- `scripts/validate_pyqt6_phase_gate.py` now provides the repeatable phase-gate validator for Qt-side lifecycle parity and runs without the prior probe-layout warning noise.
- The generic migration-era sidecar stack is removed from the live tree; only the explicit `layout_manager` dedicated runtime contract remains.
- Repository instructions and historical references have been realigned to the completed PyQt6-only architecture.

## Target Architecture
- The application runs as a real in-process PyQt6 shell with a shared central viewport.
- The Dispatcher mirrors the mature Tk module-loading lifecycle on the Qt side.
- Modules continue to enter through `get_ui(parent, dispatcher)`.
- Controllers and models remain backend-neutral where practical; views are free to be backend-specific.
- Every migrated PyQt6 module must match the user-facing behavior of its Tk counterpart.
- No summary modules, reduced-function Qt ports, or reintroduced generic sidecar scaffolding are acceptable.

## Phases

### Phase 0: Canonical Baseline (COMPLETED)
1. Align repository guidance with the target architecture.
2. Mark sidecars as temporary and Tk as transitional.
3. Ensure all planning references point back to this master plan.

### Phase 1: Backend-Neutral Host Contract (COMPLETED)
Part 1 COMPLETED
1. Preserve `get_ui(parent, dispatcher)` as the module entry contract.
2. Preserve and mirror lifecycle hooks: `can_navigate_away()`, `on_hide()`, `on_unload()`, and `apply_theme()`.
3. Add explicit dispatcher signaling for active-form changes so in-process modules do not depend on sidecar polling.

Part 2 COMPLETED
1. Split the current Tk loader sequence into reusable dispatcher lifecycle helpers.
2. Route active-module tracking, persistent-session restore, unload/hide behavior, and post-load theme refresh through the shared helper flow.

Part 3 COMPLETED
Section A: Qt Viewport Host Scaffold
1. Refactor the PyQt6 host shell so it exposes a real shared viewport container instead of only sidecar-management controls and runtime-state panels.
2. Preserve sidebar, menu, status/banner behavior, and active navigation state while introducing the in-process viewport host surface.
3. Exit criteria: the PyQt6 shell can hand a real Qt parent/container to the module-loading path.
4. Status: COMPLETED.

Section B: Dispatcher Qt Load Routing
1. Add a real `_load_module_in_qt_viewport()` path and route `_load_module_in_active_viewport()` by active backend instead of always falling back to Tk.
2. Reuse the shared dispatcher lifecycle helpers for authorization, `can_navigate_away()`, persistent hide, non-persistent unload, cache invalidation, parent container creation, module instantiation, active-module tracking, and `apply_theme()`.
3. Exit criteria: the dispatcher can load a module into a Qt viewport container without using `QtModuleRuntimeManager`.
4. Status: COMPLETED.

Section C: In-Process Pilot Module Path
1. Convert one low-risk module path, preferably About, Help Viewer, or Recovery Viewer, from `QtModuleBridgeView` / dedicated runtime handling to an embeddable in-process Qt path.
2. Keep temporary sidecars only for modules that are not yet ready for viewport hosting.
3. Exit criteria: at least one user-facing module mounts inside the shared Qt viewport through the dispatcher lifecycle path.
4. Status: COMPLETED with `about` as the first in-process pilot.

Section D: Phase-Gate Validation
1. Validate active navigation state, persistent hide/show, non-persistent unload, theme application, active-form notifications where applicable, and protected/security behavior in the Qt host.
2. Confirm the in-process pilot path coexists safely with remaining sidecar-backed modules during the migration window.
3. Exit criteria: Phase 1 Part 3 can be marked COMPLETED and Phase 2 can begin.
4. Status: COMPLETED via `scripts/validate_pyqt6_phase_gate.py`.

### Phase 2: Real PyQt6 Host Shell
1. Refactor the PyQt6 host shell into the real application shell.
2. Replace the sidecar-management content area with a shared Qt viewport.
3. Keep navigation, update banner behavior, lifecycle handling, and theme application at shell level.
4. Ensure pilot modules do not block the Qt main thread.
5. Status: COMPLETED.

Section 1: Shell Chrome Refactor
1. Make the shell viewport-first and user-facing instead of runtime-diagnostics-first.
2. Preserve shell parity items such as sidebar behavior, active navigation state, update banner behavior, and menu integration.
3. Status: COMPLETED.

Section 1A: Viewport-First Shell Layout
1. Reduce always-visible runtime-diagnostics scaffolding and make the shared viewport the dominant workspace.
2. Add core shell chrome parity such as sidebar collapse and user-facing shell copy.
3. Status: COMPLETED.

Section 1B: Contextual External-Window Session State
1. Keep temporary sidecar-backed modules functional without presenting the shell as a runtime-manager console.
2. Represent external-window module state as contextual shell state rather than as the primary shell content.
3. Status: COMPLETED.

Section 1C: Active Module Shell Context
1. Finish shell-level title, placeholder, and active-module messaging parity for both in-viewport and temporary sidecar-backed modules.
2. Remove remaining migration-scaffolding wording from user-facing shell surfaces where the host should behave like the real application shell.
3. Status: COMPLETED.

### Phase 3: Host Adapter And Dispatcher Routing
1. Complete `PyQt6HostUiAdapter` services needed by shared-viewport modules.
2. Split Tk-specific loading logic out of the Dispatcher.
3. Add a real `_load_module_in_qt_viewport()` path that mirrors the mature Tk loader.

Section 3A: PyQt6 Host Adapter Completion
1. Complete the Qt-side adapter services that shared-viewport modules depend on, including viewport resize binding, viewport size queries, and wheel-forwarding behavior.
2. Wire the PyQt6 host shell so those adapter services operate on the real shared workspace instead of generic top-level window measurements.
3. Status: COMPLETED.

Section 3B: Dispatcher Tk-Logic Extraction
1. Move remaining Tk-specific shell behavior such as direct `root.after(...)`, alpha-transition handling, and Tk-specific container creation out of the backend-neutral dispatcher flow.
2. Keep Dispatcher focused on lifecycle sequencing and let backend-specific shell behavior live behind host-adapter and shell-view contracts.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/host_ui_adapter.py`, `app/views/pyqt6_host_shell_view.py`, and `app/controllers/app_controller.py`; `scripts/validate_pyqt6_phase_gate.py` passed.
5. Deferred to Section 3C: shared load-path preamble extraction and full Tk/Qt viewport lifecycle normalization. No known Phase 3B regressions are currently tracked.

Section 3C: Qt Viewport Load Normalization
1. Normalize the Qt in-viewport load branch so it uses the same lifecycle sequencing as the mature Tk loader for navigate-away checks, deactivation, persistent restore, container creation, instantiation, and finalization.
2. Keep sidecar fallback only for non-pilot Qt modules while `about` remains the sole in-process pilot during Phase 3.
3. Status: COMPLETED.
4. Slice 1 complete: Dispatcher now uses a shared viewport-load preamble for Tk and Qt load paths, and both Tk plus Qt in-viewport loading now route through the same shared viewport loader.
5. Slice 2 complete: the non-pilot Qt sidecar fallback now follows an explicit prepare, launch, and finalize dispatcher flow instead of keeping its end-state inline inside `_load_module_in_qt_viewport()`.
6. Validation: `py_compile` passed for `app/controllers/app_controller.py` and `app/views/pyqt6_host_shell_view.py`; `scripts/validate_pyqt6_phase_gate.py` passed after both slices.
7. No known Phase 3C regressions are currently tracked.

### Phase 4: Low-Risk Pilot Modules
1. Treat `about` as the completed in-process reference pilot and use this phase to migrate `help_viewer` and `recovery_viewer` into true in-process PyQt6 viewport modules.
2. Keep Tk fallback intact while each pilot module moves from sidecar-oriented Qt flows to embedded Qt viewport flows.
3. Verify navigation, persistence behavior, unload/hide behavior, theme refresh, active-form signaling where applicable, and mixed-session stability before Phase 5.
4. Status: COMPLETED.

Section 4A: Help Viewer In-Viewport Pilot
1. Convert Help Viewer from a sidecar-oriented Qt path into an embeddable in-process Qt viewport module using the About pilot pattern.
2. Keep the temporary sidecar path intact until embedded routing, lifecycle parity, and validation are stable.
3. Status: COMPLETED.

Section 4A.1: Embedded Foundation
1. Add conditional shim routing and embedded-mode support to the Help Viewer Qt controller and Qt view without changing the active pilot set yet.
2. Preserve sidecar compatibility while the embedded path is being prepared.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/help_viewer.py`, `app/controllers/help_viewer_qt_controller.py`, and `app/views/help_viewer_qt_view.py`; import checks passed; `scripts/validate_pyqt6_phase_gate.py` passed.

Section 4A.2: Lifecycle And Theme Parity
1. Preserve selected-document state, persistent hide/restore behavior, and theme refresh in the embedded Help Viewer path.
2. Remove sidecar-only assumptions from the embedded Qt path, including command polling and unload behavior.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/controllers/help_viewer_qt_controller.py` and `app/views/help_viewer_qt_view.py`; an embedded-mode smoke test verified active-document, scroll-position, and dispatcher-open behavior across `apply_theme()`; `scripts/validate_pyqt6_phase_gate.py` passed.

Section 4A.3: Help Viewer Pilot Cutover
1. Enable Help Viewer as an active in-viewport pilot on the PyQt6 host path.
2. Expand validation coverage so Help Viewer participates in the Phase 4 gate without breaking mixed in-viewport plus sidecar sessions.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/controllers/app_controller.py`, `scripts/validate_pyqt6_phase_gate.py`, `app/help_viewer.py`, `app/controllers/help_viewer_qt_controller.py`, and `app/views/help_viewer_qt_view.py`; `Validate Changed UI Modules` passed for `help_viewer`; `scripts/validate_pyqt6_phase_gate.py` passed with Help Viewer viewport routing, persistent restore, and mixed coexistence coverage.

Section 4B: Recovery Viewer In-Viewport Pilot
1. Convert Recovery Viewer from a sidecar-oriented Qt path into an embeddable in-process Qt viewport module while preserving backend-neutral model behavior.
2. Keep cross-module Production Log coordination and active-form refresh behavior correct during the migration.
3. Status: COMPLETED.

Section 4B.1: Read-Only Embedded Foundation
1. Add conditional shim routing and embedded-mode support to the Recovery Viewer Qt controller and Qt view.
2. Limit the first Recovery slice to rendering, selection, and refresh before restore/resume actions are cut over.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/recovery_viewer.py`, `app/controllers/recovery_viewer_qt_controller.py`, and `app/views/recovery_viewer_qt_view.py`; `scripts/validate_module_loads.py recovery_viewer help_viewer production_log` passed.

Section 4B.2: Action Parity
1. Cut over open-file, open-folder, resume, and restore actions for the embedded Recovery Viewer path.
2. Explicitly resolve whether restore operations remain synchronous or move to a worker-backed path before pilot cutover.
3. Status: COMPLETED.
4. Decision: restore operations remain synchronous in Phase 4 because the current model path performs bounded local JSON backup writes and the targeted embedded smoke test stayed responsive; worker-backed restore remains a future optimization rather than a migration blocker.

Section 4B.3: Lifecycle And Signaling Parity
1. Preserve Recovery Viewer theme refresh, persistent hide/restore behavior, and `on_active_form_changed()` signaling in the in-process path.
2. Validate that Recovery Viewer still cooperates correctly with mixed sidecar-backed modules such as `production_log`.
3. Status: COMPLETED.
4. Validation: the expanded phase gate now verifies Recovery Viewer persistent restore, mixed coexistence with sidecar-backed `production_log`, and hidden-module active-form refresh behavior.

Section 4B.4: Recovery Viewer Pilot Cutover
1. Enable Recovery Viewer as an active in-viewport pilot on the PyQt6 host path.
2. Remove module-local sidecar dependence from the normal PyQt6 host path while keeping Tk fallback intact.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/recovery_viewer.py`, `app/controllers/app_controller.py`, `app/controllers/recovery_viewer_controller.py`, `app/controllers/recovery_viewer_qt_controller.py`, `app/views/recovery_viewer_qt_view.py`, `app/controllers/production_log_qt_controller.py`, `app/views/pyqt6_host_shell_view.py`, and `scripts/validate_pyqt6_phase_gate.py`; `scripts/validate_module_loads.py recovery_viewer help_viewer production_log` passed; `scripts/validate_pyqt6_phase_gate.py` passed with Recovery Viewer pilot coverage; an embedded Recovery Viewer smoke test passed.

Section 4C: Phase 4 Gate And Closeout
1. Expand the PyQt6 phase gate to cover Help Viewer and Recovery Viewer as in-viewport pilots.
2. Run the compile, validator, and shown-window smoke checks needed to close the phase cleanly.
3. Status: COMPLETED.

Section 4C.1: Validator Expansion
1. Extend `scripts/validate_pyqt6_phase_gate.py` to cover Help Viewer and Recovery Viewer in-viewport pilot behavior, mixed-session stability, and Recovery Viewer active-form refresh behavior.
2. Keep the validator useful for both in-viewport pilots and remaining sidecar-backed modules.
3. Status: COMPLETED.
4. Validation: `scripts/validate_pyqt6_phase_gate.py` now passes with 10 checks covering Help Viewer restore, Recovery Viewer restore, Recovery Viewer active-form refresh, protected/security behavior, and mixed coexistence with sidecar-backed `production_log`.

Section 4C.2: Manual Gate And Documentation Update
1. Run `py_compile`, rerun the phase gate, perform a shown-window PyQt6 smoke pass for Help Viewer and Recovery Viewer, and update this document in place as each section completes.
2. Do not mark Phase 4 complete until both pilots and the expanded validator are green.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for the Phase 4 pilot surfaces and gate files; `scripts/validate_pyqt6_phase_gate.py` passed with 10 checks; a shown-window PyQt6 smoke script passed after opening the real host shell, navigating Help Viewer, switching themes, exercising Recovery Viewer draft handoff, and restoring both pilot controllers from persistence.

### Phase 5: Pilot Cleanup And Shared-Sidecar Boundary Verification
1. Retire dead sidecar-era scaffolding from the completed pilot modules only: `about`, `help_viewer`, and `recovery_viewer`.
2. Keep shared sidecar infrastructure in place for the remaining unmigrated modules until later phases.
3. Validate that cleaned pilots stay in-process in the PyQt6 viewport while sidecar-backed modules continue to work unchanged.
4. Status: COMPLETED.
5. Validation: `py_compile` passed for the cleaned pilot controller, view, and launcher surfaces; `scripts/validate_pyqt6_phase_gate.py` passed all 10 checks; `scripts/validate_module_loads.py about help_viewer recovery_viewer production_log` passed; and a shown-window PyQt6 smoke script passed while asserting that `about`, `help_viewer`, and `recovery_viewer` no longer create sidecar runtime managers.

Section 5A: Scope Lock
1. Phase 5 is limited to pilot cleanup for `about`, `help_viewer`, and `recovery_viewer`.
2. Do not delete `QtModuleRuntimeManager`, `QtModuleBridgeView`, or the remaining launcher session branches globally in this phase.
3. Status: COMPLETED.

Section 5B: About Pilot Cleanup
1. Remove module-local `QtModuleRuntimeManager`, bridge-view, and JSON IPC/session entrypoint code from `about` while preserving direct Tk fallback plus embedded PyQt6 viewport behavior.
2. Delete the About view-factory seam and prune the About launcher session branch once no local callers remain.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/controllers/about_controller.py`, `app/controllers/about_qt_controller.py`, `app/views/about_qt_view.py`, and `launcher.py`; `scripts/validate_pyqt6_phase_gate.py` passed all 10 checks; `scripts/validate_module_loads.py about production_log` passed.

Section 5C: Help Viewer Pilot Cleanup
1. Remove module-local runtime-manager, bridge-view, and JSON IPC/session entrypoint code from `help_viewer` while preserving document state, theme refresh, and Tk fallback.
2. Status: COMPLETED.
3. Validation: `HelpViewerController` now constructs `HelpViewerView` directly, the Help Viewer view-factory seam is deleted, the Qt controller/view are embedded-only, and the Help Viewer launcher session branch is removed. `py_compile`, `scripts/validate_pyqt6_phase_gate.py`, `scripts/validate_module_loads.py`, and the shown-window smoke pass all succeeded after the cleanup.

Section 5D: Recovery Viewer Pilot Cleanup
1. Remove module-local runtime-manager, bridge-view, and JSON IPC/session entrypoint code from `recovery_viewer` while preserving draft handoff, selection state, theme refresh, and Tk fallback.
2. Status: COMPLETED.
3. Validation: `RecoveryViewerController` now constructs `RecoveryViewerView` directly, the Recovery Viewer view-factory seam is deleted, the Qt controller/view are embedded-only, and the Recovery Viewer launcher session branch is removed. `py_compile`, `scripts/validate_pyqt6_phase_gate.py`, `scripts/validate_module_loads.py`, and the shown-window smoke pass all succeeded after the cleanup.

Section 5E: Shared Boundary Validation
1. Keep protected-module/security behavior green and confirm remaining sidecar-backed modules still work after pilot cleanup.
2. Status: COMPLETED.
3. Validation: the existing protected/security phase-gate checks remained green, `production_log` still loaded correctly through `scripts/validate_module_loads.py`, and the shown-window smoke pass confirmed the cleaned pilots coexist safely with a still-sidecar-backed module.

### Phase 6: Medium-Complexity Module Migration
Recommended order:
1. Rate Manager - Completed, Confirmed
2. Production Log Calculations - Completed, Confirmed
3. Developer Admin - Completed, Confirmed
4. Security Admin - Completed, Confirmed
5. Update Manager - Completed, Confirmed


Rules:
1. Each migrated module must ship with parity for the same user-facing behavior and controller/model responsibilities as its Tk counterpart.
2. No reduced-function Qt versions are acceptable.
3. Every Qt viewport migration must explicitly support embedded mode when a viewport parent is supplied: attach the view to the parent container layout, clear top-level window behavior, and do not treat controller routing alone as sufficient.

Section 6A: Rate Manager Migration
1. Remove module-local runtime-manager, bridge-view, and JSON IPC/session entrypoint code from `rate_manager` while preserving search/filter behavior, shared-data publication, and add/edit/delete parity with the Tk path.
2. Enable Rate Manager in the shared PyQt6 viewport and validate the default non-persistent lifecycle so it reloads cleanly without creating a sidecar runtime.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/rate_manager.py`, `app/controllers/app_controller.py`, `app/controllers/rate_manager_controller.py`, `app/controllers/rate_manager_qt_controller.py`, `app/views/rate_manager_qt_view.py`, `launcher.py`, and `scripts/validate_pyqt6_phase_gate.py`; `scripts/validate_module_loads.py rate_manager production_log help_viewer` passed; `scripts/validate_pyqt6_phase_gate.py` passed with the new `rate_manager_viewport_load` check covering embedded-mode load, shared-data sync, and clean reload behavior.

Section 6B: Production Log Calculations Migration
1. Remove module-local runtime-manager, bridge-view, and JSON IPC/session entrypoint code from `production_log_calculations` while preserving live preview updates, save/reload/defaults behavior, and the developer-facing formula editor parity from the Tk path.
2. Enable Production Log Calculations in the shared PyQt6 viewport and preserve the host callbacks that save the active profile, notify open Production Log instances about changed calculation settings, publish host toasts, and navigate directly into Production Log.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/production_log_calculations.py`, `app/controllers/app_controller.py`, `app/controllers/production_log_calculations_controller.py`, `app/controllers/production_log_calculations_qt_controller.py`, `app/views/production_log_calculations_qt_view.py`, `launcher.py`, and `scripts/validate_pyqt6_phase_gate.py`; `scripts/validate_module_loads.py production_log rate_manager help_viewer` passed; `scripts/validate_pyqt6_phase_gate.py` passed with the new `production_log_calculations_viewport_load` check covering embedded-mode load, preview refresh, save notifications, host toast publication, host navigation, and clean reload behavior.

Section 6C: Developer Admin, Security Admin, and Update Manager Migration
1. Migrate `developer_admin` and `security_admin` into the shared PyQt6 viewport through the shared Settings Manager Qt stack while preserving section-mode behavior, runtime settings refresh, external override policy application, security-session refresh, and default non-persistent reload semantics.
2. Migrate `update_manager` into the shared PyQt6 viewport as an in-process Qt controller/view pair that reuses the host Update Manager behavior directly, preserves stable-update, payload-restore, documentation-restore, and advanced-source actions, and keeps the registry-defined always-persistent lifecycle.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/developer_admin.py`, `app/security_admin.py`, `app/update_manager.py`, `app/controllers/app_controller.py`, `app/controllers/settings_manager_qt_controller.py`, `app/views/settings_manager_qt_view.py`, `app/controllers/update_manager_controller.py`, `app/controllers/update_manager_qt_controller.py`, `app/views/update_manager_qt_view.py`, `launcher.py`, and `scripts/validate_pyqt6_phase_gate.py`; `scripts/validate_module_loads.py update_manager production_log` passed; `scripts/validate_pyqt6_phase_gate.py` passed with the `admin_modules_viewport_load` and `update_manager_viewport_load` checks covering embedded-mode load, host callback behavior, persistence semantics, and clean reload behavior.

### Phase 7: Highest-Risk Module Migration
Recommended order:
1. Layout Manager - dedicated runtime decision required before any viewport work
2. Settings Manager - Completed, Confirmed
3. Production Log

Rules:
1. These modules require dedicated parity checklists before sidecar removal.
2. They must preserve protected-module behavior, theme propagation, persistence, and cross-module coordination.
3. Layout Manager is an explicit exception: keep it on the dedicated external PyQt6 runtime path and do not add it to `QT_IN_VIEWPORT_PILOT_MODULES` unless this plan is revised.
4. The rationale for that exception is workload isolation: the Layout Manager editor, preview, preload, and form-management flows should not be moved into the shared host viewport thread casually.

Section 7A: Layout Manager Dedicated Runtime Rule
1. Keep `layout_manager` on the dedicated external PyQt6 runtime path under the host shell instead of routing it through the shared in-process viewport loader.
2. Do not add `layout_manager` to `QT_IN_VIEWPORT_PILOT_MODULES` or introduce a normal in-process viewport controller path without revising this plan first.
3. Preserve protected-module visibility, dedicated-runtime reuse across navigation, preload invalidation, and external-window raise/restart flows.
4. Validation: `scripts/validate_pyqt6_phase_gate.py` must keep a dedicated `layout_manager_dedicated_runtime` check that proves Layout Manager stays external, reuses its runtime manager across navigation, and is not promoted into the shared viewport.

Section 7B: Settings Manager Migration
1. Route `settings_manager` into the shared PyQt6 viewport as an in-process `SettingsManagerQtController` and `SettingsManagerQtView`, preserving the full settings surface, theme save/preview flow, downtime-code editing, security-admin and developer-admin coordination, and the default non-persistent reload lifecycle.
2. Remove the module-local Settings Manager sidecar path by deleting the `QtModuleRuntimeManager`/bridge-view routing from the Tk fallback controller path, removing the Settings Manager launcher session branch, and pruning the dead standalone Qt session entrypoints from the shared Qt view.
3. Status: COMPLETED.
4. Validation: `py_compile` passed for `app/settings_manager.py`, `app/controllers/app_controller.py`, `app/controllers/settings_manager_controller.py`, `app/controllers/settings_manager_qt_controller.py`, `app/views/settings_manager_view.py`, `app/views/settings_manager_qt_view.py`, `app/views/settings_manager_view_factory.py`, `launcher.py`, and `scripts/validate_pyqt6_phase_gate.py`; `scripts/validate_module_loads.py settings_manager production_log` passed; `scripts/validate_pyqt6_phase_gate.py` passed with the new `settings_manager_viewport_load` check covering embedded-mode load, host save callbacks, non-persistent unload, and clean reload behavior.

Section 7C: Production Log Migration
1. Land embedded-mode `ProductionLogQtController` and `ProductionLogQtView` foundations while the dedicated runtime path remains active.
2. Preserve draft save/load, recovery handoff, calculation refresh, Excel import/export, active-form coordination, theme refresh, and bounded auto-save behavior.
3. Promote `production_log` into `QT_IN_VIEWPORT_PILOT_MODULES` only after validator coverage exists for viewport load, recovery handoff, non-persistent unload, and clean reload behavior.
4. Status: Complete, Confirmed
5. Current state: `production_log` now routes through `QT_IN_VIEWPORT_PILOT_MODULES` on the PyQt6 host path, and the embedded Qt controller now covers dispatcher-facing lifecycle hooks that were still missing from the initial groundwork slice: unsaved navigation confirmation through `can_navigate_away()`, active-form reload, calculation-settings refresh, draft save/load dirty-state handling, and Recovery Viewer handoff through the shared viewport dispatcher flow.
6. Remaining sidecar boundary: the dedicated Production Log runtime path still exists as the intentional fallback surface outside the active PyQt6 viewport pilot path. The remaining sidecar references are limited to the Tk fallback controller/view-factory flow plus the standalone Qt session entrypoint; they are not removed in Phase 7C.
7. Validation in this checkout: `py_compile` passed for `app/controllers/app_controller.py`, `app/controllers/production_log_qt_controller.py`, `app/views/production_log_qt_view.py`, and `app/production_log.py`. The repository snapshot referenced by this workspace does not currently contain the documented `scripts/validate_pyqt6_phase_gate.py` or `scripts/validate_module_loads.py` files, so the full scripted phase gate could not be rerun locally from this checkout. An offscreen PyQt6 smoke probe reached controller/view startup and exercised the embedded viewport path far enough to confirm pilot routing and headless Qt initialization, but the probe did not produce a clean automated exit because headless Qt teardown remained unstable in this environment.

### Phase 8: Sidecar Infrastructure Removal
1. Remove `QtModuleRuntimeManager` once no migrated modules depend on it.
2. Retire JSON session/state/command files and bridge views.
3. Keep standalone Qt windows only if they remain an intentional product feature.
4. Status: COMPLETED.
5. Current dependency snapshot before Phase 8 work begins: the generic sidecar stack is still present in `app/qt_module_runtime.py`, `app/views/qt_module_bridge_view.py`, the launcher-side Qt session branch in `launcher.py`, and the PyQt6 host shell separate-window runtime-manager path in `app/views/pyqt6_host_shell_view.py`. The current tree still contains module-local sidecar seams for `production_log`, `update_manager`, and `internal_code_editor`, while `layout_manager` remains the explicit dedicated-runtime exception under Phase 7A.

Section 8A: Inventory And Scope Lock
1. Freeze a verified inventory of all remaining sidecar-era consumers and classify each one as either dead migrated-module fallback, active intentional external-window feature, or temporary dedicated-runtime exception.
2. Treat `layout_manager` as the protected dedicated-runtime exception from Phase 7A unless this master plan is revised. Do not remove its external-window behavior during the generic sidecar cleanup.
3. `internal_code_editor` is confirmed as an in-process PyQt6 viewport target for Phase 8 work, not an intentional long-term external-window exception. Its current sidecar path in `app/controllers/internal_code_editor_controller.py`, `app/views/internal_code_editor_view_factory.py`, `app/controllers/internal_code_editor_qt_controller.py`, and `app/views/internal_code_editor_qt_view.py` should be treated as migration-era scaffolding to remove once the embedded viewport route is finished.
4. Verified remaining sidecar-era inventory at the start of Phase 8A:
	- Shared migration stack: `app/qt_module_runtime.py`, `app/views/qt_module_bridge_view.py`, launcher-side Qt session dispatch in `launcher.py`, and the separate-window runtime-manager path in `app/views/pyqt6_host_shell_view.py`.
	- Dead or temporary migrated-module fallback seams still to remove: `production_log`, `update_manager`, and `internal_code_editor`.
	- Dedicated-runtime exception to preserve through generic sidecar cleanup: `layout_manager`, including its specialized runtime flow in `app/layout_manager_dispatcher.py` and related host wiring.
5. Status: COMPLETED.

Section 8B: Remove Dead Migrated-Module Sidecar Fallbacks
1. Delete sidecar-only fallback seams that remain in already migrated modules, starting with `production_log`, then restoring `internal_code_editor` to the shared viewport, and then removing any other modules whose in-viewport migration is complete but whose Tk fallback controller path still instantiates `QtModuleRuntimeManager` or `QtModuleBridgeView`.
2. Remove module-local JSON session/state/command IPC, stale launcher session branches, and bridge-view factory paths for those completed modules while preserving their direct Tk fallback and shared-viewport PyQt6 behavior.
3. The current tree already shows Phase 8B targets in `app/controllers/production_log_controller.py`, `app/views/production_log_view_factory.py`, `app/controllers/internal_code_editor_controller.py`, `app/views/internal_code_editor_view_factory.py`, `app/controllers/update_manager_controller.py`, and `app/views/update_manager_view_factory.py`; re-verify the live call paths before deleting each seam.
4. Current state after the completed 8B cleanup: `internal_code_editor`, `production_log`, and `update_manager` now route through the shared PyQt6 viewport on the host path without module-local `QtModuleRuntimeManager` or `QtModuleBridgeView` fallback seams. Their Tk fallback controllers now construct direct Tk views only, their stale launcher-side sidecar session branches have been removed, and their embedded Qt controllers/views no longer keep module-local JSON IPC as an active product path.
5. Remaining generic sidecar surface after 8B: the shared runtime infrastructure in `app/qt_module_runtime.py` and the host-shell separate-window runtime manager path remain in place only for the intentional `layout_manager` dedicated-runtime exception plus the generic infrastructure that still needs 8C/8D refactoring.
6. Validation in this checkout: `py_compile` passed for the cleaned 8B surfaces including `launcher.py`, `app/views/pyqt6_host_shell_view.py`, `app/controllers/production_log_controller.py`, `app/views/production_log_view_factory.py`, `app/controllers/update_manager_controller.py`, `app/views/update_manager_view_factory.py`, `app/controllers/production_log_qt_controller.py`, `app/controllers/internal_code_editor_qt_controller.py`, `app/views/production_log_qt_view.py`, and `app/views/internal_code_editor_qt_view.py`.
7. Status: COMPLETED.

Section 8C: Intentional External-Window Boundary Extraction
1. Replace migration-era generic sidecar dependencies for any intentionally external Qt modules with explicit long-term host abstractions so those features no longer depend on `QtModuleRuntimeManager` or `QtModuleBridgeView` as migration scaffolding.
2. This section currently applies only to `layout_manager` unless this master plan is revised again.
3. Preserve external-window reuse, raise, restart, state refresh, and protected-module behavior for those intentional windows while moving them off the generic migration stack.
4. Current implementation state: `layout_manager` now uses an explicit dedicated-window contract centered on `app/layout_manager_dispatcher.py`. The active PyQt6 host shell drives Layout Manager through dispatcher-owned open/restart/stop/state helpers instead of binding it to the generic host `runtime_managers` path, and the module-local controller/view-factory path no longer constructs `QtModuleRuntimeManager` or `QtModuleBridgeView`.
5. Validation in this checkout: `py_compile` passed for `app/layout_manager_dispatcher.py`, `app/views/pyqt6_host_shell_view.py`, `app/controllers/layout_manager_controller.py`, `app/views/layout_manager_view_factory.py`, and `app/controllers/app_controller.py`. A follow-up tree scan showed the only remaining `QtModuleRuntimeManager` construction in `app/**/*.py` is the generic host-shell infrastructure for 8D cleanup, not an active Layout Manager consumer.
6. Status: COMPLETED.

Section 8D: Remove Shared Sidecar Infrastructure
1. Delete the shared migration-era sidecar infrastructure only after Sections 8A through 8C leave no remaining consumers on the generic path.
2. Candidate removals for this section include `app/qt_module_runtime.py`, `app/views/qt_module_bridge_view.py`, the generic separate-window runtime-manager handling in `app/views/pyqt6_host_shell_view.py`, and the generic Qt session dispatch branch in `launcher.py` that exists only for migration-era sidecars.
3. Retire JSON session/state/command IPC files and any now-dead host-shell messaging that refers to migration-sidecar runtime status rather than intentional product behavior.
4. Current implementation state: the shared sidecar infrastructure has been removed. `app/qt_module_runtime.py` and `app/views/qt_module_bridge_view.py` are deleted, the PyQt6 host shell no longer maintains a generic runtime-manager path for non-viewport modules, `app/controllers/app_controller.py` no longer carries the dead runtime-command fallback for Production Log draft opening, and `launcher.py` now accepts only the dedicated Layout Manager session environment instead of the old generic Qt module session path.
5. Remaining intentional runtime IPC is limited to the explicit Layout Manager dedicated-window contract in `app/layout_manager_dispatcher.py` and `app/views/layout_manager_qt_view.py`; it is no longer shared migration scaffolding.
6. Validation in this checkout: `py_compile` passed for `main.py`, `launcher.py`, `app/views/pyqt6_host_shell_view.py`, `app/controllers/app_controller.py`, `app/layout_manager_dispatcher.py`, `app/views/layout_manager_qt_view.py`, `app/controllers/layout_manager_controller.py`, and `app/host_ui_adapter.py`. Smoke validation was run by launching `main.py` directly and by launching a dedicated Layout Manager session through `AIMARTIN_LAYOUT_MANAGER_QT_SESSION`; both processes stayed alive past the timeout window with no error output.
7. Status: COMPLETED.

Section 8E: Validation And Closeout
1. Restore or replace the missing scripted validation path referenced elsewhere in this document so Phase 8 closeout does not depend on absent local scripts.
2. Validate that all completed PyQt6 viewport modules load without sidecar infrastructure, and that any intentional external-window modules still open, reuse, raise, restart, and report status correctly.
3. Keep explicit coverage for `layout_manager` as the dedicated-runtime exception, and add closeout coverage proving that `internal_code_editor` now mounts in the shared viewport instead of the separate-window runtime path.
4. Exit criteria: no completed migration path depends on the generic sidecar stack, intentional external windows use stable non-migration contracts, and the master plan plus validation evidence reflect the new architecture state.
5. Current implementation state: the missing scripted validation path has been replaced in this checkout with `scripts/validate_module_loads.py` and `scripts/validate_pyqt6_phase_gate.py`, backed by `scripts/_pyqt6_validation_harness.py`. The restored closeout checks now validate the current Phase 8 architecture instead of the older migration-era sidecar flow: all completed PyQt6 viewport modules load through the shared host viewport, `internal_code_editor` is explicitly verified as an in-viewport `InternalCodeEditorQtController` route, and `layout_manager` is explicitly verified as the remaining dedicated-window exception through `app/layout_manager_dispatcher.py` rather than the deleted generic sidecar stack.
6. Validation in this checkout: `py_compile` passed for `scripts/_pyqt6_validation_harness.py`, `scripts/validate_module_loads.py`, `scripts/validate_pyqt6_phase_gate.py`, and `app/controllers/app_controller.py`. `scripts/validate_module_loads.py --json` passed for `about`, `help_viewer`, `recovery_viewer`, `rate_manager`, `production_log`, `production_log_calculations`, `developer_admin`, `security_admin`, `settings_manager`, `update_manager`, and `internal_code_editor`, with each module reporting `status: in_viewport` and `sidecar_runtime: false`. `scripts/validate_pyqt6_phase_gate.py` passed with explicit checks for generic-sidecar removal, shared-viewport module loading, `internal_code_editor` viewport routing, and the `layout_manager` dedicated-window contract covering open, raise/reuse, restart, reload, stop, and host status reporting. Manual smoke validation also passed by launching `main.py` directly and by launching a dedicated Layout Manager session through `AIMARTIN_LAYOUT_MANAGER_QT_SESSION`; on Windows PowerShell the session JSON must be written without a UTF-8 BOM for that smoke path.
7. Status: COMPLETED.

Phase 8 closeout: COMPLETED.

### Phase 9: Tk Host Removal
1. Status: COMPLETED.
2. Live startup now enforces the PyQt6 host path and fails fast when `ui_shell_backend` is set to `tk` or PyQt6 support is unavailable.
3. Dispatcher-managed module shims now lazy-load the Qt controller path and raise immediately if a removed Tk controller path is requested.
4. Disconnected Tk controllers, views, view factories, the legacy Tk shell view, and splash module now hard-fail on import in the live tree and are mirrored under `shadow/` for demolition reference.
5. App icon setup now runs through Qt-native `QIcon` handling in the live startup path instead of the removed Tk image loader.
6. Theme resolution in the live runtime now uses only the internal semantic token system; legacy ttkbootstrap theme names are compatibility keys only and no longer trigger ttkbootstrap lookups.
7. Packaging/build inputs now target the PyQt6 runtime and no longer require Tk or ttkbootstrap hidden imports or dependency checks.
8. Preserve backend-neutral business logic, models, persistence, security, and valid abstractions while deleting the remaining live Tk dependencies.
9. Validation in this checkout: `py_compile` passes for the recent Qt admin workflow changes, `scripts/validate_pyqt6_phase_gate.py` and `scripts/validate_module_loads.py` pass against the live PyQt6 runtime, source startup smoke passed for both `main.py` and `launcher.py --module about`, and the rebuilt Windows EXE was accepted by the user as passing.
10. Ubuntu DEB smoke is deferred as follow-up packaging validation and does not keep the Tk-host removal phase open.

### Phase 10: Overflow Hardening and Screen-Fit Audit
1. Status: COMPLETED.
2. Audit every shared-viewport module and dedicated runtime window for content that exceeds the visible viewport or screen height/width.
3. Replace layout compression with scrollable containers so large forms, editors, tables, and preview surfaces stay readable instead of shrinking their internals.
4. Clamp standalone PyQt6 window sizes and major dialogs to the available screen geometry before showing them.
5. Treat `layout_manager`, `settings_manager`, and `production_log` as required validation targets because their current Qt surfaces are the most likely to exceed available space.
6. Entry note: packaged path seeding and Qt admin-auth dead-end regressions were resolved before starting this phase, so overflow hardening can proceed from a working packaged host baseline.
7. Current implementation state: `layout_manager` and `production_log` already use scrollable central surfaces plus screen-fit clamping for standalone windows. `settings_manager` and `update_manager` now match that baseline with scrollable central workspaces and screen-fit sizing so long stacked admin/update sections remain reachable in the host viewport and in standalone launches.
8. Broader screen-fit hardening in this checkout: `about`, `help_viewer`, `rate_manager`, `recovery_viewer`, `internal_code_editor`, and `production_log_calculations` now clamp standalone Qt window size to the available screen geometry instead of assuming a large desktop. Their embedded viewport paths remain unchanged.
9. Validation in this checkout: `py_compile` passed for the broadened Phase 10 view changes, `scripts/validate_module_loads.py` passed for `about`, `help_viewer`, `recovery_viewer`, `rate_manager`, `production_log_calculations`, `update_manager`, and `internal_code_editor` after the screen-fit sweep, and the current `scripts/validate_pyqt6_phase_gate.py` closeout run remains green with all 19 checks passing across the live host and dedicated runtime surfaces.

Phase 10 closeout: COMPLETED.

### Phase 11: Post-Migration UI Cleanup
1. Status: COMPLETED.
2. Remove leftover host-shell migration artifacts that are no longer useful in the live PyQt6 application, including the obsolete Active Module viewport panel.
3. Remove migration-era slice labels, dedicated migration notes, and other transition wording from user-facing Qt module surfaces where the modules now behave as normal application pages.
4. Finish retiring residual migration-only affordances from security, update, and host-shell surfaces while preserving any still-required backend or dedicated-runtime behavior behind the scenes.
5. Validation targets: `pyqt6_host_shell_view`, `settings_manager`, `security_admin`, `developer_admin`, and `update_manager`.
6. Current implementation state: the obsolete host-shell Active Module diagnostics surface has been removed, the Qt settings and update pages now use normal product copy instead of snapshot/debug labels, shared module shims no longer expose Phase 9 or shadow-path messaging as live user-facing language, and the remaining dedicated-window exception for `layout_manager` uses its explicit post-migration contract rather than generic sidecar behavior.
7. Closeout evidence in this checkout:
	- `app/views/pyqt6_host_shell_view.py` no longer constructs the hidden `runtime_diagnostics_group` panel or exposes the old Active Module session controls.
	- `app/views/settings_manager_qt_view.py`, `app/views/update_manager_qt_view.py`, `app/controllers/settings_manager_qt_controller.py`, `app/controllers/update_manager_qt_controller.py`, the affected module shims, and `app/security.py` have all been normalized away from migration/snapshot wording.
	- `layout_manager` launch and theme propagation regressions discovered during closeout were fixed through the dedicated runtime path in `app/layout_manager_dispatcher.py`, `app/controllers/layout_manager_qt_controller.py`, and `app/views/layout_manager_qt_view.py`.
	- `scripts/validate_pyqt6_phase_gate.py` now includes explicit cleanup-surface absence checks and validates the dedicated `layout_manager` runtime against its real launching-to-running lifecycle.
8. Validation in this checkout: `py_compile` passed for the touched Phase 11 cleanup and dedicated-runtime files, the focused Layout Manager runtime probe confirmed the dedicated window applied updated theme tokens live, and `scripts/validate_pyqt6_phase_gate.py` passed with all 19 checks green.
9. Closeout result: Phase 11.10 is satisfied. The wording cleanup is landed, the validator covers the removed artifacts explicitly, the dedicated Layout Manager exception is stable again, and Phase 11 is closed.

Phase 11 closeout: COMPLETED.

### Phase 12: Documentation Finalization
1. Status: COMPLETED.
2. Keep `.github/copilot-instructions.md` aligned with the target PyQt6-first architecture.
3. Mark older module-specific migration plans as historical or absorb their remaining useful content into canonical docs.
4. Ensure future implementation work follows this plan instead of creating local planning sprawl.
5. Final implementation state:
	- `.github/copilot-instructions.md` now describes the live runtime as PyQt6-only, keeps `layout_manager` on the explicit dedicated-window contract, and removes remaining transitional-Tk guidance from the active architecture, shell, theme, module-creation, and validation sections.
	- this document's verification and related-documents blocks now reflect the completed Phase 8 through Phase 11 architecture instead of pre-closeout migration criteria.
	- `docs/phase9_runbook.md` is explicitly labeled as a historical closeout artifact, and the older `docs/Completed Plans/layout_manager_pyqt6_migration_plan.md` remains labeled as historical reference.
6. Validation in this checkout: documentation consistency was updated in place across the canonical master plan, repo instructions, and historical runbook surfaces; file-level diagnostics report no errors for the touched documentation files.

Phase 12 closeout: COMPLETED.

## Verification
1. Canonical docs agree that the live application is PyQt6-only, `layout_manager` is the explicit dedicated-window exception, and reduced-function Qt modules are out of scope.
2. `Dispatcher.load_module()` behavior is mirrored on the Qt side for authorization, lifecycle hooks, caching, active-form notifications, theme application, and active navigation state.
3. Pilot modules render inside the shared Qt viewport rather than opening separate top-level windows, except for intentional dedicated-runtime modules such as `layout_manager`.
4. Live theme switching updates active and cached in-process Qt modules correctly.
5. Protected-module and security-lock behavior remains correct on the live PyQt6 runtime.
6. Shared-viewport modules and the dedicated `layout_manager` runtime coexist safely without generic sidecar infrastructure.
7. Migrated modules avoid blocking the Qt main thread or move heavy work off-thread safely.
8. Confirm no completed migration path depends on the removed generic sidecar infrastructure.
9. Shared-viewport modules and dedicated runtime windows use scrollable surfaces and screen-fit sizing instead of compressing unreadable internals.
10. Confirm user-facing modules and the dedicated `layout_manager` runtime continue to pass scripted validation plus targeted manual regression.

## Related Documents
- Historical reference: `docs/Completed Plans/layout_manager_pyqt6_migration_plan.md`
- Historical closeout artifact: `docs/phase9_runbook.md`
- Deferred future architecture: `docs/multi_user_migration_assessment.md`
- Operational QA: `docs/release_regression_checklist.md`
- Operational QA: `docs/packaged_windows_validation_runbook.md`
- Production Log architecture reference: `docs/production_log_json_architecture.md`