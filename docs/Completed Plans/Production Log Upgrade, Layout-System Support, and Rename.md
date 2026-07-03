# Plan: Form Loader (production_log) Upgrade, Layout-System Support, and Preferred Alias Rollout

> **Status**: Completed. All tranches, including the dynamic-renderer, custom section/header runtime implementation, options sources, and preferred-alias rollout, are fully executed and validated.
>
> **Scope**: Carefully plan and execute the next internal `production_log` upgrade in sequenced tranches so the module can support the newer layout-system direction, absorb the upcoming feature changes, and complete the preferred `Form Loader` alias rollout without breaking runtime behavior, draft compatibility, or downstream verification work.
>
> **Relationship To Accessibility Planning**: NVDA verification is now unblocked and ready for execution.
>
> **Planning Note**: This document serves as the final report for the completed dynamic-renderer tranche, custom section completion, and rename decisions. The runtime and all documentation now consistently use the `Form Loader` and `Form Calculations` aliases while maintaining stable compatibility-sensitive internal identifiers.

---

## Intent

Form Loader and Layout Manager must now converge on a complete custom-form contract where authoring JSON can produce full operator-ready forms with custom sections and custom headers without profile-specific hardcoding.

This plan now prioritizes closing the custom section/header runtime gap first. NVDA verification remains important but is intentionally deferred until this form-authoring/runtime contract is complete and stable.

---

## Why This Plan Exists

The remaining NVDA work should not proceed against a Form Loader surface that is still changing materially.

The internal `production_log` family still needs a planned upgrade that covers:

- new feature support
- support for the newer layout system
- completion of the preferred Form Loader alias rollout

Those changes can alter field labeling, focus flow, workflow sequencing, help documentation, export wording, and user-facing status messages. They need to settle first so accessibility verification is performed once against the intended final state.

The current planning decision was to land the layout-driven rebuild first, then return to the preferred-alias rollout as a follow-up tranche instead of combining both changes into one implementation pass.

---

## Baseline

- The live application already has PyQt6 Form Loader controller/view foundations.
- Layout Manager can now author richer layout metadata, including section behavior and repeating-row delete policy.
- Form Loader already normalizes active forms through the form registry and section-aware layout config, and the live PyQt6 view now renders the selector shell plus the section-driven body for the supported runtime profiles.
- The live runtime currently implements behavior for `header`, `production`, and `downtime` section profiles. Future profile declarations may exist in JSON, but they remain warning-capable no-ops until explicit runtime support is added.
- Draft metadata is already form-aware through stored `form_id` and `form_name` values, which gives the upgrade a compatibility path for selector-driven form switching.
- The public layout-config help reference is partially behind the live section-driven runtime and should not be treated as the only contract source during implementation planning.
- The preferred `Form Loader` alias is now live in runtime/help surfaces, while permanent internal `production_log` identifiers remain unchanged.

## Capability Snapshot (June 2026)

Current strengths:

- Layout Manager can create, rename, reorder, and remove arbitrary sections and can persist custom `fields_key`, `mapping_key`, `section_type`, and `behavior_profile` metadata.
- Layout Manager can generate custom section keys and mapping objects for non-default sections (`<section_id>_fields`, `<section_id>_row_fields`, `<section_id>_mapping`).
- Form Loader already renders sections in `sections[]` order and respects section names/descriptions for supported profiles.
- Data handler and model layers normalize unknown profiles safely and avoid silent crashes.

Current blockers for complete custom-form generation:

- Form Loader rendering is still behavior-profile hardcoded to `header`, `production`, and `downtime` in the live Qt view.
- Form Loader controller/runtime wiring still loads only default field groups (`header_fields`, `production_row_fields`, `downtime_row_fields`) instead of fully dynamic section key routing.
- Layout Manager authoring controls still hardcode row/mapping selectors to production and downtime in key surfaces.
- Validation and guardrail helpers still enforce uniqueness and routing assumptions around the three supported profiles.
- Import/export routing remains bounded to implemented profiles, so custom repeating sections cannot fully participate in workbook paths yet.

## Priority Pivot (June 2026)

The highest-priority tranche is now custom section/header completion for runtime parity between Layout Manager authoring and Form Loader rendering.

Scope of this tranche:

- Make Form Loader runtime section-key driven for both single and repeating sections.
- Expand Layout Manager authoring surfaces to dynamically target all repeating sections declared in `sections[]`.
- Add bounded, explicit import/export behavior for custom repeating sections (either supported generic routing or intentionally documented no-op behavior).
- Keep compatibility with existing default profiles and existing drafts/forms.

---

## Locked Decisions For The Current Tranche

