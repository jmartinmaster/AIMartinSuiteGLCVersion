# settings.json Reference

`settings.json` stores user-configurable defaults for the application.

## Structure

```json
{
  "export_directory": "exports",
  "organize_exports_by_date": true,
  "default_export_prefix": "Disamatic Production Sheet",
  "theme": "journal",
  "toast_duration_sec": 5,
  "auto_save_interval_min": 5,
  "default_shift_hours": 8.0,
  "default_goal_mph": 240,
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
    "10": "No Sand"
  }
}
```

## Keys

- `export_directory`
  - Type: string
  - Purpose: Folder used for Excel exports.

- `organize_exports_by_date`
  - Type: boolean
  - Purpose: If true, exports can be grouped by date.

- `default_export_prefix`
  - Type: string
  - Purpose: Prefix used when naming exported files.

- `theme`
  - Type: string
  - Purpose: One of the curated readable theme names supported by the suite.

- `toast_duration_sec`
  - Type: integer
  - Purpose: Seconds that routine toast notifications remain visible.

- `auto_save_interval_min`
  - Type: integer
  - Purpose: Minutes between automatic draft saves.

- `default_shift_hours`
  - Type: number
  - Purpose: Default shift hours loaded into Production Log.

- `default_goal_mph`
  - Type: number
  - Purpose: Default goal molds per hour loaded into Production Log.

- `downtime_codes`
  - Type: object
  - Purpose: Optional label overrides for downtime code numbers used by Production Log and Excel import/export. Extra numeric codes can be added here in addition to the defaults.

## Recommended Editing Path

Use Settings Manager for normal changes so values stay inside the supported range of the app.