# rates.json Reference

`rates.json` stores the standard molds-per-hour target for each part number.

## Structure

The file is a single JSON object where:

- each key is a part number string
- each value is the stored molds-per-hour target text for that part number

Example:

```json
{
  "010023112D": "200",
  "012586R": "246",
  "0201400C": "200"
}
```

## How It Is Used

- Production Log looks up the entered part number in this file.
- If a part number is found, its target rate is used to estimate row time.
- If a part number is not found, the Production Log falls back to the current goal MPH.
- The active row rate is shown in Production Log, and each line can temporarily override that value without changing `rates.json`.

## Good Practices

- Keep part numbers exactly as operators enter them.
- Keep values as clean numeric text so Production Log can convert them safely.
- Avoid duplicate keys written in slightly different formats.
- Avoid units or extra text such as `mph` in the stored value.

## Recommended Editing Path

Use Rate Manager instead of editing the file directly whenever possible.