- The first implementation tranche rebuilds Form Loader around a fixed top selector shell and a section-driven body renderer.
- The fixed top shell keeps the form selector only for form-defined data entry. Form-defined fields move into the dynamic body below it.
- The selector updates the app-wide active form through the existing form registry and dispatcher notification path rather than introducing a local-only form switch mode.
- The first tranche supports only the runtime profiles already implemented today: `header`, `production`, and `downtime`.
- If entered data exists, a form change prompts immediately, then reloads the selected form blank after the chosen prompt flow.
- The same prompt-to-switch behavior applies when another module changes the active form while Form Loader contains entered data.
- If the user cancels a pending switch, the loaded form stays active and the selector state must reset so the UI does not imply a switch that never completed.
- The preferred-alias rollout remains separate from permanent internal naming: runtime text uses `Form Loader`, while internal `production_log` identifiers remain compatibility-stable.
- Strict MVC boundaries remain mandatory during the rebuild: model owns schema and normalization, controller owns switching and orchestration, and view owns rendering and events only.

---

## Current Progress Snapshot

Completed slices:

- Slice 1: Fixed top selector shell added to `app/views/production_log_qt_view.py` with local guarded form switching wired through `app/controllers/production_log_qt_controller.py`.
- Slice 2: The hard-coded body ordering was replaced with section-driven rendering in `app/views/production_log_qt_view.py` for the currently supported `header`, `production`, and `downtime` profiles.
- Slice 3: Compatibility cleanup aligned external active-form notifications with the guarded local switch flow and moved the remaining repeating-section helper paths in `app/views/production_log_qt_view.py` onto shared section metadata for the supported profiles.

Current behavior after those slices:

- Form Loader now exposes the stored-form selector in the Qt surface.
- The selector is synchronized with the active form registry.
- Local form switching prompts for save, discard, or cancel when entered data exists.
- External active-form changes now use the same guarded save, discard, or cancel behavior and preserve the current form when the switch is cancelled.
- The form body is rendered in `sections[]` order for supported profiles.
- Supported repeating sections now share the same metadata-driven runtime helpers for table lookup, row actions, delete confirmations, and form-data collection instead of branching through duplicated production/downtime-only paths.
- Unsupported or duplicate section declarations fail safely in the renderer instead of silently remapping to a hard-coded order.

Validated after implementation slices:

- `python -m py_compile app/controllers/production_log_qt_controller.py app/views/production_log_qt_view.py` passed.
- `scripts/validate_module_loads.py production_log layout_manager help_viewer` passed through the `Validate Changed UI Modules` task.
- `scripts/run_production_log_smoke.py` now covers the guarded switch, section-order, repeating-row, draft, and import/export checklist items and passed with `SMOKE SUMMARY: PASS (7 checks)`.
- Defect-driven cleanup from the smoke pass fixed two live regressions in `app/views/production_log_qt_view.py`: `Remove Selected` now honors per-section delete-confirmation policy, and derived-only values no longer cause blank open rows to persist as collected data.

Current tranche close-out state:

- Smoke coverage for selector switching, cancel/reset behavior, section ordering, repeating-row behavior, drafts, and import/export is now recorded and green.
- Any remaining cleanup in this tranche should stay defect-driven from later regressions rather than reopening structural implementation work for the currently supported profile set.

### Recorded Smoke Coverage

The current dynamic-renderer tranche now has recorded smoke evidence for these behaviors:

- Built-in form load and default `header`, `production`, and `downtime` rendering.
- Stored-form switching from Form Loader with save, discard, and cancel behavior.
- External active-form changes with prompt behavior and cancel preservation.
- Section ordering changes reflected from Layout Manager into Form Loader.
- Repeating-row behavior for production and downtime, including open-row handling, row deletion, delete confirmation policy, and derived field refresh.
- Draft behavior across form switching, including preserved `form_id` / `form_name` context.
- Excel import and export against the active form mappings after the section-driven rebuild.

---

## Major Planning Tracks

### Track 1: Requirements, Tranche Boundary, And Rename Definition
**Goal**: Define the upgrade boundary before implementation begins.

- Freeze the feature set for the first Form Loader tranche around the dynamic renderer and selector workflow
- Define what "support for the new layout system" means in concrete runtime terms for that tranche
- Record the explicit decision to keep internal `production_log` identifiers permanent while moving user-facing runtime text to the `Form Loader` alias
- Identify which user-facing labels, documentation surfaces, and registry metadata stay unchanged until the preferred-alias rollout is fully complete

**Output**: Signed-off scope, tranche boundary, and rename deferment decision.

### Track 2: Layout-System Contract Review
**Goal**: Ensure Form Loader can safely consume the newer layout-system behavior.

- Freeze the live schema surface from the runtime rather than from older docs alone
- Review section ordering, `section_type`, `behavior_profile`, `fields_key`, `mapping_key`, `default_max_rows`, and `delete_row_policy`
- Review repeating-row behavior, delete-policy handling, and current role-driven field behavior
- Review compatibility expectations for existing forms, drafts, and supported import/export paths
- Define where the section-driven behavior belongs across model, controller, and view layers
- Define how unsupported future profiles are handled in this tranche

