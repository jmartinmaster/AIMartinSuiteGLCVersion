# Shadow Qt App Archive

This folder stores reference copies of live PyQt6-era modules that were simplified or removed from runtime code.

Rules:
- Preserve the live relative structure under `shadow/qt_app/`.
- Keep files here read-only for runtime; these are archive snapshots only.
- Prefer moving redundant wrappers/utilities here before deleting from live paths.
