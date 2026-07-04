# Standalone Session (Sidecar) Usage Guide

This guide explains how to configure and use the standalone session launcher (the sidecar mechanism) to run individual modules (e.g. Layout Manager, Internal Code Editor, Form Loader) standalone in their own window for development, testing, and debugging.

---

## How It Works

The standalone runner is activated when the launcher detects the presence of the environment variable:
`AIMARTIN_LAYOUT_MANAGER_QT_SESSION`

When set, the main `launcher.py` intercepts the standard dispatcher start flow and routes execution to the generic sidecar runner (`app/sidecar.py`). The sidecar runner loads the session JSON configuration, verifies module-level security requirements, and launches the target module in a dedicated window.

---

## Session Payload Format

The session configuration file must be a JSON object containing at least the `module` key, along with optional module-specific inputs:

```json
{
  "module": "layout_manager",
  "theme_tokens": {
    "background_color": "#1f1f2e",
    "text_color": "#ffffff",
    "accent_color": "#7e57c2"
  },
  "form_info": {
    "id": "standard_mold",
    "name": "Standard Mold Form"
  },
  "source_path": "data/config/layout_config.json",
  "state_path": "C:/Users/username/AppData/Local/Temp/state.json",
  "command_path": "C:/Users/username/AppData/Local/Temp/command.json"
}
```

### Supported Modules
- `layout_manager`
- `internal_code_editor` (Internal Code Editor)
- `production_log` (Form Loader)

---

## Security & Module Authentication

If the target module is configured as protected in `app/module_registry.json` (i.e. `"protected": true`), the sidecar runner enforces access security:
1. It initializes the PyQt6 application environment so GUI prompts can render.
2. It queries the `SecurityService` for the module's required access rights and role restrictions.
3. It pops up the PyQt6 **Security Access** dialog box prompting for a vault selection and password challenge.
4. If authentication fails, or the dialog is closed, the runner exits immediately with exit code `1`.
5. If authentication succeeds, the session is unlocked and the module window launches.

---

## How to Execute Standalone

To start a standalone session, configure the session JSON path environment variable, then run the launcher:

### Windows (PowerShell)
```powershell
# Configure session path
$env:AIMARTIN_LAYOUT_MANAGER_QT_SESSION = "C:\path\to\session.json"

# Launch application
python main.py
```

### Linux / macOS (Bash)
```bash
# Run with environment variable set
AIMARTIN_LAYOUT_MANAGER_QT_SESSION="/path/to/session.json" python main.py
```