**Output**: Approved runtime/layout contract for the upgraded Form Loader surface.

### Track 3: UI And Workflow Upgrade Design
**Goal**: Plan the user-facing workflow changes before coding begins.

- Replace the fixed header layout with a dynamic single-section renderer below a fixed selector shell
- Replace the hard-coded production and downtime layout with repeating-section renderers driven by `sections[]`
- Define the selector interaction, prompt-to-switch flow, blank reload behavior, and cancel/reset behavior
- Define local and external active-form change behavior through the existing dispatcher notifications
- Define repeating-row workflow changes, validation/status messaging changes, and draft/import/export impacts for supported profiles
- Record that rename propagation through runtime text and labels is not part of this tranche

**Output**: UI/workflow specification for the dynamic-renderer tranche.

### Track 4: Data, Draft, And Compatibility Strategy
**Goal**: Prevent upgrade churn from breaking live data and recovery workflows.

- Existing draft compatibility using stored `form_id` and `form_name` metadata
- Existing form compatibility for the supported `header`, `production`, and `downtime` profiles
- Export/import behavior continuity for the currently implemented profiles and mappings
- Safe handling of canceled form switches so the selector returns to the loaded form
- Explicit no-op or warning behavior for unsupported future profiles
- Backward-compatibility handling for renamed module references deferred until the rename tranche

**Output**: Migration and compatibility approach.

### Track 5: Documentation And Registry Updates
**Goal**: Keep runtime and docs aligned while the dynamic-renderer tranche lands and the preferred alias rollout is completed.

- Update maintainer and help documentation to reflect the live section-driven contract and selector workflow
- Document which existing references remain unchanged until the rename tranche
- Defer module registry, navigation label, and packaging wording changes that belong to the rename
- Capture the later rename checklist so it is not lost while the architecture tranche proceeds first

**Output**: Documentation/update checklist for the current tranche plus deferred rename checklist.

### Track 6: Validation And Release Readiness
**Goal**: Define the validation contract for the upgraded module.

- Focused compile validation for the touched Form Loader model, controller, and view files
- Module-load validation through `scripts/validate_module_loads.py` or the `Validate Changed UI Modules` task
- Phase-gate validation when the active-form lifecycle or viewport contract changes materially
- Manual workflow smoke tests for selector-driven switching, external form changes, blank reload behavior, dynamic section rendering, repeating-row delete policy, drafts, and import/export
- Accessibility-plan unblock criteria for the dynamic-renderer tranche and the later rename follow-up

**Output**: Verified readiness to hand off into the application-wide NVDA plan.

---

## Proposed Execution Phases

### Phase 1: Live Contract Freeze And Tranche Boundary
- Confirm the source-of-truth runtime contract from `app/models/production_log_model.py`, `app/data_handler_service.py`, and `app/form_definition_registry.py`
- Freeze the first-tranche schema and renderer scope around the supported `header`, `production`, and `downtime` profiles
- Record the explicit rename deferment so the current tranche cannot drift back into mixed-scope implementation

### Phase 2: Architecture And Switch-Flow Design
- Define model/controller/view ownership for the section-driven rebuild
- Define the selector-driven switch flow through the existing app-wide active-form pipeline
- Define local and external active-form prompt, save, cancel, reload, and selector-reset behavior
- Define runtime/layout compatibility rules for supported and unsupported profiles

### Phase 3: Dynamic Renderer Implementation Planning
- Break the rebuild into safe implementation slices across model, controller, and view
- Prioritize the fixed selector shell, dynamic body rendering, then compatibility cleanup
- Identify validation points after each slice

Current progress within Phase 3:

- Completed: fixed selector shell
- Completed: section-driven body rendering for supported profiles
- Completed: external active-form guardrail alignment and supported-profile compatibility cleanup
- Completed: scripted smoke coverage plus defect-driven cleanup from the smoke pass
- Completed: documentation and runbook follow-up for the rename surfaces

### Phase 4: Documentation Alignment And Rename Follow-Up Planning
- Completed: Update architecture and schema docs to match the implemented dynamic renderer contract
- Completed: Finish the remaining documentation and runbook rename surfaces that were left out of the first runtime rollout

### Rename Decisions And Initial Rollout

Settled decisions for the live rename rollout:

- The overall application name remains `Production Logging Center`.
- The main user-facing module label is now `Form Loader`.
- The companion calculations surface is now `Form Calculations`.
- The built-in default form identity now uses id `temp_form_title` and visible name `Temp Form Title`.
- Legacy default-form id `production_logging_center` remains loadable through a compatibility alias in the form registry.
- Internal compatibility-sensitive identifiers remain stable for now, including module ids such as `production_log`, file names, draft metadata keys, dispatcher load helpers, and companion data filenames.
- The workbook fallback sheet title intentionally remains `Production Log` for compatibility.

