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
from app.form_definition_registry import DEFAULT_FORM_ID, FormDefinitionRegistry
from app.persistence import write_json_with_backup
from app.utils import external_path


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
                return "Production Logging Center"
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
