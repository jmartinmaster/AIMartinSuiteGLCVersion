## Plan: Post-Migration Tk Cleanup And Parity Sweep

Clean the live PyQt6 branch in two linked tracks: first remove dead or unreachable Tk-era remnants from non-shadow `app/` files without breaking the live runtime, then perform a targeted `main`-branch parity sweep to reintroduce missing user-facing behavior into the PyQt6 runtime. The recommended approach is to sequence this as dependency extraction -> dead archive removal -> live compatibility cleanup -> main-branch feature migration, with validation after each phase using the PyQt6 host shell and dedicated `layout_manager` contract.

Progress note: Phase 2 extraction baseline is complete for Help Viewer and Update Manager. Live Qt paths now resolve through Qt-native controllers without importing legacy Tk controllers.
Progress note: Phase 3 cleanup has started. The Help Viewer dead Tk controller/view files and the Update Manager dead Tk view/factory files have been collapsed to pure fail-fast stubs.
Progress note: The next implementation step is the high-priority `app/views/app_view.py` shell cleanup, followed by the remaining guarded controller/view/factory files that are now fully dead in the live PyQt6 runtime.
Progress note: A targeted MVC boundary audit of the changed PyQt6 parity files found a short cleanup list before the next regression sweep: move Settings Manager ready/status messaging behind a view method, and remove direct dispatcher toast routing from the Internal Code Editor, Production Log, and Settings Manager views by shifting host-toast orchestration into their controllers.
Progress note: The developer-vault native security-key regression is now restored in the live PyQt6 security path: developer vaults default back to native verification, the gatekeeper enforces the challenge at login, and Windows native verification now uses a tested Windows Hello WinRT bridge while Ubuntu/Linux continues to use native polkit prompting.
Progress note: The remaining Security Admin parity items from the embedded Settings surface are now addressed in PyQt6: the full Settings page keeps a visible locked entry path with unlock/re-auth controls, and the vault list again prefers and marks the active session vault instead of falling back to the first row.
Progress note: Developer Admin parity is tightened on the shared PyQt6 Settings surface: the external override trust control again explains that external files stay inert until trust is enabled, and saving a trust-state change now surfaces the same explicit bundled-vs-override runtime message the older flow provided.
Progress note: The Rate Manager pass is complete for this sweep. No new user-facing parity gap surfaced beyond one remaining MVC cleanup item in the Qt path, and host-toast orchestration now lives in the controller instead of the view before the module-load validation pass.
Progress note: The About, Help Viewer, and Update Manager audit passes are complete for this sweep. Their deferred regressions now live in the dedicated findings section below instead of being tracked only as progress notes.
Progress note: The audit-only toast pass is complete. The logical PyQt6 toast routes are mapped module-by-module, and the host presentation gap is now addressed: the live PyQt6 host adapter presents a real non-blocking overlay toast surface instead of collapsing requests into status-bar text.
Progress note: The `production_log_calculations` MVC toast-routing defect is now fixed in the live Qt path. Host-toast orchestration moved into the controller, the view is again a pure delegate, and the calculations slice revalidated through compile checks plus the supported `production_log` load path.
Progress note: Production Log toast parity is complete in the live Qt path. `Refresh View`, `Resume Latest`, `Delete Draft` empty-state, `Export Complete`, generic export/import warning notices, `Balance Downtime`, and `Open/Print Last Export` outcomes route through controller-owned host toasts.
Progress note: Production Log header auto-population was re-audited in the live Qt path. The controller now normalizes header payloads on initialization/load and the Qt view now routes header `editingFinished` through the controller focus-out normalization hook, restoring Tk-equivalent derived-header refresh behavior (for example cast-date/target-time style dependent fields) without moving business logic back into the view.
Progress note: Recovery Viewer toast parity is tightened in the live Qt path. Selection-required notices, unsupported resume/restore notices, and restore-complete notifications again route through controller-owned host toasts, while confirmation prompts remain intentionally dialog-based in the Qt runtime.
Progress note: Remaining model-side audit targets were reviewed. `security_model.py` currently preserves native-key defaults and serialization as expected, while `update_manager_model.py` still carries one deferred parity risk tied to legacy payload-path enumeration.
Progress note: Deferred model parity work has started. `update_manager_model.py` payload bundle discovery is now narrowed to live PyQt6 MVC files (`*_qt_controller.py`, `*_model.py`, `*_qt_view.py`), so dead Tk-era controller/view files are no longer pulled into module payload comparison/install scope.
Progress note: Help Viewer deferred parity work has started. The Qt action row again exposes `Open License File`, restoring the dedicated shortcut to `docs/legal/LICENSE.txt` while keeping the remaining wide-text-reader behavior change tracked separately.
Progress note: Update Manager deferred parity work continues. The Qt summary now renders an explicit release target heading from `target_name_var`, and the runtime status surface now reflects `status_var` (including the status bar) instead of a generic snapshot-refreshed message.
Progress note: Update Manager deferred parity work is complete for this sweep. The previously deferred summary/status surfaces and payload-path scope are now restored in the live Qt path and validated.
Progress note: Layout Manager deferred parity work is now partially complete for this sweep. The dedicated Qt runtime now includes real `Block View` and `Import / Export` authoring surfaces backed by model validation/update methods, and host navigation away from the module now guards on dedicated-runtime dirty state.
Progress note: Layout Manager deferred parity work is complete for this sweep. The dedicated runtime now emits runtime-to-host toast events for validation success, form create/activate/rename/duplicate/delete actions, and save completion, and the host bridge forwards those events through the shared PyQt6 toast presenter.
Progress note: Production Log Calculations deferred parity work is complete for this sweep. The Qt page now restores the explicit operational guidance block that explains calculation-profile impact on live recalculations, target-time normalization, workbook import/export transforms, and draft-input behavior.
Progress note: About and Help Viewer deferred parity work is complete for this sweep. About restores frozen-runtime repack affordance with confirmation/build flow, and Help Viewer restores a fixed-width no-wrap reader with explicit horizontal scrolling for wide reference content.
Progress note: Production Log deferred parity work is complete for this sweep. The Qt surface now restores action-level `Balance Downtime` outcomes plus `Open Last Export` and `Print Last Export` flows with controller-owned host toasts, and the earlier header auto-population normalization fix remains in place for dependent-field refresh.
Progress note: Toast routing and presentation closure pass is complete for the live PyQt6 runtime. Remaining toast helper/search hits are limited to legacy non-Qt files already tracked under Tk cleanup phases, while active Qt paths now use controller-owned host-toast routing and main-thread-safe presentation.
Progress note: Phase 2 is actively resumed from documentation cleanup. The immediate next tranche is a dependency-verification sweep across remaining legacy guarded modules before batch archival in Phase 3.
Progress note: Phase 2 dependency sweep checkpoint: no live imports remain for `help_viewer_controller`, `update_manager_controller`, `help_viewer_view`, or `update_manager_view`, and Qt views show no imports of legacy non-Qt views. Remaining sweep work is focused on broader guarded-module families before Phase 3 archival batches.
Progress note: Phase 2 is now complete. A full guarded-module dependency sweep shows one intentional live dependency (`update_manager_qt_controller` -> `update_manager_runtime_controller`), while the remaining guarded Tk-era controller/view files currently have zero live non-shadow runtime dependencies and are ready for an initial archival batch.
Progress note: Phase 3 has started with Batch 1 Tranche A archived from non-shadow `app/views`: `app_view.py`, `about_view.py`, `help_viewer_view.py`, and `developer_admin_view_factory.py`. Shadow counterparts remain available and no live non-shadow runtime references were found before removal.
Progress note: Phase 3 Batch 1 Tranche B is now archived from non-shadow `app/views`: `internal_code_editor_view.py`, `internal_code_editor_view_factory.py`, `production_log_view_factory.py`, and `settings_manager_view_factory.py`. Validation after removal confirms active Qt module paths still load.
Progress note: Phase 3 is now complete for Batch 1 archival scope. Remaining safe non-shadow guarded controller/view files from Batch 1 have been archived with shadow counterparts retained, and post-change module-load validation passed on the active Qt surfaces.
Progress note: Phase 4 has started. The live host adapter cleanup removed the dead `TkHostUiAdapter` stub and stale migration commentary from `app/host_ui_adapter.py`, with compile and module-load validation passing afterward.
Progress note: Phase 4 dedicated-runtime cleanup continued for Layout Manager. `app/views/layout_manager_view_factory.py` now treats dedicated PyQt6 runtime as the only live backend path (legacy backend requests are ignored with a recorded fallback note), and `app/controllers/layout_manager_controller.py` no longer defaults to Tk-oriented backend state or stale migration subtitle wording.
Progress note: Phase 5 audit is complete. The planned high-confidence parity targets already appear resolved in the live PyQt6 runtime: Update Manager payload/status visibility, Settings Manager theme preview/revert, Settings Manager export-directory browse, the Settings shortcut to Internal Code Editor, and the Production Log -> Recovery Viewer selected-context handoff. No new confirmed user-facing parity gaps were identified during this audit pass.
Progress note: Phase 6 pre-packaging validation is in progress. Non-packaging shell and dedicated-window checks are green: targeted compile checks passed, `validate_module_loads.py production_log layout_manager help_viewer` passed, the full PyQt6 phase gate passed, direct shell startup via `main.py` stayed stable, focused launcher startup stayed stable for `about` and `update_manager`, and `launcher.py --module layout_manager` held the dedicated-window path without early exit. The only validation caveat in this tranche is that `scripts/validate_module_loads.py` currently rejects `internal_code_editor` as an unknown launcher module name, which is a validator/module-list scope issue rather than a confirmed runtime regression.
Progress note: Phase 6 is now complete. Full closeout validation passed on the live branch: compile checks, launcher-surface module-load checks, full `validate_pyqt6_phase_gate.py` coverage, direct shell/launcher entry checks, dedicated-window startup probe for `layout_manager`, and Windows packaging after the runtime-seeding hardening. The packaging split requirement also validated: private `dist` output now carries real runtime data (`settings`, `form_definitions`, `rates`, forms), while tracked `dist/variants/public` output carries sanitized dummy-safe runtime data.

