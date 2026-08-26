# Planning Overview and Index

> **Purpose**: Centralized reference for all active and completed project plans.
>
> **Last Updated**: July 3, 2026

---

## Status Summary

| Category | Plan | Status | Phases | Location |
|----------|------|--------|--------|----------|
| Architecture | PyQt6 Host Migration Master Plan | **Completed** | 1-12 | `docs/Completed Plans/` |
| Architecture | Layout Manager PyQt6 Migration Plan | **Historical Reference** | — | `docs/Completed Plans/` |
| Migration & Cleanup | Post-Migration Tk Cleanup and Parity Sweep | **Completed** | 1-6 | `docs/Completed Plans/` |
| Module Enhancements | Layout Manager Future Enhancements | **Completed** | 1-8 | `docs/Completed Plans/` |
| Module Enhancements | Form Loader (production_log) Upgrade, Layout-System Support, and Preferred Alias Rollout | **Completed** | 1-7 | `docs/Completed Plans/` |
| Architecture | Decouple Digital Form Engine and Global Registry System | **Active** | 1-8 planned | `docs/Plans in Progress or not started/` |
| Accessibility | Application-Wide NVDA Accessibility Verification | **Active** | 0-5 planned | `docs/Plans in Progress or not started/` |

---

## Completed Plans (Archive)

### [PyQt6 Host Migration Master Plan](docs/Completed Plans/pyqt6_host_migration_master_plan.md)
- **Status**: ✅ Completed (Phases 1-12)
- **Scope**: Migration from Tk/ttkbootstrap to PyQt6-only host shell with dedicated Layout Manager exception.
- **Key Deliverables**: 
  - Live PyQt6 host shell with shared viewport and sidebar navigation
  - Dedicated external-window runtime for Layout Manager (never add to shared viewport without plan revision)
  - Removal of generic sidecar migration scaffolding
  - Tk host complete removal with fast-fail on legacy backend requests
  - Overflow hardening and screen-fit clamping for all modules
  - Post-migration UI cleanup and wording normalization
- **Validation**: 19-check phase gate (`scripts/validate_pyqt6_phase_gate.py`), module-load validation (`scripts/validate_module_loads.py`), manual smoke tests.
- **Governance Note**: Do not reopen this document for routine feature planning. Future work should use dedicated feature plans (e.g., Layout Manager Future Enhancements).

### [Post-Migration Tk Cleanup and Parity Sweep](docs/Completed Plans/Post-Migration%20Tk%20Cleanup%20and%20Parity%20Sweep.md)
- **Status**: ✅ Completed (Phases 1-6)
- **Scope**: Remove dead Tk-era code from non-shadow `app/` files and restore missing user-facing parity features in PyQt6 runtime.
- **Key Deliverables**:
  - Phase 1: Extraction baseline (Help Viewer, Update Manager Qt paths stable)
  - Phase 2: Dependency sweep confirming no live runtime imports of Tk-era files
  - Phase 3: Archive of definite dead controller/view files with shadow retention
  - Phase 4: Live compatibility cleanup in host adapter, security, and Layout Manager files
  - Phase 5: Parity audit confirming all high-confidence user-facing features present
  - Phase 6: Shell/dedicated-window validation, packaging split implementation (private real data, public dummy data, git tracking inversion)
- **Validation**: Compile checks, module-load validation, PyQt6 phase gate, Windows build with packaging artifact verification.
- **Governance Note**: All cleanup work is now complete. No open deferred items. Layout Manager upgrades are tracked separately in the future-work plan.

### [Layout Manager Future Enhancements](docs/Completed Plans/Layout%20Manager%20Future%20Enhancements.md)
- **Status**: ✅ Completed (Phases 1-8)
- **Scope**: Dedicated Layout Manager runtime UX, performance, feature-expansion, and component-accessibility improvements.
- **Key Deliverables**:
  - Authoring-surface flattening with inner tabs across large multi-pane Layout Manager workflows
  - Undo/redo, version snapshots, context menus, bulk row-field tools, and dependency/safety guardrails
  - Component-level accessibility hardening including accessible labels, tab-order work, High Contrast, and readability font options
  - Documentation and focused regression closure for the dedicated Layout Manager runtime
- **Validation**: Focused compile checks, `validate_module_loads.py layout_manager`, and full `validate_pyqt6_phase_gate.py` pass.
- **Governance Note**: Final NVDA verification was re-scoped into a dedicated application-wide plan because the remaining accessibility gate depends on broader Form Loader modernization rather than Layout Manager-only scope.

### [Form Loader (production_log) Upgrade, Layout-System Support, and Preferred Alias Rollout](docs/Completed%20Plans/Production%20Log%20Upgrade,%20Layout-System%20Support,%20and%20Rename.md)
- **Status**: ✅ Completed (Phases 1-7)
- **Scope**: Execute the permanent internal `production_log` upgrade in sequenced tranches, keep layout-system support aligned with the live runtime contract, and finish the preferred `Form Loader` alias rollout without renaming compatibility-sensitive internal identifiers.
- **Key Deliverables**:
  * Fixed selector shell and section-driven body rendering for supported profiles.
  * External active-form guardrail alignment and default-form migration.
  * Integration of custom options sources and Excel import/export value transformations.
  * Preferred alias rollout in PyQt6 runtime text and help guides.
