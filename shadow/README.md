# Shadow Archive

This directory holds disconnected Tk and ttkbootstrap-era surfaces copied from the live app during Phase 9.

Rules:
- Files under `shadow/` are reference-only and are not part of the live runtime.
- The live application is being cut over to PyQt6-only startup and should fail fast if a removed Tk path is still reached.
- Keep the relative project structure under `shadow/` aligned with the live tree so removed paths are easy to compare.

Additional archive lane:
- `shadow/qt_app/` stores reference snapshots of PyQt6-era modules that were reduced or removed from live runtime paths.
- Keep `shadow/qt_app/` structure aligned to the live tree for straightforward diff and rollback.
