# Draft JSON Reference

Draft files store in-progress Production Log work so a session can be resumed after interruption.

- Default location: `data/pending`
- Created by: Production Log manual and automatic draft saves

Filename pattern is generated from header values:

```text
draft_{date-with-slashes-replaced}_shift{shift}.json
```

Examples:

```text
draft_04-11-2026_shift3.json
draft_unsaved_shift0.json
```

Notes:
- If `header.date` is missing, `unsaved` is used.
- If `header.shift` is missing, `0` is used.

## Structure

```json
{
  "meta": {
    "saved_at": "2026-04-04T13:45:00",
    "auto_save": false,
    "version": "1.0.3",
    "draft_name": "draft_04-04-2026_shift3.json"
  },
  "header": {},
  "production": [],
  "downtime": []
}
```

## meta

- Type: object
- Purpose: Save metadata used for draft listing and recovery context

Keys:

- `saved_at`: ISO timestamp for when the draft was written
- `auto_save`: `true` for automatic saves, `false` for manual saves
- `version`: module version that created the draft
- `draft_name`: basename of the draft file path

## header

- Type: object
- Purpose: Current values of the Production Log header fields

Example:

```json
{
  "date": "04/04/2026",
  "cast_date": "095",
  "shift": "3",
  "hours": "8.0",
  "goal_mph": "240"
}
```

## production

- Type: array of row objects
- Purpose: Saved production rows from the form

Example row:

```json
{
  "shop_order": "123456",
  "part_number": "012586R",
  "molds": "240",
  "time_calc": "58 min"
}
```

## downtime

- Type: array of row objects
- Purpose: Saved downtime rows from the form

Example row:

```json
{
  "start": "0715",
  "stop": "0735",
  "code": "2 Machine Repairs",
  "cause": "Hydraulic leak",
  "time_calc": "20 min"
}
```

## Recommended Editing Path

Treat draft files as recovery data. In normal use they should be created, resumed, and deleted through Production Log rather than edited manually.

## Save and Recovery Behavior

- Draft saves use atomic writes with backup rotation.
- Recovery snapshots are stored under `data/pending/history`.
- When listing drafts, missing or malformed `meta.saved_at` values fall back to file modification time.