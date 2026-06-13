# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import json
import os
from datetime import datetime

from app.external_data_registry import ExternalDataRegistry
from app.form_definition_registry import DEFAULT_FORM_ID, DEFAULT_FORM_NAME, FormDefinitionRegistry
from app.persistence import write_json_with_backup
from app.utils import external_path


__module_name__ = "Recovery Viewer"
__version__ = "1.0.0"

BACKUP_TARGET_DEFINITIONS = (
    {
        "key": "settings",
        "label": "Settings",
        "description": "Backs up the editable settings.json file.",
        "target_path": external_path("data/config/settings.json"),
        "backup_dir": external_path("data/backups/settings"),
    },
    {
        "key": "layout_config",
        "label": "Default Layout",
        "description": "Backs up the shared default layout configuration.",
        "target_path": external_path("data/config/layout_config.json"),
        "backup_dir": external_path("data/backups/layouts"),
    },
    {
        "key": "form_definitions",
        "label": "Form Definitions",
        "description": "Backs up the form registry.",
        "target_path": external_path("data/config/form_definitions.json"),
        "backup_dir": external_path("data/backups/forms"),
    },
    {
        "key": "rates",
        "label": "Rates",
        "description": "Backs up the rate configuration.",
        "target_path": external_path("data/config/rates.json"),
        "backup_dir": external_path("data/backups/rates"),
    },
    {
        "key": "production_log_calculations",
        "label": "Form Calculations",
        "description": "Backs up the calculation formulas and runtime defaults.",
        "target_path": external_path("data/config/production_log_calculations.json"),
        "backup_dir": external_path("data/backups/production_log_calculations"),
    },
    {
        "key": "form_layouts",
        "label": "Form Layout Backups",
        "description": "Backs up per-form layout files under data/backups/layouts.",
        "target_path": external_path("data/forms"),
        "backup_dir": external_path("data/backups/layouts"),
    },
    {
        "key": "form_calculations",
        "label": "Form Calculation Backups",
        "description": "Backs up per-form calculation files under data/backups/form_calculations.",
        "target_path": external_path("data/forms"),
        "backup_dir": external_path("data/backups/form_calculations"),
    },
    {
        "key": "draft_history",
        "label": "Draft History",
        "description": "Backs up pending drafts into data/pending/history.",
        "target_path": external_path("data/pending"),
        "backup_dir": external_path("data/pending/history"),
    },
)


