# GitHub Copilot Instructions — Production Logging Center (GLC Edition)

> **Runtime context:** local agent, 12 GB VRAM, 14 B-parameter context window.
> Load this entire file into context before starting any session on this repository.

---

## 1. Project Identity

| Key | Value |
|-----|-------|
| **Application** | Production Logging Center — GLC Edition |
| **Author / Copyright** | Jamie Martin, 2026 |
| **License** | GNU GPL v3 |
| **Language** | Python 3 |
| **GUI stack** | Tkinter + ttkbootstrap |
| **Entry point** | `main.py` → `launcher.py::run_application()` |
| **Dispatcher version export** | `launcher.py::__version__` |
| **Repository** | `jmartinmaster/AIMartinSuiteGLCVersion` |

Every `.py` file in `app/` **must** begin with the standard GPL v3 header block exactly as it appears in existing source files (lines 1–15 of any file in `app/`). Do not omit or abbreviate it.

---

## 2. Repository Layout

```
AIMartinSuiteGLCVersion/
├── main.py                  # Runtime entry boundary
├── launcher.py              # run_application(), argument parser, __version__
├── app/
│   ├── theme_manager.py     # Aesthetic base — all color tokens & named styles
│   ├── controllers/         # MVC: controller layer
│   ├── models/              # MVC: model layer
│   ├── views/               # MVC: view layer
│   ├── app_controller.py    # Dispatcher class (shell orchestrator)
│   ├── app_model.py         # AppModel dataclass (runtime state)
│   ├── app_view.py          # AppShellView (sidebar + scrollable canvas shell)
│   ├── app_identity.py      # App name, EXE naming, version parsing helpers
│   ├── app_platform.py      # OS-specific helpers (icon, work area, etc.)
│   ├── security.py / security_service.py / security_model.py
│   ├── persistence.py       # Atomic JSON write + rotated backups
│   ├── data_handler.py / data_handler_service.py
│   ├── layout_config_service.py
│   ├── layout_manager.py    # Module entry shim → LayoutManagerController
│   ├── update_state.py      # UpdateCoordinator
│   └── ...                  # Other service/utility modules
├── assets/                  # Icons and image assets
├── docs/                    # Help Center markdown files
├── templates/               # Excel template(s)
├── layout_config.json       # Production Log layout definition
├── rates.json               # Rate configuration
└── build.py                 # PyInstaller build script (Windows EXE / Ubuntu DEB)
```

The `app/` directory is flat for service/utility modules. All **dashboard modules** (Production Log, Rate Manager, etc.) follow strict MVC splits inside `app/controllers/`, `app/models/`, and `app/views/`.

---

## 3. Strict MVC Architecture Rules

### 3.1 Layer Responsibilities

| Layer | Location | Purpose |
|-------|----------|---------|
| **Model** | `app/models/<name>_model.py` | Data, persistence, business logic, no UI imports |
| **View** | `app/views/<name>_view.py` | Widget construction, layout, theme application, **no business logic** |
| **Controller** | `app/controllers/<name>_controller.py` | Wires model ↔ view; handles events; orchestrates saves/loads |

- Models **must not** import `tkinter`, `ttkbootstrap`, or any view/controller.
- Views **must not** call persistence, file I/O, or business logic directly — delegate to `self.controller`.
- Controllers receive `parent` (tk widget) and `dispatcher` as constructor arguments.

### 3.2 Module Entry Convention

Every dashboard module file (`app/<module_name>.py`) is a thin shim that exposes exactly one public function:

```python
def get_ui(parent, dispatcher):
    return <ModuleNameController>(parent, dispatcher)
```

The Dispatcher imports this function dynamically to mount the module into the content area.

### 3.3 Naming Convention

| Artifact | Pattern | Example |
|----------|---------|---------|
| Module shim | `app/<snake_name>.py` | `app/production_log.py` |
| Controller | `app/controllers/<snake_name>_controller.py` | `production_log_controller.py` |
| Model | `app/models/<snake_name>_model.py` | `production_log_model.py` |
| View | `app/views/<snake_name>_view.py` | `production_log_view.py` |
| Controller class | `<TitleCase>Controller` | `ProductionLogController` |
| Model class | `<TitleCase>Model` | `ProductionLogModel` |
| View class | `<TitleCase>View` | `ProductionLogView` |

