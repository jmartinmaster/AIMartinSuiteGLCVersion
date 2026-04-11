# Release Regression Checklist

Use this checklist before packaging or publishing the next Dispatcher Core release.

## Security And Admin Checks

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

## Runtime And Packaging Checks

- Run `py_compile` on touched Python files before release.
- Smoke-test startup from source mode.
- If packaging on Windows, confirm the packaged EXE starts, loads bundled modules by default, and respects override trust after admin changes.
- If packaging on Windows, confirm side-by-side EXE handoff still works and older EXE cleanup remains available.

## Production Log Follow-Up Checks

- Confirm Production Log no longer shows a large blank region above `Draft Status` inside the shared app shell.
- Confirm the Production Log responsive summary charts appear at the intended window size after the whitespace issue is resolved.
- Confirm the summary panel does not force the main shell canvas to remain scrolled away from the top when the module loads or resizes.