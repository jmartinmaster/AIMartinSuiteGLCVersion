# settings.json Reference

`settings.json` stores user-configurable defaults for the application.

## Structure

```json
{
  "export_directory": "exports",
  "organize_exports_by_date": true,
  "default_export_prefix": "Disamatic Production Sheet",
  "theme": "journal",
  "enable_screen_transitions": true,
  "screen_transition_duration_ms": 360,
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
  - Purpose: Base folder used for Excel exports.
  - Notes: When `organize_exports_by_date` is enabled, exports are written under `YYYY/MM MonthName` inside this base folder.

- `organize_exports_by_date`
  - Type: boolean
  - Purpose: If true, exports are grouped by date.
  - Notes: The app uses year folders with month folders such as `04 April`. If it finds an older month folder such as `04`, it renames it to the newer format when that month is exported.

- `default_export_prefix`
  - Type: string
  - Purpose: Prefix used when naming exported files.

- `theme`
  - Type: string
  - Purpose: One of the curated readable theme names supported by Logging Center.

- `enable_screen_transitions`
  - Type: boolean
  - Purpose: Enables or disables the short fade used when switching between major pages in the application.

- `screen_transition_duration_ms`
  - Type: integer
  - Purpose: Duration of the screen-change fade in milliseconds.
  - Supported range: `0` to `500`.
  - Notes: `0` makes page switches immediate.

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