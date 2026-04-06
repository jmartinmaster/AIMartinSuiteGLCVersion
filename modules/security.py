# The Martin Suite (GLC Edition)
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

import base64
import ctypes
import hashlib
import json
import os
import re
import secrets
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog

import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
from app_identity import DEFAULT_UPDATE_REPOSITORY_URL

from modules.persistence import write_json_with_backup
from modules.utils import ensure_external_directory, external_path

END = tk.END
PBYTE = ctypes.POINTER(ctypes.c_ubyte)

__module_name__ = "Security Manager"
__version__ = "2.1.0"

SECURITY_ROOT_RELATIVE_PATH = os.path.join("data", "security")
VAULT_DIRECTORY_RELATIVE_PATH = os.path.join(SECURITY_ROOT_RELATIVE_PATH, "vaults")
SECURITY_SETTINGS_RELATIVE_PATH = os.path.join(SECURITY_ROOT_RELATIVE_PATH, "security_settings.json")
SECURITY_BACKUP_ROOT_RELATIVE_PATH = os.path.join("data", "backups", "security")
SETTINGS_BACKUP_ROOT_RELATIVE_PATH = os.path.join("data", "backups", "settings")
PBKDF2_ITERATIONS = 240000
GENERAL_USER_LIMIT = 9
ADMIN_USER_LIMIT = 3
DEVELOPER_USER_LIMIT = 1
VAULT_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
LEGACY_VAULT_PATH = external_path(".vault")
WEBAUTHN_HASH_ALGORITHM_SHA_256 = "SHA-256"
WEBAUTHN_CREDENTIAL_TYPE_PUBLIC_KEY = "public-key"
WEBAUTHN_RP_ENTITY_INFORMATION_CURRENT_VERSION = 1
WEBAUTHN_USER_ENTITY_INFORMATION_CURRENT_VERSION = 1
WEBAUTHN_CLIENT_DATA_CURRENT_VERSION = 1
WEBAUTHN_COSE_CREDENTIAL_PARAMETER_CURRENT_VERSION = 1
WEBAUTHN_CREDENTIAL_CURRENT_VERSION = 1
WEBAUTHN_AUTHENTICATOR_MAKE_CREDENTIAL_OPTIONS_VERSION_1 = 1
WEBAUTHN_AUTHENTICATOR_GET_ASSERTION_OPTIONS_VERSION_1 = 1
WEBAUTHN_COSE_ALGORITHM_ECDSA_P256_WITH_SHA256 = -7
WEBAUTHN_COSE_ALGORITHM_RSASSA_PKCS1_V1_5_WITH_SHA256 = -257
WEBAUTHN_AUTHENTICATOR_ATTACHMENT_CROSS_PLATFORM = 2
WEBAUTHN_USER_VERIFICATION_REQUIREMENT_DISCOURAGED = 3
WEBAUTHN_ATTESTATION_CONVEYANCE_PREFERENCE_NONE = 1

FORWARD_FACING_MODULES = [
    {"module_name": "production_log", "label": "Production Log", "description": "Open the production logging screen."},
    {"module_name": "recovery_viewer", "label": "Recovery Viewer", "description": "Open backup and recovery tools."},
    {"module_name": "layout_manager", "label": "Layout Manager", "description": "Open and edit layout configuration."},
    {"module_name": "rate_manager", "label": "Rate Manager", "description": "Open and edit production rates."},
    {"module_name": "settings_manager", "label": "Settings Manager", "description": "Open application settings."},
    {"module_name": "update_manager", "label": "Update Manager", "description": "Open update workflows and version tools."},
]


class WEBAUTHN_EXTENSION(ctypes.Structure):
    _fields_ = [
        ("pwszExtensionIdentifier", ctypes.c_wchar_p),
        ("cbExtension", ctypes.c_uint32),
        ("pvExtension", ctypes.c_void_p),
    ]


class WEBAUTHN_EXTENSIONS(ctypes.Structure):
    _fields_ = [
        ("cExtensions", ctypes.c_uint32),
        ("pExtensions", ctypes.POINTER(WEBAUTHN_EXTENSION)),
    ]


class WEBAUTHN_CLIENT_DATA(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("cbClientDataJSON", ctypes.c_uint32),
        ("pbClientDataJSON", PBYTE),
        ("pwszHashAlgId", ctypes.c_wchar_p),
    ]


class WEBAUTHN_RP_ENTITY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("pwszId", ctypes.c_wchar_p),
        ("pwszName", ctypes.c_wchar_p),
        ("pwszIcon", ctypes.c_wchar_p),
    ]


class WEBAUTHN_USER_ENTITY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("cbId", ctypes.c_uint32),
        ("pbId", PBYTE),
        ("pwszName", ctypes.c_wchar_p),
        ("pwszIcon", ctypes.c_wchar_p),
        ("pwszDisplayName", ctypes.c_wchar_p),
    ]


class WEBAUTHN_COSE_CREDENTIAL_PARAMETER(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("pwszCredentialType", ctypes.c_wchar_p),
        ("lAlg", ctypes.c_long),
    ]


class WEBAUTHN_COSE_CREDENTIAL_PARAMETERS(ctypes.Structure):
    _fields_ = [
        ("cCredentialParameters", ctypes.c_uint32),
        ("pCredentialParameters", ctypes.POINTER(WEBAUTHN_COSE_CREDENTIAL_PARAMETER)),
    ]


class WEBAUTHN_CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("cbId", ctypes.c_uint32),
        ("pbId", PBYTE),
        ("pwszCredentialType", ctypes.c_wchar_p),
    ]


class WEBAUTHN_CREDENTIALS(ctypes.Structure):
    _fields_ = [
        ("cCredentials", ctypes.c_uint32),
        ("pCredentials", ctypes.POINTER(WEBAUTHN_CREDENTIAL)),
    ]


