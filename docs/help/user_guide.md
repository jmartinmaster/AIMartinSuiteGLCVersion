# Production Logging Center - User Guide

Welcome to the Production Logging Center. This desktop application is designed
to help you record Disamatic production, track downtime, manage standard part
rates, and export shift records into the plant's Excel template.

---

## What Does This App Do?

The application is built around four daily tasks:

1. **Fill out the shift form** in the **Form Loader**.
2. **Save and restore drafts** so you never lose your work.
3. **Manage standard rates** (molds per hour) for time and efficiency calculations.
4. **Customize forms and settings** without having to write or edit code.

You can also check for application updates using the **Update Manager** and view
license information on the **About** screen.

### Security Default

By default, the app starts in **non-secure mode**, which allows full access
without authentication prompts. Security Admin can disable non-secure mode in
Settings Manager to enforce vault authentication and rights.

---

## Accessibility (ADA Compliance)

We are actively working on making the program easier to use for everyone:
- Accessibility improvements are currently being developed and added.
- We welcome your suggestions, feedback, and contributions to help improve
  the app for all operators.

---

## How to Find Your Way Around

To keep things simple, details for each part of the app are broken into separate
guides. You can click on the sections below them in the Help Center:

- **Overview** (This page): General workflow and general guidelines.
- **Form Loader**: How to enter shift data, balance downtime, and import/export Excel.
- **Rate Manager**: Where you update standard production rates for part numbers.
- **Layout Manager**: Customize form sections, field types, and Excel mappings.
- **Settings Manager**: Change defaults, themes, saving options, and access security controls.
- **Backup / Recovery**: Recover lost drafts or restore layout/settings backups.
- **Update Manager**: Check for app updates and view release details.

---

## Typical Daily Workflow

Follow these steps for a standard shift:

1. **Open Form Loader** at the start of your shift.
2. **Enter Shift Info** (date, shift, team, etc.) at the top.
3. **Add Production Rows** as you run different parts.
4. **Add Downtime Rows** whenever a stoppage or delay occurs.
5. **Save Drafts** periodically during your shift to keep your progress safe.
6. **Calculate All** to review shift efficiency.
7. **Export Excel** once the record is finished and ready to submit.

---

## Drafts and Recovery

The draft status bar at the top of the **Form Loader** helps protect your work:

- **Resume Latest**: Loads your most recent saved draft.
- **Pending Drafts**: Opens a list of all saved drafts.
- **Backup / Recovery**: Provides tools to restore from older snapshots or backup files.
- **Delete Current Draft**: Clears the current draft file from the system.

> **Note:** If you try to load a draft or import an Excel file while you have
> unsaved changes, the app will ask for your confirmation first to avoid
> overwriting your work.

---

## Excel Import & Export Guidelines

- **Exporting**: The app exports data using the template path set in your
  active layout file.
- **Organization**: If enabled, the app automatically organizes exports into folders
  by year and month (e.g., `2026/06 June`). If it finds a folder named `06`, it
  will rename it to `06 June` automatically.
- **Downtime Balancing**: If your shift hours do not match the total production
  and downtime, the app will ask if you want to balance your downtime before
  saving.
- **Importing**: You can load older Excel files back into the application.
  The app is smart enough to detect columns correctly even if they differ
  between older and newer templates.

---

## Editing Data Files

For safety, always use the built-in editors in the app instead of editing JSON
files directly:
- To edit rates, use the **Rate Manager** (edits `rates.json`).
- To edit settings, use the **Settings Manager** (edits `settings.json`).
- To edit layouts, use the **Layout Manager** (edits form layouts).

The program automatically makes backup copies in the `data/backups/` folder
every time you save settings, rates, or layouts.