### 3.4 Module Metadata

Every shim and every view/controller module declares:

```python
__module_name__ = "Human-Readable Title"
__version__ = "X.Y.Z"
```

### 3.5 Dispatcher Integration

When the Dispatcher loads a module, it calls `get_ui(parent, dispatcher)` and injects the returned controller instance into `AppShellView.content_area`. The controller is responsible for packing its root frame into `parent` using `fill=BOTH, expand=True`.

Managed module names live in `app/controllers/app_controller.py::MANAGED_MODULE_NAMES`. Add a new module name to that list when creating a new dashboard module.

Protected modules (cannot be unloaded while security lock is active): `layout_manager`, `settings_manager`, `rate_manager`, `update_manager`.

---

## 4. ThemeManager — Aesthetic Base

### 4.1 Overview (`app/theme_manager.py`)

The ThemeManager is the **single source of truth** for all colors, fonts, and named ttk styles in the application. Never hardcode color hex values or font tuples in views or controllers. Always read from theme tokens.

```python
from app.theme_manager import get_theme_tokens
tokens = get_theme_tokens(root=self.root)  # reads cached tokens from root
```

### 4.2 Theme Presets

| Theme key | Display label | Base ttkbootstrap theme | Character |
|-----------|---------------|------------------------|-----------|
| `martin_modern_light` *(default)* | Martin Modern Light — industrial | `flatly` | Industrial slate-and-steel light mode |
| `cyber_industrial_dark` | Cyber-Industrial Dark — neon steel | `superhero` | Deep navy/charcoal with cyan neon accents |
| `flatly` | Flatly — balanced light | — | ttkbootstrap built-in |
| `cosmo` | Cosmo — crisp light | — | ttkbootstrap built-in |
| `lumen` | Lumen — soft light | — | ttkbootstrap built-in |
| `journal` | Journal — paper light | — | ttkbootstrap built-in |
| `litera` | Litera — text-forward light | — | ttkbootstrap built-in |
| `darkly` | Darkly — balanced dark | — | ttkbootstrap built-in |
| `superhero` | Superhero — high-contrast dark | — | ttkbootstrap built-in |

`DEFAULT_THEME = "martin_modern_light"`. The settings system persists the theme key in `settings.json`.

### 4.3 Semantic Color Token Reference

All views should consume these token keys (strings) from the `tokens` dict returned by `get_theme_tokens()`.

#### Shell & Global

| Token | Martin Modern Light | Cyber-Industrial Dark | Purpose |
|-------|--------------------|-----------------------|---------|
| `app_bg` | `#edf1f4` | `#081016` | Root window background |
| `content_bg` | `#edf1f4` | `#0a131a` | Main right-pane background |
| `surface_bg` | `#ffffff` | `#101b22` | Card / panel surface |
| `surface_fg` | `#152129` | `#e7f8fb` | Primary text on surface |
| `muted_fg` | `#637782` | `#88a9b4` | Secondary / subtitle text |
| `border_color` | `#c6d2d8` | `#23414d` | Widget borders |
| `accent` | `#0f7c8f` | `#22d1ee` | Primary accent / interactive |
| `accent_soft` | `#d6eef2` | `#123845` | Soft accent fill |
| `canvas_bg` | `#e8eef1` | `#081219` | tk.Canvas background |

#### Sidebar

| Token | Martin Modern Light | Cyber-Industrial Dark |
|-------|--------------------|-----------------------|
| `sidebar_bg` | `#162229` | `#0d171d` |
| `sidebar_fg` | `#f2f6f8` | `#d9f7ff` |
| `sidebar_muted_fg` | `#adc0c9` | `#78a4b0` |
| `sidebar_border` | `#273740` | `#1f3b47` |
| `sidebar_button_bg` | `#213038` | `#102029` |
| `sidebar_button_hover` | `#2c404a` | `#16313d` |
| `sidebar_button_active_bg` | `#d7e7ef` | `#22d1ee` |
| `sidebar_button_active_fg` | `#10222b` | `#041015` |