class WEBAUTHN_AUTHENTICATOR_MAKE_CREDENTIAL_OPTIONS(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("dwTimeoutMilliseconds", ctypes.c_uint32),
        ("CredentialList", WEBAUTHN_CREDENTIALS),
        ("Extensions", WEBAUTHN_EXTENSIONS),
        ("dwAuthenticatorAttachment", ctypes.c_uint32),
        ("bRequireResidentKey", ctypes.c_int),
        ("dwUserVerificationRequirement", ctypes.c_uint32),
        ("dwAttestationConveyancePreference", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("pCancellationId", ctypes.c_void_p),
    ]


class WEBAUTHN_AUTHENTICATOR_GET_ASSERTION_OPTIONS(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("dwTimeoutMilliseconds", ctypes.c_uint32),
        ("CredentialList", WEBAUTHN_CREDENTIALS),
        ("Extensions", WEBAUTHN_EXTENSIONS),
        ("dwAuthenticatorAttachment", ctypes.c_uint32),
        ("dwUserVerificationRequirement", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("pwszU2fAppId", ctypes.c_wchar_p),
        ("pbU2fAppId", ctypes.c_void_p),
        ("pCancellationId", ctypes.c_void_p),
    ]


class WEBAUTHN_CREDENTIAL_ATTESTATION(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("pwszFormatType", ctypes.c_wchar_p),
        ("cbAuthenticatorData", ctypes.c_uint32),
        ("pbAuthenticatorData", PBYTE),
        ("cbAttestation", ctypes.c_uint32),
        ("pbAttestation", PBYTE),
        ("dwAttestationDecodeType", ctypes.c_uint32),
        ("pvAttestationDecode", ctypes.c_void_p),
        ("cbAttestationObject", ctypes.c_uint32),
        ("pbAttestationObject", PBYTE),
        ("cbCredentialId", ctypes.c_uint32),
        ("pbCredentialId", PBYTE),
        ("Extensions", WEBAUTHN_EXTENSIONS),
        ("dwUsedTransport", ctypes.c_uint32),
        ("bEpAtt", ctypes.c_int),
        ("bLargeBlobSupported", ctypes.c_int),
        ("bResidentKey", ctypes.c_int),
        ("bPrfEnabled", ctypes.c_int),
        ("cbUnsignedExtensionOutputs", ctypes.c_uint32),
        ("pbUnsignedExtensionOutputs", PBYTE),
        ("pHmacSecret", ctypes.c_void_p),
        ("bThirdPartyPayment", ctypes.c_int),
        ("dwTransports", ctypes.c_uint32),
        ("cbClientDataJSON", ctypes.c_uint32),
        ("pbClientDataJSON", PBYTE),
        ("cbRegistrationResponseJSON", ctypes.c_uint32),
        ("pbRegistrationResponseJSON", PBYTE),
    ]


class WEBAUTHN_ASSERTION(ctypes.Structure):
    _fields_ = [
        ("dwVersion", ctypes.c_uint32),
        ("cbAuthenticatorData", ctypes.c_uint32),
        ("pbAuthenticatorData", PBYTE),
        ("cbSignature", ctypes.c_uint32),
        ("pbSignature", PBYTE),
        ("Credential", WEBAUTHN_CREDENTIAL),
        ("cbUserId", ctypes.c_uint32),
        ("pbUserId", PBYTE),
        ("Extensions", WEBAUTHN_EXTENSIONS),
        ("cbCredLargeBlob", ctypes.c_uint32),
        ("pbCredLargeBlob", PBYTE),
        ("dwCredLargeBlobStatus", ctypes.c_uint32),
        ("pHmacSecret", ctypes.c_void_p),
        ("dwUsedTransport", ctypes.c_uint32),
        ("cbUnsignedExtensionOutputs", ctypes.c_uint32),
        ("pbUnsignedExtensionOutputs", PBYTE),
        ("cbClientDataJSON", ctypes.c_uint32),
        ("pbClientDataJSON", PBYTE),
        ("cbAuthenticationResponseJSON", ctypes.c_uint32),
        ("pbAuthenticationResponseJSON", PBYTE),
    ]

ACCESS_RIGHTS = [
    {
        "key": f"module:{entry['module_name']}",
        "label": entry["label"],
        "description": entry["description"],
    }
    for entry in FORWARD_FACING_MODULES
] + [
    {"key": "security:manage_vaults", "label": "Security Admin", "description": "Create vaults, change passwords, and manage YubiKey registration."},
]
ACCESS_RIGHTS_BY_KEY = {entry["key"]: entry for entry in ACCESS_RIGHTS}
ALL_ACCESS_RIGHT_KEYS = [entry["key"] for entry in ACCESS_RIGHTS]
MODULE_ACCESS_RIGHTS = {entry["module_name"]: f"module:{entry['module_name']}" for entry in FORWARD_FACING_MODULES}
ROLE_LIMITS = {"general": GENERAL_USER_LIMIT, "admin": ADMIN_USER_LIMIT, "developer": DEVELOPER_USER_LIMIT}
ROLE_DEFAULT_RIGHTS = {
    "general": ["module:production_log"],
    "admin": [entry["key"] for entry in ACCESS_RIGHTS],
    "developer": list(ALL_ACCESS_RIGHT_KEYS),
}


def _utc_timestamp():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize_rights(rights, role=None):
    normalized = []
    if isinstance(rights, str):
        rights = [part.strip() for part in rights.split(",")]
    if not isinstance(rights, (list, tuple, set)):
        rights = []
    for right in rights:
        right_key = str(right or "").strip()
        if right_key in ACCESS_RIGHTS_BY_KEY and right_key not in normalized:
            normalized.append(right_key)
    if role == "developer":
        return list(ALL_ACCESS_RIGHT_KEYS)
    return normalized


def _sanitize_vault_name(raw_value):
    text = str(raw_value or "").strip()
    text = VAULT_NAME_PATTERN.sub("_", text)
    text = text.strip("._-")
    return text[:64]


def _role_requires_password(role):
    return str(role or "general").strip().lower() in {"admin", "developer"}


def _default_security_settings():
    return {
        "version": 1,
        "non_secure_mode": False,
        "yubikey": {
            "label": "Developer YubiKey",
            "provider": "windows_webauthn",
            "windows_hello_required": True,
            "rp_id": "localhost",
            "origin": "https://localhost",
            "credential_id": "",
            "user_handle": "",
            "last_registered_at": None,
            "last_verified_at": None,
            "last_updated_at": None,
            "last_updated_by": "",
        },
    }


def _b64url_encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


def _b64url_decode(encoded_text):
    text = str(encoded_text or "").strip()
    if not text:
        return b""
    padding = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(text + padding)


class Gatekeeper:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Gatekeeper, cls).__new__(cls)
            cls._instance._session = None
        return cls._instance

    def _vault_directory(self):
        return ensure_external_directory(VAULT_DIRECTORY_RELATIVE_PATH)

    def _security_settings_path(self):
        ensure_external_directory(SECURITY_ROOT_RELATIVE_PATH)
        return external_path(SECURITY_SETTINGS_RELATIVE_PATH)

    def _security_backup_directory(self):
        return ensure_external_directory(os.path.join(SECURITY_BACKUP_ROOT_RELATIVE_PATH, "config"))

    def _vault_backup_directory(self):
        return ensure_external_directory(os.path.join(SECURITY_BACKUP_ROOT_RELATIVE_PATH, "vaults"))

    def _hash_password(self, password, salt_hex=None, iterations=PBKDF2_ITERATIONS):
        salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return {
            "hash_scheme": "pbkdf2_sha256",
            "password_salt": salt.hex(),
            "password_hash": derived.hex(),
            "password_iterations": int(iterations),
        }

    def _verify_password(self, vault_record, password):
        if not self._vault_requires_password(vault_record):
            return True
        scheme = str(vault_record.get("hash_scheme", "pbkdf2_sha256") or "pbkdf2_sha256")
        if scheme == "legacy_sha256":
            return hashlib.sha256(password.encode("utf-8")).hexdigest() == str(vault_record.get("password_hash", ""))
        salt_hex = str(vault_record.get("password_salt", "") or "")
        stored_hash = str(vault_record.get("password_hash", "") or "")
        iterations = int(vault_record.get("password_iterations", PBKDF2_ITERATIONS) or PBKDF2_ITERATIONS)
        if not salt_hex or not stored_hash:
            return False
        return self._hash_password(password, salt_hex=salt_hex, iterations=iterations)["password_hash"] == stored_hash

    def _vault_requires_password(self, vault_record):
        if not isinstance(vault_record, dict):
            return True
        stored_value = vault_record.get("password_required")
        if stored_value is None:
            return _role_requires_password(vault_record.get("role"))
        return bool(stored_value)

    def _load_security_settings(self):
        settings = _default_security_settings()
        path = self._security_settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass
        yubi = settings.get("yubikey")
        if not isinstance(yubi, dict):
            yubi = {}
        normalized_yubi = _default_security_settings()["yubikey"]
        normalized_yubi.update(yubi)
        normalized_yubi["label"] = str(normalized_yubi.get("label", "Developer YubiKey") or "Developer YubiKey").strip() or "Developer YubiKey"
        legacy_windows_auth_required = normalized_yubi.get("windows_auth_required", None)
        if legacy_windows_auth_required is not None and "windows_hello_required" not in yubi:
            normalized_yubi["windows_hello_required"] = bool(legacy_windows_auth_required)
        normalized_yubi["windows_hello_required"] = bool(normalized_yubi.get("windows_hello_required", True))
        normalized_yubi["provider"] = "windows_webauthn"
        normalized_yubi["rp_id"] = str(normalized_yubi.get("rp_id", "localhost") or "localhost").strip() or "localhost"
        normalized_yubi["origin"] = str(normalized_yubi.get("origin", "https://localhost") or "https://localhost").strip() or "https://localhost"
        normalized_yubi["credential_id"] = str(normalized_yubi.get("credential_id", "") or "").strip()
        normalized_yubi["user_handle"] = str(normalized_yubi.get("user_handle", "") or "").strip()
        normalized_yubi.pop("windows_auth_required", None)
        normalized_yubi.pop("windows_settings_uri", None)
        normalized_yubi.pop("registration_url", None)
        normalized_yubi.pop("verification_url", None)
        normalized_yubi.pop("serial", None)
        settings["yubikey"] = normalized_yubi
        return settings

    def _save_security_settings(self, settings_payload):
        write_json_with_backup(self._security_settings_path(), settings_payload, backup_dir=self._security_backup_directory(), keep_count=12)

    def is_non_secure_mode_enabled(self):
        return bool(self._load_security_settings().get("non_secure_mode", False))

    def set_non_secure_mode(self, enabled):
        settings = self._load_security_settings()
        settings["non_secure_mode"] = bool(enabled)
        self._save_security_settings(settings)
        if not settings["non_secure_mode"] and self._session and self._session_role() not in {"admin", "developer"}:
            self.logout()
        return settings["non_secure_mode"]

    def _vault_path_for_name(self, vault_name):
        return os.path.join(self._vault_directory(), f"{_sanitize_vault_name(vault_name)}.vault")

    def _normalize_vault_record(self, record, path):
        normalized = dict(record or {})
        vault_name = str(normalized.get("vault_name") or os.path.splitext(os.path.basename(path))[0]).strip()
        normalized["vault_name"] = vault_name
        normalized["display_name"] = str(normalized.get("display_name") or vault_name).strip() or vault_name
        role = str(normalized.get("role", "general") or "general").strip().lower()
        if role not in ROLE_LIMITS:
            role = "general"
        normalized["role"] = role
        normalized["enabled"] = bool(normalized.get("enabled", True))
        normalized["requires_yubikey"] = bool(normalized.get("requires_yubikey", role == "developer"))
        normalized["password_required"] = bool(normalized.get("password_required", _role_requires_password(role)))
        normalized["password_iterations"] = int(normalized.get("password_iterations", PBKDF2_ITERATIONS) or PBKDF2_ITERATIONS)
        normalized["rights"] = _normalize_rights(normalized.get("rights", ROLE_DEFAULT_RIGHTS.get(role, [])), role=role)
        normalized["path"] = path
        normalized["file_name"] = os.path.basename(path)
        normalized["version"] = int(normalized.get("version", 2) or 2)
        return normalized

    def _list_vault_paths(self):
        vault_dir = self._vault_directory()
        return [os.path.join(vault_dir, file_name) for file_name in sorted(os.listdir(vault_dir)) if file_name.lower().endswith(".vault")]

    def _load_vault(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return self._normalize_vault_record(payload, path)

    def _import_legacy_vault_if_needed(self):
        if self._list_vault_paths() or not os.path.exists(LEGACY_VAULT_PATH):
            return
        try:
            with open(LEGACY_VAULT_PATH, "r", encoding="utf-8") as handle:
                legacy_hash = handle.read().strip()
        except OSError:
            return
        if not legacy_hash:
            return
        payload = {
            "version": 1,
            "vault_name": "legacy_admin",
            "display_name": "Legacy Admin",
            "role": "admin",
            "enabled": True,
            "requires_yubikey": False,
            "rights": ROLE_DEFAULT_RIGHTS["admin"],
            "hash_scheme": "legacy_sha256",
            "password_hash": legacy_hash,
            "password_salt": "",
            "password_iterations": 0,
            "created_at": _utc_timestamp(),
            "updated_at": _utc_timestamp(),
            "imported_from_legacy_vault": True,
        }
        self._write_vault_payload(payload, existing_path=None)

    def list_vaults(self):
        self._import_legacy_vault_if_needed()
        vaults = []
        for path in self._list_vault_paths():
            vault_record = self._load_vault(path)
            if vault_record is not None:
                vaults.append(vault_record)
        return vaults

    def _find_vault(self, vault_name):
        for vault_record in self.list_vaults():
            if vault_record["vault_name"] == vault_name:
                return vault_record
        return None

    def _count_role(self, role, exclude_name=None):
        total = 0
        for vault_record in self.list_vaults():
            if exclude_name and vault_record["vault_name"] == exclude_name:
                continue
            if vault_record.get("role") == role:
                total += 1
        return total

    def _validate_role_limit(self, role, exclude_name=None):
        limit = ROLE_LIMITS.get(role)
        if limit and self._count_role(role, exclude_name=exclude_name) >= limit:
            raise ValueError(f"{role.title()} vaults are limited to {limit}.")

    def _write_vault_payload(self, payload, existing_path=None):
        target_path = self._vault_path_for_name(payload.get("vault_name"))
        write_json_with_backup(target_path, payload, backup_dir=self._vault_backup_directory(), keep_count=20)
        if existing_path and os.path.abspath(existing_path) != os.path.abspath(target_path) and os.path.exists(existing_path):
            os.remove(existing_path)
        return target_path

    def _update_session_from_vault(self, vault_record):
        if self._session and self._session.get("vault_name") == vault_record.get("vault_name"):
            self._session.update({"display_name": vault_record.get("display_name", vault_record.get("vault_name")), "role": vault_record.get("role"), "rights": list(vault_record.get("rights", []))})

    def create_or_update_vault(self, vault_name, role, rights, password=None, enabled=True, requires_yubikey=False, existing_name=None):
        normalized_name = _sanitize_vault_name(vault_name)
        if not normalized_name:
            raise ValueError("Vault name is required.")
        role_key = str(role or "general").strip().lower()
        if role_key not in ROLE_LIMITS:
            raise ValueError("Role must be general, admin, or developer.")
        existing_record = self._find_vault(existing_name or normalized_name)
        if existing_record is None:
            self._validate_role_limit(role_key)
        elif existing_record.get("role") != role_key:
            self._validate_role_limit(role_key, exclude_name=existing_record.get("vault_name"))
        normalized_rights = list(ALL_ACCESS_RIGHT_KEYS) if role_key == "developer" else _normalize_rights(rights, role=role_key)
        if not normalized_rights:
            raise ValueError("At least one access right must be selected.")
        payload = {
            "version": 2,
            "vault_name": normalized_name,
            "display_name": normalized_name,
            "role": role_key,
            "enabled": bool(enabled),
            "requires_yubikey": True if role_key == "developer" else bool(requires_yubikey),
            "password_required": _role_requires_password(role_key),
            "rights": normalized_rights,
            "created_at": existing_record.get("created_at") if existing_record else _utc_timestamp(),
            "updated_at": _utc_timestamp(),
        }
        if not payload["password_required"]:
            payload.update(
                {
                    "hash_scheme": "",
                    "password_hash": "",
                    "password_salt": "",
                    "password_iterations": 0,
                }
            )
        elif existing_record:
            payload["hash_scheme"] = existing_record.get("hash_scheme", "pbkdf2_sha256")
            payload["password_hash"] = existing_record.get("password_hash", "")
            payload["password_salt"] = existing_record.get("password_salt", "")
            payload["password_iterations"] = int(existing_record.get("password_iterations", PBKDF2_ITERATIONS) or PBKDF2_ITERATIONS)
        elif password:
            payload.update(self._hash_password(password))
        else:
            raise ValueError("A password is required for a new vault.")
        written_path = self._write_vault_payload(payload, existing_path=existing_record.get("path") if existing_record else None)
        self._update_session_from_vault(self._normalize_vault_record(payload, written_path))
        return written_path

    def delete_vault(self, vault_name):
        vault_record = self._find_vault(vault_name)
        if vault_record is None:
            raise ValueError("Vault not found.")
        target_role = str(vault_record.get("role", "general") or "general").strip().lower()
        if target_role == "developer" and not self._developer_session_active():
            raise ValueError("Only a logged-in developer can delete a developer vault.")
        os.remove(vault_record["path"])
        if self._session and self._session.get("vault_name") == vault_name:
            self.logout()

    def change_vault_password(self, vault_name, new_password):
        vault_record = self._find_vault(vault_name)
        if vault_record is None:
            raise ValueError("Vault not found.")
        if not self._vault_requires_password(vault_record):
            raise ValueError("General vaults do not use passwords.")
        payload = dict(vault_record)
        payload.update(self._hash_password(new_password))
        payload["updated_at"] = _utc_timestamp()
        payload.pop("path", None)
        payload.pop("file_name", None)
        written_path = self._write_vault_payload(payload, existing_path=vault_record.get("path"))
        self._update_session_from_vault(self._normalize_vault_record(payload, written_path))
        return written_path

    def logout(self):
        self._session = None

    def get_session_summary(self):
        if not self._session:
            return "Locked"
        role_text = str(self._session.get("role", "general") or "general").title()
        return f"{self._session.get('display_name', self._session.get('vault_name', 'Unknown'))} ({role_text})"

    def _session_role(self):
        if not self._session:
            return None
        return str(self._session.get("role") or "").strip().lower() or None

    def _developer_session_active(self):
        return self._session_role() == "developer"

    def developer_login(self, parent=None, reason=None, force_reauth=True):
        if not self._ensure_bootstrap_vault(parent=parent):
            return False
        return self._prompt_for_vault_login(
            required_right=None,
            parent=parent,
            reason=reason or "Developer login is required to access developer tools.",
            force_reauth=force_reauth,
            allowed_roles={"developer"},
        )

    def _load_app_settings(self):
        settings_path = external_path("settings.json")
        if not os.path.exists(settings_path):
            return {}
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}

    def _save_app_settings(self, settings_payload):
        write_json_with_backup(
            external_path("settings.json"),
            settings_payload,
            backup_dir=external_path(SETTINGS_BACKUP_ROOT_RELATIVE_PATH),
            keep_count=12,
        )

    def _get_module_editor_options(self, dispatcher):
        if dispatcher is None or not os.path.isdir(dispatcher.modules_path):
            return []
        hidden_modules = {"__init__", "app_logging", "downtime_codes", "persistence", "splash", "theme_manager", "utils", "data_handler"}
        options = []
        for file_name in sorted(os.listdir(dispatcher.modules_path)):
            if not file_name.endswith(".py"):
                continue
            module_name = os.path.splitext(file_name)[0]
            if module_name in hidden_modules:
                continue
            options.append((module_name.replace("_", " ").title(), module_name))
        return options

    def open_update_configuration_dialog(self, parent=None, dispatcher=None):
        if not self._developer_session_active():
            Messagebox.show_info("Only a logged-in developer can edit the update repository configuration.", "Update Configuration")
            return False

        settings_payload = self._load_app_settings()
        top = tb.Toplevel(parent)
        top.title("Update Configuration")
        top.geometry("700x260")
        top.minsize(560, 220)

        container = tb.Frame(top, padding=18)
        container.pack(fill=tk.BOTH, expand=True)

        tb.Label(container, text="Update Configuration", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tb.Label(
            container,
            text="Set the GitHub repository URL used by Update Manager. Leave it blank to keep update checks and payload restores disabled.",
            bootstyle="secondary",
            justify=tk.LEFT,
            wraplength=620,
        ).pack(anchor=tk.W, pady=(4, 14))

        url_var = tk.StringVar(value=str(settings_payload.get("update_repository_url", DEFAULT_UPDATE_REPOSITORY_URL) or "").strip())
        row = tb.Frame(container)
        row.pack(fill=tk.X)
        tb.Label(row, text="Repository URL", width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 12))
        url_entry = tb.Entry(row, textvariable=url_var)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        note_var = tk.StringVar(value="Blank keeps updates disabled.")
        tb.Label(container, textvariable=note_var, bootstyle="secondary", justify=tk.LEFT, wraplength=620).pack(anchor=tk.W, pady=(10, 0))

        def save_update_configuration():
            settings_payload["update_repository_url"] = str(url_var.get() or "").strip()
            try:
                self._save_app_settings(settings_payload)
            except Exception as exc:
                Messagebox.show_error(f"Could not save update configuration: {exc}", "Update Configuration")
                return
            if dispatcher is not None:
                dispatcher.refresh_runtime_settings()
                dispatcher.show_toast("Security", "Saved update repository configuration.", "success")
            top.destroy()

        actions = tb.Frame(container)
        actions.pack(fill=tk.X, pady=(18, 0))
        tb.Button(actions, text="Clear", bootstyle="secondary", command=lambda: url_var.set("")).pack(side=tk.LEFT)
        tb.Button(actions, text="Cancel", bootstyle="secondary", command=top.destroy).pack(side=tk.RIGHT)
        tb.Button(actions, text="Save Update URL", bootstyle="success", command=save_update_configuration).pack(side=tk.RIGHT, padx=(0, 8))
        url_entry.focus_set()
        return True

    def open_external_module_editor_dialog(self, parent=None, dispatcher=None):
        if not self._developer_session_active():
            Messagebox.show_info("Only a logged-in developer can edit external module overrides.", "Module Editor")
            return False
        module_options = self._get_module_editor_options(dispatcher)
        if not module_options:
            Messagebox.show_info("No editable modules are available.", "Module Editor")
            return False

        top = tb.Toplevel(parent)
        top.title("External Module Editor")
        top.geometry("920x700")
        top.minsize(760, 540)

        container = tb.Frame(top, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        tb.Label(container, text="External Module Editor", font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tb.Label(
            container,
            text="This edits module files in the external modules folder beside the app. Saving here creates or updates external overrides and does not modify the bundled internal module files.",
            bootstyle="danger",
            justify=tk.LEFT,
            wraplength=760,
        ).pack(anchor=tk.W, pady=(4, 14))

        selector_row = tb.Frame(container)
        selector_row.pack(fill=tk.X, pady=(0, 8))
        tb.Label(selector_row, text="Module", width=14).pack(side=tk.LEFT)
        module_display_var = tk.StringVar(value=module_options[0][0])
        option_lookup = {display_name: module_name for display_name, module_name in module_options}
        module_combo = tb.Combobox(selector_row, values=list(option_lookup), textvariable=module_display_var, state="readonly")
        module_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        path_var = tk.StringVar(value="")
        source_var = tk.StringVar(value="")

        path_row = tb.Frame(container)
        path_row.pack(fill=tk.X, pady=(0, 6))
        tb.Label(path_row, text="External Path", width=14).pack(side=tk.LEFT)
        tb.Entry(path_row, textvariable=path_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True)

        source_row = tb.Frame(container)
        source_row.pack(fill=tk.X, pady=(0, 12))
        tb.Label(source_row, textvariable=source_var, bootstyle="secondary", justify=tk.LEFT, wraplength=760).pack(anchor=tk.W)

        editor_frame = tb.Frame(container)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        text_widget = tk.Text(editor_frame, wrap="none", font=("Consolas", 10), undo=True)
        text_widget.grid(row=0, column=0, sticky="nsew")
        y_scroll = tb.Scrollbar(editor_frame, orient=tk.VERTICAL, command=text_widget.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = tb.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        text_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        def get_selected_module_name():
            return option_lookup.get(module_display_var.get(), module_options[0][1])

        def get_external_target_path(module_name):
            return os.path.join(dispatcher.external_modules_path, f"{module_name}.py")

        def get_bundled_module_path(module_name):
            return os.path.join(dispatcher.modules_path, f"{module_name}.py")

        def load_selected_module(_event=None):
            module_name = get_selected_module_name()
            override_path = get_external_target_path(module_name)
            bundled_path = get_bundled_module_path(module_name)
            source_path = override_path if os.path.exists(override_path) else bundled_path
            path_var.set(override_path)
            if os.path.exists(override_path):
                source_var.set("Editing existing external override. Saving updates the external module file directly.")
            else:
                source_var.set("No external override exists yet. Saving will create one in the external modules folder using the content shown here.")
            try:
                with open(source_path, "r", encoding="utf-8") as handle:
                    module_text = handle.read()
            except Exception as exc:
                Messagebox.show_error(f"Could not load module text: {exc}", "Module Editor")
                return
            text_widget.delete("1.0", END)
            text_widget.insert("1.0", module_text)

        def save_module_override():
            module_name = get_selected_module_name()
            dispatcher.ensure_external_modules_package()
            target_path = get_external_target_path(module_name)
            temp_path = f"{target_path}.tmp"
            module_text = text_widget.get("1.0", END)
            try:
                with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(module_text)
                os.replace(temp_path, target_path)
            except Exception as exc:
                Messagebox.show_error(f"Could not save external module override: {exc}", "Module Editor")
                return
            dispatcher.reset_module_import_state(keep_active=True)
            dispatcher.refresh_runtime_settings()
            dispatcher.show_toast("Module Editor", f"Saved external override for {module_name}.", "success")
            load_selected_module()

        def delete_module_override():
            module_name = get_selected_module_name()
            target_path = get_external_target_path(module_name)
            if not os.path.exists(target_path):
                Messagebox.show_info("No external override exists for this module.", "Module Editor")
                return
            if not Messagebox.okcancel(f"Delete the external override for {module_name}?", "Delete Module Override"):
                return
            try:
                os.remove(target_path)
            except Exception as exc:
                Messagebox.show_error(f"Could not delete external module override: {exc}", "Module Editor")
                return
            dispatcher.reset_module_import_state(keep_active=True)
            dispatcher.refresh_runtime_settings()
            dispatcher.show_toast("Module Editor", f"Removed external override for {module_name}.", "info")
            load_selected_module()

        def open_module_folder():
            dispatcher.ensure_external_modules_package()
            try:
                os.startfile(dispatcher.external_modules_path)
            except Exception as exc:
                Messagebox.show_error(f"Could not open external modules folder: {exc}", "Module Editor")

        action_row = tb.Frame(container)
        action_row.pack(fill=tk.X, pady=(12, 0))
        tb.Button(action_row, text="Reload Selected", bootstyle="secondary", command=load_selected_module).pack(side=tk.LEFT)
        tb.Button(action_row, text="Open Module Folder", bootstyle="info", command=open_module_folder).pack(side=tk.LEFT, padx=(8, 0))
        tb.Button(action_row, text="Delete Override", bootstyle="danger", command=delete_module_override).pack(side=tk.RIGHT)
        tb.Button(action_row, text="Save Override", bootstyle="success", command=save_module_override).pack(side=tk.RIGHT, padx=(0, 8))
        module_combo.bind("<<ComboboxSelected>>", load_selected_module)
        load_selected_module()
        return True

    def has_right(self, right_key):
        if not right_key:
            return True
        if not self._session:
            return False
        return right_key in self._session.get("rights", [])

    def requires_module_access(self, module_name):
        return MODULE_ACCESS_RIGHTS.get(module_name)

    def _prompt_for_new_password(self, parent=None, title="Change Password"):
        first = simpledialog.askstring(title, "Enter the new password:", show="*", parent=parent)
        if not first:
            return None
        second = simpledialog.askstring(title, "Confirm the new password:", show="*", parent=parent)
        if second is None:
            return None
        if first != second:
            Messagebox.show_error("Passwords did not match.", title)
            return None
        return first

    def _ensure_bootstrap_vault(self, parent=None):
        if self.list_vaults():
            return True
        if not messagebox.askyesno("Security Setup", "No vault files are configured yet. Create the first admin vault now?", parent=parent):
            return False
        vault_name = simpledialog.askstring("Create Admin Vault", "Name for the first admin vault:", initialvalue="admin_1", parent=parent)
        if vault_name is None:
            return False
        new_password = self._prompt_for_new_password(parent=parent, title="Create Admin Password")
        if not new_password:
            return False
        self.create_or_update_vault(vault_name=vault_name, role="admin", rights=ROLE_DEFAULT_RIGHTS["admin"], password=new_password, enabled=True, requires_yubikey=False)
        messagebox.showinfo("Security Setup", f"Created admin vault '{_sanitize_vault_name(vault_name) or 'admin_1'}'.", parent=parent)
        return True

    def _get_webauthn_api(self):
        cached_api = getattr(self, "_webauthn_api", None)
        if cached_api is not None:
            return cached_api
        if os.name != "nt":
            raise RuntimeError("Native Windows security-key verification is only available on Windows.")
        try:
            dll = ctypes.WinDLL("webauthn")
        except Exception as exc:
            raise RuntimeError(f"Could not load webauthn.dll: {exc}") from exc

        get_version = dll.WebAuthNGetApiVersionNumber
        get_version.argtypes = []
        get_version.restype = ctypes.c_uint32

        get_error_name = dll.WebAuthNGetErrorName
        get_error_name.argtypes = [ctypes.c_long]
        get_error_name.restype = ctypes.c_wchar_p

        make_credential = dll.WebAuthNAuthenticatorMakeCredential
        make_credential.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(WEBAUTHN_RP_ENTITY_INFORMATION),
            ctypes.POINTER(WEBAUTHN_USER_ENTITY_INFORMATION),
            ctypes.POINTER(WEBAUTHN_COSE_CREDENTIAL_PARAMETERS),
            ctypes.POINTER(WEBAUTHN_CLIENT_DATA),
            ctypes.POINTER(WEBAUTHN_AUTHENTICATOR_MAKE_CREDENTIAL_OPTIONS),
            ctypes.POINTER(ctypes.POINTER(WEBAUTHN_CREDENTIAL_ATTESTATION)),
        ]
        make_credential.restype = ctypes.c_long

        get_assertion = dll.WebAuthNAuthenticatorGetAssertion
        get_assertion.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.POINTER(WEBAUTHN_CLIENT_DATA),
            ctypes.POINTER(WEBAUTHN_AUTHENTICATOR_GET_ASSERTION_OPTIONS),
            ctypes.POINTER(ctypes.POINTER(WEBAUTHN_ASSERTION)),
        ]
        get_assertion.restype = ctypes.c_long

        free_attestation = dll.WebAuthNFreeCredentialAttestation
        free_attestation.argtypes = [ctypes.POINTER(WEBAUTHN_CREDENTIAL_ATTESTATION)]
        free_attestation.restype = None

        free_assertion = dll.WebAuthNFreeAssertion
        free_assertion.argtypes = [ctypes.POINTER(WEBAUTHN_ASSERTION)]
        free_assertion.restype = None

        cached_api = {
            "dll": dll,
            "version": int(get_version()),
            "get_error_name": get_error_name,
            "make_credential": make_credential,
            "get_assertion": get_assertion,
            "free_attestation": free_attestation,
            "free_assertion": free_assertion,
        }
        self._webauthn_api = cached_api
        return cached_api

    def _webauthn_error_text(self, hresult):
        try:
            api = self._get_webauthn_api()
            error_name = api["get_error_name"](int(hresult))
            if error_name:
                return f"{error_name} (0x{int(hresult) & 0xFFFFFFFF:08X})"
        except Exception:
            pass
        return f"0x{int(hresult) & 0xFFFFFFFF:08X}"

    def _resolve_webauthn_hwnd(self, parent=None):
        widget = parent or getattr(self, "_active_security_parent", None)
        if widget is not None:
            try:
                return ctypes.c_void_p(int(widget.winfo_id()))
            except Exception:
                return ctypes.c_void_p(0)
        return ctypes.c_void_p(0)

    def _empty_extensions(self):
        return WEBAUTHN_EXTENSIONS(0, None)

    def _empty_credentials(self):
        return WEBAUTHN_CREDENTIALS(0, None)

    def _build_client_data(self, operation_type, origin):
        challenge_bytes = secrets.token_bytes(32)
        client_data_json = json.dumps(
            {
                "type": operation_type,
                "challenge": _b64url_encode(challenge_bytes),
                "origin": origin,
                "crossOrigin": False,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        client_data_buffer = (ctypes.c_ubyte * len(client_data_json)).from_buffer_copy(client_data_json)
        client_data = WEBAUTHN_CLIENT_DATA(
            WEBAUTHN_CLIENT_DATA_CURRENT_VERSION,
            len(client_data_json),
            ctypes.cast(client_data_buffer, PBYTE),
            WEBAUTHN_HASH_ALGORITHM_SHA_256,
        )
        return client_data, client_data_buffer

    def _native_yubikey_settings(self):
        return self._load_security_settings().get("yubikey", {})

    def _native_yubikey_registered(self):
        return bool(self._native_yubikey_settings().get("credential_id"))

    def _save_native_yubikey_registration(self, credential_id_bytes, user_handle_bytes, label=None):
        settings = self._load_security_settings()
        yubi = settings["yubikey"]
        yubi["provider"] = "windows_webauthn"
        yubi["credential_id"] = _b64url_encode(credential_id_bytes)
        yubi["user_handle"] = _b64url_encode(user_handle_bytes)
        yubi["label"] = str(label or yubi.get("label") or "Developer YubiKey").strip() or "Developer YubiKey"
        yubi["last_registered_at"] = _utc_timestamp()
        yubi["last_updated_at"] = yubi["last_registered_at"]
        yubi["last_updated_by"] = os.environ.get("USERNAME") or os.environ.get("USER") or "Unknown"
        self._save_security_settings(settings)
        return settings

    def _mark_native_yubikey_verified(self):
        settings = self._load_security_settings()
        settings["yubikey"]["last_verified_at"] = _utc_timestamp()
        self._save_security_settings(settings)
        return settings

    def register_native_yubikey(self, parent=None, label=None):
        api = self._get_webauthn_api()
        yubi = self._native_yubikey_settings()
        hwnd = self._resolve_webauthn_hwnd(parent)
        user_handle_bytes = _b64url_decode(yubi.get("user_handle")) or secrets.token_bytes(32)
        user_handle_buffer = (ctypes.c_ubyte * len(user_handle_bytes)).from_buffer_copy(user_handle_bytes)
        rp_info = WEBAUTHN_RP_ENTITY_INFORMATION(
            WEBAUTHN_RP_ENTITY_INFORMATION_CURRENT_VERSION,
            yubi.get("rp_id", "localhost"),
            "The Martin Suite",
            None,
        )
        user_label = str(label or yubi.get("label") or "Developer YubiKey").strip() or "Developer YubiKey"
        user_info = WEBAUTHN_USER_ENTITY_INFORMATION(
            WEBAUTHN_USER_ENTITY_INFORMATION_CURRENT_VERSION,
            len(user_handle_bytes),
            ctypes.cast(user_handle_buffer, PBYTE),
            user_label,
            None,
            user_label,
        )
        cose_array = (WEBAUTHN_COSE_CREDENTIAL_PARAMETER * 2)(
            WEBAUTHN_COSE_CREDENTIAL_PARAMETER(
                WEBAUTHN_COSE_CREDENTIAL_PARAMETER_CURRENT_VERSION,
                WEBAUTHN_CREDENTIAL_TYPE_PUBLIC_KEY,
                WEBAUTHN_COSE_ALGORITHM_ECDSA_P256_WITH_SHA256,
            ),
            WEBAUTHN_COSE_CREDENTIAL_PARAMETER(
                WEBAUTHN_COSE_CREDENTIAL_PARAMETER_CURRENT_VERSION,
                WEBAUTHN_CREDENTIAL_TYPE_PUBLIC_KEY,
                WEBAUTHN_COSE_ALGORITHM_RSASSA_PKCS1_V1_5_WITH_SHA256,
            ),
        )
        cose_parameters = WEBAUTHN_COSE_CREDENTIAL_PARAMETERS(2, cose_array)
        client_data, client_data_buffer = self._build_client_data("webauthn.create", yubi.get("origin", "https://localhost"))
        make_options = WEBAUTHN_AUTHENTICATOR_MAKE_CREDENTIAL_OPTIONS(
            WEBAUTHN_AUTHENTICATOR_MAKE_CREDENTIAL_OPTIONS_VERSION_1,
            60000,
            self._empty_credentials(),
            self._empty_extensions(),
            WEBAUTHN_AUTHENTICATOR_ATTACHMENT_CROSS_PLATFORM,
            0,
            WEBAUTHN_USER_VERIFICATION_REQUIREMENT_DISCOURAGED,
            WEBAUTHN_ATTESTATION_CONVEYANCE_PREFERENCE_NONE,
            0,
            None,
        )
        attestation_ptr = ctypes.POINTER(WEBAUTHN_CREDENTIAL_ATTESTATION)()
        hresult = api["make_credential"](
            hwnd,
            ctypes.byref(rp_info),
            ctypes.byref(user_info),
            ctypes.byref(cose_parameters),
            ctypes.byref(client_data),
            ctypes.byref(make_options),
            ctypes.byref(attestation_ptr),
        )
        if hresult != 0:
            raise RuntimeError(f"Windows native security-key registration failed: {self._webauthn_error_text(hresult)}")
        try:
            attestation = attestation_ptr.contents
            credential_id = ctypes.string_at(attestation.pbCredentialId, attestation.cbCredentialId)
            self._save_native_yubikey_registration(credential_id, user_handle_bytes, label=user_label)
            return {
                "credential_id": _b64url_encode(credential_id),
                "transport": int(attestation.dwUsedTransport),
            }
        finally:
            if attestation_ptr:
                api["free_attestation"](attestation_ptr)

    def verify_native_yubikey(self, parent=None, reason=None):
        yubi = self._native_yubikey_settings()
        credential_id_bytes = _b64url_decode(yubi.get("credential_id"))
        if not credential_id_bytes:
            raise RuntimeError("No native Windows security key has been registered yet.")
        api = self._get_webauthn_api()
        hwnd = self._resolve_webauthn_hwnd(parent)
        credential_buffer = (ctypes.c_ubyte * len(credential_id_bytes)).from_buffer_copy(credential_id_bytes)
        allow_credential = WEBAUTHN_CREDENTIAL(
            WEBAUTHN_CREDENTIAL_CURRENT_VERSION,
            len(credential_id_bytes),
            ctypes.cast(credential_buffer, PBYTE),
            WEBAUTHN_CREDENTIAL_TYPE_PUBLIC_KEY,
        )
        allow_credentials = (WEBAUTHN_CREDENTIAL * 1)(allow_credential)
        credential_list = WEBAUTHN_CREDENTIALS(1, allow_credentials)
        client_data, client_data_buffer = self._build_client_data("webauthn.get", yubi.get("origin", "https://localhost"))
        assertion_options = WEBAUTHN_AUTHENTICATOR_GET_ASSERTION_OPTIONS(
            WEBAUTHN_AUTHENTICATOR_GET_ASSERTION_OPTIONS_VERSION_1,
            60000,
            credential_list,
            self._empty_extensions(),
            WEBAUTHN_AUTHENTICATOR_ATTACHMENT_CROSS_PLATFORM,
            WEBAUTHN_USER_VERIFICATION_REQUIREMENT_DISCOURAGED,
            0,
            None,
            None,
            None,
        )
        assertion_ptr = ctypes.POINTER(WEBAUTHN_ASSERTION)()
        hresult = api["get_assertion"](
            hwnd,
            yubi.get("rp_id", "localhost"),
            ctypes.byref(client_data),
            ctypes.byref(assertion_options),
            ctypes.byref(assertion_ptr),
        )
        if hresult != 0:
            reason_text = f" for {reason}" if reason else ""
            raise RuntimeError(f"Windows native security-key verification failed{reason_text}: {self._webauthn_error_text(hresult)}")
        try:
            self._mark_native_yubikey_verified()
            return True
        finally:
            if assertion_ptr:
                api["free_assertion"](assertion_ptr)

    def authenticate(self, required_right=None, parent=None, reason=None, force_reauth=False):
        if self.is_non_secure_mode_enabled() and required_right and str(required_right).startswith("module:"):
            return True
        if not force_reauth and self._session and self.has_right(required_right):
            return True
        if not self._ensure_bootstrap_vault(parent=parent):
            return False
        return self._prompt_for_vault_login(required_right=required_right, parent=parent, reason=reason, force_reauth=force_reauth)

    def require_module_access(self, module_name, parent=None):
        required_right = self.requires_module_access(module_name)
        if self.is_non_secure_mode_enabled():
            return True
        if not required_right or self.has_right(required_right):
            return True
        return self.authenticate(required_right=required_right, parent=parent, reason=f"Access to {module_name.replace('_', ' ').title()} requires an approved vault.")

    def _prompt_for_vault_login(self, required_right=None, parent=None, reason=None, force_reauth=False, allowed_roles=None):
        normalized_roles = {str(role).strip().lower() for role in (allowed_roles or set()) if str(role).strip()}
        if not force_reauth and self._session and self.has_right(required_right):
            if not normalized_roles or self._session_role() in normalized_roles:
                return True
        available_vaults = [vault for vault in self.list_vaults() if vault.get("enabled", True) and (not normalized_roles or str(vault.get("role", "")).strip().lower() in normalized_roles)]
        if not available_vaults:
            Messagebox.show_error("No enabled vaults are available for this login.", "Security")
            return False
        result = {"granted": False}
        top = tb.Toplevel(parent)
        top.title("Security Access")
        top.geometry("520x320")
        top.resizable(False, False)
        top.transient(parent)
        top.grab_set()
        container = tb.Frame(top, padding=18)
        container.pack(fill=tk.BOTH, expand=True)
        tb.Label(container, text="Security Access", font=("Helvetica", 15, "bold")).pack(anchor=tk.W)
        note_text = reason or "Choose a vault and enter the password to continue."
        if required_right and required_right in ACCESS_RIGHTS_BY_KEY:
            note_text = f"{note_text}\n\nRequired right: {ACCESS_RIGHTS_BY_KEY[required_right]['label']}"
        tb.Label(container, text=note_text, bootstyle="secondary", justify=tk.LEFT, wraplength=470).pack(anchor=tk.W, pady=(4, 12))
        selected_name = tk.StringVar(value=available_vaults[0]["vault_name"])
        password_var = tk.StringVar(value="")
        status_var = tk.StringVar(value="")
        vault_lookup = {vault["vault_name"]: vault for vault in available_vaults}
        vault_row = tb.Frame(container)
        vault_row.pack(fill=tk.X, pady=4)
        tb.Label(vault_row, text="Vault", width=18).pack(side=tk.LEFT)
        vault_combo = tb.Combobox(vault_row, state="readonly", textvariable=selected_name, values=list(vault_lookup))
        vault_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        password_row = tb.Frame(container)
        password_row.pack(fill=tk.X, pady=4)
        tb.Label(password_row, text="Password", width=18).pack(side=tk.LEFT)
        password_entry = tb.Entry(password_row, textvariable=password_var, show="*")
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        vault_status_var = tk.StringVar(value="")
        tb.Label(container, textvariable=vault_status_var, bootstyle="secondary", justify=tk.LEFT, wraplength=470).pack(anchor=tk.W, pady=(6, 10))
        tb.Label(container, textvariable=status_var, bootstyle="danger", justify=tk.LEFT, wraplength=470).pack(anchor=tk.W, pady=(0, 10))

        def refresh_vault_note(_event=None):
            selected_vault = vault_lookup.get(selected_name.get())
            if not selected_vault:
                vault_status_var.set("")
                return
            rights_text = ", ".join(ACCESS_RIGHTS_BY_KEY[right_key]["label"] for right_key in selected_vault.get("rights", []) if right_key in ACCESS_RIGHTS_BY_KEY)
            yubi_text = "YubiKey required" if selected_vault.get("requires_yubikey") else "No YubiKey required"
            password_text = "Password required" if self._vault_requires_password(selected_vault) else "No password required"
            vault_status_var.set(f"Role: {selected_vault.get('role', 'general').title()} | {password_text} | {yubi_text}\nRights: {rights_text}")
            if self._vault_requires_password(selected_vault):
                password_entry.configure(state=tk.NORMAL)
                password_entry.focus_set()
            else:
                password_var.set("")
                password_entry.configure(state=tk.DISABLED)

        def submit_login(_event=None):
            selected_vault = vault_lookup.get(selected_name.get())
            if not selected_vault:
                status_var.set("Choose a vault.")
                return
            if required_right and required_right not in selected_vault.get("rights", []):
                status_var.set("That vault does not have the required access right.")
                return
            if self._vault_requires_password(selected_vault):
                entered_password = password_var.get()
                if not entered_password:
                    status_var.set("Enter the vault password.")
                    return
                if not self._verify_password(selected_vault, entered_password):
                    status_var.set("Incorrect password.")
                    return
            if selected_vault.get("requires_yubikey"):
                try:
                    self.verify_native_yubikey(parent=top, reason=selected_vault.get("display_name", selected_vault.get("vault_name")))
                except Exception as exc:
                    status_var.set(str(exc))
                    return
            self._session = {"vault_name": selected_vault.get("vault_name"), "display_name": selected_vault.get("display_name", selected_vault.get("vault_name")), "role": selected_vault.get("role"), "rights": list(selected_vault.get("rights", [])), "authenticated_at": _utc_timestamp()}
            result["granted"] = True
            top.destroy()

        button_row = tb.Frame(container)
        button_row.pack(fill=tk.X, side=tk.BOTTOM)
        tb.Button(button_row, text="Cancel", bootstyle="secondary", command=top.destroy).pack(side=tk.RIGHT)
        tb.Button(button_row, text="Unlock", bootstyle="success", command=submit_login).pack(side=tk.RIGHT, padx=(0, 8))
        vault_combo.bind("<<ComboboxSelected>>", refresh_vault_note)
        password_entry.bind("<Return>", submit_login)
        refresh_vault_note()
        password_entry.focus_set()
        top.wait_window()
        return result["granted"]

    def open_security_admin_dialog(self, parent=None, dispatcher=None):
        if self.list_vaults() and not self.is_non_secure_mode_enabled() and not self.authenticate(required_right="security:manage_vaults", parent=parent, reason="Security administration requires an approved admin or developer vault."):
            return False
        top = tb.Toplevel(parent)
        top.title("Security Vault Manager")
        top.geometry("980x680")
        top.minsize(720, 520)
        container = tb.Frame(top)
        container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tb.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        scroll_body = tb.Frame(canvas, padding=18)
        scroll_window = canvas.create_window((0, 0), window=scroll_body, anchor="nw")

        def sync_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_body_width(event):
            canvas.itemconfigure(scroll_window, width=event.width)

        def on_mousewheel(event):
            if event.delta:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"
            return None

        scroll_body.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_body_width)
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        top.bind("<Destroy>", lambda _event: canvas.unbind_all("<MouseWheel>"))

        tb.Label(scroll_body, text="Security Vault Manager", font=("Helvetica", 16, "bold")).pack(anchor=tk.W)
        tb.Label(scroll_body, text="Create and maintain .vault files, assign central access rights for visible modules, rotate admin passwords, and register the developer YubiKey.", bootstyle="secondary", justify=tk.LEFT, wraplength=860).pack(anchor=tk.W, pady=(4, 14))
        content = tb.Frame(scroll_body)
        content.pack(fill=tk.BOTH, expand=True)
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=1)
        left_panel = tb.Labelframe(content, text=" Vaults ", padding=12)
        right_panel = tb.Frame(content)
        left_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        right_panel.grid(row=0, column=1, sticky="nsew")
        vault_listbox = tk.Listbox(left_panel, width=28, height=24)
        vault_listbox.pack(fill=tk.BOTH, expand=True)
        counts_var = tk.StringVar(value="")
        tb.Label(left_panel, textvariable=counts_var, bootstyle="secondary", justify=tk.LEFT, wraplength=220).pack(anchor=tk.W, pady=(8, 8))
        vault_name_var = tk.StringVar(value="")
        role_var = tk.StringVar(value="general")
        enabled_var = tk.BooleanVar(value=True)
        requires_yubikey_var = tk.BooleanVar(value=False)
        session_var = tk.StringVar(value=f"Current session: {self.get_session_summary()}")
        yubi_status_var = tk.StringVar(value="")
        developer_tools_status_var = tk.StringVar(value="")
        security_mode_var = tk.BooleanVar(value=self.is_non_secure_mode_enabled())
        security_mode_status_var = tk.StringVar(value="")
        rights_vars = {entry["key"]: tk.BooleanVar(value=False) for entry in ACCESS_RIGHTS}
        current_record = {"vault_name": None, "path": None, "is_new": False}
        form_panel = tb.Labelframe(right_panel, text=" Vault Details ", padding=12)
        form_panel.pack(fill=tk.X)
        row = tb.Frame(form_panel)
        row.pack(fill=tk.X, pady=4)
        tb.Label(row, text="Vault Name", width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 12))
        tb.Entry(row, textvariable=vault_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        row = tb.Frame(form_panel)
        row.pack(fill=tk.X, pady=4)
        tb.Label(row, text="Role", width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 12))
        role_combo = tb.Combobox(row, textvariable=role_var, state="readonly", values=["general", "admin", "developer"])
        role_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row = tb.Frame(form_panel)
        row.pack(fill=tk.X, pady=4)
        tb.Label(row, text="Enabled", width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 12))
        tb.Checkbutton(row, variable=enabled_var, bootstyle="round-toggle").pack(side=tk.LEFT)
        tb.Label(row, text="Requires YubiKey", width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(20, 12))
        requires_yubi_checkbox = tb.Checkbutton(row, variable=requires_yubikey_var, bootstyle="round-toggle")
        requires_yubi_checkbox.pack(side=tk.LEFT)
        tb.Label(form_panel, text="General vaults are passwordless and only control access to the visible module buttons.", bootstyle="secondary", justify=tk.LEFT, wraplength=620).pack(anchor=tk.W, pady=(0, 8))
        rights_panel = tb.Labelframe(right_panel, text=" Central Access Rights ", padding=12)
        rights_panel.pack(fill=tk.X, pady=(12, 0))
        for entry in ACCESS_RIGHTS:
            right_row = tb.Frame(rights_panel)
            right_row.pack(fill=tk.X, pady=2)
            tb.Checkbutton(right_row, text=entry["label"], variable=rights_vars[entry["key"]], bootstyle="round-toggle").pack(side=tk.LEFT)
            tb.Label(right_row, text=entry["description"], bootstyle="secondary", wraplength=520, justify=tk.LEFT).pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        yubi_panel = tb.Labelframe(right_panel, text=" Developer YubiKey ", padding=12)
        yubi_panel.pack(fill=tk.X, pady=(12, 0))
        tb.Label(yubi_panel, textvariable=yubi_status_var, justify=tk.LEFT, bootstyle="secondary", wraplength=620).pack(anchor=tk.W)
        security_mode_panel = tb.Labelframe(right_panel, text=" Security Mode ", padding=12)
        security_mode_panel.pack(fill=tk.X, pady=(12, 0))
        security_mode_toggle_row = tb.Frame(security_mode_panel)
        security_mode_toggle_row.pack(fill=tk.X)
        tb.Label(security_mode_toggle_row, text="Non-Secure Mode", width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 12))
        non_secure_toggle = tb.Checkbutton(security_mode_toggle_row, variable=security_mode_var, bootstyle="round-toggle")
        non_secure_toggle.pack(side=tk.LEFT)
        tb.Label(security_mode_panel, textvariable=security_mode_status_var, justify=tk.LEFT, bootstyle="secondary", wraplength=620).pack(anchor=tk.W, pady=(8, 0))
        developer_tools_panel = tb.Labelframe(right_panel, text=" Developer Tools ", padding=12)
        developer_tools_panel.pack(fill=tk.X, pady=(12, 0))
        tb.Label(developer_tools_panel, textvariable=developer_tools_status_var, justify=tk.LEFT, bootstyle="secondary", wraplength=620).pack(anchor=tk.W, pady=(0, 10))

        def relayout_content(_event=None):
            available_width = content.winfo_width() or top.winfo_width()
            if available_width < 900:
                left_panel.grid_configure(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 0), pady=(0, 12))
                right_panel.grid_configure(row=1, column=0, columnspan=2, sticky="nsew")
            else:
                left_panel.grid_configure(row=0, column=0, columnspan=1, sticky="nsw", padx=(0, 12), pady=(0, 0))
                right_panel.grid_configure(row=0, column=1, columnspan=1, sticky="nsew")

        content.bind("<Configure>", relayout_content)

        def refresh_counts_label():
            vaults = self.list_vaults()
            counts_var.set(f"General: {sum(1 for vault in vaults if vault.get('role') == 'general')}/{GENERAL_USER_LIMIT}\nAdmin: {sum(1 for vault in vaults if vault.get('role') == 'admin')}/{ADMIN_USER_LIMIT}\nDeveloper: {sum(1 for vault in vaults if vault.get('role') == 'developer')}/{DEVELOPER_USER_LIMIT}")

        def refresh_yubikey_status():
            settings = self._load_security_settings()
            yubi = settings.get("yubikey", {})
            credential_id = str(yubi.get("credential_id") or "").strip()
            credential_summary = f"{credential_id[:18]}..." if len(credential_id) > 18 else (credential_id or "Not registered")
            yubi_status_var.set(
                f"Provider: Native Windows WebAuthn\n"
                f"Label: {yubi.get('label', 'Developer YubiKey')}\n"
                f"Relying Party ID: {yubi.get('rp_id', 'localhost')}\n"
                f"Registered Credential: {credential_summary}\n"
                f"Last registered: {yubi.get('last_registered_at') or 'Never'}\n"
                f"Last verified: {yubi.get('last_verified_at') or 'Never'}"
            )

        def refresh_session_status():
            session_var.set(f"Current session: {self.get_session_summary()}")

        developer_button_refs = []

        def refresh_security_mode_status():
            if security_mode_var.get():
                security_mode_status_var.set("Non-secure mode lets normal application modules open without vault authentication. Developer tools still require a developer login.")
            else:
                security_mode_status_var.set("Secure mode enforces vault-based access rights on the visible application modules.")

        def refresh_developer_tools_state():
            is_developer_session = self._developer_session_active()
            is_non_secure_mode = security_mode_var.get()
            if is_non_secure_mode and not is_developer_session:
                if not developer_login_button.winfo_manager():
                    developer_login_button.pack(side=tk.LEFT)
            elif developer_login_button.winfo_manager():
                developer_login_button.pack_forget()
            developer_tools_status_var.set(
                "Developer tools are available for the currently logged-in developer session."
                if is_developer_session
                else ("Non-secure mode is active. Use Developer Login to access update configuration and external module editing." if is_non_secure_mode else "Log in with the developer vault to configure updates or edit external modules.")
            )
            for button in developer_button_refs:
                button.configure(state=tk.NORMAL if is_developer_session else tk.DISABLED)

        def selected_vault_record():
            selection = vault_listbox.curselection()
            if not selection:
                return None
            vaults = self.list_vaults()
            index = selection[0]
            return vaults[index] if 0 <= index < len(vaults) else None

        def apply_role_defaults(force=False):
            selected_role = role_var.get().strip().lower()
            is_developer = selected_role == "developer"
            is_general = selected_role == "general"
            if is_developer:
                requires_yubikey_var.set(True)
                for right_key in rights_vars:
                    rights_vars[right_key].set(True)
            elif force:
                for right_key in rights_vars:
                    rights_vars[right_key].set(right_key in ROLE_DEFAULT_RIGHTS.get(selected_role, []))
            if is_general:
                requires_yubikey_var.set(False)
            requires_yubi_checkbox.configure(state=tk.DISABLED if is_developer or is_general else tk.NORMAL)
            state_value = tk.DISABLED if is_developer else tk.NORMAL
            for child in rights_panel.winfo_children():
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, tb.Checkbutton):
                        grandchild.configure(state=state_value)

        def load_form(vault_record=None):
            current_record["vault_name"] = None
            current_record["path"] = None
            current_record["is_new"] = vault_record is None
            if vault_record is None:
                vault_name_var.set("")
                role_var.set("general")
                enabled_var.set(True)
                requires_yubikey_var.set(False)
                for right_key in rights_vars:
                    rights_vars[right_key].set(right_key in ROLE_DEFAULT_RIGHTS["general"])
                apply_role_defaults(force=True)
                return
            current_record["vault_name"] = vault_record.get("vault_name")
            current_record["path"] = vault_record.get("path")
            current_record["is_new"] = False
            vault_name_var.set(vault_record.get("vault_name", ""))
            role_var.set(vault_record.get("role", "general"))
            enabled_var.set(bool(vault_record.get("enabled", True)))
            requires_yubikey_var.set(bool(vault_record.get("requires_yubikey", False)))
            vault_rights = set(vault_record.get("rights", []))
            for right_key in rights_vars:
                rights_vars[right_key].set(right_key in vault_rights)
            apply_role_defaults(force=False)

        def refresh_vault_list(select_name=None):
            vaults = self.list_vaults()
            vault_listbox.delete(0, END)
            for vault_record in vaults:
                role_text = vault_record.get("role", "general").title()
                disabled_text = " [Disabled]" if not vault_record.get("enabled", True) else ""
                vault_listbox.insert(END, f"{vault_record['vault_name']} ({role_text}){disabled_text}")
            refresh_counts_label()
            refresh_session_status()
            refresh_yubikey_status()
            refresh_developer_tools_state()
            if not vaults:
                load_form(None)
                return
            target_index = 0
            if select_name:
                for index, vault_record in enumerate(vaults):
                    if vault_record["vault_name"] == select_name:
                        target_index = index
                        break
            vault_listbox.selection_clear(0, END)
            vault_listbox.selection_set(target_index)
            vault_listbox.activate(target_index)
            load_form(vaults[target_index])

        def handle_vault_selection(_event=None):
            load_form(selected_vault_record())

        def add_vault_with_role(target_role):
            load_form(None)
            role_var.set(target_role)
            apply_role_defaults(force=True)

        def save_vault():
            selected_role = role_var.get().strip().lower()
            selected_rights = [right_key for right_key, variable in rights_vars.items() if variable.get()]
            new_password = None
            if current_record["is_new"] and _role_requires_password(selected_role):
                new_password = self._prompt_for_new_password(parent=top, title="Set Vault Password")
                if not new_password:
                    return
            try:
                self.create_or_update_vault(vault_name=vault_name_var.get(), role=selected_role, rights=selected_rights, password=new_password, enabled=enabled_var.get(), requires_yubikey=requires_yubikey_var.get(), existing_name=current_record["vault_name"])
            except Exception as exc:
                Messagebox.show_error(str(exc), "Security Vault Manager")
                return
            saved_name = _sanitize_vault_name(vault_name_var.get())
            current_record["is_new"] = False
            current_record["vault_name"] = saved_name
            refresh_vault_list(select_name=saved_name)
            if dispatcher is not None:
                dispatcher.show_toast("Security", f"Saved vault {saved_name}.", "success")

        def delete_selected_vault():
            vault_record = selected_vault_record()
            if vault_record is None:
                Messagebox.show_info("Choose a vault first.", "Security Vault Manager")
                return
            if not Messagebox.okcancel(f"Delete {vault_record['vault_name']}?", "Delete Vault"):
                return
            try:
                self.delete_vault(vault_record["vault_name"])
            except Exception as exc:
                Messagebox.show_error(str(exc), "Security Vault Manager")
                return
            refresh_vault_list()
            if dispatcher is not None:
                dispatcher.show_toast("Security", f"Deleted vault {vault_record['vault_name']}.", "info")

        def change_selected_password():
            vault_record = selected_vault_record()
            if vault_record is None:
                Messagebox.show_info("Choose a vault first.", "Security Vault Manager")
                return
            if not self._vault_requires_password(vault_record):
                Messagebox.show_info("General vaults do not use passwords.", "Security Vault Manager")
                return
            new_password = self._prompt_for_new_password(parent=top, title=f"Change Password: {vault_record['vault_name']}")
            if not new_password:
                return
            try:
                self.change_vault_password(vault_record["vault_name"], new_password)
            except Exception as exc:
                Messagebox.show_error(str(exc), "Security Vault Manager")
                return
            refresh_vault_list(select_name=vault_record["vault_name"])
            if dispatcher is not None:
                dispatcher.show_toast("Security", f"Password updated for {vault_record['vault_name']}.", "success")

        def request_key_access():
            try:
                self.verify_native_yubikey(parent=top, reason="Security admin verification")
            except Exception as exc:
                Messagebox.show_error(str(exc), "Security Key Verification")
                return
            refresh_yubikey_status()
            Messagebox.show_info("Security key verification succeeded. Touch confirmation came from the native Windows prompt.", "Security Key Verification")

        def register_or_update_key():
            current_label = self._load_security_settings().get("yubikey", {}).get("label", "Developer YubiKey")
            label = simpledialog.askstring("Register Security Key", "Label for the developer security key:", initialvalue=current_label, parent=top)
            try:
                self.register_native_yubikey(parent=top, label=label)
            except Exception as exc:
                Messagebox.show_error(str(exc), "Register Security Key")
                return
            refresh_yubikey_status()
            if dispatcher is not None:
                dispatcher.show_toast("Security", "Registered native Windows security key.", "success")

        def logout_session():
            self.logout()
            refresh_session_status()
            refresh_developer_tools_state()
            if dispatcher is not None:
                dispatcher.show_toast("Security", "Security session cleared.", "info")

        def developer_login():
            if self.developer_login(parent=top, reason="Developer login is required for update configuration and external module editing."):
                refresh_session_status()
                refresh_developer_tools_state()
                if dispatcher is not None:
                    dispatcher.show_toast("Security", "Developer login accepted.", "success")

        def toggle_non_secure_mode():
            desired_state = bool(security_mode_var.get())
            if desired_state and not Messagebox.okcancel("Enable Non-Secure Mode", "Non-secure mode removes vault prompts for the visible application modules. Developer tools will still require a developer login. Continue?"):
                security_mode_var.set(False)
                refresh_security_mode_status()
                return
            self.set_non_secure_mode(desired_state)
            refresh_security_mode_status()
            refresh_developer_tools_state()
            refresh_session_status()
            if dispatcher is not None:
                dispatcher.refresh_runtime_settings()
                dispatcher.show_toast("Security", "Non-secure mode enabled." if desired_state else "Secure mode restored.", "warning" if desired_state else "info")

        def open_update_configuration():
            if self.open_update_configuration_dialog(parent=top, dispatcher=dispatcher):
                refresh_developer_tools_state()

        def open_module_editor():
            if dispatcher is None:
                Messagebox.show_info("Module editing is unavailable without the active dispatcher.", "Module Editor")
                return
            self.open_external_module_editor_dialog(parent=top, dispatcher=dispatcher)

        button_strip = tb.Frame(left_panel)
        button_strip.pack(fill=tk.X, pady=(0, 8))
        tb.Button(button_strip, text="New General", bootstyle="info", command=lambda: add_vault_with_role("general")).pack(fill=tk.X, pady=(0, 6))
        tb.Button(button_strip, text="New Admin", bootstyle="warning", command=lambda: add_vault_with_role("admin")).pack(fill=tk.X, pady=(0, 6))
        tb.Button(button_strip, text="New Developer", bootstyle="success", command=lambda: add_vault_with_role("developer")).pack(fill=tk.X)
        actions_panel = tb.Frame(right_panel)
        actions_panel.pack(fill=tk.X, pady=(12, 0))
        tb.Button(actions_panel, text="Save Vault", bootstyle="success", command=save_vault).pack(side=tk.LEFT)
        tb.Button(actions_panel, text="Change Password", bootstyle="info", command=change_selected_password).pack(side=tk.LEFT, padx=(8, 0))
        tb.Button(actions_panel, text="Delete Vault", bootstyle="danger", command=delete_selected_vault).pack(side=tk.LEFT, padx=(8, 0))
        key_actions = tb.Frame(right_panel)
        key_actions.pack(fill=tk.X, pady=(12, 0))
        tb.Button(key_actions, text="Refresh Key Status", bootstyle="secondary", command=refresh_yubikey_status).pack(side=tk.LEFT)
        tb.Button(key_actions, text="Verify Security Key", bootstyle="info", command=request_key_access).pack(side=tk.LEFT, padx=(8, 0))
        tb.Button(key_actions, text="Register / Replace Security Key", bootstyle="warning", command=register_or_update_key).pack(side=tk.LEFT, padx=(8, 0))
        developer_actions = tb.Frame(developer_tools_panel)
        developer_actions.pack(fill=tk.X)
        developer_login_button = tb.Button(developer_actions, text="Developer Login", bootstyle="info", command=developer_login)
        update_button = tb.Button(developer_actions, text="Configure Update URL", bootstyle="warning", command=open_update_configuration)
        update_button.pack(side=tk.LEFT)
        module_button = tb.Button(developer_actions, text="Edit External Modules", bootstyle="danger", command=open_module_editor)
        module_button.pack(side=tk.LEFT, padx=(8, 0))
        developer_button_refs.extend([update_button, module_button])
        session_row = tb.Frame(right_panel)
        session_row.pack(fill=tk.X, pady=(12, 0))
        tb.Label(session_row, textvariable=session_var, bootstyle="secondary").pack(side=tk.LEFT)
        tb.Button(session_row, text="Logout Session", bootstyle="secondary", command=logout_session).pack(side=tk.RIGHT)
        non_secure_toggle.configure(command=toggle_non_secure_mode)
        role_combo.bind("<<ComboboxSelected>>", lambda _event: apply_role_defaults(force=not current_record["vault_name"]))
        vault_listbox.bind("<<ListboxSelect>>", handle_vault_selection)
        refresh_vault_list()
        refresh_security_mode_status()
        refresh_developer_tools_state()
        relayout_content()
        return True


gatekeeper = Gatekeeper()