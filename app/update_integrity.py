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

import hashlib
import os
from pathlib import Path, PurePosixPath

__module_name__ = "Update Integrity"
__version__ = "1.0.0"


TEXTUAL_PAYLOAD_EXTENSIONS = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def compute_sha256_hex(payload_bytes):
    return hashlib.sha256(payload_bytes).hexdigest()


def is_textual_payload(relative_path):
    extension = os.path.splitext(str(relative_path or "").strip().lower())[1]
    return extension in TEXTUAL_PAYLOAD_EXTENSIONS


def normalize_manifest_payload_bytes(payload_bytes, relative_path):
    if not is_textual_payload(relative_path):
        return payload_bytes
    try:
        payload_text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return payload_bytes
    normalized_text = payload_text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized_text.encode("utf-8")


def compute_manifest_payload_sha256(payload_bytes, relative_path):
    return compute_sha256_hex(normalize_manifest_payload_bytes(payload_bytes, relative_path))


def compute_manifest_file_sha256(file_path, relative_path=None):
    artifact_path = Path(file_path)
    repo_relative_path = relative_path or artifact_path.name
    return compute_manifest_payload_sha256(artifact_path.read_bytes(), repo_relative_path)


def compute_integrity_hashes(payload_bytes, relative_path):
    hashes = {compute_sha256_hex(payload_bytes)}
    normalized_bytes = normalize_manifest_payload_bytes(payload_bytes, relative_path)
    hashes.add(compute_sha256_hex(normalized_bytes))
    if normalized_bytes != payload_bytes:
        try:
            normalized_text = normalized_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return hashes
        hashes.add(compute_sha256_hex(normalized_text.replace("\n", "\r\n").encode("utf-8")))
    return hashes


def payload_matches_expected_hash(expected_hash, payload_bytes, relative_path):
    normalized_expected = str(expected_hash or "").strip().lower()
    return normalized_expected in compute_integrity_hashes(payload_bytes, relative_path)


def verify_expected_hash(expected_hash, payload_bytes, relative_path):
    normalized_expected = str(expected_hash or "").strip().lower()
    actual_hash = compute_sha256_hex(payload_bytes)
    if payload_matches_expected_hash(normalized_expected, payload_bytes, relative_path):
        return actual_hash
    raise RuntimeError(
        f"Integrity check failed for {relative_path}. Expected {normalized_expected}, got {actual_hash}."
    )


def is_module_manifest_artifact(relative_path):
    normalized_path = str(relative_path or "").replace("\\", "/").lstrip("/")
    return normalized_path.startswith("app/")


def verify_manifest_artifacts_against_source(manifest_payload, repo_root, module_only=False):
    artifacts = manifest_payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise RuntimeError("Manifest payload is missing a valid 'artifacts' object.")

    validated_count = 0
    normalized_repo_root = Path(repo_root)
    for relative_path, artifact_meta in artifacts.items():
        if module_only and not is_module_manifest_artifact(relative_path):
            continue
        if not isinstance(artifact_meta, dict):
            raise RuntimeError(f"Manifest entry for {relative_path} is not a valid object.")
        expected_hash = artifact_meta.get("sha256")
        if not expected_hash:
            raise RuntimeError(f"Manifest entry for {relative_path} is missing a sha256 value.")
        artifact_path = normalized_repo_root / PurePosixPath(str(relative_path).replace("\\", "/"))
        if not artifact_path.exists() or not artifact_path.is_file():
            raise RuntimeError(f"Manifest artifact path is missing from the repo: {relative_path}.")
        actual_hash = compute_manifest_file_sha256(artifact_path, relative_path=relative_path)
        if str(expected_hash).strip().lower() != actual_hash:
            raise RuntimeError(
                f"Manifest/source mismatch for {relative_path}. Expected {expected_hash}, got {actual_hash}."
            )
        validated_count += 1
    return validated_count
