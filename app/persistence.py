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
import shutil
import tempfile
from datetime import datetime

from app.utils import external_path

__module_name__ = "Persistence Helpers"
__version__ = "1.1.0"

_WARNED_BACKUP_FAILURES = set()
_BACKUP_POLICY_CACHE = {
    "settings_mtime": None,
    "policy": None,
}


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def _build_versioned_backup_path(target_path, backup_dir):
    base_name = os.path.basename(target_path)
    stem, extension = os.path.splitext(base_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate_name = f"{stem}_{timestamp}{extension}"
    candidate_path = os.path.join(backup_dir, candidate_name)
    duplicate_index = 1

    while os.path.exists(candidate_path):
        candidate_name = f"{stem}_{timestamp}_{duplicate_index}{extension}"
        candidate_path = os.path.join(backup_dir, candidate_name)
        duplicate_index += 1

    return candidate_path


def _prune_versioned_backups(target_path, backup_dir, keep_count):
    if keep_count is None or keep_count <= 0 or not os.path.exists(backup_dir):
        return

    stem, extension = os.path.splitext(os.path.basename(target_path))
    matching_files = []
    for filename in os.listdir(backup_dir):
        if filename.startswith(f"{stem}_") and filename.endswith(extension):
            path = os.path.join(backup_dir, filename)
            try:
                modified_at = os.path.getmtime(path)
            except OSError:
                continue
            matching_files.append((modified_at, path))

    matching_files.sort(reverse=True)
    for _, old_path in matching_files[keep_count:]:
        try:
            os.remove(old_path)
        except OSError:
            pass


def _warn_backup_failure(context, source_path, destination_path, exc):
    warning_key = (context, os.path.abspath(destination_path))
    if warning_key in _WARNED_BACKUP_FAILURES:
        return
    _WARNED_BACKUP_FAILURES.add(warning_key)
    print(
        f"[persistence.{context}] Backup copy skipped: "
        f"{source_path} -> {destination_path} ({exc})"
    )


def _copy_backup_with_fallback(source_path, destination_path, context):
    try:
        shutil.copy2(source_path, destination_path)
        return True
    except Exception as first_exc:
        try:
            shutil.copyfile(source_path, destination_path)
            _warn_backup_failure(context, source_path, destination_path, first_exc)
            return True
        except Exception as second_exc:
            _warn_backup_failure(context, source_path, destination_path, second_exc)
            return False


def _normalize_backup_policy(raw_policy):
    policy = {
        "enabled": True,
        "interval_min": 30,
        "keep_count": 12,
        "draft_auto_save_interval_min": 5,
        "draft_history_keep_count": 20,
        "target_overrides": {},
    }
    if not isinstance(raw_policy, dict):
        return policy

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


def _load_backup_policy():
    settings_path = external_path(os.path.join("data", "config", "settings.json"))
    try:
        settings_mtime = os.path.getmtime(settings_path)
    except OSError:
        return _normalize_backup_policy(None)

    cached_mtime = _BACKUP_POLICY_CACHE.get("settings_mtime")
    cached_policy = _BACKUP_POLICY_CACHE.get("policy")
    if cached_mtime == settings_mtime and isinstance(cached_policy, dict):
        return cached_policy

    try:
        with open(settings_path, "r", encoding="utf-8") as handle:
            settings = json.load(handle)
    except Exception:
        policy = _normalize_backup_policy(None)
        _BACKUP_POLICY_CACHE["settings_mtime"] = settings_mtime
        _BACKUP_POLICY_CACHE["policy"] = policy
        return policy

    policy = _normalize_backup_policy(settings.get("backup_policy") if isinstance(settings, dict) else None)
    _BACKUP_POLICY_CACHE["settings_mtime"] = settings_mtime
    _BACKUP_POLICY_CACHE["policy"] = policy
    return policy


def _normalize_path(path_value):
    return os.path.normcase(os.path.normpath(os.path.abspath(str(path_value or ""))))


def _resolve_backup_target(target_path, backup_dir):
    normalized_target = _normalize_path(target_path)
    normalized_backup_dir = _normalize_path(backup_dir)

    target_map = {
        _normalize_path(external_path(os.path.join("data", "config", "settings.json"))): "settings",
        _normalize_path(external_path(os.path.join("data", "config", "layout_config.json"))): "layout_config",
        _normalize_path(external_path(os.path.join("data", "config", "form_definitions.json"))): "form_definitions",
        _normalize_path(external_path(os.path.join("data", "config", "rates.json"))): "rates",
        _normalize_path(external_path(os.path.join("data", "config", "production_log_calculations.json"))): "production_log_calculations",
    }
    if normalized_target in target_map:
        return target_map[normalized_target]

    if normalized_backup_dir.endswith(_normalize_path(os.path.join("data", "backups", "layouts"))):
        return "form_layouts"
    if normalized_backup_dir.endswith(_normalize_path(os.path.join("data", "backups", "form_calculations"))):
        return "form_calculations"
    if normalized_backup_dir.endswith(_normalize_path(os.path.join("data", "pending", "history"))):
        return "draft_history"
    if _normalize_path(os.path.join("data", "pending")) in normalized_target:
        return "draft_history"
    return None


def _get_target_policy(target_key, policy):
    if not target_key:
        return None
    normalized_policy = policy if isinstance(policy, dict) else _normalize_backup_policy(None)
    if target_key == "draft_history":
        return {
            "enabled": bool(normalized_policy.get("enabled", True)),
            "interval_min": int(normalized_policy.get("draft_auto_save_interval_min", 5)),
            "keep_count": int(normalized_policy.get("draft_history_keep_count", 20)),
        }
    target_overrides = normalized_policy.get("target_overrides") if isinstance(normalized_policy.get("target_overrides"), dict) else {}
    target_policy = target_overrides.get(target_key)
    if isinstance(target_policy, dict):
        return target_policy
    return {
        "enabled": bool(normalized_policy.get("enabled", True)),
        "interval_min": int(normalized_policy.get("interval_min", 30)),
        "keep_count": int(normalized_policy.get("keep_count", 12)),
    }


def _should_create_versioned_backup(target_path, backup_dir, policy):
    target_key = _resolve_backup_target(target_path, backup_dir)
    target_policy = _get_target_policy(target_key, policy)
    if not target_policy or not bool(target_policy.get("enabled", True)):
        return False, target_key, target_policy

    interval_min = max(1, int(target_policy.get("interval_min", 1)))
    if interval_min <= 1:
        return True, target_key, target_policy

    try:
        latest_mtime = None
        if backup_dir and os.path.isdir(backup_dir):
            newest_mtime = None
            for filename in os.listdir(backup_dir):
                candidate_path = os.path.join(backup_dir, filename)
                if not os.path.isfile(candidate_path):
                    continue
                try:
                    modified_at = os.path.getmtime(candidate_path)
                except OSError:
                    continue
                if newest_mtime is None or modified_at > newest_mtime:
                    newest_mtime = modified_at
            if newest_mtime is not None:
                latest_mtime = newest_mtime

        if latest_mtime is None:
            adjacent_backup_path = f"{os.path.abspath(target_path)}.bak"
            if os.path.exists(adjacent_backup_path):
                latest_mtime = os.path.getmtime(adjacent_backup_path)

        if latest_mtime is None:
            return True, target_key, target_policy

        elapsed_minutes = (datetime.now().timestamp() - latest_mtime) / 60.0
        return elapsed_minutes >= interval_min, target_key, target_policy
    except OSError:
        return True, target_key, target_policy


def _latest_versioned_backup_age_seconds(target_path, backup_dir):
    if not backup_dir or not os.path.exists(backup_dir):
        return None

    base_name = os.path.basename(target_path)
    stem, extension = os.path.splitext(base_name)
    latest_mtime = None
    for filename in os.listdir(backup_dir):
        if not filename.startswith(f"{stem}_") or not filename.endswith(extension):
            continue
        candidate_path = os.path.join(backup_dir, filename)
        try:
            modified_at = os.path.getmtime(candidate_path)
        except OSError:
            continue
        if latest_mtime is None or modified_at > latest_mtime:
            latest_mtime = modified_at

    if latest_mtime is None:
        return None
    return max(0.0, datetime.now().timestamp() - latest_mtime)


def write_json_with_backup(target_path, payload, backup_dir=None, keep_count=10, indent=4):
    target_path = os.path.abspath(target_path)
    target_dir = os.path.dirname(target_path) or os.path.abspath(".")
    ensure_directory(target_dir)

    policy = _load_backup_policy()
    allow_backup_copy, target_key, target_policy = _should_create_versioned_backup(target_path, backup_dir, policy)
    effective_keep_count = keep_count
    if isinstance(target_policy, dict):
        effective_keep_count = int(target_policy.get("keep_count", keep_count) or keep_count)

    adjacent_backup_path = None
    versioned_backup_path = None

    if os.path.exists(target_path) and allow_backup_copy:
        adjacent_backup_path = f"{target_path}.bak"
        _copy_backup_with_fallback(target_path, adjacent_backup_path, "write_json_with_backup")

        if backup_dir:
            backup_dir = ensure_directory(os.path.abspath(backup_dir))
            versioned_backup_path = _build_versioned_backup_path(target_path, backup_dir)
            _copy_backup_with_fallback(target_path, versioned_backup_path, "write_json_with_backup")
            _prune_versioned_backups(target_path, backup_dir, effective_keep_count)

    fd, temp_path = tempfile.mkstemp(prefix="martin_", suffix=".json.tmp", dir=target_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=indent)
            handle.write("\n")

        os.replace(temp_path, target_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    return {
        "target_path": target_path,
        "adjacent_backup_path": adjacent_backup_path,
        "versioned_backup_path": versioned_backup_path,
        "backup_target": target_key,
    }


def write_text_with_backup(target_path, text, backup_dir=None, keep_count=10, encoding="utf-8"):
    target_path = os.path.abspath(target_path)
    target_dir = os.path.dirname(target_path) or os.path.abspath(".")
    ensure_directory(target_dir)

    policy = _load_backup_policy()
    allow_backup_copy, target_key, target_policy = _should_create_versioned_backup(target_path, backup_dir, policy)
    effective_keep_count = keep_count
    if isinstance(target_policy, dict):
        effective_keep_count = int(target_policy.get("keep_count", keep_count) or keep_count)

    adjacent_backup_path = None
    versioned_backup_path = None

    if os.path.exists(target_path) and allow_backup_copy:
        adjacent_backup_path = f"{target_path}.bak"
        _copy_backup_with_fallback(target_path, adjacent_backup_path, "write_text_with_backup")

        if backup_dir:
            backup_dir = ensure_directory(os.path.abspath(backup_dir))
            versioned_backup_path = _build_versioned_backup_path(target_path, backup_dir)
            _copy_backup_with_fallback(target_path, versioned_backup_path, "write_text_with_backup")
            _prune_versioned_backups(target_path, backup_dir, effective_keep_count)

    suffix = os.path.splitext(target_path)[1] or ".tmp"
    fd, temp_path = tempfile.mkstemp(prefix="martin_", suffix=suffix, dir=target_dir)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)

        os.replace(temp_path, target_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    return {
        "target_path": target_path,
        "adjacent_backup_path": adjacent_backup_path,
        "versioned_backup_path": versioned_backup_path,
        "backup_target": target_key,
    }