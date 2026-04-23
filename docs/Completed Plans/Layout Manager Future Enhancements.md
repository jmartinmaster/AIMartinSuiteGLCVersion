# Plan: Layout Manager Future Enhancements

> **Status**: Completed and archived on April 22, 2026.
>
> **Scope**: User experience refinements, performance optimization, feature expansion, and component-level accessibility hardening for the dedicated PyQt6 Layout Manager runtime.
>
> **Closure Note**: Program-wide NVDA verification was intentionally removed from this plan's closure gate and moved into a dedicated application-wide accessibility plan. Final screen-reader verification now depends on broader Production Log modernization, new layout-system support, and the planned Production Log rename rather than Layout Manager-only scope.

---

## Closure Summary

- Phase 1 (UX Quick Wins) completed for the dedicated Layout Manager runtime:
  - Create Blank workflow
  - Section Editor with section ordering and metadata editing
  - Expanded row-field authoring surface
  - Repeating-row delete-policy authoring consumed by Production Log runtime
- Phase 2 (Performance Hardening) completed for current scope:
  - Batched heavy table/tree updates
  - Reduced eager tree expansion
  - Added explicit busy/progress feedback
  - Deferred first heavy render until the window is visible
  - Added refresh timing capture for runtime profiling
- Phase 3 (Core Feature Expansion) completed for current scope:
  - Right-click context menus
  - Undo/redo history controls
  - Form version snapshots
  - Bulk row-field operations
- Phase 4 (Accessibility and Compliance) completed for component scope:
  - Accessible names/descriptions on key controls
  - Explicit tab-order wiring
  - High Contrast mode
  - Readability-oriented font profile selection
  - Non-color status prefixes (`INFO` / `ERROR`)
- Phase 5 (UX Backlog Completion) completed for current scope:
  - `Ctrl+S`, `Escape`, `Ctrl+L`, `Ctrl+Tab`, `Ctrl+Shift+Tab`
  - Preview metadata surface
  - Validation summary surface
  - Accelerated table traversal shortcuts
- Phase 6 (Scale + Throughput Completion) completed for current scope:
  - JSON Editor moved into its own top-level tab
  - Block View, Import / Export, Preview, and Structure flattened into inner-tab workspaces
  - Responsive content scaling
  - Import/export metadata caching and workbook metadata streaming
  - Chunked table rendering for larger schemas
- Phase 7 (Dependency + Safety Completion) completed for current scope:
  - Pending draft dependency audit keyed by stored `form_id`
  - Summary-tab draft usage reporting
  - Delete-form guardrails while dependent pending drafts exist
- Phase 8 (Verification and Closure) completed for Layout Manager scope:
  - Help documentation and authoring guide updated
  - Planning documentation updated
  - Focused regression/validation completed
  - Broader NVDA validation handed off to dedicated application-wide planning

---

## Validation Evidence

Focused validation for the final dependency/safety tranche passed before archival:

- `python -m py_compile app/models/layout_manager_model.py app/controllers/layout_manager_qt_controller.py app/views/layout_manager_qt_view.py app/layout_manager.py`
- `scripts/validate_module_loads.py layout_manager`
- `scripts/validate_pyqt6_phase_gate.py` with 19/19 checks passing

Manual smoke validation was performed iteratively during the feature tranches for the dedicated Layout Manager runtime. Final application-wide NVDA verification is no longer part of this completed module plan.

---

## Why NVDA Moved Out Of Scope

The final NVDA gate was removed from this plan because the remaining accessibility verification work is no longer specific to Layout Manager.

- The desired verification target is the entire application, not just the dedicated Layout Manager runtime.
- The primary blocker is a planned Production Log upgrade that must add support for the newer layout system, introduce the upcoming feature changes, and complete the Production Log rename.
- Running NVDA verification before that Production Log work would produce incomplete evidence and likely require the accessibility pass to be repeated.

Layout Manager accessibility implementation remains part of this archived plan's delivered scope. Application-wide screen-reader verification now belongs to a dedicated follow-on plan.

---

## Related Follow-On Plans

- `docs/Plans in Progress or not started/Production Log Upgrade, Layout-System Support, and Rename.md`
- `docs/Plans in Progress or not started/Application-Wide NVDA Accessibility Verification.md`

---

## Notes

- The dedicated Layout Manager external-window contract remains unchanged.
- Future Layout Manager work should be tracked through new scoped enhancement plans only if materially distinct from the completed tranche archived here.
