# Backup / Recovery

Use Backup / Recovery to inspect saved drafts, recovery snapshots, and JSON backup files.

- Pending Drafts can be resumed directly into Production Log.
- Recovery Snapshots can be restored back into `data/pending` and opened immediately.
- Settings, layout, and rate backups can be restored back into their live JSON files.
- Open Selected File and Open Containing Folder help when you want to inspect recovery files directly with the system default app or file browser.
- Selection reminders and restore-complete messages use toast notifications instead of blocking dialogs.
- The internal persistence helper powers these saves, but it is intentionally hidden from the sidebar because it is not a user-facing tool.

## Recovery Scope

- Pending drafts are active work files.
- Recovery snapshots are older versions of draft files.
- JSON backups under `data/backups` protect the main editable settings, layout, and rates files.