**Deferred Regression Findings**
Use this section as the implementation queue for parity issues that were confirmed during the post-migration sweep and intentionally deferred for a later fix pass.

Open deferred items only:
- None currently open.

**Phase 5 Audit Snapshot**
Confirmed audit result for the current live PyQt6 branch before any new parity edits:

- No confirmed open Phase 5 parity fixes are currently queued.
- Verified as already present in the live runtime:
   - Update Manager runtime status and payload/detail rendering
   - Settings Manager theme preview and revert flow
   - Settings Manager export-directory browse affordance
   - Settings Manager shortcut to Internal Code Editor
   - Production Log -> Recovery Viewer selected-record handoff
- Recommended handling: keep Phase 5 in audit-complete / no-open-findings state unless a new user-facing regression is discovered through manual smoke testing or a main-branch comparison uncovers a concrete missing behavior that is not already implemented.


**Toast Routing And Presentation Audit**
Use this section as the reference map for both logical toast routing and the separate PyQt6 presentation migration status during the later fix pass.

- Canonical logical route: module action -> Qt controller `show_toast(...)` helper or runtime controller -> `dispatcher.show_toast(...)` -> `app_controller.show_toast(...)` -> `host_ui_adapter.show_toast(...)`. Shared-viewport Qt views should only delegate; they should not own direct dispatcher toast calls.
- Presentation status: `PyQt6HostUiAdapter.show_toast(...)` now presents a dedicated non-blocking overlay toast in the live PyQt6 shell instead of degrading every request to status-bar messaging. The old status-bar behavior remains only as a defensive fallback if a presenter cannot be created.
- Presentation metadata status: the live PyQt6 branch now uses the persisted `toast_duration_sec` setting to drive toast lifetime when no explicit duration override is supplied, and the presenter maps `bootstyle` into severity-aware accent styling for the overlay surface.
- `production_log`: `Draft Saved`, `Refresh View` empty-state, `Resume Latest` empty-state, `Delete Draft` empty-state, `Export Complete`, `Import Complete`, and the generic export/import warning notices follow the canonical logical route through `production_log_qt_controller.show_toast(...)`, with `production_log_qt_view.show_toast(...)` only delegating back to the controller. The Qt runtime now also restores controller-owned action toasts for `Balance Downtime`, `Open Last Export`, and `Print Last Export` outcomes.
- `rate_manager`: `Rate Saved`, `Rate Added`, and `Rate Deleted` now originate from controller-owned `rate_manager_qt_controller.show_toast(...)` calls and route through `dispatcher.show_toast(...)`, while still mirroring status text locally.
- `settings_manager`: vault save/delete/password update, security-mode save, and developer override-trust notices now originate from controller-owned `settings_manager_qt_controller.show_toast(...)` calls and route through `dispatcher.show_toast(...)`, with panel status mirrors preserved.
- `internal_code_editor`: `File Saved` follows the canonical controller-owned route (`internal_code_editor_qt_controller.show_toast(...)` -> `dispatcher.show_toast(...)`) and mirrors the message into the local editor status line.
- `production_log_calculations`: the save-complete toast now follows the canonical logical route. `production_log_calculations_qt_view.show_toast(...)` delegates to the controller, and `production_log_calculations_qt_controller.show_toast(...)` owns the host-toast request through `dispatcher.show_toast(...)` while mirroring the message into the local status line.
- `recovery_viewer`: selection-required notices, unsupported resume/restore notices, and restore-complete notifications now follow the canonical logical route through `recovery_viewer_qt_controller.show_toast(...)` -> `dispatcher.show_toast(...)`. Qt confirmation prompts remain dialog-based through `ask_yes_no(...)`, which is appropriate for the live runtime because the confirmation UI is available instead of falling back to the old confirmation-unavailable toast branch.
- `update_manager`: the live route is intentionally controller-owned without a view helper. `update_manager_runtime_controller.py` sends worker/job, payload, documentation, and advanced-update notices directly through `dispatcher.show_toast(...)`, which remains appropriate because the runtime controller owns those asynchronous operations. This module's deferred summary/status parity items are now resolved for this sweep.
- `layout_manager`: the dedicated Qt runtime now emits runtime toast events over the external-window state contract, and `LayoutManagerQtBridge` forwards those events into `dispatcher.show_toast(...)`, restoring host-toast visibility for validation success, form actions, and save completion in the dedicated-window path.
- Shell-level note: opening `layout_manager` through the dedicated-window contract still emits a host-toast request from `pyqt6_host_shell_view.py` through `host_ui_adapter.show_toast(...)`, and that request now reaches the shared PyQt6 overlay presenter like other host-surface toasts.

