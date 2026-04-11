# Release Regression Checklist

Use this checklist before packaging or publishing Dispatcher Core `2.1.4` or the next release cut from the same MVC baseline.

## Source Gate

- Run `py_compile` or equivalent syntax validation on touched Python files.
- Smoke-test startup from source mode with `python main.py`.
- Smoke-test focused source launch with `python launcher.py --module about`.
- Confirm the app window title reports the expected Dispatcher Core version.
- Confirm About loads cleanly and no baseline navigation path raises a module load error banner.
- Confirm the first round of module switches stays responsive after the background preload cycle completes.
- Touch a managed source file, reopen the affected module, and confirm the page rebuilds instead of reusing stale UI state.

## Security And Admin Gate

- Confirm general users do not see the Developer & Admin row in Settings Manager.
- Confirm an authenticated admin does see the Developer & Admin row.
- Confirm non-secure mode can be enabled and disabled from Security Administration.
- Confirm non-secure mode persists across restart.
- Confirm Reset Vault requires confirmation, typed `RESET`, and current-password re-entry.
- Confirm Reset Vault disables non-secure mode and clears the admin session.

## External Override Trust Checks

- Confirm external override files can be saved while override trust is disabled.
- Confirm override files remain inactive while override trust is disabled.
- Confirm enabling override trust allows external overrides to load on module reload.
- Confirm disabling override trust returns the app to bundled modules.
- Confirm Update Manager payload installs report staged-but-inactive behavior when override trust is disabled.

## Settings And Update Checks

- Confirm `update_repository_url` is absent from the ordinary settings form.
- Confirm repository URL, Advanced Dev Updates, and override trust are editable only through Developer & Admin tools.
- Confirm Update Manager uses the configured repository URL.
- Confirm stable EXE checks still run and surface status correctly.
- Confirm JSON payload restores still preserve backups before overwrite.

## Packaged Windows Gate

- Complete the full packaged validation flow in [docs/packaged_windows_validation_runbook.md](./packaged_windows_validation_runbook.md).
- Confirm the built EXE name matches the release version and launches without recovery, updater, or security regressions.
- Confirm side-by-side EXE handoff and obsolete-EXE cleanup still work as expected.

## Release Hygiene

- Confirm `CHANGELOG.md` reflects the shipped behavior.
- Confirm README and Help Center guidance still match the current security, updater, and packaging flows.
- Remove or archive any temporary handoff or comparison notes that no longer carry unique information after validation completes.
