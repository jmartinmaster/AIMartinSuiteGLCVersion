# Update Manager

Use the **Update Manager** to check for new releases and update application files.

---

## How to Check for Updates

- Click **Check Repository** to compare your local version with the online repository.
- Settings like the Repository URL and Developer toggles can be changed by an
  administrator in the **Settings Manager**.

---

## Understanding Version Numbers

The system evaluates update version numbers automatically:
- **Two-part versions** (e.g. `1.07`): Any version higher than the current local
  version will trigger an update.
- **Three-part versions** (e.g. `1.07.2`): Updates only trigger if the third
  number is **even** (like `.2` or `.4`). Odd-numbered patch versions (like `.1` or `.3`)
  are development builds and will be ignored.

---

## Update Workflows by Operating System

### Windows
- **Package Release**: Downloads a new executable file (`.exe`) next to the current
  one, launches the new one, and offers to clean up the old file.
- **Development Release**: Can download stable executables directly into your local
  `dist/` directory for testing.

### Ubuntu (Linux)
- Downloads the latest `.deb` package file and launches the system package manager
  to complete the installation.

---

## Updates and Payloads

Updates are installed in separate pieces:

- **Overrides**: Custom files are saved to the `the_golden_standard` folder.
  They remain inactive until an administrator enables **Override Trust**.
- **Settings & Config**: Updates can safely replace default layouts and settings
  without deleting your existing backup files.
- **Documentation**: Help documents and licenses are updated as a single bundle
  rather than file-by-file.
