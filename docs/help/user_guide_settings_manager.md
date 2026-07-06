# Settings Manager

Use the **Settings Manager** to configure application defaults and manage security.

---

## Basic Settings

- **Sidebar Module Whitelist**: Enter names of modules to show in the sidebar.
  Leave blank to display all modules.
- **Theme**: Select the visual styling/theme for the application.
- **Revert Theme Preview**: Undo temporary theme changes if you don't save.
- **Enable Screen Transitions**: Turn page-switch fade animations on or off.
- **Transition Duration**: Control the fade length in milliseconds (0 to 500).
- **Check Module Updates On Startup**: Toggle automatic startup update checks.
- **Auto Save Interval**: How often the app automatically saves drafts (in minutes).
- **Toast Duration**: How many seconds status popups remain on screen.
- **Default Shift Hours**: The standard shift duration loaded into new forms.
- **Default Goal MPH**: The standard molds-per-hour target loaded into new forms.
- **Export Settings**: Set output folders for generated Excel files.
- **Persistent Modules**: Choose which screens keep their in-progress state
  when you switch tabs during a session.
- **Edit Downtime Codes**: Add or rename downtime code numbers and labels.
- **Manage Security**: Access security credentials and vault configurations.

---

## Security Settings

Under **Manage Security**:

- **Vault Management**: Rotate password keys and manage encrypted data.
- **Non-secure Mode**: **Enabled by default** and grants full app access
  without authentication prompts.
- **Secure Mode**: Turn non-secure mode off to enforce vault authentication
  and rights checks.
- **Reset Security Storage**: A destructive operation that deletes all security
  vault data. To execute, you must type `RESET` and re-enter your password.

---

## Developer & Admin Tools

When logged in as an administrator, a special row of tools is unlocked:

- **Repository URL**: Edit the Git URL used to check for system updates.
- **Advanced Dev Updates**: Allow installation of developer-tier updates on Windows.
- **External Module Overrides**: Save and edit custom module code under
  `data/modules/` without overwriting bundled code files.
- **Override Trust**: A safety switch. Override files on disk are ignored
  until you explicitly enable **Override Trust**.

---

## File Backups
- Settings are saved to `data/config/settings.json`.
- A backup copy of settings is kept in `data/backups/settings` every time you save.
