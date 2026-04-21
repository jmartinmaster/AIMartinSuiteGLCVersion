## Plan: Post-Migration Tk Cleanup And Parity Sweep

Clean the live PyQt6 branch in two linked tracks: first remove dead or unreachable Tk-era remnants from non-shadow `app/` files without breaking the live runtime, then perform a targeted `main`-branch parity sweep to reintroduce missing user-facing behavior into the PyQt6 runtime. The recommended approach is to sequence this as dependency extraction -> dead archive removal -> live compatibility cleanup -> main-branch feature migration, with validation after each phase using the PyQt6 host shell and dedicated `layout_manager` contract.

Progress note: Phase 2 extraction is complete for Help Viewer and Update Manager.
Progress note: Phase 3 cleanup has started. The Help Viewer dead Tk controller/view files and the Update Manager dead Tk view/factory files have been collapsed to pure fail-fast stubs.
Progress note: The next implementation step is the high-priority `app/views/app_view.py` shell cleanup, followed by the remaining guarded controller/view/factory files that are now fully dead in the live PyQt6 runtime.

**Steps**
1. Phase 0: Freeze the architecture baseline and validation contract.
   Confirm the plan treats the application as PyQt6-only with `layout_manager` as the sole dedicated-window exception. Treat `scripts/validate_module_loads.py` and `scripts/validate_pyqt6_phase_gate.py` as canonical validation surfaces for the cleanup.
2. Phase 1: Operational and tooling cleanup.
   Update runtime-adjacent docs and validation/build surfaces that still assume Tk or obsolete versions before touching runtime files. This includes stale runbooks, validator wording, and archival packaging specs so future cleanup work is not guided by dead Tk instructions.
3. Phase 2: Extract live shared logic from mixed legacy modules. *blocks Phase 3*
   Move still-live helper/data responsibilities out of Tk-era controller files that cannot yet be archived wholesale.
   Start with `help_viewer_controller` because `help_viewer_qt_controller` still depends on shared constants/helpers there.
   Refactor `update_manager_controller` next because `update_manager_qt_controller` subclasses it and `update_manager_model` still validates source snapshots against the controller file’s presence.
   End condition: the live Qt runtime no longer depends on dead Tk controller/view modules for shared logic.
4. Phase 3: Archive definite dead non-shadow `app/` files. *depends on Phase 2*
   Move or retire fail-fast-guarded controller/view files that still contain unreachable Tk bodies under `raise_tk_runtime_removed(...)`.
   Prioritize `app/views/app_view.py` and the guarded controller/view/factory files identified as definite dead code.
   Keep module shims and `tk_runtime_removed.py` intact until all moved files are accounted for and error messaging is updated.
5. Phase 4: Remove live compatibility scaffolding that still references Tk-era behavior. *depends on Phase 3*
   Simplify PyQt6 runtime files that still carry Tk-named fallback state or dead compatibility branches, especially `app/security.py`, `app/host_ui_adapter.py`, `app/views/layout_manager_view_factory.py`, `app/controllers/layout_manager_controller.py`, and selected stale messaging in dispatcher/shell files.
   Preserve defensive fail-fast behavior where it still protects against invalid backends, but stop implying that a Tk path remains supported.
6. Phase 5: Main-branch parity sweep for missing/regressed features. *can start discovery in parallel with Phases 1-4, implementation depends on cleanup stability*
   Re-check local `main` against the cleaned PyQt6 runtime and migrate only true user-facing feature gaps, not intentional Tk removals or wording-only differences.
   Prioritize the high-confidence gaps already identified:
   Update Manager payload/status visibility and live status surface.
   Settings Manager theme preview/revert and export-directory browse affordances.
   Then evaluate medium-confidence candidates such as the Settings shortcut to Internal Code Editor and Production Log -> Recovery Viewer selected-context handoff.
7. Phase 6: Shell, dedicated-window, and packaging closeout validation. *depends on all earlier phases*
   Run file-level compile checks, changed-module validation, PyQt6 phase-gate validation, direct shell startup, module-focused startup, and packaged build verification. Confirm `layout_manager` still passes as the dedicated-window exception and that no live path imports or requires Tk/ttkbootstrap.