class RecoveryViewerModel:
    def __init__(self, data_registry=None):
        self.form_registry = FormDefinitionRegistry()
        self.data_registry = data_registry or ExternalDataRegistry()
        self.records = []

    def refresh_records(self):
        self.records = []
        self.records.extend(self.collect_draft_records())
        self.records.extend(self.collect_snapshot_records())
        self.records.extend(self.collect_config_backup_records())
        self.records.sort(key=lambda item: item["sort_key"], reverse=True)
        return list(self.records)

    def normalize_backup_policy(self, raw_policy):
        policy = {
            "enabled": True,
            "interval_min": 30,
            "keep_count": 12,
            "draft_auto_save_interval_min": 5,
            "draft_history_keep_count": 20,
            "target_overrides": {},
        }
        if isinstance(raw_policy, dict):
            policy.update(raw_policy)

        try:
            policy["enabled"] = bool(policy.get("enabled", True))
        except Exception:
            policy["enabled"] = True
        try:
            policy["interval_min"] = max(1, int(policy.get("interval_min", 30)))
        except Exception:
            policy["interval_min"] = 30
        try:
            policy["keep_count"] = max(1, int(policy.get("keep_count", 12)))
        except Exception:
            policy["keep_count"] = 12
        try:
            policy["draft_auto_save_interval_min"] = max(1, int(policy.get("draft_auto_save_interval_min", 5)))
        except Exception:
            policy["draft_auto_save_interval_min"] = 5
        try:
            policy["draft_history_keep_count"] = max(1, int(policy.get("draft_history_keep_count", 20)))
        except Exception:
            policy["draft_history_keep_count"] = 20

        normalized_targets = {}
        raw_targets = policy.get("target_overrides")
        if isinstance(raw_targets, dict):
            for target_key, raw_target_policy in raw_targets.items():
                normalized_key = str(target_key or "").strip()
                if not normalized_key:
                    continue
                target_policy = {
                    "enabled": True,
                    "interval_min": policy["interval_min"],
                    "keep_count": policy["keep_count"],
                }
                if isinstance(raw_target_policy, dict):
                    target_policy.update(raw_target_policy)
                try:
                    target_policy["enabled"] = bool(target_policy.get("enabled", True))
                except Exception:
                    target_policy["enabled"] = True
                try:
                    target_policy["interval_min"] = max(1, int(target_policy.get("interval_min", policy["interval_min"])))
                except Exception:
                    target_policy["interval_min"] = policy["interval_min"]
                try:
                    target_policy["keep_count"] = max(1, int(target_policy.get("keep_count", policy["keep_count"])))
                except Exception:
                    target_policy["keep_count"] = policy["keep_count"]
                normalized_targets[normalized_key] = target_policy
        policy["target_overrides"] = normalized_targets
        return policy

    def _read_settings_payload(self):
        settings_path = self.data_registry.resolve_write_path("settings")
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    def load_backup_policy(self):
        payload = self._read_settings_payload()
        return self.normalize_backup_policy(payload.get("backup_policy") if isinstance(payload, dict) else None)

    def save_backup_policy(self, policy):
        settings_payload = self._read_settings_payload()
        if not isinstance(settings_payload, dict):
            settings_payload = {}
        settings_payload["backup_policy"] = self.normalize_backup_policy(policy)
        write_json_with_backup(
            self.data_registry.resolve_write_path("settings"),
            settings_payload,
            backup_dir=self.data_registry.resolve_backup_dir("settings"),
            keep_count=int(settings_payload["backup_policy"].get("keep_count", 12) or 12),
        )
        return settings_payload["backup_policy"]

    def get_backup_target_definitions(self):
        return [dict(definition) for definition in BACKUP_TARGET_DEFINITIONS]

    def _delete_paths(self, paths):
        deleted_count = 0
        for path in paths:
            try:
                if path and os.path.exists(path) and os.path.isfile(path):
                    os.remove(path)
                    deleted_count += 1
            except OSError:
                continue
        return deleted_count

    def prune_pending_drafts(self):
        drafts = sorted(self.collect_draft_records(), key=lambda item: item["sort_key"], reverse=True)
        deleted_count = self._delete_paths([record.get("path") for record in drafts[1:]])
        return {
            "kept": 1 if drafts else 0,
            "deleted": deleted_count,
            "total": len(drafts),
        }

    def prune_recovery_snapshots(self):
        snapshots = sorted(self.collect_snapshot_records(), key=lambda item: item["sort_key"], reverse=True)
        deleted_count = self._delete_paths([record.get("path") for record in snapshots[1:]])
        return {
            "kept": 1 if snapshots else 0,
            "deleted": deleted_count,
            "total": len(snapshots),
        }

    def prune_config_backups(self):
        records_by_target = {}
        for record in self.collect_config_backup_records():
            target_path = str(record.get("target_path") or "").strip()
            if not target_path:
                continue
            records_by_target.setdefault(target_path, []).append(record)

        deleted_count = 0
        kept_count = 0
        total_count = 0
        for grouped_records in records_by_target.values():
            sorted_records = sorted(grouped_records, key=lambda item: item["sort_key"], reverse=True)
            total_count += len(sorted_records)
            if sorted_records:
                kept_count += 1
            deleted_count += self._delete_paths([record.get("path") for record in sorted_records[1:]])

        return {
            "kept": kept_count,
            "deleted": deleted_count,
            "total": total_count,
        }

    def collect_draft_records(self):
        pending_dir = external_path("data/pending")
        os.makedirs(pending_dir, exist_ok=True)
        records = []
        for filename in os.listdir(pending_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(pending_dir, filename)
            if os.path.isdir(path):
                continue
            saved_at = self.read_saved_at(path)
            records.append(
                {
                    "record_type": "draft",
                    "kind": "Pending Draft",
                    "form_name": self._read_payload_form_name(path),
                    "name": filename,
                    "path": path,
                    "saved_at": saved_at,
                    "sort_key": self.sort_key(saved_at, path),
                    "restore_target": filename,
                    "target_path": path,
                }
            )
        return records

    def collect_snapshot_records(self):
        history_dir = external_path("data/pending/history")
        os.makedirs(history_dir, exist_ok=True)
        records = []
        for filename in os.listdir(history_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(history_dir, filename)
            saved_at = self.read_saved_at(path)
            payload = self.load_json(path)
            draft_name = payload.get("meta", {}).get("draft_name") or filename
            records.append(
                {
                    "record_type": "snapshot",
                    "kind": "Recovery Snapshot",
                    "form_name": payload.get("meta", {}).get("form_name") or self.get_form_name(payload.get("meta", {}).get("form_id")),
                    "name": filename,
                    "path": path,
                    "saved_at": saved_at,
                    "sort_key": self.sort_key(saved_at, path),
                    "restore_target": draft_name,
                    "target_path": os.path.join(external_path("data/pending"), draft_name),
                }
            )
        return records

    def collect_config_backup_records(self):
        shared_sources = self.collect_shared_config_backup_sources()
        sources = shared_sources[:1] + self.collect_form_layout_backup_sources() + shared_sources[1:]

        records = []
        for source in sources:
            records.extend(self._collect_config_backup_records_for_source(source))
        return records

    def collect_shared_config_backup_sources(self):
        sources = []
        for spec in self.data_registry.get_recovery_specs():
            if spec.key == "layout_config":
                continue
            sources.append(
                {
                    "kind": spec.recovery_kind or spec.display_name,
                    "form_name": "System",
                    "target_path": self.data_registry.resolve_write_path(spec.key),
                    "backup_dir": self.data_registry.resolve_backup_dir(spec.key),
                    "notifies_active_form": bool(spec.notifies_active_form),
                }
            )
        return sources

    def collect_form_layout_backup_sources(self):
        sources = []
        known_form_ids = set()
        for form_info in self.form_registry.list_forms():
            form_id = form_info.get("id") or DEFAULT_FORM_ID
            known_form_ids.add(form_id)
            kind = "Default Layout Backup" if form_info.get("built_in") else "Form Layout Backup"
            sources.append(
                {
                    "kind": kind,
                    "form_id": form_id,
                    "form_name": form_info.get("name") or self.get_form_name(form_id),
                    "target_path": form_info.get("save_path"),
                    "backup_dir": form_info.get("backup_dir"),
                    "notifies_active_form": True,
                }
            )

        layout_backup_root = external_path(os.path.join("data", "backups", "layouts"))
        os.makedirs(layout_backup_root, exist_ok=True)
        for child_name in os.listdir(layout_backup_root):
            child_path = os.path.join(layout_backup_root, child_name)
            if not os.path.isdir(child_path):
                continue
            form_id = str(child_name or "").strip()
            if not form_id or form_id in known_form_ids:
                continue
            sources.append(
                {
                    "kind": "Archived Form Layout Backup",
                    "form_id": form_id,
                    "form_name": self.get_form_name(form_id),
                    "target_path": external_path(os.path.join("data", "forms", f"{form_id}.json")),
                    "backup_dir": child_path,
                    "notifies_active_form": True,
                }
            )

        return sources

    def _collect_config_backup_records_for_source(self, source):
        records = []
        backup_dir = source["backup_dir"]
        os.makedirs(backup_dir, exist_ok=True)
        adjacent_backup = f"{source['target_path']}.bak"
        if os.path.exists(adjacent_backup):
            saved_at = self.read_saved_at(adjacent_backup)
            records.append(
                {
                    "record_type": "config_backup",
                    "kind": f"{source['kind']} (.bak)",
                    "form_name": source.get("form_name", "System"),
                    "name": os.path.basename(adjacent_backup),
                    "path": adjacent_backup,
                    "saved_at": saved_at,
                    "sort_key": self.sort_key(saved_at, adjacent_backup),
                    "restore_target": os.path.basename(source["target_path"]),
                    "target_path": source["target_path"],
                    "backup_dir": backup_dir,
                    "notifies_active_form": bool(source.get("notifies_active_form")),
                }
            )

        for filename in os.listdir(backup_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(backup_dir, filename)
            saved_at = self.read_saved_at(path)
            records.append(
                {
                    "record_type": "config_backup",
                    "kind": source["kind"],
                    "form_name": source.get("form_name", "System"),
                    "name": filename,
                    "path": path,
                    "saved_at": saved_at,
                    "sort_key": self.sort_key(saved_at, path),
                    "restore_target": os.path.basename(source["target_path"]),
                    "target_path": source["target_path"],
                    "backup_dir": backup_dir,
                    "notifies_active_form": bool(source.get("notifies_active_form")),
                }
            )
        return records

    def _read_payload_form_name(self, path):
        payload = self.load_json(path)
        meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
        return meta.get("form_name") or self.get_form_name(meta.get("form_id"))

    def get_form_name(self, form_id=None):
        try:
            form_info = self.form_registry.get_form(form_id)
            return str(form_info.get("name") or form_info.get("id") or "Form")
        except Exception:
            if str(form_id or "").strip() in {"", DEFAULT_FORM_ID}:
                return DEFAULT_FORM_NAME
            return str(form_id or "Form").replace("_", " ").title()

    def read_saved_at(self, path):
        payload = self.load_json(path)
        saved_at = payload.get("meta", {}).get("saved_at")
        if saved_at:
            return saved_at
        return datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")

    def sort_key(self, saved_at, path):
        try:
            return datetime.fromisoformat(saved_at)
        except Exception:
            return datetime.fromtimestamp(os.path.getmtime(path))

    def load_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    def restore_config_backup(self, record):
        payload = self.load_json(record["path"])
        write_json_with_backup(
            record["target_path"],
            payload,
            backup_dir=record.get("backup_dir"),
            keep_count=12,
        )
        return record["target_path"]

    def restore_snapshot_as_draft(self, record):
        payload = self.load_json(record["path"])
        write_json_with_backup(
            record["target_path"],
            payload,
            backup_dir=external_path("data/pending/history"),
            keep_count=20,
        )
        return record["target_path"]