- **Validation**: Compile checks, `scripts/run_production_log_smoke.py` passes, and MVC file coverage.

### [Layout Manager PyQt6 Migration Plan](docs/Completed Plans/layout_manager_pyqt6_migration_plan.md)
- **Status**: Historical Reference Only
- **Note**: Superseded by the PyQt6 Host Migration Master Plan and the live dedicated-window contract in `app/layout_manager_dispatcher.py`.
- **Use**: Reference only for understanding earlier migration strategy; do not use for active work.

---

## Active Plans (In Progress or Backlog)

### [Decouple Digital Form Engine and Global Registry System](docs/Plans%20in%20Progress%20or%20not%20started/Decouple%20Digital%20Form%20Engine%20and%20Global%20Registry%20System.md)
- **Status**: Active (Ready for execution)
- **Scope**: End-to-end decoupling of the Form Engine into a portable Create/Modify/Fill/Export digital form system. Establish self-contained form packages in `data/forms/<form_id>/`, enforce zero-defaults loading, generalize event-driven calculations and shift configurations, evolve Rate Manager into Global Registry Editor, add soft-deletion/restoration for packaged starter forms, and implement graceful 0-form empty states.
- **Trigger Keyword**: `EXECUTE_DECOUPLE_FORM_ENGINE_PLAN`
- **Key Constraints**: Preserve full backward compatibility and functional parity for `temp_form_title` (canonical GLC Production Log) via automated migration with backup.

### [Application-Wide NVDA Accessibility Verification](docs/Plans%20in%20Progress%20or%20not%20started/Application-Wide%20NVDA%20Accessibility%20Verification.md)
- **Status**: Active (Ready for execution)
- **Scope**: Verify NVDA accessibility across the full program after the upgraded Form Loader flows and related labels/workflows have stabilized.
- **Baseline**: Layout Manager component-level accessibility work is already delivered. Form Loader prerequisite upgrade has been completed and validated.
- **Key Constraints**: Review accessibility against the modern Form Loader state with proper role resolution.
- **Start Criteria**: The Form Loader upgrade plan is completed and archived.

---

## Planning Principles

### Active Plans
1. **No Mini-Plans**: Do not create module-specific or per-feature migration plans. Update the appropriate master plan in place.
2. **Canonical References**: 
  - PyQt6 host architecture → `docs/Completed Plans/pyqt6_host_migration_master_plan.md`
  - Post-migration cleanup → `docs/Completed Plans/Post-Migration Tk Cleanup and Parity Sweep.md`
  - Form Loader / `production_log` upgrade planning → `docs/Completed Plans/Production Log Upgrade, Layout-System Support, and Rename.md`
  - Application-wide NVDA verification → `docs/Plans in Progress or not started/Application-Wide NVDA Accessibility Verification.md`
3. **Governance Documents**: `.github/copilot-instructions.md` is the active runtime/architecture reference. Keep it aligned with completed phase closure summaries.

### Historical Plans
- Older migration runbooks and phase reports are preserved in `docs/` and `docs/Completed Plans/` as reference only.
- Do not extract new plans from historical artifacts. Update the canonical active plan instead.

### Validation Continuity
- **Canonical Validation Path**: Use the best available local path in this checkout: focused `py_compile`, available VS Code validation tasks, and direct manual smoke runs.
- **If Legacy Validators Exist**: `scripts/validate_pyqt6_phase_gate.py` and `scripts/validate_module_loads.py` remain the target validator surface and should be kept aligned with completed PyQt6 architecture.
- **Keep Updated**: Validation guidance must match the current repository snapshot and should not assume optional scripts are always present.

---

## Next Steps

### Immediate (July 2026)
1. Initiate the Application-Wide NVDA Accessibility Verification plan since the Form Loader prerequisites are complete.
2. Keep planning and delegation docs tidy by archiving transient smoke and review artifacts out of active roots.

### Medium Term (1-2 months)
1. Execute the remaining phases of the NVDA Accessibility Verification plan.
2. Maintain validator alignment with any new architecture changes.

### Long Term (Post-Enhancement Work)
1. Complete and archive the Form Loader / `production_log` upgrade plan.
2. Execute and archive the application-wide NVDA verification plan.
3. Use this index as the template for future planning governance.

---

## Quick Navigation

**Completed Work**: All 12 phases of PyQt6 migration + 6 phases of Tk cleanup are done. Branch is production-ready for release with packaging split (private real data, public dummy data).

**Current Active Plans**: Application-wide NVDA verification is the active plan now that the Form Loader upgrade prerequisite has been completed.

**Governance**: Use `.github/copilot-instructions.md` for architecture questions; use this index to find the right plan for your current task.

**Validation**: Run `scripts/validate_pyqt6_phase_gate.py` after any system changes to confirm architecture integrity.
