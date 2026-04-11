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

from app.persistence import write_json_with_backup
from app.utils import external_path


class RecoveryViewerModel:
    def __init__(self):
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
        sources = [
            {
                "kind": "Settings Backup",
                "target_path": external_path("settings.json"),
                "backup_dir": external_path("data/backups/settings"),
            },
            {
                "kind": "Layout Backup",
                "target_path": external_path("layout_config.json"),
                "backup_dir": external_path("data/backups/layouts"),
            },
            {
                "kind": "Rates Backup",
                "target_path": external_path("rates.json"),
                "backup_dir": external_path("data/backups/rates"),
            },
        ]

        records = []
        for source in sources:
            os.makedirs(source["backup_dir"], exist_ok=True)
            adjacent_backup = f"{source['target_path']}.bak"
            if os.path.exists(adjacent_backup):
                saved_at = self.read_saved_at(adjacent_backup)
                records.append(
                    {
                        "record_type": "config_backup",
                        "kind": f"{source['kind']} (.bak)",
                        "name": os.path.basename(adjacent_backup),
                        "path": adjacent_backup,
                        "saved_at": saved_at,
                        "sort_key": self.sort_key(saved_at, adjacent_backup),
                        "restore_target": os.path.basename(source["target_path"]),
                        "target_path": source["target_path"],
                        "backup_dir": source["backup_dir"],
                    }
                )

            for filename in os.listdir(source["backup_dir"]):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(source["backup_dir"], filename)
                saved_at = self.read_saved_at(path)
                records.append(
                    {
                        "record_type": "config_backup",
                        "kind": source["kind"],
                        "name": filename,
                        "path": path,
                        "saved_at": saved_at,
                        "sort_key": self.sort_key(saved_at, path),
                        "restore_target": os.path.basename(source["target_path"]),
                        "target_path": source["target_path"],
                        "backup_dir": source["backup_dir"],
                    }
                )
        return records

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