**Relevant files**
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\help_viewer_controller.py` — extract live constants/helpers used by `help_viewer_qt_controller` before archival.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\help_viewer_qt_controller.py` — update imports after helper extraction.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\update_manager_controller.py` — split shared updater logic from dead Tk view construction.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\update_manager_qt_controller.py` — preserve subclass behavior while migrating shared logic and later backfilling main-branch parity gaps.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\models\update_manager_model.py` — remove or revise controller-file existence assumptions before archiving legacy controller files.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\app_view.py` — high-priority unreachable Tk shell archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\about_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\developer_admin_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\internal_code_editor_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\production_log_calculations_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\production_log_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\rate_manager_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\recovery_viewer_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\security_admin_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\settings_manager_controller.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\about_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\developer_admin_view_factory.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\help_viewer_view.py` — definite dead guarded archive candidate after helper extraction work.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\internal_code_editor_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\internal_code_editor_view_factory.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\layout_manager_view.py` — definite dead guarded archive candidate once dedicated Qt contract is confirmed stable.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\production_log_calculations_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\production_log_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\production_log_view_factory.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\rate_manager_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\recovery_viewer_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\security_admin_view_factory.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\settings_manager_view.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\settings_manager_view_factory.py` — definite dead guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\update_manager_view.py` — definite dead guarded archive candidate after update-manager shared logic extraction.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\update_manager_view_factory.py` — definite dead guarded archive candidate after update-manager shared logic extraction.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\security.py` — remove Tk sentinel globals and dead Tk-named compatibility paths after PyQt6-only security flow is fully confirmed.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\host_ui_adapter.py` — remove `TkHostUiAdapter` stub and stale migration commentary.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\layout_manager_view_factory.py` — normalize requested backend parsing to Qt-only dedicated runtime behavior.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\layout_manager_controller.py` — finish cleanup of stale Tk-oriented backend state and maintain dedicated runtime behavior.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\app_controller.py` — remove obsolete Tk comments/branches only after runtime cleanup stabilizes.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\about_qt_controller.py` — remove stale user-facing Tk host wording.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\update_manager_qt_view.py` — restore missing payload/status detail rendering from the old runtime where still relevant.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\settings_manager_qt_controller.py` — add parity affordances for theme preview/revert and file browsing where approved.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\settings_manager_qt_view.py` — restore missing interactive settings affordances in PyQt6.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\production_log_qt_controller.py` — evaluate selected-context Recovery Viewer handoff during parity phase.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\recovery_viewer_qt_controller.py` — add targeted handoff/select API if the Production Log parity item is accepted.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\scripts\validate_module_loads.py` — keep aligned with live PyQt6 host behavior and dedicated `layout_manager` exception.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\scripts\validate_pyqt6_phase_gate.py` — preserve mixed viewport and dedicated-runtime verification as cleanup proceeds.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\build.py` — confirm build remains Tk-excluding and update only if cleanup changes packaging assumptions.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\launcher.py` — retain PyQt6-only shell bootstrap while simplifying stale Tk removal wording where appropriate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\docs\packaged_windows_validation_runbook.md` — update stale version/Tk assumptions in the operational validation path.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\docs\release_regression_checklist.md` — align versioned regression guidance with the live branch.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\packaging\specs\main.spec` — archive or mark obsolete if no longer part of the active build pipeline.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\packaging\specs\Production Logging Center_GLC_v2.1.2.spec` — archive or mark obsolete if no longer part of the active build pipeline.

**Verification**
1. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe -m py_compile` on each touched phase file set before broader validation.
2. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe scripts/validate_module_loads.py production_log layout_manager help_viewer` after each major cleanup tranche.
3. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe scripts/validate_module_loads.py about rate_manager settings_manager update_manager internal_code_editor` after the controller/view archive sweep.
4. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe scripts/validate_pyqt6_phase_gate.py` after any dispatcher, shell, security, or `layout_manager` contract changes.
5. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe main.py` for a direct shell smoke test after Phases 3, 4, and 5.
6. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe launcher.py --module about` and a second focused module launch such as `--module update_manager` after parity work lands.
7. Run `c:/Users/jamie/OneDrive/Personel/Documents/AI-Martin/AIMartinSuiteGLCVersion/.venv/Scripts/python.exe build.py --target windows --non-interactive` once runtime cleanup is stable.
8. Follow the updated packaged validation runbook for a packaged Windows smoke pass.
9. If Ubuntu packaging remains supported, run the equivalent `build.py --target ubuntu --non-interactive` validation in an appropriate environment after cleanup closeout.
10. During parity work, manually verify the recovered user-facing behaviors in Settings Manager, Update Manager, Production Log, and Recovery Viewer rather than relying only on module-load checks.

**Decisions**
- Included: non-shadow `app/` cleanup, runtime-adjacent validation/tooling cleanup, and a later `main`-branch feature-parity phase for the live PyQt6 runtime.
- Excluded for now: deleting the entire `shadow/` tree, reopening the completed migration master plan, reintroducing any Tk fallback, or migrating intentional architecture exceptions such as `layout_manager` into the shared viewport.
- `layout_manager` remains the explicit dedicated-window exception throughout all phases; validator expectations must continue to reflect that.
- Dead guarded files should only move after their live shared dependencies are extracted, not by bulk archive-first deletion.

**Further Considerations**
1. Recommended implementation order inside Phase 5: Update Manager parity first, then Settings Manager affordances, then lower-confidence cross-module handoff polish. This keeps early parity fixes view/controller-local and avoids new dispatcher contracts until needed.
2. Recommended archive strategy: move dead guarded files to the existing `shadow/` structure in controlled batches and update any fail-fast messages that mention exact shadow paths in the same batch.
3. Recommended governance: track cleanup and parity as a new post-migration workstream rather than extending `docs/Completed Plans/pyqt6_host_migration_master_plan.md`, which is now a completed architecture record.