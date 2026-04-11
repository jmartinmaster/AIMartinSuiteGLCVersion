# Snapshot Feature Sweep

This note extends the earlier security-focused migration review and checks the rest of newest-main against the current MVC code in the_golden_standard.

## Summary

- Production Log is closer to parity than it first appeared.
- Layout Manager is largely already migrated.
- Recovery Viewer is already at feature parity for the snapshot behaviors checked.
- The best remaining reusable changes are a few targeted Production Log workflow improvements plus a small number of dispatcher and updater behaviors that are already mostly present.

## Production Log

### Already Present In MVC

The current MVC implementation already includes most of the snapshot behaviors that were worth keeping:

- draft save, resume, pending-draft browsing, and current-draft deletion
- backup and recovery integration
- Excel export and import
- open last export and print last export
- downtime balancing and ghost-time display
- rate override checkbox behavior
- auto-save and live row math updates

Evidence:

- the_golden_standard/views/production_log_view.py already exposes Export Excel, Open Last Export, Print Last Export, Balance Downtime, and Import Excel.
- the_golden_standard/views/production_log_view.py already implements rate override toggling and ghost-time handling.
- the_golden_standard/views/production_log_view.py already includes Resume Latest, Pending Drafts, Backup / Recovery, and Delete Current Draft.

### Likely Remaining Gaps Worth Porting

#### 1. Row-level delete actions for production and downtime rows

Status: port

Why:

- The current MVC Production Log keeps open-row behavior, but it does not appear to expose snapshot-style per-row delete actions for existing rows.
- That is a useful operator workflow improvement, especially when cleaning up imported or resumed drafts.

How to fit MVC:

- Add delete buttons in the view for production and downtime rows.
- Let the controller or view remove the row from in-memory UI state, then recalculate totals and save draft state if needed.
- Do not copy the snapshot save-and-reload approach literally if direct row removal is cleaner in the MVC implementation.

#### 2. Explicit refresh or reload-current-draft action

Status: adapt

Why:

- newest-main had a simple refresh workflow that reloaded the current state.
- The current MVC screen has recovery actions but no obvious dedicated refresh control.

How to fit MVC:

- Add a small Refresh View or Reload Draft button only if the workflow proves useful after row-delete support.
- Prefer a controller method that reloads from current_draft_path or latest_draft_path instead of re-instantiating the whole module.

#### 3. Snapshot pending-drafts card layout

Status: optional adapt

Why:

- The snapshot used a more custom pending-drafts presentation.
- The current MVC version already has Pending Drafts and a separate Backup / Recovery module.

Recommendation:

- Only revisit this if the existing pending-draft dialog feels too limited in use.
- Prefer improving the existing recovery and pending-draft views rather than duplicating navigation paths.

### Not A Priority

- Excel import and export: already present
- print support: already present
- ghost time balancing logic: already present
- rate override logic: already present
- pending drafts and recovery flow: already present

## Layout Manager

### Current State

Layout Manager appears effectively migrated already.

The current MVC version already has:

- block view and JSON editor tabs
- add, move, update, and remove header fields
- config validation
- protected fields
- live preview
- preview tooltips
- service-backed load and save path handling

Evidence:

- the_golden_standard/views/layout_manager_view.py already implements preview tooltip helpers and binds them into the preview.
- the_golden_standard/models/layout_manager_model.py already uses LayoutConfigService and covers validation, add, move, remove, and update operations.

### Action

Status: verify only

Recommendation:

- No meaningful snapshot feature appears missing here from the behaviors checked.
- Only verify that load precedence and save targets still behave as expected under external files.

## Recovery Viewer

### Current State

Recovery Viewer is already at parity for the snapshot behaviors examined.

The current MVC implementation already includes:

- pending draft records
- recovery snapshot records
- configuration backup records
- restore selected
- resume selected draft
- open selected file and containing folder

Evidence:

- the_golden_standard/models/recovery_viewer_model.py mirrors the snapshot record-collection structure.
- the_golden_standard/controllers/recovery_viewer_controller.py preserves restore and resume workflows.
- the_golden_standard/views/recovery_viewer_view.py provides the same main actions.

### Action

Status: no port needed

## Other Quick-Sweep Findings

### Dispatcher and Shell

The useful snapshot-era shell changes called out in newest-main are already largely present in MVC:

- Help menu Report A Problem exists.
- persistent modules exist.
- startup module update notifications exist.
- Install All Available Payloads exists in Update Manager.
- update banner is mounted above the main content viewport.
- stale external overrides are cleared before executable handoff.

This means the dispatcher and updater migration is further along than the snapshot-only comparison suggested.

### Settings Manager

Settings Manager is already ahead of or parallel to newest-main in several places because the MVC version has separate controller and view pieces and already includes:

- persistent modules selection
- security status
- developer and admin tools dialog
- external override trust management

The main open issue there is still the broader security redesign from the earlier assessment, not ordinary settings parity.

### Rate Manager

No significant reusable behavior gap was found in the quick sweep.

## Practical Priority List

If we pull anything else from newest-main outside the security work, the best order is:

1. Add row-level delete actions to Production Log
2. Consider a simple Production Log refresh or reload-current-draft action
3. Recheck Layout Manager load and save precedence under local versus bundled config files

## Bottom Line

Outside the multi-user security work, the current MVC version has already absorbed most of the worthwhile newest-main behaviors. The remaining practical gap is mainly Production Log row-management polish, not a broad module migration.