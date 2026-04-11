# Development Handoff - 2026-04-11

This note captures the current handoff state for the `2.0.5` development checkpoint so work can continue on another machine without repeating investigation.

## Current Branch State

- Dispatcher Core has been advanced from stable `2.0.4` to development checkpoint `2.0.5`.
- The checkpoint is intentionally an odd patch version so the packaged EXE update gate ignores it.
- The primary work in progress is the Production Log responsive summary/chart feature.

## Completed In This Checkpoint

- Added a new Production Log visual summary area in [app/views/production_log_view.py](../app/views/production_log_view.py).
- Added a mold-contribution chart based on populated production rows.
- Added a production-vs-downtime-vs-ghost-time chart based on existing minute calculations.
- Kept the chart implementation dependency-free by using native Tk canvas drawing instead of matplotlib or plotly.
- Hooked summary refreshes into:
  - row math updates
  - draft loads
  - Excel imports
  - theme application
  - window resize events
- Lowered the initial chart visibility threshold from the earlier rigid `1180x760` gating.

## Open Issue

The Production Log screen still shows a large blank region above `Draft Status` in the full app shell, and that layout issue is likely still interfering with when the summary panel becomes visible during normal use.

### Important Observation

- Isolated geometry checks showed the Production Log view itself packs its sections from the top correctly.
- The persistent blank area appears when the view is hosted inside the shared shell/canvas runtime, which means the remaining issue is likely in the interaction between the module frame, the app shell content canvas, and the Production Log summary visibility/layout logic.

## Most Relevant Files

- [app/views/production_log_view.py](../app/views/production_log_view.py)
- [app/views/app_view.py](../app/views/app_view.py)
- [app/controllers/app_controller.py](../app/controllers/app_controller.py)
- [CHANGELOG.md](../CHANGELOG.md)

## Recommended Next Steps

1. Reproduce the top-gap issue directly in the full shell on the laptop and verify whether the shell canvas scroll position or canvas window sizing shifts after the Production Log module mounts.
2. Inspect [app/views/app_view.py](../app/views/app_view.py) `sync_content_canvas_layout()` and the `content_area` canvas window behavior while Production Log loads and after the summary panel toggles.
3. If the shell canvas is auto-scrolling or preserving stale geometry, fix that in the shell rather than continuing to compensate inside Production Log.
4. After the top-gap issue is fixed, retune the summary-panel visibility thresholds in [app/views/production_log_view.py](../app/views/production_log_view.py) based on real window sizes.
5. Once layout is stable, visually tune chart spacing, sizing, and labels.

## Validation Completed Here

- [app/views/production_log_view.py](../app/views/production_log_view.py) passes diagnostics.
- `py_compile` was run successfully on the Production Log view.
- Additional in-shell geometry probes were used to inspect Production Log layout behavior under the shared app shell.

## Deferred Until Next Session

- Final fix for the blank space above `Draft Status`
- Release-ready confirmation that the charts appear at the intended window sizes
- Any visual polish beyond the current first-pass chart cards