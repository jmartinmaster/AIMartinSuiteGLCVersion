## This branch may be highly unstable. Use at own risk

# Production Logging Center - GLC Edition

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

Production Logging Center (GLC Edition) is a desktop production support suite for logging shift data, managing rates, controlling layouts, and handling safe updates.

## Security default (important)

The app defaults to **non-secure mode ON**, which means **full app access is available without authentication prompts**.

- The toggle is in **Settings Manager > Security Admin > Security Mode**.
- Turn non-secure mode OFF when you want vault-based authentication and rights enforcement.

## User levels

### 1. General users (operators and supervisors)

Use these modules day to day:

- **Form Loader / Production Log**: shift entry, downtime balancing, export/import.
- **Rate Manager**: production standards.
- **Recovery Viewer**: restore drafts and backups.
- **Help Viewer**: in-app help docs.

With default non-secure mode enabled, general users can navigate all app areas unless your team enables secure mode.

### 2. Security admins

Use **Settings Manager > Security Admin** for:

- Vault creation and vault maintenance.
- Security mode toggle (non-secure vs secure).
- Password rotation / password requirements.
- Reset of security storage (destructive operation).

Secure mode supports explicit vault access control. If secure mode is enabled and an enabled General vault has no password, the app can auto-login to that vault without prompting.

### 3. Developers and release admins

Use **Settings Manager > Developer Admin** and **Update Manager** for:

- Update repository/channel controls.
- Override policy controls and trust gates.
- Module payload restore/update actions.
- Runtime diagnostics and rollback paths.

## Core modules

| Module | Purpose |
|---|---|
| Production Log | Production entry, shift timing, exports, draft recovery |
| Rate Manager | Mold/rate standards |
| Layout Manager | Layout configuration editor (dedicated runtime window) |
| Settings Manager | Runtime settings, security admin, developer admin |
| Update Manager | Stable updates, payload checks, rollback actions |
| Recovery Viewer | Backup and draft restore |
| Help Viewer | Help center markdown docs |
| About | Version and license details |

## Architecture summary

- **Entry point**: `main.py` -> `launcher.py::run_application()`
- **Version boundary**: Dispatcher version is exported from `launcher.py::__version__`
- **Pattern**: strict MVC under `app/controllers`, `app/models`, and `app/views`
- **UI host**: PyQt6 shell (Layout Manager remains on its dedicated external runtime contract)

## Quick start

### Run from source

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install PyQt6 Pillow openpyxl
python main.py
```

### Open a specific module

```powershell
python launcher.py --module update_manager
```

## Build targets

```powershell
# Windows EXE
python build.py --target windows

# Ubuntu DEB
python build.py --target ubuntu

# Windows + Ubuntu in one run (Windows host + WSL)
python build.py --target all
```

Artifacts are written to `dist/` (Windows) and `dist/ubuntu/` (Ubuntu).

## Ubuntu self-build

### Native Ubuntu / Linux

Install the required system packages first:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip dpkg-dev libgl1 libegl1
```

Create a local build environment and install the Python build dependencies:

```bash
python3 -m venv .venv-linux
source .venv-linux/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install Pillow PyQt6 PyInstaller openpyxl
```

Build the Ubuntu package:

```bash
python build.py --target ubuntu --non-interactive
```

The finished package is written to `dist/ubuntu/`. Install it with:

```bash
sudo apt install ./dist/ubuntu/<package-name>.deb
```

### Windows host with WSL

If you are building Ubuntu packages from Windows, install a WSL Ubuntu distro first:

```powershell
wsl --install -d Ubuntu
```

Then open the distro once, clone or open this repository under a WSL-accessible path, and either:

1. Let `python build.py --target ubuntu` bootstrap `.venv-linux` for you when `python3`, `python3-venv`, and `dpkg-deb` are already available in WSL, or
2. Run the native Ubuntu steps above inside WSL yourself if you prefer to manage the environment manually.

If the automatic WSL bootstrap cannot continue, `build.py` will stop with a message that points back to this **Ubuntu self-build** section.

## Data safety and persistence

- JSON configuration writes use atomic persistence with backup rotation.
- Runtime files are externalized via path helpers (`external_path`/`external_data_path`).
- Security vault records are encrypted at rest.

Key runtime areas include:

- `data/backups/` - rotated backup history.
- `data/pending/` - active drafts and history snapshots.
- `data/security/` - security settings and encrypted vault storage.

## Update and versioning notes

- Stable release tracking is based on the Dispatcher version in `launcher.py`.
- Update Manager supports stable artifacts plus controlled payload restore/update operations.
- Checksum and rollback verification are enforced in current 2.5.1 update flows.

## Documentation map

- `docs/help/user_guide_settings_manager.md` - Settings Manager user guide
- `docs/help/settings_json.md` - `settings.json` reference
- `docs/Completed Plans/pyqt6_host_migration_master_plan.md` - canonical host migration record

## License

GNU GPL v3. See [LICENSE](LICENSE).

Copyright (C) 2026 Jamie Martin
