# Phase 9 — Tk Host Removal Runbook

Status: COMPLETED

Historical status: This document is a closeout artifact for the completed Tk-host removal phase. It is retained for audit and packaging reference, not as an active implementation plan.

This runbook documents the inventory, parity mapping, and closeout notes that supported removal of the Tk host path during Phase 9. Treat it as historical reference.

## Inventory (discovered Tk usage)
- `app/views/app_view.py` — Tk host shell (primary Tk shell view)
- `app/host_ui_adapter.py` — `TkHostUiAdapter` and `PyQt6HostUiAdapter` (adapter contains both implementations)
- `app/app_platform.py` — imports `PhotoImage` from `tkinter` (icon path handling)
- Controller files (use Tk or `ttkbootstrap` in fallback paths):
  - `app/controllers/production_log_controller.py` (imports `tk`)
  - `app/controllers/about_controller.py` (uses `tkinter.messagebox`)
  - `app/controllers/recovery_viewer_controller.py` (uses `messagebox`)
  - `app/controllers/internal_code_editor_controller.py` (uses `ttkbootstrap` constants)
  - `app/controllers/layout_manager_controller.py` (uses `ttkbootstrap` constants)
  - `app/controllers/production_log_calculations_controller.py` (uses `ttkbootstrap`)
  - `app/controllers/rate_manager_controller.py` (uses `ttkbootstrap`)
  - `app/security.py` (uses `tkinter.messagebox`, `simpledialog`, `ttk`)
- `launcher.py` and `build.py` — contain launcher logic and packaging references to `tkinter` and `ttkbootstrap`.

(Discovery used a repo-wide scan for `tkinter`, `from tkinter import`, and `ttkbootstrap`.)

## PyQt6 parity mapping (Qt equivalents found)
Most modules have Qt parity files already present (controller/view pairs):
- `about` — `app/controllers/about_qt_controller.py`, `app/views/about_qt_view.py`
- `help_viewer` — `app/controllers/help_viewer_qt_controller.py`, `app/views/help_viewer_qt_view.py`
- `recovery_viewer` — `app/controllers/recovery_viewer_qt_controller.py`, `app/views/recovery_viewer_qt_view.py`
- `rate_manager` — `app/controllers/rate_manager_qt_controller.py`, `app/views/rate_manager_qt_view.py`
- `production_log` — `app/controllers/production_log_qt_controller.py`, `app/views/production_log_qt_view.py`
- `production_log_calculations` — `app/controllers/production_log_calculations_qt_controller.py`, `app/views/production_log_calculations_qt_view.py`
- `internal_code_editor` — `app/controllers/internal_code_editor_qt_controller.py`, `app/views/internal_code_editor_qt_view.py`
- `settings_manager`, `update_manager`, `developer_admin`, `security_admin` — Qt controllers/views exist
- `layout_manager` — dedicated runtime has `app/views/layout_manager_qt_view.py` and `layout_manager_qt_controller.py` (deliberate exception; remains separate-window by plan)

Conclusion: module-level parity is present for the main navigation and pilot modules.

## Uncertainties / Notes (leave these alone until resolved)
- `app/app_platform.py` imports `tkinter.PhotoImage`. Confirm whether `PIL`-only or Qt-native icon handling is safe to switch. If unsure, leave `app_platform` as-is and adapt packaging later.
- `app/security.py` uses `tkinter.simpledialog` and `messagebox`. Confirm that all call sites use the host `show_error()/ask_yes_no()` adapter rather than calling `tk` dialogs directly. If direct Tk calls remain, they must be ported or routed via `host_ui_adapter`.
- Packaging and CI: `build.py` currently references `tkinter` and `ttkbootstrap` in hidden imports. Ensure packagers and build scripts are updated in a follow-up change only after removal is validated.
- Windows launcher behavior: previous Phase 8 closeout noted a Windows UTF-8 BOM gotcha for standalone session JSON; keep this in mind when running dedicated-session smoke tests.

## Final Removal State
- `launcher.py` now enforces PyQt6-only startup and records `phase9_tk_removed = True` in runtime settings.
- `app/controllers/app_controller.py` no longer imports `ttkbootstrap`, routes notifications through the host adapter, and raises on unsupported non-PyQt backends.
- Managed module shims now lazy-load Qt controllers and fail fast instead of importing Tk controllers at module import time.
- `app/host_ui_adapter.py`, `app/security.py`, and update-state support now fail fast on Tk-only runtime paths instead of silently falling back.
- Disconnected Tk and ttkbootstrap-heavy surfaces are mirrored under `shadow/` with the same relative project structure for reference during removal.
- Disconnected Tk controllers, views, view factories, the legacy Tk shell view, and `app/splash.py` now fail immediately on import through `app/tk_runtime_removed.py`.
- `app/app_platform.py` now applies the live app icon through Qt-native `QIcon` handling for the application and host window during PyQt6 startup.
- `app/theme_manager.py` now resolves all live theme tokens internally. Legacy ttkbootstrap theme names are retained only as compatibility labels that map onto the internal light/dark token profiles.
- The live `app/` tree no longer contains Tk or ttkbootstrap imports.
- `build.py`, the active PyInstaller spec, archived packaging specs, and `README.md` no longer require or describe Tk or ttkbootstrap for packaging.
- PyInstaller packaging now explicitly excludes `tkinter`, `_tkinter`, `ttkbootstrap`, `PIL.ImageTk`, `PIL._tkinter_finder`, and `PyInstaller` so the removed Tk bridge cannot be reintroduced by optional Pillow or hook analysis.
- Packaged runtime JSON seeds now come from bundled `data/config/*` files and are copied into the writable external runtime tree on first use so EXE and DEB runs do not depend on repo-root JSON paths.
- The PyQt6 Security Admin and Developer Tools slices now prompt for vault authentication on demand and render read-only while locked instead of failing with a dead-end access error.
- `py_compile` now passes for the live Qt admin controller/view surfaces after the Security Admin and Developer Tools lock-state fix.
- `scripts/validate_pyqt6_phase_gate.py` and `scripts/validate_module_loads.py` now pass again against the live Phase 9 runtime, including `developer_admin`, `security_admin`, `settings_manager`, and the dedicated `layout_manager` runtime contract.
- Source-mode smoke passed by launching `main.py` and `launcher.py --module about` through the PyQt6-only runtime with no startup error output and both processes remaining alive until manually stopped.
- The rebuilt Windows EXE was manually validated by the user and accepted as passing for the Phase 9 packaged runtime closeout gate.

## Closeout Notes
1. Windows EXE validation is accepted as complete for migration closeout in this checkout.
2. Ubuntu DEB follow-up is deferred and will be handled as a packaging validation task rather than keeping the Tk-host removal phase open.
3. Phase 10 overflow hardening begins from this PyQt6-only packaged baseline.
