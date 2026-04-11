import json
import os
import shutil
import tempfile
from datetime import datetime

__module_name__ = "Persistence Helpers"
__version__ = "1.0.9"


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


def write_json_with_backup(target_path, payload, backup_dir=None, keep_count=10, indent=4):
    target_path = os.path.abspath(target_path)
    target_dir = os.path.dirname(target_path) or os.path.abspath(".")
    ensure_directory(target_dir)

    adjacent_backup_path = None
    versioned_backup_path = None

    if os.path.exists(target_path):
        adjacent_backup_path = f"{target_path}.bak"
        shutil.copy2(target_path, adjacent_backup_path)

        if backup_dir:
            backup_dir = ensure_directory(os.path.abspath(backup_dir))
            versioned_backup_path = _build_versioned_backup_path(target_path, backup_dir)
            shutil.copy2(target_path, versioned_backup_path)
            _prune_versioned_backups(target_path, backup_dir, keep_count)

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
    }


def write_text_with_backup(target_path, text, backup_dir=None, keep_count=10, encoding="utf-8"):
    target_path = os.path.abspath(target_path)
    target_dir = os.path.dirname(target_path) or os.path.abspath(".")
    ensure_directory(target_dir)

    adjacent_backup_path = None
    versioned_backup_path = None

    if os.path.exists(target_path):
        adjacent_backup_path = f"{target_path}.bak"
        shutil.copy2(target_path, adjacent_backup_path)

        if backup_dir:
            backup_dir = ensure_directory(os.path.abspath(backup_dir))
            versioned_backup_path = _build_versioned_backup_path(target_path, backup_dir)
            shutil.copy2(target_path, versioned_backup_path)
            _prune_versioned_backups(target_path, backup_dir, keep_count)

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
    }