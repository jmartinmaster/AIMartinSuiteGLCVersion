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
import copy
import json
import os

from cryptography.fernet import Fernet, InvalidToken

from app.persistence import write_json_with_backup
from app.utils import ensure_external_data_directory, external_data_path

__module_name__ = "Security Storage"
__version__ = "1.0.0"

SECURITY_DIRECTORY_NAME = "security"
SECURITY_ENVELOPE_ENCODING = "fernet-json-v1"
SECURITY_KEY_FILE_NAME = "vaults.key"


def security_data_path(relative_path=""):
    normalized_relative_path = str(relative_path or "").strip().replace("\\", "/").lstrip("/")
    if not normalized_relative_path:
        return external_data_path(SECURITY_DIRECTORY_NAME)
    return external_data_path(os.path.join(SECURITY_DIRECTORY_NAME, normalized_relative_path))


def ensure_security_directory(relative_path=""):
    normalized_relative_path = str(relative_path or "").strip().replace("\\", "/").lstrip("/")
    if not normalized_relative_path:
        return ensure_external_data_directory(SECURITY_DIRECTORY_NAME)
    return ensure_external_data_directory(os.path.join(SECURITY_DIRECTORY_NAME, normalized_relative_path))


def security_key_path():
    ensure_security_directory()
    return security_data_path(SECURITY_KEY_FILE_NAME)


def get_or_create_security_key(key_path=None):
    key_path = os.path.abspath(key_path or security_key_path())
    if os.path.exists(key_path):
        with open(key_path, "rb") as handle:
            key_bytes = handle.read().strip()
        if not key_bytes:
            raise ValueError("Vault encryption key file is empty.")
        Fernet(key_bytes)
        return key_bytes

    generated_key = Fernet.generate_key()
    temp_path = f"{key_path}.tmp"
    with open(temp_path, "wb") as handle:
        handle.write(generated_key)
    os.replace(temp_path, key_path)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return generated_key


def encrypt_security_payload(payload, key_path=None):
    if not isinstance(payload, (dict, list)):
        raise ValueError("Security payload must be a JSON-compatible dictionary or list.")
    fernet = Fernet(get_or_create_security_key(key_path=key_path))
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = fernet.encrypt(plaintext).decode("utf-8")
    return {
        "encoding": SECURITY_ENVELOPE_ENCODING,
        "ciphertext": ciphertext,
    }


def decrypt_security_payload(envelope, description="Security payload", key_path=None):
    if not isinstance(envelope, dict):
        raise ValueError(f"{description} envelope must be a dictionary.")
    if str(envelope.get("encoding") or "").strip().lower() != SECURITY_ENVELOPE_ENCODING:
        raise ValueError(f"Unsupported {description.lower()} encoding.")
    ciphertext = str(envelope.get("ciphertext") or "").strip()
    if not ciphertext:
        raise ValueError(f"{description} is missing ciphertext.")
    fernet = Fernet(get_or_create_security_key(key_path=key_path))
    try:
        plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError(f"{description} decryption failed: invalid token.") from exc
    payload = json.loads(plaintext.decode("utf-8"))
    if not isinstance(payload, (dict, list)):
        raise ValueError(f"{description} decrypted to an invalid format.")
    return payload


def write_encrypted_json_file(path, payload, backup_dir=None, keep_count=10, key_path=None):
    target_path = os.path.abspath(path)
    target_dir = os.path.dirname(target_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    envelope = encrypt_security_payload(payload, key_path=key_path)
    return write_json_with_backup(target_path, envelope, backup_dir=backup_dir, keep_count=keep_count)


def load_encrypted_json_file(
    path,
    *,
    default=None,
    description="Security payload",
    migrate_plaintext=True,
    backup_dir=None,
    keep_count=10,
    key_path=None,
):
    target_path = os.path.abspath(path)
    if not os.path.exists(target_path):
        return copy.deepcopy(default), False

    with open(target_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and str(payload.get("encoding") or "").strip().lower() == SECURITY_ENVELOPE_ENCODING:
        return decrypt_security_payload(payload, description=description, key_path=key_path), False
    if migrate_plaintext:
        write_encrypted_json_file(target_path, payload, backup_dir=backup_dir, keep_count=keep_count, key_path=key_path)
        return payload, True
    return payload, False
