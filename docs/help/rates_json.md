# rates.json Reference

The `rates.json` file stores the standard molds-per-hour target for each part
number.

---

## File Structure

The file is a simple list of part numbers mapped to their targets in JSON format:

```json
{
  "010023112D": "200",
  "012586R": "246",
  "0201400C": "200"
}
```

- **Key**: The part number string.
- **Value**: The target molds-per-hour value (as a text string).

---

## How It Is Used

1. When an operator types a part number in the **Form Loader**, the app looks it
   up in this file.
2. If found, the app uses that rate to estimate the run time for the row.
3. If not found, the app falls back to the default **Goal MPH** set in settings.
4. **Temporary Overrides**: To temporarily change a rate for a specific row, check the
   **Override** box on that row. This allows you to type a custom rate without modifying
   the global `rates.json` file.

---

## Guidelines

- Keep part numbers formatted exactly as operators write them.
- Enter numbers only. Do not add units like `mph` or text labels.
- Avoid duplicate keys.
- **Best Practice**: Always use the built-in **Rate Manager** interface in the app
  to make changes instead of editing this file manually.