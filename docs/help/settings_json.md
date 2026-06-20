# settings.json Reference

The `data/config/settings.json` file contains default configuration settings
and options for the application.

---

## File Example

```json
{
  "export_directory": "data/exports",
  "organize_exports_by_date": true,
  "default_export_prefix": "Disamatic Production Sheet",
  "update_repository_url": "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion.git",
  "enable_advanced_dev_updates": false,
  "theme": "martin_modern_light",
  "enable_screen_transitions": true,
  "enable_module_update_notifications": true,
  "screen_transition_duration_ms": 360,
  "toast_duration_sec": 5,
  "auto_save_interval_min": 5,
  "default_shift_hours": 8.0,
  "default_goal_mph": 240,
  "module_whitelist": [],
  "persistent_modules": [],
  "downtime_codes": {
    "1": "Misc Reason",
    "2": "Machine Repairs",
    "3": "Auto Pour",
    "4": "Inoculator",
    "5": "Pattern Repair",
    "6": "No Iron (Cupola)",
    "7": "No Iron (Transfer)",
    "8": "AMC, SBC, Shakeout",
    "9": "Pattern Change",
    "10": "No Sand",
    "X": "Startup or other permissible"
  }
}
```

---

## Settings Keys Reference

### **export_directory**
- **Type**: String
- **Description**: The folder where Excel exports are saved. (Default: `data/exports`).

### **organize_exports_by_date**
- **Type**: Boolean (`true`/`false`)
- **Description**: If true, exports are sorted into year/month folders (e.g. `2026/06 June`).

### **default_export_prefix**
- **Type**: String
- **Description**: Prefix prepended to the filenames of exported files.

### **update_repository_url**
- **Type**: String
- **Description**: Online repository URL used to check for system updates.

### **enable_advanced_dev_updates**
- **Type**: Boolean (`true`/`false`)
- **Description**: Enables/disables development updates (accessible via admin tools).

### **theme**
- **Type**: String
- **Description**: The visual theme key for styling the application layout.

### **enable_screen_transitions**
- **Type**: Boolean (`true`/`false`)
- **Description**: Enable or disable page-change fade animations.

### **enable_module_update_notifications**
- **Type**: Boolean (`true`/`false`)
- **Description**: Toggles check for updates on application startup.

### **screen_transition_duration_ms**
- **Type**: Integer
- **Description**: Length of page transition animation (0 to 500 milliseconds).

### **toast_duration_sec**
- **Type**: Integer
- **Description**: Duration in seconds that popup alerts stay on screen.

### **auto_save_interval_min**
- **Type**: Integer
- **Description**: Minutes between automatic draft saves.

### **default_shift_hours**
- **Type**: Number
- **Description**: Default shift duration loaded into the production form.

### **default_goal_mph**
- **Type**: Number
- **Description**: Default molds-per-hour target loaded into the production form.

### **module_whitelist**
- **Type**: Array of Strings
- **Description**: Optional list of modules to show in sidebar. If empty, all are shown.

### **persistent_modules**
- **Type**: Array of Strings
- **Description**: Modules that keep their in-progress state when you navigate away.

### **downtime_codes**
- **Type**: Object (Key-Value map)
- **Description**: Custom labels and categories for numeric downtime codes.

---

## Guidelines

- **Best Practice**: Always use the **Settings Manager** visual tool inside the
  app rather than editing this file manually to prevent errors.
- Admin security options and module trust keys are stored separately and cannot
  be edited inside `settings.json`.