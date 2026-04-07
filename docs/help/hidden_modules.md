# Hidden Modules

These modules are bundled with Logging Center but intentionally do not appear in the left navigation because they are support components, internal services, or context-specific tools.

## About System

- Shows module names and versions.
- Marks loaded external override modules with `(external)`.
- Opens license access from inside the app.

## App Logging

- Captures internal exception logging.
- Supports diagnostics without exposing a user-facing page.

## Data Handler

- Owns workbook import and export logic.
- Normalizes Production Log header values used by draft JSON and Excel routing.
- Exists as a shared service module rather than a standalone page.

## Downtime Codes

- Provides the default downtime-code map and normalization helpers.
- Supports Settings Manager and Production Log without acting as its own screen.

## Help Viewer

- Powers the Help Center itself.
- Stays out of sidebar navigation because it is opened from Help actions rather than treated as a workflow module.

## Persistence

- Writes JSON files with rotating backup copies.
- Used by draft saves, settings saves, layout saves, rate saves, and updater restores.

## Splash

- Handles startup presentation behavior for the application launch sequence.
- Not meant to be opened during normal in-app navigation.

## Theme Manager

- Applies theme normalization and readability overrides.
- Supports live theme switching across the app.

## Path Helpers

- Resolves local, bundled, and external file paths.
- Supports packaged and source workflows, including local `.venv` resolution for build tasks.

## Notes

- Hidden does not mean unused. These modules are active support layers used throughout Logging Center.
- Backup / Recovery is user-facing and stays in the sidebar even though it works closely with the internal persistence helper.
- Update Manager remains visible because it is a user workflow, even though some of its behavior also overlaps with internal support logic.