#### Banner / Status Bar

| Token | Purpose |
|-------|---------|
| `banner_bg` | Update status frame background |
| `banner_fg` | Update status label foreground |
| `banner_border` | Update status frame border |

#### Layout Manager Preview Grid

| Token | Purpose |
|-------|---------|
| `layout_block_canvas_bg` | Block-view canvas background |
| `layout_card_shell_bg` | Card shell background in block view |
| `layout_preview_grid_bg` | Preview grid outer background |
| `layout_preview_cell_bg` | Unselected preview cell background |
| `layout_preview_selected_bg` | Selected preview cell background |
| `layout_preview_muted_fg` | Muted label text in preview |
| `layout_preview_empty_fg` | Empty slot placeholder text |
| `layout_preview_text_fg` | Normal preview cell text |
| `layout_preview_readonly_fg` | Read-only field text (accent-tinted) |
| `layout_preview_border` | Cell border color |
| `layout_preview_selected_border` | Selected cell border (accent) |
| `layout_tooltip_bg/fg/border` | Tooltip surface |

#### Typography Tokens

| Token | Martin Modern Light | Cyber-Industrial Dark |
|-------|--------------------|-----------------------|
| `nav_font` | `("Segoe UI", 10)` | `("Segoe UI", 10)` |
| `title_font` | `("Segoe UI", 16, "bold")` | `("Segoe UI Semibold", 16)` |
| `heading_font` | `("Segoe UI", 11, "bold")` | `("Segoe UI Semibold", 11)` |

Font tokens are tuples. When passing to `tk.widget.option_add` or `style.configure`, use `theme_manager._format_option_font(token)`.

### 4.4 Named ttk Style Reference

All custom styles use the `Martin.` prefix. **Always** use these style names in views; never configure raw widget backgrounds directly.

| Style name | Applied to | Description |
|------------|-----------|-------------|
| `Martin.App.TFrame` | Root container Frame | App-level background |
| `Martin.Content.TFrame` | Right-pane Frames | Content area background |
| `Martin.Sidebar.TFrame` | Sidebar Frames | Dark sidebar fill |
| `Martin.Surface.TFrame` | Card inner Frames | White/dark surface |
| `Martin.Sidebar.TLabel` | Labels inside sidebar | Sidebar text |
| `Martin.SidebarTitle.TLabel` | Sidebar header label | Bold title in sidebar |
| `Martin.PageTitle.TLabel` | Page heading labels | Large page title |
| `Martin.Subtitle.TLabel` | Page subtitle labels | Muted subtitle |
| `Martin.Section.TLabel` | Section header labels | Surface-colored section text |
| `Martin.Muted.TLabel` | Helper/hint text | Muted secondary text |
| `Martin.Card.TLabelframe` | Card container | Bordered card panel |
| `Martin.Card.TLabelframe.Label` | Card title label | Card heading font |
| `Martin.Recovery.TLabelframe` | Recovery card | Bordered panel (recovery context) |
| `Martin.Recovery.TLabelframe.Label` | Recovery card title | Heading font |
| `Martin.Status.TFrame` | Update banner frame | Slim top status bar |
| `Martin.Status.TLabel` | Update banner text | Muted banner label |
| `Martin.Nav.TButton` | Inactive sidebar nav buttons | Flat left-anchored nav item |
| `Martin.NavActive.TButton` | Active sidebar nav button | Highlighted active nav item |

Global overrides applied by `apply_readability_overrides()`:
- `Treeview` rowheight → 28
- `TNotebook.Tab` padding → `(10, 6)`
- `TEntry` padding → 6
- `TCombobox` padding → 4

### 4.5 Applying Themes in Views

**Startup / initial render:**

```python
# In view __init__ or setup_ui, after widgets are built:
self.apply_theme()

def apply_theme(self):
    tokens = getattr(self.root, "_martin_theme_tokens", None) or {}
    # Reassign styles to all styled widgets
    self.main_frame.configure(style="Martin.Content.TFrame")
    # For raw tk.Canvas, apply canvas_bg directly:
    self.canvas.configure(background=tokens.get("canvas_bg", "#edf1f4"))
```

