# Layout Manager PyQt6 Migration Plan

## Goals
- Decouple Layout Manager runtime lifecycle from the main Tk dispatcher.
- Migrate the Layout Manager UI from Tkinter/ttkbootstrap to PyQt6 while preserving model behavior and persisted data contract.
- Keep the rest of the app stable during migration with a controlled adapter boundary.

## Current State
- `LayoutManagerController` currently owns both UI orchestration and model interactions.
- `LayoutManagerView` is tightly bound to Tk widgets, ttk styles, and dispatcher mousewheel bindings.
- The main dispatcher currently hosts module frames in a Tk canvas/content area and expects module controllers to expose Tk lifecycle methods.

## Target State
- Layout Manager keeps the same model and controller intent, but uses a Qt view implementation.
- A mini dispatcher launches and preloads layout manager resources independently.
- A bridge layer allows the Tk shell to open and control a Qt-backed layout manager surface without breaking module-level contracts.

## Migration Phases

### Phase 1: Stabilize Dispatcher Boundary (Completed in this change)
- Introduce a dedicated Layout Manager mini dispatcher.
- Move preload payload creation/consumption and module bundle warmup into that mini dispatcher.
- Keep backward-compatible dispatcher methods (`invalidate_layout_manager_preload`, `schedule_layout_manager_preload`, `consume_layout_manager_preload`) to avoid controller churn.

### Phase 2: Extract View Interface Contract (Completed in this change)
- Define a view protocol used by `LayoutManagerController` (methods/events only).
- Capture all current `LayoutManagerView` methods invoked by controller.
- Move controller construction onto a view factory so backend choice is isolated.
- Ensure controller typing no longer depends on Tk widget types.

Deliverable:
- A `layout_manager_view_contract.py` interface (or typed protocol) and controller updates to target the interface.

### Phase 3: Build Qt View Adapter (Parallel Path)
- Implement `LayoutManagerQtView` with PyQt6 widgets and signals.
- Mirror major tabs and workflows first:
  - Block View
  - Import / Export
  - JSON Editor
  - Preview
- Map controller callbacks to Qt signals/slots.
- Add a Qt-safe theme token adapter from `ThemeManager` semantic tokens.
- Bootstrap started in this change with a standalone PyQt6 probe window for import, event-loop, and theme-token validation.

Deliverable:
- `app/views/layout_manager_qt_view.py` with parity for load/edit/save/preview critical paths.

### Phase 4: Runtime Integration Strategy
- Choose one of two integration options:
  - A: Sidecar Qt top-level window launched from Tk shell (lowest risk).
  - B: Embedded hybrid bridge (higher complexity due to event loop ownership).
- Recommended first step: Option A.

Option A details:
- Launch a PyQt6 `QApplication` (or reuse singleton if active).
- Open Layout Manager in a managed Qt window from mini dispatcher.
- Keep controller lifecycle methods (`on_hide`, `on_unload`, `apply_theme`) mapped to Qt window show/hide/close handlers.

### Phase 5: Feature Parity and Hardening
- Port all dialogs and confirmation flows.
- Port keyboard shortcuts and dirty-state protection.
- Rebuild preview rendering and selection affordances.
- Validate JSON import/export section workflows.

### Phase 6: Flip Default + Decommission Tk View
- Keep a feature flag during transition (`layout_manager_ui_backend = tk|qt`).
- Run regression checklist on both backends.
- Remove Tk-specific view once Qt parity and stability criteria are met.

## Event Loop and Threading Constraints
- Tk and Qt event loops must not block each other.
- If running sidecar Qt window, ensure Qt UI operations stay on Qt thread.
- Dispatcher-driven notifications should cross boundary via queued callbacks.
- Preserve atomic JSON writes and existing persistence paths.

## Theme and Styling Plan
- Keep `ThemeManager` as source of truth for semantic tokens.
- Build a token translator from Martin style semantics to Qt palettes/stylesheets.
- Preserve light/dark custom presets:
  - `martin_modern_light`
  - `cyber_industrial_dark`

## Risks
- Dual event loop complexity (Tk + Qt).
- Widget behavior mismatches (table/grid editing, shortcut handling).
- Possible divergence between Tk and Qt view behavior during phased rollout.

## Test Strategy
- Unit tests for model/controller logic (no UI dependency).
- Targeted integration tests for:
  - Form activation + preload invalidation
  - Save/load default/current
  - Section-based JSON merge and validation
- Manual smoke tests for Qt launch, navigation away, and recovery from invalid JSON.

## Acceptance Criteria
- Layout manager launches through mini dispatcher without regressions.
- Qt backend can perform full edit-save-preview cycle for active forms.
- Preload cache remains valid across source generation changes and active form changes.
- No regressions in existing protected-module security behavior.
