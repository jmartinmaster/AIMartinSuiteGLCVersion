# rates.json Reference

`rates.json` stores the standard molds-per-hour target for each part number.

## Structure

The file is a single JSON object where:

- each key is a part number string
- each value is a numeric molds-per-hour target

Example:

```json
{
  "010023112D": 200,
  "012586R": 246,
  "0201400C": 200
}
```

## How It Is Used

- Production Log looks up the entered part number in this file.
- If a part number is found, its target rate is used to estimate row time.
- If a part number is not found, the Production Log falls back to the current goal MPH.

## Good Practices

- Keep part numbers exactly as operators enter them.
- Keep values numeric.
- Avoid duplicate keys written in slightly different formats.

## Recommended Editing Path

Use Rate Manager instead of editing the file directly whenever possible.