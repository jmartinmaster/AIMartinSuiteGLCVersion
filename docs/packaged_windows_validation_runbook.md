# Packaged Windows Validation Runbook

Use this runbook on a Windows packaging machine after building the next EXE release. This is the canonical step-by-step packaged validation document; the shorter release checklist should point here instead of repeating the same manual checks.

## Preparation

1. Open a Windows machine with the project checkout and its packaging dependencies installed.
2. From the project root, build the EXE with `python build.py`.
3. Confirm a versioned EXE for Dispatcher Core `2.1.4` appears in `dist/` and that older EXEs, if any, were archived to `dist/Old_exe`.
4. Close any previously running copy of the application before starting validation.

## Baseline Startup

1. Launch the newly built EXE from `dist/`.
2. Confirm the splash screen appears and the app opens without an error dialog.
3. Confirm the window title reports Dispatcher Core `2.1.4`.
4. Confirm Production Log opens by default.
5. Confirm the footer update banner is hidden while no update job is active.

## Production Log Validation

1. Confirm `Refresh View`, `Resume Latest`, `Pending Drafts`, and `Delete Current Draft` are visible and responsive.
2. Create a small draft, save it, delete a production row, reload the draft, and confirm the deletion persisted.
3. Add downtime rows, change the Balance Mix control, run Balance Downtime, and confirm the ghost-time display and summary charts update correctly.
4. Export a workbook and confirm `Open Last Export` plus `Print Last Export` enable only after the export succeeds.
5. Confirm the module does not show the earlier blank region above `Draft Status` in the shared shell.

## Security And Admin Validation

1. Open Settings Manager before authenticating.
2. Confirm the Developer & Admin row is not visible.
3. Open Manage Security and authenticate as admin.
4. Confirm the Developer & Admin row now appears.
5. In Security Administration, enable non-secure mode.
6. Close and relaunch the EXE.
7. Confirm a startup warning indicates non-secure mode is enabled.
8. Open a protected module and confirm it opens without a password prompt.
9. Disable non-secure mode.
10. Confirm protected modules require authentication again.

## Vault Reset Validation

1. Open Security Administration with an active admin session.
2. Start Reset Vault.
3. Cancel before typing `RESET` and confirm nothing changes.
4. Start Reset Vault again and type an incorrect confirmation string.
5. Confirm the vault remains intact and the admin session stays active.
6. Start Reset Vault again, type `RESET`, and enter the current password.
7. Confirm the vault reset succeeds, non-secure mode is disabled, and the admin session is cleared.
8. Confirm the next authentication attempt requires creating or re-entering the master password as expected.

## External Override Trust Validation

1. Re-enter an admin session and open Developer & Admin tools.
2. Confirm External Override Trust is disabled by default.
3. Save an override for a safe module such as `about`.
4. Confirm the UI reports the file was saved but remains inactive.
5. Reload that module and confirm the bundled version still loads.
6. Enable External Override Trust.
7. Reload the same module and confirm the override now loads.
8. Disable External Override Trust again.
9. Reload the module and confirm the bundled version is preferred again.

## Update Manager Validation

1. Open Update Manager.
2. Confirm repository information resolves correctly and matches the currently configured repository URL.
3. If a module payload is available, install one while External Override Trust is disabled.
4. Confirm the install message says the payload is staged but inactive.
5. Enable External Override Trust and reload the affected module.
6. Confirm the staged override becomes active.
7. If documentation or JSON restores are available, confirm they still install successfully and preserve backups.

## Recovery And Settings Validation

1. Open Backup / Recovery and restore a draft snapshot back into Production Log.
2. Restore a configuration backup and confirm the record list refreshes after restore.
3. Open Settings and attempt to save invalid downtime-code rows, then confirm validation blocks the save.
4. Save a valid downtime-code change and confirm it persists after reopening the dialog.
5. Confirm module whitelist and persistent-module selections still save and reload correctly.

## EXE Handoff Validation

1. If a newer packaged EXE is available from the configured repository, start the stable update flow.
2. Confirm the newer EXE downloads beside the current one instead of overwriting it in place.
3. Confirm stale external module overrides are cleaned up before handoff when expected.
4. Confirm the newer EXE launches successfully.
5. Confirm the app later offers cleanup of older EXE copies and ignores the running `2.1.4` build itself.

## Sign-Off

- Record PASS or FAIL for each section above.
- If any section fails, capture the exact step number, visible message, and whether the issue reproduces on relaunch.
- After a clean pass, update release notes or packaging notes if the Windows behavior differs from the current docs.