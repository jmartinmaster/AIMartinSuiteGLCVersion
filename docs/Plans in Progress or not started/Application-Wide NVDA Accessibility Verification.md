# Plan: Application-Wide NVDA Accessibility Verification

> **Status**: Blocked pending Production Log modernization and rename prerequisites.
>
> **Scope**: Adjust, verify, and document NVDA accessibility behavior across the full PyQt6 application shell and module set, including shared-viewport modules, dedicated-window exceptions, dialogs, status surfaces, and workflow transitions.
>
> **Primary Gate**: Do not execute the final NVDA validation pass until the Production Log upgrade, layout-system adoption, and Production Log rename work are complete.
>
> **Planning Note**: This work also requires dedicated planning sessions before implementation or remediation begins. Once the prerequisite Production Log work is complete, start with a planning chat to freeze verification scope, audit order, evidence format, and remediation handling before running the formal NVDA pass.

---

## Intent

This plan exists so NVDA work is tracked at the correct scope.

- The target is the entire program, not Layout Manager in isolation.
- Accessibility fixes and verification evidence should be gathered against the post-upgrade application state.
- The final output should be a reusable accessibility verification record, not a one-off module note.

---

## Why This Is Separate

The earlier Layout Manager plan incorrectly carried NVDA as its final closure gate. That is no longer the right boundary.

- Layout Manager accessibility implementation is already delivered at component scope.
- The remaining verification is application-wide and must include Production Log, shell navigation, dialogs, status messaging, and cross-module workflow behavior.
- The largest unresolved variable is the Production Log upgrade and rename effort, which can materially change control labels, workflow order, layout usage, and screen-reader expectations.

Until that Production Log work is finished, any final NVDA validation pass would be incomplete and likely need to be rerun.

---

## Blocking Prerequisites

This plan stays blocked until the following are complete:

1. The Production Log upgrade plan is implemented and validated.
2. Production Log supports the new layout system expected by the upgraded workflow.
3. The Production Log rename is finalized and reflected in runtime labels, help documentation, and navigation text.
4. Shared module labels, status text, and user-facing terminology are stable enough to produce durable NVDA evidence.

See the prerequisite plan:

- `docs/Plans in Progress or not started/Production Log Upgrade, Layout-System Support, and Rename.md`

---

## Verification Scope

When unblocked, NVDA verification must cover the full application surface, including:

- Host shell navigation, sidebar labels, focus order, and non-blocking toast/status behavior
- Production Log workflows after modernization and rename
- Layout Manager dedicated runtime flows
- Settings Manager, Recovery Viewer, Update Manager, Help Viewer, Rate Manager, About, and related dialogs
- Cross-module transitions where focus or announced context can be lost
- Confirmation dialogs, warnings, validation errors, and success surfaces

---

## Planned Phases

### Phase 0: Accessibility Baseline Freeze
**Goal**: Freeze the app state that NVDA evidence will be gathered against.

- Confirm Production Log modernization/rename is complete
- Confirm module labels and user-facing names are stable
- Confirm help/documentation wording is aligned with runtime text

**Validation**: Regression check that no major rename/layout churn remains open.

### Phase 1: Shell And Shared Surface Audit
**Goal**: Verify the host shell and shared interaction surfaces before module-specific passes.

- Sidebar navigation order and announcement quality
- Focus transitions between shell chrome and active module surface
- Toast/status announcement behavior
- Dialog titles, warning text, and confirmation flow readability

**Validation**: Manual NVDA smoke pass through startup, navigation, and common dialogs.

### Phase 2: Production Log NVDA Pass
**Goal**: Verify the upgraded Production Log after layout-system adoption and rename.

- Header workflow
- Repeating-row workflows
- Draft save/resume/delete flows
- Import/export flows
- Validation, calculation, and status messaging

**Validation**: Manual NVDA walkthrough of the full Production Log authoring and export loop.

### Phase 3: Module Sweep
**Goal**: Verify the rest of the application modules against stable terminology and focus behavior.

- Layout Manager
- Settings Manager
- Recovery Viewer
- Update Manager
- Help Viewer
- Rate Manager
- About and smaller support surfaces

**Validation**: Module-by-module NVDA notes and defect list.

### Phase 4: Remediation Pass
**Goal**: Fix issues found during the shell/module sweeps.

- Adjust accessible names/descriptions
- Correct focus order or missing announcements
- Refine warning/status wording where screen-reader output is unclear
- Recheck any broken cross-module transitions

**Validation**: Repeat focused NVDA checks for all remediated surfaces.

### Phase 5: Final Evidence And Sign-Off
**Goal**: Produce final program-wide NVDA verification evidence.

- Consolidated verification notes
- Residual risk list, if any
- Sign-off that accessibility evidence matches the renamed, upgraded application state

**Validation**: Final end-to-end NVDA pass across startup, navigation, Production Log, supporting modules, and shutdown.

---

## Acceptance Criteria

- Production Log modernization, layout-system support, and rename are complete before formal NVDA execution begins.
- NVDA verification covers the full program, not just isolated module slices.
- Focus order, labels, status messaging, and confirmation flows are documented with manual verification notes.
- Any issues discovered during the pass are either fixed or explicitly tracked as residual risks.
- The resulting evidence reflects the final renamed Production Log and stable post-upgrade application state.

---

## Notes

- This plan is intentionally blocked until the Production Log prerequisite plan is complete.
- Layout Manager component-level accessibility work is already delivered; it should be revalidated here only as part of the full application pass.
