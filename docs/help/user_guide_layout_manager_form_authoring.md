# Form Creation & Editing

Follow this guide when creating a new form layout or editing an existing one
from scratch.

---

## Quick Start Steps

1. Open **Layout Manager**.
2. Choose one:
   - Click **Create** to branch off the current form layout.
   - Click **Create Blank** to start with a minimal blank template.
3. Enter a name and description for your form.
4. Use **Block View** and `Structure > Section Editor` to design sections and columns.
5. Use **Preview** to check field alignment and placements.
6. Check `Structure > Validation` to fix any layout issues or warnings.
7. Click **Save** to write the layout.
8. Click **Activate** to make the form active in the **Form Loader**.

---

## Recommended Setup Order

1. **Sections first**: Go to `Structure > Section Editor` to add your tables
   and single field blocks, and set their ordering.
2. **Fields second**: Go to **Block View** to define header and row columns,
   set names, data types, read-only permissions, and options lists.
3. **Excel mappings third**: Go to **Import / Export** to select your template and
   map form fields to the correct Excel sheet columns/cells.
4. **Verify fourth**: Use the **Preview** and **Validation** tabs to verify your
   work and resolve any errors before saving.

---

## Practical Editing Tips

### Section Editor
- Keep **Section IDs** short and stable. Changing them later can break maps.
- For repeating tables, configure the row deletion settings (labels, confirmations)
  intentionally to protect operator data entry.

### Row Fields
- Assign **Role** values carefully (like `part_number` or `mold_count`) so the app
  knows how to calculate values and lookup rates.
- Use **Bulk Actions** (Bulk Rename, Bulk Delete, Bulk Convert) if you need to
  make major changes to many columns at once.

### Mappings
- Click preview cells in `Preview > Header Preview` to quickly see which fields
  they map to.
- Use the **Validation** summary tab frequently to identify duplicate names, missing
  mappings, or invalid widget configurations.

---

## Workflow Safety

- **Save Snapshots**: Go to the **Summary** tab, enter a label, and click
  **Save Version** before making major structural edits or running bulk actions.
  Use **Restore Latest** to roll back if needed.
- **Save Warnings**: If you save a layout that requires new calculations, the
  app will offer to open the **Form Calculations** setup tool. We recommend
  completing calculations setup immediately.

---

## Checklist for Launching a Form

- [ ] Form has a clear, descriptive name.
- [ ] Table sections have deletion and repeat rules set.
- [ ] Header and table fields are marked correct (read-only, roles, triggers).
- [ ] Excel mapping references the correct columns/cells.
- [ ] The **Validation** tab shows no errors (and warnings are verified).
- [ ] Layout is **Saved** and then **Activated**.
