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
import json
import os
import secrets
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

from app.app_logging import log_exception
from app.models.security_model import (
    ACCESS_RIGHTS_BY_KEY,
    PBKDF2_ITERATIONS,
    ROLE_DEFAULT_RIGHTS,
    ROLE_LIMITS,
    SecuritySession,
    VaultRecord,
    normalize_rights,
    normalize_role,
    role_requires_password,
)
from app.utils import ensure_external_directory, external_path

__module_name__ = "Security Blanket"
__version__ = "2.0.1"


class Gatekeeper:
    _instance = None
    _legacy_vault_path = os.path.join(os.getcwd(), ".vault")
    _security_settings_path = external_path(os.path.join("data", "security", "security_settings.json"))

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Gatekeeper, cls).__new__(cls)
            cls._instance._session = None
            cls._instance._authenticated = False
            cls._instance._session_role = "general"
            cls._instance._session_listeners = []
        return cls._instance

    def _vault_directory(self):
        return ensure_external_directory(os.path.join("data", "security", "vaults"))

    def _vault_backup_directory(self):
        return ensure_external_directory(os.path.join("data", "security", "backups", "vaults"))

    def _create_temp_root(self):
        temp_root = tk.Tk()
        temp_root.withdraw()
        return temp_root

    def _sanitize_vault_name(self, raw_value):
        text = str(raw_value or "").strip()
        filtered = []
        for character in text:
            filtered.append(character if character.isalnum() or character in {"_", "-", "."} else "_")
        normalized = "".join(filtered).strip("._-")
        return normalized[:64]

    def _utc_timestamp(self):
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _prompt_secret(self, title, prompt, parent=None):
        return simpledialog.askstring(title, prompt, show="*", parent=parent)

    def _ensure_security_settings_directory(self):
        ensure_external_directory(os.path.join("data", "security"))

    def _load_security_settings(self):
        settings = {"non_secure_mode": False, "external_module_override_trust": False}
        if not os.path.exists(self._security_settings_path):
            return settings
        try:
            with open(self._security_settings_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                settings["non_secure_mode"] = bool(payload.get("non_secure_mode", False))
                settings["external_module_override_trust"] = bool(payload.get("external_module_override_trust", False))
        except Exception as exc:
            log_exception("gatekeeper._load_security_settings", exc)
        return settings

    def _save_security_settings(self, settings):
        self._ensure_security_settings_directory()
        payload = {
            "non_secure_mode": bool(settings.get("non_secure_mode", False)),
            "external_module_override_trust": bool(settings.get("external_module_override_trust", False)),
        }
        temp_path = f"{self._security_settings_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4)
        os.replace(temp_path, self._security_settings_path)

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
        if not vault_record.password_required:
            return True
        if vault_record.hash_scheme == "legacy_sha256":
            return hashlib.sha256(password.encode("utf-8")).hexdigest() == str(vault_record.password_hash or "")
        if not vault_record.password_salt or not vault_record.password_hash:
            return False
        hashed = self._hash_password(
            password,
            salt_hex=vault_record.password_salt,
            iterations=vault_record.password_iterations or PBKDF2_ITERATIONS,
        )
        return hashed["password_hash"] == vault_record.password_hash

    def _list_vault_paths(self):
        vault_dir = self._vault_directory()
        return [
            os.path.join(vault_dir, file_name)
            for file_name in sorted(os.listdir(vault_dir))
            if file_name.lower().endswith(".vault")
        ]

    def _vault_path_for_name(self, vault_name):
        return os.path.join(self._vault_directory(), f"{self._sanitize_vault_name(vault_name)}.vault")

    def _write_vault_record(self, vault_record, existing_path=None):
        target_path = self._vault_path_for_name(vault_record.vault_name)
        temp_path = f"{target_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(vault_record.to_payload(), handle, indent=4)
        os.replace(temp_path, target_path)
        if existing_path and os.path.abspath(existing_path) != os.path.abspath(target_path) and os.path.exists(existing_path):
            os.remove(existing_path)
        vault_record.path = target_path
        return target_path

    def _load_vault_record(self, path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return VaultRecord.from_payload(payload, path=path)

    def list_vaults(self):
        vaults = []
        for path in self._list_vault_paths():
            vault_record = self._load_vault_record(path)
            if vault_record is not None and vault_record.vault_name:
                vaults.append(vault_record)
        return vaults

    def _find_vault(self, vault_name):
        normalized_name = self._sanitize_vault_name(vault_name)
        for vault_record in self.list_vaults():
            if vault_record.vault_name == normalized_name:
                return vault_record
        return None

    def _count_role(self, role, exclude_name=None):
        total = 0
        for vault_record in self.list_vaults():
            if exclude_name and vault_record.vault_name == exclude_name:
                continue
            if vault_record.role == normalize_role(role):
                total += 1
        return total

    def _validate_role_limit(self, role, exclude_name=None):
        role_key = normalize_role(role)
        limit = ROLE_LIMITS.get(role_key)
        if limit and self._count_role(role_key, exclude_name=exclude_name) >= limit:
            raise ValueError(f"{role_key.title()} vaults are limited to {limit}.")

    def create_or_update_vault(self, vault_name, role, rights, password=None, enabled=True, existing_name=None):
        normalized_name = self._sanitize_vault_name(vault_name)
        if not normalized_name:
            raise ValueError("Vault name is required.")
        role_key = normalize_role(role)
        existing_record = self._find_vault(existing_name or normalized_name)
        current_session_name = self._session.vault_name if self._session else None
        if existing_record is None:
            self._validate_role_limit(role_key)
        elif existing_record.role != role_key:
            self._validate_role_limit(role_key, exclude_name=existing_record.vault_name)

        if existing_record is not None and current_session_name == existing_record.vault_name and not enabled:
            raise ValueError("The active session vault cannot be disabled.")

        if existing_record is not None and existing_record.role == "admin":
            will_stop_being_enabled_admin = (not enabled) or role_key != "admin"
            if will_stop_being_enabled_admin:
                remaining_enabled_admins = [
                    vault
                    for vault in self.list_vaults()
                    if vault.enabled and vault.role == "admin" and vault.vault_name != existing_record.vault_name
                ]
                if not remaining_enabled_admins:
                    raise ValueError("At least one enabled admin vault must remain available.")

        password_required = role_requires_password(role_key)
        normalized_rights = normalize_rights(rights or ROLE_DEFAULT_RIGHTS.get(role_key, []), role=role_key)
        if not normalized_rights:
            raise ValueError("At least one access right must be selected.")

        vault_record = VaultRecord(
            vault_name=normalized_name,
            display_name=normalized_name,
            role=role_key,
            enabled=bool(enabled),
            password_required=password_required,
            requires_yubikey=False,
            rights=normalized_rights,
            created_at=existing_record.created_at if existing_record else self._utc_timestamp(),
            updated_at=self._utc_timestamp(),
            path=existing_record.path if existing_record else None,
        )

        if not password_required:
            vault_record.hash_scheme = ""
            vault_record.password_hash = ""
            vault_record.password_salt = ""
            vault_record.password_iterations = 0
        elif existing_record and not password:
            vault_record.hash_scheme = existing_record.hash_scheme
            vault_record.password_hash = existing_record.password_hash
            vault_record.password_salt = existing_record.password_salt
            vault_record.password_iterations = existing_record.password_iterations
        elif password:
            hashed = self._hash_password(password)
            vault_record.hash_scheme = hashed["hash_scheme"]
            vault_record.password_hash = hashed["password_hash"]
            vault_record.password_salt = hashed["password_salt"]
            vault_record.password_iterations = hashed["password_iterations"]
        else:
            raise ValueError("A password is required for this vault.")

        self._write_vault_record(vault_record, existing_path=existing_record.path if existing_record else None)
        if existing_record is not None and current_session_name == existing_record.vault_name:
            self._set_session_from_vault(vault_record)
        return vault_record

    def change_vault_password(self, vault_name, new_password):
        vault_record = self._find_vault(vault_name)
        if vault_record is None:
            raise ValueError("Vault not found.")
        if not vault_record.password_required:
            raise ValueError("This vault does not use a password.")
        hashed = self._hash_password(new_password)
        vault_record.hash_scheme = hashed["hash_scheme"]
        vault_record.password_hash = hashed["password_hash"]
        vault_record.password_salt = hashed["password_salt"]
        vault_record.password_iterations = hashed["password_iterations"]
        vault_record.updated_at = self._utc_timestamp()
        self._write_vault_record(vault_record, existing_path=vault_record.path)
        if self._session and self._session.vault_name == vault_record.vault_name:
            self._set_session_from_vault(vault_record)
        return vault_record

    def delete_vault(self, vault_name):
        vault_record = self._find_vault(vault_name)
        if vault_record is None:
            raise ValueError("Vault not found.")
        if self._session and self._session.vault_name == vault_record.vault_name:
            raise ValueError("The active session vault cannot be deleted.")
        if vault_record.role == "admin":
            remaining_enabled_admins = [
                vault
                for vault in self.list_vaults()
                if vault.enabled and vault.role == "admin" and vault.vault_name != vault_record.vault_name
            ]
            if not remaining_enabled_admins:
                raise ValueError("At least one enabled admin vault must remain available.")
        if vault_record.path and os.path.exists(vault_record.path):
            os.remove(vault_record.path)
        return True

    def _load_legacy_password_hash(self):
        if os.path.exists(self._legacy_vault_path):
            with open(self._legacy_vault_path, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        return None

    def has_master_password(self):
        return bool(self.list_vaults() or self._load_legacy_password_hash())

    def logout(self):
        self._set_session(None)

    def _clear_admin_session(self):
        self.logout()

    def _set_session(self, session):
        self._session = session
        self._authenticated = session is not None
        self._session_role = normalize_role(session.role if session else "general")
        self._notify_session_listeners("session-changed")

    def add_session_listener(self, listener):
        if callable(listener) and listener not in self._session_listeners:
            self._session_listeners.append(listener)

    def remove_session_listener(self, listener):
        if listener in self._session_listeners:
            self._session_listeners.remove(listener)

    def _notify_session_listeners(self, event_name):
        for listener in list(self._session_listeners):
            try:
                listener(event_name)
            except Exception as exc:
                log_exception("gatekeeper.session_listener", exc)

    def _merge_role_default_rights(self, role, rights):
        merged_rights = list(rights or [])
        for right_key in ROLE_DEFAULT_RIGHTS.get(normalize_role(role), []):
            if right_key not in merged_rights:
                merged_rights.append(right_key)
        return normalize_rights(merged_rights, role=role)

    def _set_session_from_vault(self, vault_record):
        self._set_session(
            SecuritySession(
                vault_name=vault_record.vault_name,
                display_name=vault_record.display_name,
                role=vault_record.role,
                rights=self._merge_role_default_rights(vault_record.role, vault_record.rights),
                authenticated_at=self._utc_timestamp(),
            )
        )

    def get_session(self):
        return self._session

    def get_session_role(self):
        return self._session_role if self._session else None

    def has_right(self, right_key):
        if not right_key:
            return True
        if not self._session:
            return False
        return self._session.has_right(right_key)

    def _confirm_current_password(self, parent=None, prompt=None):
        if not self._session:
            return False
        vault_record = self._find_vault(self._session.vault_name)
        if vault_record is None or not vault_record.password_required:
            return False
        entered_password = self._prompt_secret(
            "Security Administration",
            prompt or "Re-enter the current vault password to continue:",
            parent=parent,
        )
        return bool(entered_password) and self._verify_password(vault_record, entered_password)

    def _archive_existing_vault(self):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = self._vault_backup_directory()
        created_backups = []
        if os.path.exists(self._legacy_vault_path):
            legacy_backup = os.path.join(backup_dir, f"legacy-vault-{timestamp}.bak")
            shutil.copy2(self._legacy_vault_path, legacy_backup)
            created_backups.append(legacy_backup)
        for vault_record in self.list_vaults():
            if not vault_record.path or not os.path.exists(vault_record.path):
                continue
            backup_name = f"{vault_record.vault_name}-{timestamp}.vault"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(vault_record.path, backup_path)
            created_backups.append(backup_path)
        return created_backups

    def _delete_all_vaults(self):
        for vault_record in self.list_vaults():
            if vault_record.path and os.path.exists(vault_record.path):
                os.remove(vault_record.path)
        if os.path.exists(self._legacy_vault_path):
            os.remove(self._legacy_vault_path)

    def _prompt_for_new_password(self, parent=None, title="Security Setup"):
        first = self._prompt_secret(title, "Enter a password:", parent=parent)
        if not first:
            return None
        second = self._prompt_secret(title, "Re-enter the password:", parent=parent)
        if second != first:
            messagebox.showerror("Security", "The passwords did not match.", parent=parent)
            return None
        return first

    def _migrate_legacy_vault_if_needed(self, parent=None):
        if self.list_vaults() or not os.path.exists(self._legacy_vault_path):
            return True
        legacy_hash = self._load_legacy_password_hash()
        if not legacy_hash:
            return False
        vault_name = simpledialog.askstring(
            "Security Migration",
            "Name the first admin vault for the migrated security system:",
            initialvalue="admin_1",
            parent=parent,
        )
        if vault_name is None:
            return False
        normalized_name = self._sanitize_vault_name(vault_name)
        if not normalized_name:
            messagebox.showerror("Security Migration", "A valid admin vault name is required.", parent=parent)
            return False

        self._validate_role_limit("admin")
        vault_record = VaultRecord(
            vault_name=normalized_name,
            display_name=normalized_name,
            role="admin",
            enabled=True,
            password_required=True,
            requires_yubikey=False,
            rights=list(ROLE_DEFAULT_RIGHTS["admin"]),
            hash_scheme="legacy_sha256",
            password_hash=legacy_hash,
            password_salt="",
            password_iterations=0,
            created_at=self._utc_timestamp(),
            updated_at=self._utc_timestamp(),
        )
        self._write_vault_record(vault_record)
        return True

    def _ensure_bootstrap_vault(self, parent=None):
        if self.list_vaults():
            return True
        if os.path.exists(self._legacy_vault_path):
            return self._migrate_legacy_vault_if_needed(parent=parent)
        if not messagebox.askyesno(
            "Security Setup",
            "No security vaults are configured yet. Create the first admin vault now?",
            parent=parent,
        ):
            return False
        vault_name = simpledialog.askstring(
            "Create Admin Vault",
            "Name for the first admin vault:",
            initialvalue="admin_1",
            parent=parent,
        )
        if vault_name is None:
            return False
        password = self._prompt_for_new_password(parent=parent, title="Create Admin Vault")
        if not password:
            return False
        vault_record = self.create_or_update_vault(
            vault_name=vault_name,
            role="admin",
            rights=ROLE_DEFAULT_RIGHTS["admin"],
            password=password,
            enabled=True,
        )
        self._set_session_from_vault(vault_record)
        messagebox.showinfo("Security Setup", f"Created admin vault '{vault_record.vault_name}'.", parent=parent)
        return True

    def reset_vault(self, parent=None, dispatcher=None):
        if not self.has_admin_session():
            return False
        if not self.has_master_password():
            messagebox.showinfo("Security", "No security vault is configured, so there is nothing to reset.", parent=parent)
            self.logout()
            return False

        if not messagebox.askyesno(
            "Reset Security Storage",
            "This will back up and remove the current security vaults, disable persisted non-secure mode, and end the active admin session. Continue?",
            parent=parent,
        ):
            return False

        confirmation_text = simpledialog.askstring(
            "Reset Security Storage",
            "Type RESET to confirm this destructive action:",
            parent=parent,
        )
        if confirmation_text != "RESET":
            messagebox.showinfo("Security", "Vault reset cancelled.", parent=parent)
            return False

        if not self._confirm_current_password(
            parent=parent,
            prompt="Re-enter the current vault password to authorize the security reset:",
        ):
            messagebox.showerror("Security", "The current vault password was not confirmed. Security reset cancelled.", parent=parent)
            return False

        backup_paths = self._archive_existing_vault()
        try:
            self._delete_all_vaults()
            self.set_non_secure_mode(False)
            self.logout()
        except Exception as exc:
            log_exception("gatekeeper.reset_vault", exc)
            messagebox.showerror("Security", f"The security storage could not be reset: {exc}", parent=parent)
            return False

        if dispatcher is not None:
            dispatcher.show_toast("Security", "Security storage reset. Non-secure mode was disabled and the session was cleared.", "warning")

        backup_note = ""
        if backup_paths:
            backup_note = f" Backups were written to {self._vault_backup_directory()}."
        messagebox.showinfo("Security", f"The security storage was reset successfully.{backup_note}", parent=parent)
        return True

    def has_admin_session(self):
        return self._authenticated and self._session_role in {"admin", "developer"}

    def is_non_secure_mode_enabled(self):
        return bool(self._load_security_settings().get("non_secure_mode", False))

    def set_non_secure_mode(self, enabled):
        settings = self._load_security_settings()
        settings["non_secure_mode"] = bool(enabled)
        self._save_security_settings(settings)
        self._notify_session_listeners("session-changed")
        return settings["non_secure_mode"]

    def is_external_module_override_trust_enabled(self):
        return bool(self._load_security_settings().get("external_module_override_trust", False))

    def set_external_module_override_trust(self, enabled):
        settings = self._load_security_settings()
        settings["external_module_override_trust"] = bool(enabled)
        self._save_security_settings(settings)
        self._notify_session_listeners("session-changed")
        return settings["external_module_override_trust"]

    def authenticate(self, required_right=None, parent=None, reason=None, force_reauth=False, allowed_roles=None):
        if self.is_non_secure_mode_enabled() and required_right and str(required_right).startswith("module:"):
            return True

        normalized_roles = {normalize_role(role) for role in (allowed_roles or set()) if str(role).strip()}
        if not force_reauth and self._session and self.has_right(required_right):
            if not normalized_roles or self._session_role in normalized_roles:
                return True

        temp_root = None
        prompt_parent = parent
        if prompt_parent is None:
            temp_root = self._create_temp_root()
            prompt_parent = temp_root

        try:
            if not self._ensure_bootstrap_vault(parent=prompt_parent):
                return False
            return self._prompt_for_vault_login(
                required_right=required_right,
                parent=prompt_parent,
                reason=reason,
                force_reauth=force_reauth,
                allowed_roles=normalized_roles,
            )
        finally:
            if temp_root is not None:
                temp_root.destroy()

    def _prompt_for_vault_login(self, required_right=None, parent=None, reason=None, force_reauth=False, allowed_roles=None):
        normalized_roles = {normalize_role(role) for role in (allowed_roles or set())}
        if not force_reauth and self._session and self.has_right(required_right):
            if not normalized_roles or self._session_role in normalized_roles:
                return True

        available_vaults = [
            vault for vault in self.list_vaults()
            if vault.enabled and (not normalized_roles or vault.role in normalized_roles)
        ]
        if not available_vaults:
            messagebox.showerror("Security", "No enabled vaults are available for this login.", parent=parent)
            return False

        result = {"granted": False}
        top = tk.Toplevel(parent)
        top.title("Security Access")
        top.resizable(False, False)
        if parent is not None:
            top.transient(parent)
        top.grab_set()

        container = tk.Frame(top, padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        note_text = reason or "Choose a vault and enter the password to continue."
        if required_right and required_right in ACCESS_RIGHTS_BY_KEY:
            note_text = f"{note_text}\n\nRequired right: {ACCESS_RIGHTS_BY_KEY[required_right].label}"

        tk.Label(container, text="Security Access", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(container, text=note_text, justify="left", wraplength=420).pack(anchor="w", pady=(4, 12))

        selected_name = tk.StringVar(value=available_vaults[0].vault_name)
        password_var = tk.StringVar(value="")
        status_var = tk.StringVar(value="")
        vault_status_var = tk.StringVar(value="")
        vault_lookup = {vault.vault_name: vault for vault in available_vaults}

        def get_effective_rights(vault_record):
            return self._merge_role_default_rights(vault_record.role, vault_record.rights)

        vault_row = tk.Frame(container)
        vault_row.pack(fill=tk.X, pady=4)
        tk.Label(vault_row, text="Vault", width=16, anchor="w").pack(side=tk.LEFT)
        vault_combo = ttk.Combobox(vault_row, state="readonly", textvariable=selected_name, values=list(vault_lookup))
        vault_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        password_row = tk.Frame(container)
        password_row.pack(fill=tk.X, pady=4)
        tk.Label(password_row, text="Password", width=16, anchor="w").pack(side=tk.LEFT)
        password_entry = tk.Entry(password_row, textvariable=password_var, show="*")
        password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(container, textvariable=vault_status_var, justify="left", wraplength=420).pack(anchor="w", pady=(6, 8))
        tk.Label(container, textvariable=status_var, justify="left", fg="#b22222", wraplength=420).pack(anchor="w", pady=(0, 8))

        def refresh_vault_note(_event=None):
            selected_vault = vault_lookup.get(selected_name.get())
            if selected_vault is None:
                vault_status_var.set("")
                return
            effective_rights = get_effective_rights(selected_vault)
            rights_text = ", ".join(
                ACCESS_RIGHTS_BY_KEY[right_key].label
                for right_key in effective_rights
                if right_key in ACCESS_RIGHTS_BY_KEY
            ) or "No rights assigned"
            password_text = "Password required" if selected_vault.password_required else "No password required"
            vault_status_var.set(f"Role: {selected_vault.role.title()} | {password_text}\nRights: {rights_text}")
            if selected_vault.password_required:
                password_entry.configure(state=tk.NORMAL)
                password_entry.focus_set()
            else:
                password_var.set("")
                password_entry.configure(state=tk.DISABLED)

        def submit_login(_event=None):
            selected_vault = vault_lookup.get(selected_name.get())
            if selected_vault is None:
                status_var.set("Choose a vault.")
                return
            effective_rights = get_effective_rights(selected_vault)
            if required_right and required_right not in effective_rights:
                status_var.set("That vault does not have the required access right.")
                return
            if selected_vault.password_required:
                entered_password = password_var.get()
                if not entered_password:
                    status_var.set("Enter the vault password.")
                    return
                if not self._verify_password(selected_vault, entered_password):
                    status_var.set("Incorrect password.")
                    return
            self._set_session_from_vault(selected_vault)
            result["granted"] = True
            top.destroy()

        button_frame = tk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Unlock", command=submit_login).pack(side=tk.RIGHT, padx=(0, 8))

        vault_combo.bind("<<ComboboxSelected>>", refresh_vault_note)
        password_entry.bind("<Return>", submit_login)
        refresh_vault_note()
        top.wait_window()
        return result["granted"]

    def get_session_summary(self):
        if not self.has_master_password():
            session_label = "Security setup required"
        elif self._session:
            session_label = f"{self._session.display_name} ({self._session.role.title()})"
        else:
            session_label = "Locked"
        if self.is_non_secure_mode_enabled():
            return f"{session_label} | Non-secure mode enabled"
        return session_label

    def _rotate_master_password(self, parent=None):
        if not self._session:
            return False
        vault_record = self._find_vault(self._session.vault_name)
        if vault_record is None or not vault_record.password_required:
            messagebox.showerror("Security", "The current session vault cannot rotate a password.", parent=parent)
            return False
        new_password = self._prompt_for_new_password(parent=parent, title="Security Administration")
        if not new_password:
            return False
        self.change_vault_password(vault_record.vault_name, new_password)
        messagebox.showinfo("Security", "Vault password updated.", parent=parent)
        return True

    def open_security_admin_dialog(self, parent=None, dispatcher=None):
        if not self.authenticate(
            required_right="security:manage_vaults",
            parent=parent,
            reason="Security administration requires an admin or developer vault.",
        ):
            return False

        owner = parent.winfo_toplevel() if parent is not None else None
        dialog = tk.Toplevel(owner)
        dialog.title("Security Administration")
        dialog.resizable(False, False)
        if owner is not None:
            dialog.transient(owner)
        dialog.grab_set()

        container = tk.Frame(dialog, padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        status_var = tk.StringVar(value=self.get_session_summary())
        non_secure_var = tk.BooleanVar(value=self.is_non_secure_mode_enabled())
        changed = {"value": False}

        tk.Label(container, text="Security Administration", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(
            container,
            text="Use this panel to rotate the current vault password, review the active session, and control persisted non-secure mode while the larger MVC security admin rebuild is underway.",
            justify="left",
            wraplength=420,
        ).pack(anchor="w", pady=(6, 12))

        status_frame = tk.Frame(container)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(status_frame, text="Current session:", anchor="w", width=18).pack(side=tk.LEFT)
        tk.Label(status_frame, textvariable=status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        vault_frame = tk.LabelFrame(container, text="Vault Summary", padx=12, pady=12)
        vault_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            vault_frame,
            text=(
                f"Configured vaults: {len(self.list_vaults())}\n"
                "Settings Manager remains the entry point for security administration in this first implementation pass."
            ),
            justify="left",
            wraplength=380,
        ).pack(anchor="w")

        toggle_frame = tk.LabelFrame(container, text="Non-Secure Mode", padx=12, pady=12)
        toggle_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Checkbutton(
            toggle_frame,
            text="Persistently bypass protected-module authentication",
            variable=non_secure_var,
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            toggle_frame,
            text="This is a global persisted setting intended for controlled admin use only.",
            justify="left",
            wraplength=380,
        ).pack(anchor="w", pady=(6, 0))

        reset_frame = tk.LabelFrame(container, text="Security Reset", padx=12, pady=12)
        reset_frame.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            reset_frame,
            text="Resetting security storage is destructive. Existing vault files will be backed up, persisted non-secure mode will be disabled, and the active session will be cleared.",
            justify="left",
            wraplength=380,
        ).pack(anchor="w")

        def handle_vault_reset():
            if not self.reset_vault(parent=dialog, dispatcher=dispatcher):
                return
            status_var.set(self.get_session_summary())
            non_secure_var.set(self.is_non_secure_mode_enabled())
            changed["value"] = True
            dialog.destroy()

        def save_security_state():
            desired_state = bool(non_secure_var.get())
            current_state = self.is_non_secure_mode_enabled()
            if desired_state == current_state:
                return
            action_text = "enable" if desired_state else "disable"
            if not messagebox.askyesno(
                "Confirm Security Change",
                f"Are you sure you want to {action_text} persisted non-secure mode?",
                parent=dialog,
            ):
                non_secure_var.set(current_state)
                return
            self.set_non_secure_mode(desired_state)
            status_var.set(self.get_session_summary())
            changed["value"] = True
            if dispatcher is not None:
                if desired_state:
                    dispatcher.show_toast("Security", "Non-secure mode is enabled. Protected-module authentication is bypassed.", "warning")
                else:
                    dispatcher.show_toast("Security", "Non-secure mode is disabled. Protected modules are locked again.", "success")

        button_frame = tk.Frame(container)
        button_frame.pack(fill=tk.X)
        tk.Button(button_frame, text="Save Mode", command=save_security_state).pack(side=tk.LEFT)
        tk.Button(
            button_frame,
            text="Rotate Current Vault Password",
            command=lambda: changed.__setitem__("value", self._rotate_master_password(parent=dialog) or changed["value"]),
        ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(button_frame, text="Reset Security Storage", command=handle_vault_reset).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)

        dialog.wait_window()
        return changed["value"]


gatekeeper = Gatekeeper()