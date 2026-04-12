# Production Logging Center — GLC Edition

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

**Production Logging Center (GLC Edition)** is a desktop production support application for GLC operators. Built with Python, Tkinter, and `ttkbootstrap`, it provides a modern, high-DPI–aware interface for tracking production logs, managing rates, and handling shift transitions with robust data-safety features. It can be run directly from source, distributed as a standalone Windows `.exe`, or installed as an Ubuntu Debian package.

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features and Modules](#key-features-and-modules)
3. [Working Modes](#working-modes)
4. [Quick Start](#quick-start)
5. [Build Targets](#build-targets)
6. [Configuration, Data Files, and Safety](#configuration-data-files-and-safety)
7. [Update Manager and Versioning](#update-manager-and-versioning)
8. [Troubleshooting](#troubleshooting)
9. [Repository Structure](#repository-structure)
10. [Contributing and Development Notes](#contributing-and-development-notes)
11. [License](#license)

---

## Overview

Production Logging Center tracks shop orders, part numbers, molds, and downtime across shifts. Operators enter production data, balance downtime, and export workbooks for review. Developers and administrators can manage layout configuration, rate standards, security settings, and application updates from within the application shell.

The application shell is built around a dispatcher core (`launcher.py`) that hosts independent modules. Entry point: `main.py` calls `run_application` from `launcher.py`.

---

## Key Features and Modules

### Core Modules

| Module | Description |
|---|---|
| **Production Log** | Track shop orders, part numbers, and molds per shift. Includes draft auto-save, recovery snapshots, Excel export/import, and a live Ghost Time footer indicator. |
| **Rate Manager** | Manage production rate standards used for performance tracking. |
| **Layout Manager** | Configure UI field mappings dynamically via `layout_config.json`. |
| **Recovery Viewer** | Browse and restore draft snapshots and configuration backups without using the file explorer. |
| **Settings Manager** | Manage themes, export paths, production defaults, downtime-code labels, and per-module persistence. Separates general settings from admin-only Developer & Admin tools. |
| **Update Manager** | Check for new releases, download versioned EXEs, and install selected module payload updates without rebuilding the full executable. |
| **Help Viewer** | In-app Help Center with top-level guide chips, Hidden Modules reference, and module-specific User Guide sections. |
| **About** | Application version information and bundled GPL license access. |

### Notable Capabilities

- **Ghost Time Indicator** — live color-coded footer: red for missing time, green for extra time.
- **Balance Downtime** — fills missing downtime proportionally across existing rows before export; adds a fallback adjustment row when needed.
- **Atomic Writes** — `settings.json`, `layout_config.json`, and `rates.json` write through an atomic save path to prevent data corruption.
- **Rotated Backups** — each config file keeps a `.bak` copy and a rotated history under `data/backups/`.
- **Theme Support** — includes the Martin Modern Light industrial preset with readability overrides.
- **Module Preloader** — background warm-up in source mode so page navigation avoids repeated import work; disk changes invalidate the cache automatically.
- **External Module Overrides** — per-file `.py` overrides beside the EXE activate automatically when admin-controlled override trust is enabled.

---

## Working Modes

### Source / Python Mode

Runs directly from the repository. Intended for developers, testers, and local rebuild workflows.

- Full access to repository source, docs, templates, and build tooling.
- Can rebuild with `build.py` and PyInstaller.
- Update Manager can hand off to a downloaded packaged EXE for testing.

### Packaged EXE Mode

Runs as a standalone Windows executable built by PyInstaller. Intended for normal operator use outside a Python environment.

- Bundles help documentation and `LICENSE.txt` for in-app access.
- Uses the Update Manager for release checks and module payload installs.
- Versioned EXE filenames allow a newer build to download beside the current one and launch separately.
- Archives up to 10 older versioned EXEs under `dist/Old_exe/`.
- External Python override files can be staged beside the EXE and only activate when an admin enables override trust.

### Installed Ubuntu Package Mode

Runs from a Debian package installed on Ubuntu (or via WSL). Intended for Linux deployments.

- Application bundle placed under `/opt/production-logging-center-glc`.
- User-writable runtime files stored under `$XDG_DATA_HOME/production-logging-center-glc` (defaults to `~/.local/share/production-logging-center-glc` when `XDG_DATA_HOME` is not set).
- Runtime files include editable JSON files, pending drafts, backups, security data, and external override files.

---

## Quick Start

### For Operators — Windows (Packaged EXE)

1. Download the latest versioned `.exe` from the `dist/` folder in the repository (e.g., `Production Logging Center_GLC_v2.1.4.exe`).
2. Place it in a dedicated folder alongside any existing `settings.json`, `layout_config.json`, and `rates.json` files if you have them.
3. Double-click the `.exe` to launch. The application will create `settings.json` on first run if it does not exist.
4. Use **Settings Manager → Export Path** to configure where workbooks are saved.
5. Use **Update Manager** to check for and apply available updates.

### For Operators — Ubuntu (Debian Package)

1. Obtain the `.deb` package (e.g., `production-logging-center-glc_2.1.4_amd64.deb`) from `dist/ubuntu/`.
2. Install it:
   ```bash
   sudo dpkg -i production-logging-center-glc_2.1.4_amd64.deb
   sudo apt-get install -f   # resolve any missing dependencies
   ```
3. Launch from the application menu or run:
   ```bash
   production-logging-center-glc
   ```

### For Developers — Running from Source

**Prerequisites:** Python 3.10+, `ttkbootstrap`, `Pillow`, `openpyxl`.

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install ttkbootstrap Pillow openpyxl

# Run the application
python main.py

# Open a specific module directly (useful for debugging)
python launcher.py --module production_log
```

Supported `--module` values: `about`, `help_viewer`, `layout_manager`, `production_log`, `rate_manager`, `recovery_viewer`, `settings_manager`, `update_manager`.

---

## Build Targets

The project uses `build.py` for all packaging. Running `build.py` in an interactive terminal on Windows prompts you to choose a target; non-interactive runs default to the host-native target.

### Windows — Standalone EXE

```bash
python build.py --target windows
```

Produces a versioned `.exe` in `dist/` (e.g., `Production Logging Center_GLC_v2.1.4.exe`). The current EXE is kept in `dist/` and older copies are archived to `dist/Old_exe/` (up to 10 kept).

### Ubuntu — Debian Package

**From a Linux host (or inside WSL directly):**

```bash
python build.py --target ubuntu
```

**From Windows using a specific WSL distro:**

```bash
python build.py --target ubuntu --wsl-distro Ubuntu-24.04
```

Artifacts are written to `dist/ubuntu/`.

**WSL prerequisites:**

```bash
# Inside the WSL distro, set up a Linux venv
python3 -m venv .venv-linux
.venv-linux/bin/python -m pip install Pillow PyInstaller openpyxl ttkbootstrap
# Also ensure dpkg-deb is available (standard on Ubuntu)
```

> **Note:** If the repository lives on a Windows drive (e.g., `D:\`), the WSL distro must expose that drive under `/mnt/<drive-letter>` (e.g., `/mnt/d`), or the Ubuntu build will fail with a prerequisite error.

Ubuntu packaging prefers the Linux venv in this order: `.venv-linux/bin/python` → `.venv/bin/python` → distro `python3`.

### Symbol Index Only

Refresh the local Python symbol index without building any artifact:

```bash
python build.py --index-only
```

Outputs:
- `build/symbol-index/symbol-index.json` — machine-readable manifest.
- `build/symbol-index/symbol-index.md` — human-readable lookup.

Normal packaging runs also refresh the index before building. The VS Code task **Refresh Python Symbol Index** runs the same command.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MARTIN_BUILD_TARGET` | *(none)* | Override the build target (`windows` or `ubuntu`) without passing `--target`. |
| `MARTIN_WSL_DISTRO` | *(none)* | Override the WSL distro name without passing `--wsl-distro`. |
| `MARTIN_BUILD_PYTHON` | *(none)* | Override the Python interpreter used inside the WSL/Linux build. |
| `MARTIN_KEEP_DIST` | `1` | Set to `0` to clear `dist/` before each build. |
| `MARTIN_SKIP_TASKKILL` | `0` | Set to `1` to skip killing running EXE instances before a Windows build. |

---

## Configuration, Data Files, and Safety

### Configuration Files

| File | Location | Description |
|---|---|---|
| `settings.json` | Beside the EXE / repo root | Theme, export path, production defaults, downtime labels, module persistence. Created on first run. |
| `layout_config.json` | Beside the EXE / repo root | Field mappings and header layout for the Production Log UI. |
| `rates.json` | Beside the EXE / repo root | Production rate standards used by Rate Manager. |

All three files write through an **atomic path** (write to a temp file, then replace) to prevent corruption if the application is interrupted mid-save.

### Backups and Recovery

| Path | Contents |
|---|---|
| `data/backups/` | Rotated recovery history for `settings.json`, `layout_config.json`, and `rates.json`. Each save also keeps a `.bak` copy beside the live file. |
| `data/pending/` | Active Production Log drafts. |
| `data/pending/history/` | Recovery snapshots for overwritten Production Log drafts. |

The **Recovery Viewer** module lets operators browse and restore drafts, recovery snapshots, and JSON backup copies without using the file explorer.

### Installed Ubuntu Package — Runtime File Locations

For the installed `.deb` package, user-writable runtime files (JSON configs, drafts, backups, security data) are stored at:

- `$XDG_DATA_HOME/production-logging-center-glc/` if `XDG_DATA_HOME` is set.
- `~/.local/share/production-logging-center-glc/` otherwise.

### Compatibility Notes

- `layout_config.json` routes `target_time` through `header_fields`. Older local builds from before the config-driven Target Time change may not present that field correctly if they reuse the newer layout file.
- `settings.json` includes a `persistent_modules` key. Older builds ignore it safely but do not preserve module state across navigation.

---

## Update Manager and Versioning

The Update Manager checks the Dispatcher Core version exported from `launcher.py` (`__version__ = "2.1.4"`). `main.py` remains the runtime entry boundary.

### Versioning Rules

| Version format | Update triggered when… |
|---|---|
| Two-part (e.g., `1.07`) | Remote version is greater than the local version. |
| Three-part, even patch (e.g., `1.07.2`) | Remote version is greater and the patch number is even. |
| Three-part, odd patch (e.g., `1.07.1`) | **Never** — odd patch versions are ignored by the auto-updater. |

Even patch releases are stable and eligible for the auto-update gate. Odd patch releases are development builds.

### Update Behavior by Mode

**Source / Python mode:**
- Stable updates download the published versioned EXE into local `dist/` and launch it for handoff testing.

**Packaged EXE mode:**
- Stable updates download a versioned EXE beside the current copy, clear stale bundled-module overrides, and launch the newer build.
- The newer build offers cleanup of older local EXEs after launch.
- Module payload installs update individual modules without rebuilding the EXE.
- JSON payload restores (`layout_config.json`, `rates.json`) preserve local backups before overwriting.
- Documentation payload restores (Help Center markdown files, `LICENSE.txt`) are available as a grouped update.

Update availability also requires a matching published EXE artifact in `dist/`. The default repository URL can be overridden or cleared from Security Admin developer tools.

---

## Troubleshooting

**Application does not start (source mode)**
- Confirm Python 3.10+ is active: `python --version`
- Confirm `ttkbootstrap`, `Pillow`, and `openpyxl` are installed in the active environment.
- Check `logs/` for exception details.

**Windows build fails with "process in use" error**
- Ensure the EXE is not running before building.
- Set `MARTIN_SKIP_TASKKILL=1` only if you have confirmed no EXE instance is running.

**Ubuntu/WSL build fails with "drive not mounted" error**
- The repository is on a Windows drive (e.g., `D:\`) that the WSL distro does not expose under `/mnt/d`.
- In WSL, run `ls /mnt/` to confirm available mounts. Enable `automount` in `/etc/wsl.conf` if the drive is missing.

**Ubuntu build fails with "dpkg-deb not found"**
- Install it inside the WSL distro: `sudo apt-get install dpkg`.

**Ghost Time shows wrong values**
- Confirm `layout_config.json` includes `target_time` under `header_fields`. If you upgraded from a pre–config-driven build, copy the current `layout_config.json` from the repository.

**Settings or layout lost after update**
- Use **Recovery Viewer** to restore a backup from `data/backups/`.
- Alternatively, restore from the `.bak` file beside the live JSON file.

**Update Manager does not detect a newer version**
- Verify the repository URL in Security Admin developer tools is set correctly.
- Confirm the remote `dist/` folder contains a published versioned EXE artifact.
- Check that the remote version uses an even patch number (odd patches are intentionally ignored).

---

## Repository Structure

```
AIMartinSuiteGLCVersion/
├── main.py                    # Runtime entry point — calls run_application from launcher.py
├── launcher.py                # Dispatcher Core: __version__, USER_FACING_MODULE_NAMES, run_application
├── build.py                   # Build script for Windows EXE and Ubuntu DEB targets
├── symbol_index.py            # Python symbol index generator
├── layout_config.json         # UI layout and field mapping configuration
├── rates.json                 # Production rate standards
├── app/                       # Application source (MVC structure)
│   ├── controllers/           # Module controllers (Dispatcher, per-feature controllers)
│   ├── models/                # Data/business logic models
│   ├── views/                 # UI view classes
│   ├── about.py               # About module entry
│   ├── production_log.py      # Production Log module entry
│   ├── rate_manager.py        # Rate Manager module entry
│   ├── layout_manager.py      # Layout Manager module entry
│   ├── recovery_viewer.py     # Recovery Viewer module entry
│   ├── settings_manager.py    # Settings Manager module entry
│   ├── update_manager.py      # Update Manager module entry
│   ├── help_viewer.py         # Help Viewer module entry
│   ├── app_identity.py        # Version parsing, EXE/DEB name formatting
│   ├── app_platform.py        # Platform helpers (icons, app ID, window management)
│   ├── theme_manager.py       # Theme resolution and readability overrides
│   ├── security.py            # Vault and session authentication
│   └── utils.py               # Path helpers (resource_path, external_path)
├── assets/                    # Icons and image assets
├── docs/                      # Bundled help documentation (Markdown)
├── templates/                 # Workbook export templates
├── packaging/
│   ├── ubuntu/                # Ubuntu-specific .desktop and launcher.sh templates
│   └── specs/                 # PyInstaller spec files
├── dist/                      # Build output (Windows EXE; dist/ubuntu/ for DEB)
├── build/                     # Intermediate build artifacts and symbol index
├── data/                      # Runtime data (created at runtime, not committed)
│   ├── backups/               # Rotated JSON config backups
│   └── pending/               # Production Log drafts and history snapshots
├── logs/                      # Application log files (created at runtime)
├── CHANGELOG.md               # Release history
└── LICENSE                    # GNU General Public License v3.0
```

---

## Contributing and Development Notes

### Architecture

The application follows a strict MVC layout under `app/`:

- **Controllers** (`app/controllers/`) — handle user actions, delegate to models, update views.
- **Models** (`app/models/`) — contain business logic, data access, and persistence; no Tk imports.
- **Views** (`app/views/`) — define UI widgets; no business logic.

Module entry points (`app/about.py`, `app/production_log.py`, etc.) are thin controller-delegation wrappers.

### Adding or Modifying a Module

1. Add or modify the model in `app/models/`.
2. Add or modify the view in `app/views/`.
3. Add or modify the controller in `app/controllers/`.
4. Keep the entry-point wrapper (`app/<module_name>.py`) as a thin delegate.
5. If the module should be user-facing, add its name to `USER_FACING_MODULE_NAMES` in `launcher.py`.

### Development Workflow

```bash
# Run from source
python main.py

# Launch a specific module focused (no need to navigate through the shell)
python launcher.py --module <module_name>

# Refresh the symbol index after significant changes
python build.py --index-only

# Build for distribution
python build.py --target windows     # Windows EXE
python build.py --target ubuntu      # Ubuntu DEB (Linux host or WSL)
```

### Version Bump

1. Update `__version__` in `launcher.py`.
2. Use an even patch number for a stable (auto-update eligible) release; use an odd patch number for a development build.
3. Update `CHANGELOG.md` with the new version entry.

### External Module Overrides

Place a `.py` file matching a module name in the external override `app/` folder beside the EXE to override that module at runtime. Override trust must be explicitly enabled by an admin through Security Admin. This mechanism is intended for targeted fixes between full EXE releases.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for the full text.

© 2026 Jamie Martin
