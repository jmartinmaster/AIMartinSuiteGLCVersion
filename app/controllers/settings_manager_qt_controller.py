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
import time

from app.downtime_codes import DEFAULT_DT_CODE_MAP
from app.models.security_model import ACCESS_RIGHTS, ROLE_DEFAULT_RIGHTS, ROLE_LIMITS, normalize_role, role_requires_password
from app.security import gatekeeper
from app.theme_manager import get_theme_label
from app.models.settings_manager_model import SettingsManagerModel
from app.views.settings_manager_qt_view import SettingsManagerQtView

__module_name__ = "Settings Manager Qt Controller"
__version__ = "1.4.0"


class SettingsManagerQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.module_name = str(self.payload.get("module_name") or self.payload.get("module") or "settings_manager")
        self.module_title = str(self.payload.get("title") or "Settings Manager")
        self.section_mode = str(self.payload.get("section_mode") or "full")
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.theme_options = list(self.payload.get("theme_options") or [])
        self.navigation_modules = list(self.payload.get("navigation_modules") or [])
        self.persistable_modules = list(self.payload.get("persistable_modules") or [])
        self.external_modules_status = str(self.payload.get("external_modules_status") or "")
        self.model = SettingsManagerModel()
        self.model.set_valid_modules(
            [item.get("module_name") for item in self.navigation_modules],
            [item.get("module_name") for item in self.persistable_modules],
        )
        self.view = SettingsManagerQtView(self, self.payload)
        self.refresh_snapshot(initial=True)

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False, runtime_event=None, metadata=None):
        if not self.state_path:
            return
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": self.module_name,
            "updated_at": time.time(),
        }
        if runtime_event:
            payload["runtime_event"] = str(runtime_event)
        if isinstance(metadata, dict):
            payload.update(metadata)
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def refresh_snapshot(self, initial=False):
        self.model.settings = self.model.load_settings()
        self.model.set_valid_modules(
            [item.get("module_name") for item in self.navigation_modules],
            [item.get("module_name") for item in self.persistable_modules],
        )
        selected_theme = self.model.settings.get("theme", self.model.saved_theme)
        whitelist = list(self.model.settings.get("module_whitelist", []))
        persistent_modules = list(self.model.settings.get("persistent_modules", []))

        has_admin_session = gatekeeper.has_admin_session()
        security_visible = has_admin_session
        developer_visible = has_admin_session
        if self.section_mode == "security_admin":
            security_visible = True
            developer_visible = False
        elif self.section_mode == "developer_admin":
            security_visible = False
            developer_visible = True

        snapshot = {
            "theme": get_theme_label(selected_theme),
            "security_summary": gatekeeper.get_session_summary(),
            "security_admin_visible": security_visible,
            "developer_admin_visible": developer_visible,
            "module_whitelist": ", ".join(whitelist) if whitelist else "All visible modules",
            "persistent_modules": ", ".join(persistent_modules) if persistent_modules else "Disabled",
            "external_override_trust": "Enabled" if gatekeeper.is_external_module_override_trust_enabled() else "Disabled",
            "section_mode": self.section_mode,
            "note": "Slice 4 Qt sidecar: core settings, downtime codes, security administration, and developer tools are editable and persisted.",
        }
        self.view.set_editable_settings(
            self.model.get_settings_copy(),
            self.theme_options,
            self.navigation_modules,
            self.persistable_modules,
        )
        self.view.render_snapshot(snapshot)
        self.view.configure_security_admin_panel(self.get_security_admin_state())
        self.view.configure_developer_admin_tools(self.get_developer_admin_settings_state())
        message = f"{self.module_title} Qt window ready." if initial else f"Refreshed {self.module_title} snapshot."
        self.write_state(status="ready", message=message)

    def on_form_changed(self):
        self.write_state(status="ready", message="Edited settings fields.", dirty=True)

    def save_settings(self):
        form_values = self.view.get_form_values()
        try:
            settings = self.model.build_settings_from_form(form_values)
            settings["module_whitelist"] = self.model.normalize_module_names(
                form_values.get("module_whitelist", []),
                self.model.valid_navigation_modules or None,
            )
            settings["persistent_modules"] = self.model.normalize_module_names(
                form_values.get("persistent_modules", []),
                self.model.valid_persistent_modules or None,
            )
            self.model.update_settings(settings)
            backup_info = self.model.save_settings_with_backup()
        except Exception as exc:
            self.view.show_error("Settings Manager", f"Could not save settings:\n{exc}")
            self.write_state(status="ready", message=f"Save failed: {exc}", dirty=True)
            return

        self.refresh_snapshot(initial=False)
        backup_note = ""
        if isinstance(backup_info, dict) and backup_info.get("versioned_backup_path"):
            backup_note = " A backup copy was stored in data/backups/settings."
        self.view.show_info("Settings Manager", f"Saved settings successfully.{backup_note}")
        self._write_saved_runtime_state("Saved settings successfully.")

    def add_next_downtime_code_row(self):
        rows = self.view.get_downtime_code_rows()
        self.view.add_downtime_code_row(self.model.get_next_downtime_code(rows), "")
        self.on_form_changed()

    def reset_downtime_codes_to_defaults(self):
        self.view.set_downtime_code_rows(DEFAULT_DT_CODE_MAP)
        self.on_form_changed()

    def apply_downtime_codes(self):
        rows = self.view.get_downtime_code_rows()
        try:
            updated_codes = self.model.validate_downtime_code_rows(rows)
            self.model.update_downtime_codes(updated_codes)
            backup_info = self.model.save_settings_with_backup()
        except ValueError as exc:
            self.view.show_error("Downtime Codes", str(exc))
            self.write_state(status="ready", message=f"Invalid downtime codes: {exc}", dirty=True)
            return
        except Exception as exc:
            self.view.show_error("Downtime Codes", f"Could not save downtime codes:\n{exc}")
            self.write_state(status="ready", message=f"Downtime save failed: {exc}", dirty=True)
            return

        self.refresh_snapshot(initial=False)
        backup_note = ""
        if isinstance(backup_info, dict) and backup_info.get("versioned_backup_path"):
            backup_note = " A backup copy was stored in data/backups/settings."
        self.view.show_info("Downtime Codes", f"Saved downtime codes successfully.{backup_note}")
        self._write_saved_runtime_state("Saved downtime codes successfully.")

    def _serialize_vault(self, vault_record):
        return {
            "vault_name": vault_record.vault_name,
            "display_name": vault_record.display_name,
            "role": vault_record.role,
            "enabled": bool(vault_record.enabled),
            "password_required": bool(vault_record.password_required),
            "rights": list(vault_record.rights),
            "created_at": vault_record.created_at,
            "updated_at": vault_record.updated_at,
        }

    def _ensure_security_access(self):
        if gatekeeper.has_admin_session() and gatekeeper.has_right("security:manage_vaults"):
            return True
        self.view.show_error(
            "Security",
            "Security administration requires an active admin or developer session with security rights.",
        )
        return False

    def get_security_admin_state(self):
        session = gatekeeper.get_session()
        return {
            "session_summary": gatekeeper.get_session_summary(),
            "non_secure_mode": gatekeeper.is_non_secure_mode_enabled(),
            "session_vault_name": session.vault_name if session else None,
            "vaults": [self._serialize_vault(vault) for vault in gatekeeper.list_vaults()],
            "role_defaults": {key: list(value) for key, value in ROLE_DEFAULT_RIGHTS.items()},
            "role_limits": dict(ROLE_LIMITS),
            "access_rights": [
                {
                    "key": entry.key,
                    "label": entry.label,
                    "description": entry.description,
                }
                for entry in ACCESS_RIGHTS
            ],
        }

    def load_selected_security_vault(self, _event=None):
        self.view.set_security_vault_form(self.view._get_selected_vault_record())

    def start_new_security_vault(self):
        if not self._ensure_security_access():
            return
        self.view.clear_security_vault_selection()
        self.view.set_security_vault_form(None)

    def on_security_role_selected(self, _event=None):
        self.view.update_security_role_note()
        self.on_form_changed()

    def apply_selected_security_role_defaults(self):
        if not self._ensure_security_access():
            return
        self.view.apply_security_role_defaults()

    def save_current_security_vault(self, reset_password=False):
        if not self._ensure_security_access():
            return
        payload = self.view.get_security_vault_payload(reset_password=reset_password)
        try:
            new_state = self.save_security_vault(payload)
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            return
        if new_state is None:
            return
        preferred_name = payload.get("vault_name") or payload.get("existing_name")
        self.view.configure_security_admin_panel(new_state, preferred_name=preferred_name)

    def save_security_vault(self, payload):
        existing_name = str(payload.get("existing_name") or "").strip() or None
        vault_name = str(payload.get("vault_name") or "").strip()
        role = normalize_role(payload.get("role"))
        enabled = bool(payload.get("enabled", True))
        rights = payload.get("rights", [])
        reset_password = bool(payload.get("reset_password", False))

        password = None
        if role_requires_password(role) and (existing_name is None or reset_password):
            password = self.view.ask_for_password_pair(
                "Vault Password",
                f"Set the password for {vault_name or 'this vault'}.",
            )
            if password is None:
                return None

        gatekeeper.create_or_update_vault(
            vault_name=vault_name,
            role=role,
            rights=rights,
            password=password,
            enabled=enabled,
            existing_name=existing_name,
        )
        self.view.show_toast("Security", f"Saved vault {vault_name}.")
        self.write_state(status="ready", message="Saved security vault.", dirty=False)
        return self.get_security_admin_state()

    def delete_selected_security_vault(self):
        if not self._ensure_security_access():
            return
        vault_name = self.view.get_selected_security_vault_name()
        if not vault_name:
            self.view.show_error("Security", "Select an existing vault before deleting it.")
            return
        try:
            new_state = self.delete_security_vault(vault_name)
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            return
        if new_state is None:
            return
        self.view.configure_security_admin_panel(new_state)

    def delete_security_vault(self, vault_name):
        if not self.view.ask_yes_no(
            "Delete Vault",
            f"Delete vault {vault_name}? This cannot be undone.",
        ):
            return None
        gatekeeper.delete_vault(vault_name)
        self.view.show_toast("Security", f"Deleted vault {vault_name}.")
        self.write_state(status="ready", message="Deleted security vault.", dirty=False)
        return self.get_security_admin_state()

    def rotate_selected_security_vault_password(self):
        if not self._ensure_security_access():
            return
        vault_name = self.view.get_selected_security_vault_name()
        if not vault_name:
            self.view.show_error("Security", "Select an existing vault before rotating its password.")
            return
        try:
            new_state = self.rotate_security_vault_password(vault_name)
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            return
        if new_state is None:
            return
        self.view.configure_security_admin_panel(new_state, preferred_name=vault_name)

    def rotate_security_vault_password(self, vault_name):
        password = self.view.ask_for_password_pair(
            "Rotate Vault Password",
            f"Enter a new password for {vault_name}.",
        )
        if password is None:
            return None
        gatekeeper.change_vault_password(vault_name, password)
        self.view.show_toast("Security", f"Updated password for {vault_name}.")
        self.write_state(status="ready", message="Rotated vault password.", dirty=False)
        return self.get_security_admin_state()

    def save_current_security_mode(self):
        if not self._ensure_security_access():
            return
        desired_state = self.view.get_security_non_secure_mode()
        current_state = gatekeeper.is_non_secure_mode_enabled()
        if desired_state == current_state:
            return
        action_text = "enable" if desired_state else "disable"
        if not self.view.ask_yes_no(
            "Confirm Security Change",
            f"Are you sure you want to {action_text} persisted non-secure mode?",
        ):
            self.view.configure_security_admin_panel(
                self.get_security_admin_state(),
                preferred_name=self.view.get_selected_security_vault_name(),
            )
            return
        try:
            new_state = self.set_security_non_secure_mode(desired_state)
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            return
        self.view.configure_security_admin_panel(new_state, preferred_name=self.view.get_selected_security_vault_name())

    def set_security_non_secure_mode(self, enabled):
        gatekeeper.set_non_secure_mode(bool(enabled))
        message = (
            "Non-secure mode is enabled. Protected-module authentication is bypassed."
            if enabled
            else "Non-secure mode is disabled. Protected modules are locked again."
        )
        self.view.show_toast("Security", message)
        self.write_state(status="ready", message="Updated security mode.", dirty=False)
        return self.get_security_admin_state()

    def get_developer_admin_settings_state(self):
        return {
            "update_repository_url": self.model.settings.get("update_repository_url", ""),
            "enable_advanced_dev_updates": bool(self.model.settings.get("enable_advanced_dev_updates", False)),
            "enable_external_override_trust": gatekeeper.is_external_module_override_trust_enabled(),
            "external_modules_status": self.external_modules_status or "External override status is provided by the host dispatcher.",
        }

    def save_current_developer_admin_settings(self):
        values = self.view.get_developer_admin_settings_values()
        self.save_developer_admin_settings(
            values["update_repository_url"],
            values["enable_advanced_dev_updates"],
            values["enable_external_override_trust"],
        )

    def save_developer_admin_settings(self, update_repository_url, enable_advanced_dev_updates, enable_external_override_trust):
        trust_changed = gatekeeper.is_external_module_override_trust_enabled() != bool(enable_external_override_trust)
        self.model.settings["update_repository_url"] = str(update_repository_url or "").strip()
        self.model.settings["enable_advanced_dev_updates"] = bool(enable_advanced_dev_updates)
        self.model.settings = self.model.normalize_settings(self.model.settings)
        gatekeeper.set_external_module_override_trust(bool(enable_external_override_trust))
        backup_info = self.model.save_settings_with_backup()

        backup_note = ""
        if isinstance(backup_info, dict) and backup_info.get("versioned_backup_path"):
            backup_note = " A backup copy was stored in data/backups/settings."
        self.view.show_info("Developer Settings", f"Saved developer settings successfully.{backup_note}")

        metadata = {
            "applied_theme": str(self.model.saved_theme or ""),
            "refresh_runtime_settings": True,
            "refresh_downtime_codes": False,
            "apply_external_override_policy_change": bool(trust_changed),
        }
        self._write_saved_runtime_state("Saved developer settings successfully.", metadata=metadata)
        self.refresh_snapshot(initial=False)

    def _write_saved_runtime_state(self, message, metadata=None):
        base_metadata = {
            "applied_theme": str(self.model.saved_theme or ""),
            "refresh_runtime_settings": True,
            "refresh_downtime_codes": True,
        }
        if isinstance(metadata, dict):
            base_metadata.update(metadata)
        self.write_state(
            status="ready",
            message=str(message or "Saved settings successfully."),
            dirty=False,
            runtime_event="settings_saved",
            metadata=base_metadata,
        )

    def poll_commands(self):
        if not self.command_path or not os.path.exists(self.command_path):
            return
        try:
            with open(self.command_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            payload = {}
        try:
            os.remove(self.command_path)
        except OSError:
            pass

        action = str(payload.get("action") or "").strip().lower()
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Settings Manager Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="Settings Manager Qt window closed.")