**Steps**
1. Phase 0: Freeze the architecture baseline and validation contract.
   Confirm the plan treats the application as PyQt6-only with `layout_manager` as the sole dedicated-window exception. Treat `scripts/validate_module_loads.py` and `scripts/validate_pyqt6_phase_gate.py` as canonical validation surfaces for the cleanup.
2. Phase 1: Operational and tooling cleanup.
   Update runtime-adjacent docs and validation/build surfaces that still assume Tk or obsolete versions before touching runtime files. This includes stale runbooks, validator wording, and archival packaging specs so future cleanup work is not guided by dead Tk instructions.
3. Phase 2: Verify and finish live-shared logic extraction from legacy modules. *completed*
   Confirmed: live Qt runtime no longer imports or depends on Tk-era controller/view modules for operational behavior, except the intentional shared runtime base `update_manager_runtime_controller.py`.
   Completed checks: guarded-module sweep across `app/controllers` and `app/views`, plus focused import/reference checks for Help Viewer and Update Manager legacy controllers/views.
   End state reached: no live runtime path requires guarded Tk controller/view files for shared logic.
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
   Before starting the next regression sweep, run a focused MVC boundary cleanup on newly touched parity files so controller/view responsibilities stay strict while parity fixes land.
7. Phase 6: Shell, dedicated-window, and packaging closeout validation. *completed*
   Run file-level compile checks, changed-module validation, PyQt6 phase-gate validation, direct shell startup, module-focused startup, and packaged build verification. Confirm `layout_manager` still passes as the dedicated-window exception and that no live path imports or requires Tk/ttkbootstrap.

