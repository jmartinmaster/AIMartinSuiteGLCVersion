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
- Phase 2 IN PROGRESS: shell-level refactor work has started from the validated mixed migration baseline.
- Phase 2 Section 1 IN PROGRESS: the PyQt6 host shell is now viewport-first and user-facing, but sidecar-backed modules still retain temporary external-window session handling.
- Phase 2 Section 1A COMPLETED: shell chrome refactor landed with viewport-first layout, sidebar collapse, user-facing copy, and a compact module-session panel.
- Phase 2 Section 1B NOT STARTED: move remaining external-window session handling out of shell-centered diagnostics affordances and into contextual shell state.
- Phase 2 Section 1C NOT STARTED: finish shell-level active-module title/status parity and remove remaining migration scaffolding language from user-facing surfaces.

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
- `_load_module_in_active_viewport()` now routes by active backend, and `_load_module_in_qt_viewport()` supports both an in-process viewport path and the temporary sidecar fallback.
- `about` is the first verified in-process Qt pilot module mounted inside the shared viewport.
- `scripts/validate_pyqt6_phase_gate.py` now provides the repeatable phase-gate validator for Qt-side lifecycle parity.
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

Section 1: Shell Chrome Refactor
1. Make the shell viewport-first and user-facing instead of runtime-diagnostics-first.
2. Preserve shell parity items such as sidebar behavior, active navigation state, update banner behavior, and menu integration.
3. Status: IN PROGRESS.

Section 1A: Viewport-First Shell Layout
1. Reduce always-visible runtime-diagnostics scaffolding and make the shared viewport the dominant workspace.
2. Add core shell chrome parity such as sidebar collapse and user-facing shell copy.
3. Status: COMPLETED.

Section 1B: Contextual External-Window Session State
1. Keep temporary sidecar-backed modules functional without presenting the shell as a runtime-manager console.
2. Represent external-window module state as contextual shell state rather than as the primary shell content.
3. Status: NOT STARTED.

Section 1C: Active Module Shell Context
1. Finish shell-level title, placeholder, and active-module messaging parity for both in-viewport and temporary sidecar-backed modules.
2. Remove remaining migration-scaffolding wording from user-facing shell surfaces where the host should behave like the real application shell.
3. Status: NOT STARTED.

### Phase 3: Host Adapter And Dispatcher Routing
1. Complete `PyQt6HostUiAdapter` services needed by shared-viewport modules.
2. Split Tk-specific loading logic out of the Dispatcher.
3. Add a real `_load_module_in_qt_viewport()` path that mirrors the mature Tk loader.

### Phase 4: Low-Risk Pilot Modules
1. Convert About, Help Viewer, and Recovery Viewer into true in-process PyQt6 viewport modules.
2. Verify navigation, persistence behavior, unload/hide behavior, theme refresh, and regression safety.
3. Verify mixed sessions remain stable while unmigrated modules still use temporary sidecars.

### Phase 5: Shared Sidecar Pattern Retirement
1. Remove shared sidecar patterns from migrated modules.
2. Replace controller flows that depend on `QtModuleRuntimeManager`, `open_or_raise_qt_window()`, `restart_qt_window()`, bridge views, or JSON IPC.
3. Add explicit protected-module coordination so security lock state remains correct during migration.

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