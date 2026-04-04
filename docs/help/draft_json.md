# Draft JSON Reference

Draft files are stored in `data/pending` and are created by Production Log.

Typical filename pattern:

```text
draft_MM-DD-YYYY_shiftN.json
```

## Structure

```json
{
  "meta": {
    "saved_at": "2026-04-04T13:45:00",
    "auto_save": false,
    "version": "1.0.3"
  },
  "header": {},
  "production": [],
  "downtime": []
}
```

## meta

- `saved_at`: ISO timestamp for when the draft was written
- `auto_save`: `true` for automatic saves, `false` for manual saves
- `version`: module version that created the draft

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

Treat draft files as recovery data. In normal use they should be created, resumed, and deleted through Production Log rather than edited by hand.