**Relevant files**
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\help_viewer_controller.py` — Phase 2 baseline verified; no live Qt dependency remains. Keep as a Phase 3 guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\help_viewer_qt_controller.py` — retain Qt-native document constants/metadata sourcing and verify no legacy controller imports during the Phase 2 dependency sweep.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\update_manager_controller.py` — Phase 2 baseline verified; no live Qt dependency remains. Keep as a Phase 3 guarded archive candidate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\update_manager_qt_controller.py` — preserve runtime-controller subclass behavior while completing Phase 5 parity polish.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\models\update_manager_model.py` — keep payload-path validation aligned to Qt MVC files only during dependency and archival sweeps.
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
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\internal_code_editor_qt_controller.py` — own host-toast orchestration so the Qt view does not reach into dispatcher services directly.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\internal_code_editor_qt_view.py` — keep UI-local dialogs/status updates only; delegate toast orchestration back to the controller.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\production_log_qt_controller.py` — own host-toast orchestration and keep derived field writes behind view methods only.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\production_log_qt_view.py` — keep UI-local dialogs/status updates only; delegate toast orchestration back to the controller.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\controllers\settings_manager_qt_controller.py` — replace direct status-bar widget access with view methods and own any host-toast orchestration.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\views\settings_manager_qt_view.py` — keep status rendering local and delegate any host-toast orchestration back to the controller.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\native_security_verifier.py` — runtime-aware native developer-vault verification service for Windows Hello and Ubuntu/Linux polkit prompting.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\security.py` — enforce native verification for developer vaults in the live gatekeeper login flow without reintroducing Tk-era auth handling.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\app\models\security_model.py` — preserve and default the `requires_yubikey` developer-vault flag during payload hydration/serialization.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\scripts\validate_module_loads.py` — keep aligned with live PyQt6 host behavior and dedicated `layout_manager` exception.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\scripts\validate_pyqt6_phase_gate.py` — preserve mixed viewport and dedicated-runtime verification as cleanup proceeds.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\build.py` — confirm build remains Tk-excluding and update only if cleanup changes packaging assumptions.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\launcher.py` — retain PyQt6-only shell bootstrap while simplifying stale Tk removal wording where appropriate.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\docs\packaged_windows_validation_runbook.md` — update stale version/Tk assumptions in the operational validation path.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\docs\release_regression_checklist.md` — align versioned regression guidance with the live branch.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\packaging\specs\main.spec` — archive or mark obsolete if no longer part of the active build pipeline.
- `c:\Users\jamie\OneDrive\Personel\Documents\AI-Martin\AIMartinSuiteGLCVersion\packaging\specs\Production Logging Center_GLC_v2.1.2.spec` — archive or mark obsolete if no longer part of the active build pipeline.

**Safe-To-Archive Batch 1 (Phase 3 Candidate Set)**
Guarded files with zero live non-shadow runtime dependencies from the Phase 2 sweep.

- `app/controllers/about_controller.py`
- `app/controllers/developer_admin_controller.py`
- `app/controllers/help_viewer_controller.py`
- `app/controllers/internal_code_editor_controller.py`
- `app/controllers/production_log_calculations_controller.py`
- `app/controllers/production_log_controller.py`
- `app/controllers/rate_manager_controller.py`
- `app/controllers/recovery_viewer_controller.py`
- `app/controllers/security_admin_controller.py`
- `app/controllers/settings_manager_controller.py`
- `app/controllers/update_manager_controller.py`
- `app/views/about_view.py`
- `app/views/app_view.py`
- `app/views/developer_admin_view_factory.py`
- `app/views/help_viewer_view.py`
- `app/views/internal_code_editor_view.py`
- `app/views/internal_code_editor_view_factory.py`
- `app/views/layout_manager_view.py`
- `app/views/production_log_calculations_view.py`
- `app/views/production_log_view.py`
- `app/views/production_log_view_factory.py`
- `app/views/rate_manager_view.py`
- `app/views/recovery_viewer_view.py`
- `app/views/security_admin_view_factory.py`
- `app/views/settings_manager_view.py`
- `app/views/settings_manager_view_factory.py`
- `app/views/update_manager_view.py`
- `app/views/update_manager_view_factory.py`

Not included in Batch 1:
- `app/controllers/update_manager_runtime_controller.py` — intentionally imported by `app/controllers/update_manager_qt_controller.py` and remains live.

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