### Current Rename Inventory Baseline

Current state after the first live rename rollout:

- Runtime navigation labels, controller payloads, view fallbacks, host-shell action warnings, recovery prompts, layout-manager dependency summaries, security labels, and Help Viewer index labels now use `Form Loader` / `Form Calculations` in the active PyQt6 runtime.
- The workbook fallback sheet title is still `Production Log` by explicit decision and should not be treated as unfinished runtime rename work.
- Compatibility-sensitive internal identifiers still use `production_log`, including the module registry name, module path, dispatcher load/open helpers, security rights, validation script arguments, and the default initial module routing in the host shell.
- Related companion internals still carry the stable compatibility family name, including `production_log_calculations`, `production_log_roles`, and `production_log_calculations.json`.
- Remaining documentation follow-up still needs to sweep markdown page titles, runbooks, and any narrative references that intentionally were not part of the first runtime code rollout.
- Active-form defaults no longer use `Production Logging Center` as the built-in form id/name; the live default is `temp_form_title` / `Temp Form Title` with legacy alias support for older drafts and saved registry state.

### Phase 5: Validation And NVDA Handoff Gate
- Validate the upgraded dynamic renderer tranche
- Confirm the system is stable enough to support the later rename tranche and the eventual application-wide NVDA plan

Validation completed for the first runtime rename rollout:

- `Validate Changed UI Modules` task passed for `production_log`, `layout_manager`, and `help_viewer`.
- `scripts/run_production_log_smoke.py` passed after the default-form compatibility migration.
- `scripts/run_production_log_smoke.py` passed again after the live `Form Loader` / `Form Calculations` view-label cleanup.

### Phase 6: Custom Section/Header Runtime Completion (New Priority)

- Completed: Replace profile-specific Form Loader section rendering branches with section-key driven builders
- Completed: Update Layout Manager row-field and mapping selectors to enumerate repeating sections dynamically
- Completed: Expand validation/guardrails to permit broader custom profile usage
- Completed: Define and implement import/export behavior for custom repeating sections
- Completed: Preserve compatibility for legacy/default forms and existing draft payloads

### Phase 7: Documentation And Operational Closure

- Completed: Update maintainer and help docs to reflect complete custom section/header capabilities
- Completed: Record explicit compatibility and migration notes for existing forms
- Completed: Stabilize custom sections and transition to NVDA verification unblocking

---

## Primary Implementation Surfaces

- `app/views/production_log_qt_view.py`: Replace the hard-coded form structure with a fixed selector shell and section-driven body renderer.
- `app/controllers/production_log_qt_controller.py`: Add the guarded form-switch workflow and unify local selector changes with external active-form notifications.
- `app/models/production_log_model.py`: Expose normalized section descriptors and preserve current role-based compatibility helpers.
- `app/form_definition_registry.py`: Reuse stored-form enumeration and app-wide active-form activation.
- `app/controllers/app_controller.py`: Reuse `notify_active_form_changed()` instead of inventing a separate cross-module switch path.
- `app/views/layout_manager_qt_view.py` and `app/controllers/layout_manager_qt_controller.py`: Reuse the existing form-selector interaction as the reference pattern.
- `docs/production_log_json_architecture.md` and `docs/help/layout_config.md`: Update documentation after the runtime contract stabilizes.

---

## Acceptance Criteria

- The first implementation tranche scope is clearly defined before implementation begins.
- The new layout-system support expectations are documented as a section-driven renderer with a fixed top selector shell and support for the current `header`, `production`, and `downtime` profiles only.
- The selector workflow, blank reload behavior, cancel/reset behavior, and external active-form change behavior are documented.
- Compatibility expectations for drafts, forms, import/export behavior, and repeating-row delete policy are documented.
- The rename deferment is explicit and tracked as follow-up work rather than left ambiguous.
- Validation steps for compile checks, module-load checks, phase-gate checks when needed, and manual smoke coverage are documented.
- The upgraded module is stable enough to serve as the baseline for the later rename tranche and the application-wide NVDA verification plan.

---

## Related Plan

- `docs/Plans in Progress or not started/Application-Wide NVDA Accessibility Verification.md`

---

## Notes

- This plan should be treated as the prerequisite gate for final NVDA verification.
- Do not record final NVDA evidence against the pre-upgrade Form Loader state.
- During implementation planning, validate the live contract from the model and data-handler layers before treating the help docs as authoritative.
- If the dynamic renderer later needs truly new section behavior profiles, plan that as a follow-up tranche after the section-driven shell is stable and validated.
