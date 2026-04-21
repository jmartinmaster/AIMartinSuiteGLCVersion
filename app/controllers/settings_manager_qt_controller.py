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
from app.downtime_codes import DEFAULT_DT_CODE_MAP, clear_downtime_code_cache
from app.models.security_model import ACCESS_RIGHTS, ROLE_DEFAULT_RIGHTS, ROLE_LIMITS, normalize_role, role_requires_password
from app.security import gatekeeper
from app.theme_manager import get_theme_label, get_theme_names, normalize_theme
from app.models.settings_manager_model import SettingsManagerModel
from app.views.settings_manager_qt_view import SettingsManagerQtView

__module_name__ = "Settings Manager Qt Controller"
__version__ = "1.6.0"


class SettingsManagerQtController:
    def __init__(self, payload=None, parent=None, dispatcher=None):
        payload = dict(payload or {}) if isinstance(payload, dict) else {}
        self.parent = parent
        self.dispatcher = dispatcher
        self.embedded = dispatcher is not None
        self.payload = dict(payload)
        self.module_name = str(payload.get("module_name") or payload.get("module") or getattr(self, "module_name", "settings_manager"))
        self.module_title = str(payload.get("title") or getattr(self, "module_title", "Settings Manager"))
        self.section_mode = str(payload.get("section_mode") or getattr(self, "section_mode", "full"))
        self.payload = self._build_view_payload() if self.embedded else dict(payload)
        self.theme_options = list(self.payload.get("theme_options") or [])
        self.navigation_modules = list(self.payload.get("navigation_modules") or [])
        self.persistable_modules = list(self.payload.get("persistable_modules") or [])
        self.external_modules_status = str(self.payload.get("external_modules_status") or "")
        self.model = SettingsManagerModel()
        self.model.set_valid_modules(
            [item.get("module_name") for item in self.navigation_modules],
            [item.get("module_name") for item in self.persistable_modules],
        )
        self._security_listener_registered = False
        self.view = SettingsManagerQtView(self, self.payload, parent_widget=parent)
        if self.embedded and hasattr(self.dispatcher, "add_security_session_listener"):
            self.dispatcher.add_security_session_listener(self.on_security_session_changed)
            self._security_listener_registered = True
        self._prime_section_access()
        self.refresh_snapshot(initial=True)
        if self.embedded:
            self.view.show()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def _build_view_payload(self):
        navigation_modules = list(self.dispatcher.get_navigation_modules()) if self.dispatcher is not None else []
        persistable_modules = list(self.dispatcher.get_persistable_modules()) if self.dispatcher is not None else []
        section_label = {
            "developer_admin": "Developer administration",
            "security_admin": "Security administration",
        }.get(self.section_mode, "Settings administration")
        theme_tokens = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {}) if self.dispatcher is not None else {}
        return {
            "window_title": f"{self.module_title} - Production Logging Center",
            "title": self.module_title,
            "subtitle": f"Manage {section_label.lower()} from this page.",
            "module_name": self.module_name,
            "section_mode": self.section_mode,
            "theme_options": [{"key": theme_name, "label": get_theme_label(theme_name)} for theme_name in get_theme_names()],
            "navigation_modules": [
                {
                    "display_name": display_name,
                    "module_name": module_name,
                }
                for display_name, module_name in navigation_modules
            ],
            "persistable_modules": [
                {
                    "display_name": display_name,
                    "module_name": module_name,
                }
                for display_name, module_name in persistable_modules
            ],
            "theme_tokens": theme_tokens,
            "external_modules_status": self._resolve_external_modules_status(),
        }

    def _resolve_external_modules_status(self):
        dispatcher = self.dispatcher
        if dispatcher is None:
            return self.external_modules_status or ""
        if not dispatcher.has_external_modules_directory():
            return "External module overrides are unavailable until override files exist next to the app."
        module_names = dispatcher.get_external_module_override_names()
        if module_names:
            if dispatcher.is_external_module_override_trust_enabled():
                return f"External overrides are trusted and active. Available overrides: {', '.join(module_names)}"
            return f"External overrides exist but are inactive until an admin enables override trust. Available files: {', '.join(module_names)}"
        return "Override-capable application folder detected. No module override files were found, so bundled modules stay in use."

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def _prime_section_access(self):
        if self.section_mode == "security_admin":
            self._ensure_security_access(prompt_if_needed=True, show_error=False)
        elif self.section_mode == "developer_admin":
            self._ensure_developer_access(prompt_if_needed=True, show_error=False)

    def _get_session_role(self):
        session = gatekeeper.get_session()
        return normalize_role(session.role) if session is not None else "general"

    def _has_security_access(self):
        return gatekeeper.get_session() is not None and gatekeeper.has_right("security:manage_vaults") and self._get_session_role() in {"admin", "developer"}

    def _has_developer_access(self):
        return gatekeeper.get_session() is not None and gatekeeper.has_right("developer:update_configuration") and self._get_session_role() == "developer"

    def refresh_snapshot(self, initial=False):
        self.model.settings = self.model.load_settings()
        if self.embedded:
            self.theme_options = [{"key": theme_name, "label": get_theme_label(theme_name)} for theme_name in get_theme_names()]
            self.navigation_modules = [
                {"display_name": display_name, "module_name": module_name}
                for display_name, module_name in self.dispatcher.get_navigation_modules()
            ]
            self.persistable_modules = [
                {"display_name": display_name, "module_name": module_name}
                for display_name, module_name in self.dispatcher.get_persistable_modules()
            ]
            self.external_modules_status = self._resolve_external_modules_status()
        self.model.set_valid_modules(
            [item.get("module_name") for item in self.navigation_modules],
            [item.get("module_name") for item in self.persistable_modules],
        )
        selected_theme = self.model.settings.get("theme", self.model.saved_theme)
        whitelist = list(self.model.settings.get("module_whitelist", []))
        persistent_modules = list(self.model.settings.get("persistent_modules", []))

        has_security_access = self._has_security_access()
        has_developer_access = self._has_developer_access()
        security_visible = has_security_access
        developer_visible = has_developer_access
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
            "note": "Manage application settings, downtime codes, security administration, and developer tools from this page.",
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
        if initial:
            self.view.status_bar.showMessage(f"{self.module_title} viewport ready.", 4000)

    def on_security_session_changed(self, _event_name=None):
        self.refresh_snapshot(initial=False)

    def on_form_changed(self):
        return None

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
            return
        except Exception as exc:
            self.view.show_error("Downtime Codes", f"Could not save downtime codes:\n{exc}")
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

    def _ensure_security_access(self, prompt_if_needed=True, show_error=True):
        return self._ensure_security_access_with_prompt(prompt_if_needed=prompt_if_needed, show_error=show_error)

    def _ensure_security_access_with_prompt(self, prompt_if_needed=True, show_error=True):
        if self._has_security_access():
            return True
        if prompt_if_needed:
            try:
                granted = gatekeeper.authenticate(
                    required_right="security:manage_vaults",
                    parent=self.view,
                    reason="Security administration requires an admin or developer vault.",
                    allowed_roles={"admin", "developer"},
                )
            except Exception as exc:
                if show_error:
                    self.view.show_error("Security", f"Could not unlock security administration: {exc}")
                return False
            if granted and self._has_security_access():
                self.refresh_snapshot(initial=False)
                return True
        if show_error:
            self.view.show_error(
                "Security",
                "Security administration requires an active admin or developer session with security rights.",
            )
        return False

    def _ensure_developer_access(self, prompt_if_needed=True, show_error=True):
        if self._has_developer_access():
            return True
        if prompt_if_needed:
            try:
                granted = gatekeeper.authenticate(
                    required_right="developer:update_configuration",
                    parent=self.view,
                    reason="Developer tools require a developer vault.",
                    allowed_roles={"developer"},
                )
            except Exception as exc:
                if show_error:
                    self.view.show_error("Developer Tools", f"Could not unlock developer tools: {exc}")
                return False
            if granted and self._has_developer_access():
                self.refresh_snapshot(initial=False)
                return True
        if show_error:
            self.view.show_error(
                "Developer Tools",
                "Developer tools require an active developer session with update-configuration rights.",
            )
        return False

    def request_security_admin_access(self):
        self._ensure_security_access_with_prompt(prompt_if_needed=True, show_error=True)

    def request_developer_admin_access(self):
        self._ensure_developer_access(prompt_if_needed=True, show_error=True)

    def get_security_admin_state(self):
        session = gatekeeper.get_session()
        return {
            "can_manage_security": self._has_security_access(),
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
        if self.view._get_selected_vault_record() is None:
            self.view.apply_security_role_defaults()
            return
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
        return self.get_security_admin_state()

    def reset_security_storage(self):
        if not self._ensure_security_access():
            return None
        if not gatekeeper.reset_vault(parent=self.view, dispatcher=self.dispatcher):
            return None
        self.refresh_snapshot(initial=False)
        self.view.configure_security_admin_panel(self.get_security_admin_state())
        return self.get_security_admin_state()

    def reset_security_storage_from_ui(self):
        try:
            new_state = self.reset_security_storage()
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            return
        if new_state is None:
            return
        self.view.configure_security_admin_panel(new_state)

    def get_developer_admin_settings_state(self):
        return {
            "can_manage_developer": self._has_developer_access(),
            "update_repository_url": self.model.settings.get("update_repository_url", ""),
            "enable_advanced_dev_updates": bool(self.model.settings.get("enable_advanced_dev_updates", False)),
            "enable_external_override_trust": gatekeeper.is_external_module_override_trust_enabled(),
            "external_modules_status": self.external_modules_status or "External override status is provided by the host dispatcher.",
        }

    def save_current_developer_admin_settings(self):
        if not self._ensure_developer_access(prompt_if_needed=True, show_error=True):
            return
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

    def _apply_saved_runtime_effects(self, metadata):
        if self.dispatcher is None:
            return
        clear_downtime_code_cache()
        requested_theme = normalize_theme((metadata or {}).get("applied_theme", self.model.saved_theme))
        applied_theme = self.dispatcher.apply_theme(requested_theme)
        self.model.load_settings()
        self.model.preview_theme = applied_theme
        if bool((metadata or {}).get("refresh_runtime_settings", True)):
            self.dispatcher.refresh_runtime_settings()
        if bool((metadata or {}).get("apply_external_override_policy_change", False)):
            try:
                self.dispatcher.apply_external_override_policy_change()
            except Exception:
                pass
        active_module = getattr(self.dispatcher, "active_module_instance", None)
        if bool((metadata or {}).get("refresh_downtime_codes", True)) and hasattr(active_module, "refresh_downtime_codes"):
            try:
                active_module.refresh_downtime_codes()
            except Exception:
                pass

    def _write_saved_runtime_state(self, message, metadata=None):
        base_metadata = {
            "applied_theme": str(self.model.saved_theme or ""),
            "refresh_runtime_settings": True,
            "refresh_downtime_codes": True,
        }
        if isinstance(metadata, dict):
            base_metadata.update(metadata)
        self._apply_saved_runtime_effects(base_metadata)

    def handle_close(self):
        return None

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})

    def on_hide(self):
        return None

    def on_unload(self):
        if self._security_listener_registered and hasattr(self.dispatcher, "remove_security_session_listener"):
            self.dispatcher.remove_security_session_listener(self.on_security_session_changed)
            self._security_listener_registered = False
        try:
            self.view.close()
        except Exception:
            pass
