# Rate Manager

Use the **Rate Manager** to manage standard molds-per-hour targets for different
part numbers. These rates are used by the **Form Loader** to calculate production
time and shift efficiency.

---

## How to Manage Rates

### Finding a Part
- Type in the **Search** box to filter the list of parts. The search is case-insensitive.

### Adding a New Part Rate
1. Enter the part number in the **Part Number** field.
2. Enter the molds-per-hour target in the **Rate** field.
3. Click **Add** to save it to the list.

### Editing an Existing Rate
1. Select a part from the table.
2. Click **Edit**. The part details will load into the input fields above.
3. Modify the **Rate** (the part number itself cannot be edited).
4. Click **Save** to apply the changes, or click **Cancel** to discard them.

### Deleting a Rate
1. Select a part from the table.
2. Click **Delete** to remove it from the database.

---

## File Backups
- The app saves these rates in the `rates.json` file.
- We recommend using the **Rate Manager** instead of editing files manually.
- Every time you save changes, a backup copy is automatically created in
  `data/backups/rates` to protect your data.
