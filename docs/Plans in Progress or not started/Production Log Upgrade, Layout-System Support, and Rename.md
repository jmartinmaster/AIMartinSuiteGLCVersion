# Plan: Production Log Upgrade, Layout-System Support, and Rename

> **Status**: Not started.
>
> **Scope**: Carefully plan and execute the next Production Log upgrade so the module can support the newer layout-system direction, absorb the upcoming feature changes, and complete the Production Log rename without breaking runtime behavior, draft compatibility, or downstream verification work.
>
> **Relationship To Accessibility Planning**: Completion of this plan is the gate that unblocks the application-wide NVDA verification plan.
>
> **Planning Note**: This work requires dedicated planning sessions before implementation begins. Do not treat this document as an implementation-start signal without first running a focused planning chat for scope, rename decisions, layout-system contract decisions, and tranche sequencing.

---

## Intent

The Production Log is now the main blocker for the final NVDA pass.

This plan exists to separate that prerequisite work from the accessibility-verification plan and to ensure the upgrade is designed deliberately before implementation starts.

---

## Why This Plan Exists

The remaining NVDA work should not proceed against a Production Log surface that is about to change materially.

The Production Log still needs a planned upgrade that covers:

- new feature support
- support for the newer layout system
- completion of the Production Log rename

Those changes can alter field labeling, focus flow, workflow sequencing, help documentation, export wording, and user-facing status messages. They need to settle first so accessibility verification is performed once against the intended final state.

---

## Baseline

- The live application already has PyQt6 Production Log controller/view foundations.
- Layout Manager can now author richer layout metadata, including section behavior and repeating-row delete policy.
- Production Log consumes layout-driven structure today, but the upcoming upgrade needs a broader design pass before implementation.
- The rename target is not yet finalized in this plan and should be treated as a planned decision item rather than assumed text.

---

## Major Planning Tracks

### Track 1: Requirements And Rename Definition
**Goal**: Define the upgrade boundary before implementation begins.

- Finalize the feature set for the next Production Log tranche
- Define what "support for the new layout system" means in concrete runtime terms
- Finalize the Production Log rename target and naming rules
- Identify all user-facing labels, documentation, and registry metadata affected by the rename

**Output**: Signed-off scope and rename target.

### Track 2: Layout-System Contract Review
**Goal**: Ensure Production Log can safely consume the newer layout-system behavior.

- Review section behavior expectations
- Review repeating-row behavior and delete-policy handling
- Review compatibility expectations for existing forms and drafts
- Define where new layout-driven behavior belongs across model, controller, and view layers

**Output**: Approved runtime/layout contract for the upgraded Production Log.

### Track 3: UI And Workflow Upgrade Design
**Goal**: Plan the user-facing workflow changes before coding begins.

- Header workflow changes
- Repeating-row workflow changes
- Validation/status messaging changes
- Draft/import/export workflow impacts
- Rename propagation through runtime text and window/module labels

**Output**: UI/workflow specification for the renamed upgraded module.

### Track 4: Data, Draft, And Compatibility Strategy
**Goal**: Prevent upgrade churn from breaking live data and recovery workflows.

- Existing draft compatibility
- Existing form compatibility
- Export/import behavior continuity
- Backward-compatibility handling for renamed module references where needed

**Output**: Migration and compatibility approach.

### Track 5: Documentation And Registry Updates
**Goal**: Keep runtime and docs aligned when the rename lands.

- Help documentation updates
- Module registry and navigation label updates
- User-facing terminology updates across docs and status text
- Any packaging or launch wording that references the old name

**Output**: Documentation/update checklist tied to the rename.

### Track 6: Validation And Release Readiness
**Goal**: Define the validation contract for the upgraded module.

- Focused compile/type validation
- Module-load validation
- Phase-gate validation
- Manual workflow smoke tests for the upgraded Production Log
- Accessibility-plan unblock criteria

**Output**: Verified readiness to hand off into the application-wide NVDA plan.

---

## Proposed Execution Phases

### Phase 1: Scope And Rename Freeze
- Confirm features
- Confirm rename target
- Confirm layout-system requirements

### Phase 2: Architecture And Contract Design
- Define model/controller/view ownership for the upgrade
- Define runtime/layout compatibility rules

### Phase 3: Implementation Tranche Planning
- Break the upgrade into safe implementation slices
- Identify validation points after each slice

### Phase 4: Documentation And Runtime Terminology Planning
- Prepare rename checklist across runtime/docs/help/index surfaces

### Phase 5: Validation And NVDA Handoff
- Validate upgraded Production Log
- Confirm the system is stable enough to unblock the application-wide NVDA plan

---

## Acceptance Criteria

- The Production Log upgrade scope is clearly defined before implementation begins.
- The new layout-system support expectations are documented and validated.
- The Production Log rename target is finalized and propagated through planning, docs, and runtime surfaces.
- Compatibility expectations for drafts, forms, and workflow behavior are documented.
- The upgraded module is stable enough to serve as the baseline for the application-wide NVDA verification plan.

---

## Related Plan

- `docs/Plans in Progress or not started/Application-Wide NVDA Accessibility Verification.md`

---

## Notes

- This plan should be treated as the prerequisite gate for final NVDA verification.
- Do not record final NVDA evidence against the pre-upgrade Production Log state.
