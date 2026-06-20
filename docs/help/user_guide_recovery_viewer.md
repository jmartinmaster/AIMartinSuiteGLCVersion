# Backup / Recovery

Use the **Backup / Recovery** module to restore saved drafts, form configurations,
and system backups.

---

## Recovery Options

- **Pending Drafts**: Resume active shift entries directly in the **Form Loader**.
- **Recovery Snapshots**: Restore previous versions of your drafts back to the
  `data/pending/` folder.
- **System Settings & Rates**: Restore older configurations for settings, form definitions,
  rates, or custom layouts back to their live locations.
- **Open Selected File**: Open the backup file using your system's default text editor.
- **Open Containing Folder**: Open the file's folder in the system file browser.

> **Note**: Alerts, notifications, and confirmations appear as non-blocking
> status alerts (toast notifications) to keep your workflow smooth.

---

## Scope of Backups

The system automatically categorizes files to keep backups organized:

1. **Pending Drafts**: Active, in-progress shift logs.
2. **Recovery Snapshots**: Older timestamped checkpoints of your active drafts.
3. **Configuration Backups**: Saved under `data/backups/`, protecting your settings,
   rates, form list registry, and layout files.
