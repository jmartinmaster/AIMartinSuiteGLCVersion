# Release Regression Checklist

Use this checklist before packaging or publishing Dispatcher Core `2.1.4` or the next release cut from the same MVC baseline.

## Source Gate

- Run `py_compile` or equivalent syntax validation on touched Python files.
- Smoke-test startup from source mode.
- Confirm the app window title reports the expected Dispatcher Core version.
- Confirm About loads cleanly and no baseline navigation path raises a module load error banner.

## Packaged Windows Gate

- Complete the full packaged validation flow in [docs/packaged_windows_validation_runbook.md](./packaged_windows_validation_runbook.md).
- Confirm the built EXE name matches the release version and launches without recovery, updater, or security regressions.
- Confirm side-by-side EXE handoff and obsolete-EXE cleanup still work as expected.

## Release Hygiene

- Confirm `CHANGELOG.md` reflects the shipped behavior.
- Confirm README and Help Center guidance still match the current security, updater, and packaging flows.
- Remove or archive any temporary handoff or comparison notes that no longer carry unique information after validation completes.