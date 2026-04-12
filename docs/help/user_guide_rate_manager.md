# Rate Manager

Use Rate Manager to maintain molds-per-hour targets for part numbers.

- Search filters the visible part-number list as you type, ignoring letter case.
- Select an existing part and choose Edit to load that row into the editor.
- While editing, the part number stays locked, Add changes to Save, and Edit changes to Cancel.
- Add requires both a part number and a rate.
- Saving an edit requires a non-empty rate.
- Delete removes the selected rate entry.
- The table is the working list of stored part-number rates.

These rates are used by Production Log when calculating per-row time and overall shift efficiency.

## JSON Relationship

- Rate Manager edits the live rate file used by Logging Center.
- Use Rate Manager when possible instead of editing `rates.json` manually.
- Saving rates writes the external live `rates.json` file and keeps recovery copies under `data/backups/rates`.
