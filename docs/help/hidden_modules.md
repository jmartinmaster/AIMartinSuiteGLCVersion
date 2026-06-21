# Hidden Modules

These modules are bundled with the application but do not appear in the sidebar
navigation because they run in the background as support services, internal utilities,
or context-specific tools.

---

## Background Services

- **About System**: Manages module version information, checks for custom override
  files, and opens the GPL license screen.
- **App Logging**: Captures background errors and exceptions for troubleshooting.
- **Data Handler**: Manages Excel import and export logic, and formats header data.
- **Downtime Codes**: Provides default reason codes and labels for downtime calculations.
- **Help Viewer**: Displays these help documents when accessed from menu actions.
- **Persistence**: Handles saving and loading JSON files (drafts, settings, rates)
  with rotating backups.
- **Security Blanket**: Handles password vault access, security bypass modes, and safeguards.
- **Splash Screen**: Displays the startup screen when launching the program.
- **Theme Manager**: Manages application styling, custom colors, and dark/light themes.
- **Path Helpers**: Resolves file paths for both raw source code runs and packaged executables.

---

## Technical Notes

- **Active Services**: Even though these modules are hidden from navigation, they are
  crucial and run constantly in the background.
- **User-Facing Exceptions**: The **Backup / Recovery** module remains visible in the
  sidebar because it is a direct user workflow, even though it relies heavily on the
  hidden persistence helper.
