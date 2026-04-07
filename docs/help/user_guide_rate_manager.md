# Rate Manager

Use Rate Manager to maintain molds-per-hour targets for part numbers.

- Select an existing part to load it into the editor.
- Update the part number or rate and save the change.
- Use Clear to reset the editor without deleting anything.
- Delete removes the selected rate entry.
- The table is the working list of stored part-number rates and is sorted to make lookups easier.

These rates are used by Production Log when calculating per-row time and overall shift efficiency.

## JSON Relationship

- Rate Manager edits the live rate file used by Logging Center.
- Use Rate Manager when possible instead of editing `rates.json` manually.
- Saving rates also keeps recovery copies under `data/backups/rates`.