**Theme change (live swap via Settings Manager):**

The Dispatcher calls `apply_readability_overrides(root, new_theme_name)` first, then calls `apply_theme()` on every loaded module view. Each view's `apply_theme()` method must re-apply all `Martin.*` styles and any canvas/raw-tk backgrounds from `root._martin_theme_tokens`.

**Token lookup pattern:**

```python
from app.theme_manager import get_theme_tokens

tokens = get_theme_tokens(root=self.root)
bg = tokens["surface_bg"]
fg = tokens["surface_fg"]
accent = tokens["accent"]
```

**Never** call `tb.Style.get_instance().colors.<attribute>` directly in views. All color decisions must go through the token dict.

---

## 5. AppShell Layout Rules

The application shell (`AppShellView`) uses a fixed two-column layout:

```
┌──────────────────────────────────────────────────┐
│  Martin.App.TFrame (root container)               │
│ ┌─────────────────┐ ┌──────────────────────────┐ │
│ │ Martin.Sidebar  │ │ Martin.Content.TFrame     │ │
│ │ .TFrame         │ │ ┌──────────────────────┐  │ │
│ │ width=184px     │ │ │ Martin.Status.TFrame  │  │ │
│ │ padding=(8,14,  │ │ │ (update banner, TOP)  │  │ │
│ │   8,12)         │ │ └──────────────────────┘  │ │
│ │                 │ │ ┌── tk.Canvas ──────────┐  │ │
│ │ [LOGGING CENTER]│ │ │ content_area (Frame)  │  │ │
│ │  (title label)  │ │ │ ← modules mount here  │  │ │
│ │                 │ │ └───────────────────────┘  │ │
│ │ [Nav buttons]   │ │  Scrollbar (V + H)         │ │
│ └─────────────────┘ └──────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

- Sidebar is fixed at **184 px**, `pack_propagate(False)`.
- Content canvas stretches to fill remaining width and height.
- Module views are packed into `parent` (which is `content_area`) using `fill=BOTH, expand=True`.
- The update-status banner is conditionally shown/hidden; it mounts `side=TOP` above the canvas.
- Do not add widgets directly to `root` — always work through the shell structure.

---

## 6. Dashboard Module Creation Checklist

When adding a **new dashboard module**, follow this sequence exactly:

1. **Model** — `app/models/<name>_model.py`
   - GPL header
   - `class <Name>Model:` — no UI imports
   - All data loading, validation, and persistence methods
   - `__module_name__` and `__version__` at module level

2. **View** — `app/views/<name>_view.py`
   - GPL header
   - `from app.theme_manager import get_theme_tokens`
   - `class <Name>View:` — `__init__(self, parent, dispatcher, controller)`
   - `self.controller.view = self` at top of `__init__`
   - `self.setup_ui()` at end of `__init__`
   - `def setup_ui(self):` — build all widgets using `Martin.*` styles
   - `def apply_theme(self):` — reassign all styles and canvas backgrounds from `root._martin_theme_tokens`
   - No file I/O, no business logic

3. **Controller** — `app/controllers/<name>_controller.py`
   - GPL header
   - `class <Name>Controller:` — `__init__(self, parent, dispatcher)`
   - Instantiate model → instantiate view
   - `def __getattr__(self, attribute_name):` — delegate to `self.view` for Dispatcher compatibility
   - Wire event handlers between view callbacks and model methods
   - Expose `apply_theme(self)` that calls `self.view.apply_theme()`

4. **Module shim** — `app/<name>.py`
   - GPL header
   - `__module_name__` and `__version__`
   - `def get_ui(parent, dispatcher): return <Name>Controller(parent, dispatcher)`

5. **Register** — add `"<name>"` to `MANAGED_MODULE_NAMES` in `app/controllers/app_controller.py`

6. **Navigation** — if user-visible, add `("<Display Name>", "<name>")` to the navigation items list in the Dispatcher's `get_navigation_modules()` method.

---

## 7. Aesthetic Design Rules

### 7.1 Layout and Spacing

- Standard frame padding for content pages: `padding=20` or `padding=(20, 16, 20, 16)`
- Card (`Martin.Card.TLabelframe`) padding: `padding=(14, 10)`
- Nav button padding: `(12, 10)` (set in theme_manager, do not override)
- Form label width standard: `FORM_LABEL_WIDTH = 22`, input: `FORM_INPUT_WIDTH = 30`
- Section headings use `Martin.PageTitle.TLabel` (size 16 bold) for page titles
- Sub-headings use `Martin.Card.TLabelframe.Label` (size 11 bold) for card group titles
- Muted helper/hint text uses `Martin.Muted.TLabel` or `bootstyle=SECONDARY`

### 7.2 Typography Rules

- **Page title:** `title_font` token → Segoe UI 16 bold (light) / Segoe UI Semibold 16 (dark)
- **Card/group heading:** `heading_font` token → Segoe UI 11 bold
- **Navigation buttons:** `nav_font` token → Segoe UI 10
- **Body text:** ttkbootstrap default; do not set explicit font unless following a token
- Never set font sizes below 9 or above 16 for UI labels

### 7.3 Color Usage Rules

- **Primary accent** (`accent`): used for interactive borders, active-state indicators, and key buttons
- **Soft accent** (`accent_soft`): used for selected-row backgrounds, info highlights, soft fills
- **Surface** (`surface_bg` / `surface_fg`): card and panel content
- **Muted** (`muted_fg`): secondary labels, hints, captions — never for primary readable content
- **Sidebar**: always uses the `Martin.Sidebar.*` styles; do not mix content-area tokens
- Raw `tk.Canvas` widgets set `background=tokens["canvas_bg"]` and `highlightthickness=0, bd=0`
- Do not use raw HTML color codes in views — always derive from tokens

### 7.4 Widget Style Rules

- All `tb.Frame` → use a `Martin.*` style; never leave unstyled
- All `tb.Label` → use a `Martin.*` style for structural labels; `bootstyle=` is acceptable for status/alert labels
- All `tb.Button` → use ttkbootstrap `bootstyle=` for action buttons (PRIMARY, SUCCESS, DANGER, etc.); sidebar nav uses `Martin.Nav.TButton` / `Martin.NavActive.TButton` only
- `tb.LabelFrame` cards → use `Martin.Card.TLabelframe`
- `tb.Scrollbar` → default ttkbootstrap style (no override)
- `ttk.Treeview` → no custom style; rowheight set globally to 28 by `apply_readability_overrides`
- `ttk.Notebook` → no custom style; tab padding set globally to `(10, 6)`

### 7.5 Martin Modern Light — Industrial Palette Quick Reference

```
Background:   #edf1f4  (slate-cool light grey)
Sidebar:      #162229  (deep industrial slate)
Surface:      #ffffff  (clean white)
Text:         #152129  (near-black slate)
Muted text:   #637782  (cool grey)
Border:       #c6d2d8  (light steel)
Accent:       #0f7c8f  (teal-steel)
Accent soft:  #d6eef2  (pale teal)
Canvas:       #e8eef1  (light steel canvas)
```

### 7.6 Cyber-Industrial Dark — Neon Steel Quick Reference

```
Background:   #081016  (near-black navy)
Sidebar:      #0d171d  (dark steel navy)
Surface:      #101b22  (dark panel)
Text:         #e7f8fb  (cool near-white)
Muted text:   #88a9b4  (steel blue-grey)
Border:       #23414d  (dark teal border)
Accent:       #22d1ee  (neon cyan)
Accent soft:  #123845  (dark teal fill)
Canvas:       #081219  (deepest navy)
```

---

## 8. Persistence and Data Safety Rules

- All JSON file writes go through `app/persistence.py::write_json_with_backup()` — atomic write + rotated `.bak` copy.
- Never write JSON directly with `open(..., "w")` for configuration or settings files.
- Draft saves use the model's `save_draft_data()` method, which handles path construction, atomic write, and recovery snapshots automatically.
- Settings path: `external_path("settings.json")` — never hardcode absolute paths.
- Use `app/utils.py::external_path()` for user-writable runtime files.
- Use `app/utils.py::resource_path()` for bundled read-only assets.
- Use `app/utils.py::local_or_resource_path()` for files that may exist either locally or bundled (layout_config, rates).

---

## 9. Security and Protected Modules

- `app/security.py` provides the `@gatekeeper` decorator for admin-gated actions.
- `PROTECTED_MODULES = ["layout_manager", "settings_manager", "rate_manager", "update_manager"]` — these modules cannot be removed from the navigation while the security lock is active.
- Never bypass the gatekeeper for actions that modify settings, external overrides, or module management.

---

## 10. Update Coordinator and Banner

- `app/update_state.py::UpdateCoordinator` manages the top-of-shell status banner.
- The banner mounts above the canvas (`side=TOP`) and hides itself when `update_coordinator.active` is `False`.
- Banner bootstyle is driven by `update_coordinator.banner_bootstyle` (e.g., `INFO`, `SUCCESS`, `WARNING`).
- Module views must not manipulate the banner directly — route through the `dispatcher`.

---

## 11. Code Style and Quality Rules

- **No bare `except:`** — always catch specific exception types or `except Exception as exc:` at minimum.
- **No business logic in views** — if a view method needs data, it calls `self.controller.<method>()`.
- **No UI imports in models** — `tkinter`, `ttkbootstrap`, or any view are forbidden in model files.
- **Atomic writes** for all JSON saves — use `persistence.write_json_with_backup()`.
- **Thread safety** — UI updates must be scheduled on the main thread via `root.after(0, callback)` or `root.after(delay_ms, callback)`.
- **f-strings** preferred over `.format()` or `%` formatting.
- **snake_case** for variables and functions; **PascalCase** for classes.
- **GPL header** in every `.py` file under `app/`.
- **`__module_name__`** and **`__version__`** at module level in every dashboard shim, view, and controller.
- Do not use `from ttkbootstrap.constants import *` in new files — import only what is needed.

---

## 12. Adding a New Theme Preset

To add a new custom theme preset:

1. Add the theme key and base ttkbootstrap theme name to `THEME_PRESETS` in `theme_manager.py`.
2. Add the human-readable label to `READABLE_THEMES`.
3. Add a full token block `if normalized == "<new_key>":` inside `_build_theme_tokens()`, defining **all 35+ token keys** listed in Section 4.3. Every key must be present.
4. Test with `apply_readability_overrides(root, "<new_key>")` and verify all `Martin.*` styles render correctly.

Extending an existing ttkbootstrap theme without a custom preset: the `_build_theme_tokens()` fallback branch handles unknown themes using `style.colors` — this path provides reasonable defaults but lacks the hand-tuned industrial palette.

---

## 13. Key Module Summary

| Module name | Display name | Key responsibility |
|-------------|-------------|-------------------|
| `production_log` | Production Log | Shift entry, draft save/load, Excel export |
| `rate_manager` | Rate Manager | Mold-rate configuration editing |
| `layout_manager` | Layout Manager | JSON layout config block/grid editor |
| `settings_manager` | Settings Manager | App settings, theme, security admin |
| `recovery_viewer` | Recovery / Backup | Draft and config backup browser |
| `update_manager` | Update Manager | EXE and module payload updates |
| `help_viewer` | Help | In-app markdown Help Center |
| `about` | About | Version info and license display |

---

## 14. Session Startup Prompt for Local Agent

When starting a new coding session on this repository, confirm:

1. ✅ `app/theme_manager.py` is loaded into context — color tokens and `Martin.*` style names are available.
2. ✅ The MVC tripling (`controllers/`, `models/`, `views/`) is understood.
3. ✅ The GPL header is required on every new `.py` file.
4. ✅ `get_theme_tokens(root=self.root)` is the correct way to read color tokens in a view.
5. ✅ `write_json_with_backup()` is the correct way to persist JSON configuration files.
6. ✅ New modules must be registered in `MANAGED_MODULE_NAMES` and `get_ui()` must be the public entry point.
