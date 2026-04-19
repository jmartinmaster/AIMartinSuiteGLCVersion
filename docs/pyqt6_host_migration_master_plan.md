# PyQt6 Host Migration Master Plan

## Status
- Active canonical migration plan for host-shell and module migration work.
- Sidecars are temporary migration scaffolding only.
- Tk host support is temporary compatibility infrastructure only.
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
1. This is the only active migration plan for the PyQt6 host-shell effort.
2. Do not create mini plans, separate phase plans, or module-specific execution plans outside this document.
3. Existing audits and older migration docs are reference inputs only.
4. If sequencing, scope, risks, or requirements change, update this document in place.
5. Operational docs such as validation runbooks and release checklists remain separate because they are execution aids, not migration plans.

## Current State
- The launcher now starts the PyQt6 shell through the Dispatcher instead of bypassing dispatcher lifecycle setup.
- The PyQt6 host shell now satisfies the active shell/view contract directly: menu wiring, update-banner refresh, navigation population, timer callbacks, theme refresh, and close handling.
- The PyQt6 shell layout is now viewport-first and user-facing instead of runtime-diagnostics-first, with sidebar collapse support and a compact module-session panel.
- Separate-window actions are now contextual to active sidecar-backed modules instead of appearing as general shell controls.
- The shell window title, workspace placeholder, and active-module messaging now distinguish clearly between the main workspace and temporary separate-window modules.
- `PyQt6HostUiAdapter` now delegates shared-viewport resize binding and viewport size queries to the real Qt workspace and forwards Qt mousewheel events to scroll targets.
- The PyQt6 shell now emits viewport resize notifications when shell layout changes such as sidebar collapse, banner visibility, or viewport surface switches occur.
- `_load_module_in_active_viewport()` now routes by active backend, and `_load_module_in_qt_viewport()` supports both an in-process viewport path and the temporary sidecar fallback.
- `about` is the first verified in-process Qt pilot module mounted inside the shared viewport.
- `scripts/validate_pyqt6_phase_gate.py` now provides the repeatable phase-gate validator for Qt-side lifecycle parity and runs without the prior probe-layout warning noise.
- Multiple remaining modules still depend on `QtModuleRuntimeManager`, JSON IPC session files, and bridge views.
- Repository instructions have been realigned to the PyQt6-first target architecture.

## Target Architecture
- The application runs as a real in-process PyQt6 shell with a shared central viewport.
- The Dispatcher mirrors the mature Tk module-loading lifecycle on the Qt side.
- Modules continue to enter through `get_ui(parent, dispatcher)`.
- Controllers and models remain backend-neutral where practical; views are free to be backend-specific.
- Every migrated PyQt6 module must match the user-facing behavior of its Tk counterpart.
- No summary modules, reduced-function Qt ports, or long-term sidecars are acceptable.

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
1. Rate Manager
2. Production Log Calculations
3. Developer Admin
4. Security Admin
5. Update Manager

Rules:
1. Each migrated module must ship with parity for the same user-facing behavior and controller/model responsibilities as its Tk counterpart.
2. No reduced-function Qt versions are acceptable.

### Phase 7: Highest-Risk Module Migration
Recommended order:
1. Layout Manager
2. Settings Manager
3. Production Log

Rules:
1. These modules require dedicated parity checklists before sidecar removal.
2. They must preserve protected-module behavior, theme propagation, persistence, and cross-module coordination.

### Phase 8: Sidecar Infrastructure Removal
1. Remove `QtModuleRuntimeManager` once no migrated modules depend on it.
2. Retire JSON session/state/command files and bridge views.
3. Keep standalone Qt windows only if they remain an intentional product feature.

### Phase 9: Tk Host Removal
1. Remove the remaining Tk host path only after full PyQt6 parity.
2. Preserve backend-neutral business logic, models, persistence, security, and valid abstractions.
3. Delete or archive Tk-host-specific shell guidance once no longer needed.

### Phase 10: Documentation Finalization
1. Keep `.github/copilot-instructions.md` aligned with the target PyQt6-first architecture.
2. Mark older module-specific migration plans as historical or absorb their remaining useful content into canonical docs.
3. Ensure future implementation work follows this plan instead of creating local planning sprawl.

## Verification
1. Canonical docs agree that PyQt6 host shell is primary, sidecars are temporary, Tk host is transitional, and reduced-function Qt modules are out of scope.
2. `Dispatcher.load_module()` behavior is mirrored on the Qt side for authorization, lifecycle hooks, caching, active-form notifications, theme application, and active navigation state.
3. Pilot modules render inside the shared Qt viewport rather than opening separate top-level windows.
4. Live theme switching updates active and cached in-process Qt modules correctly.
5. Protected-module and security-lock behavior remains correct during migration.
6. Mixed-backend sessions remain stable during the migration window.
7. Migrated modules avoid blocking the Qt main thread or move heavy work off-thread safely.
8. Before sidecar removal, confirm no migrated module still depends on sidecar-only infrastructure.
9. Before Tk-host removal, confirm all user-facing modules have full PyQt6 parity and pass manual regression.

## Related Documents
- Historical reference: `docs/layout_manager_pyqt6_migration_plan.md`
- Deferred future architecture: `docs/multi_user_migration_assessment.md`
- Operational QA: `docs/release_regression_checklist.md`
- Operational QA: `docs/packaged_windows_validation_runbook.md`
- Production Log architecture reference: `docs/production_log_json_architecture.md`