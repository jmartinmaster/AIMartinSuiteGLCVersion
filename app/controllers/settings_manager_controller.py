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
from copy import deepcopy
import os

from app.downtime_codes import DEFAULT_DT_CODE_MAP, clear_downtime_code_cache
from app.qt_module_runtime import QtModuleRuntimeManager
from app.security import gatekeeper
from app.theme_manager import DEFAULT_THEME, get_theme_label, get_theme_labels, get_theme_names, normalize_theme
from app.models.security_model import ACCESS_RIGHTS, ROLE_DEFAULT_RIGHTS, ROLE_LIMITS, normalize_role, role_requires_password
from app.models.settings_manager_model import SettingsManagerModel
from app.views.settings_manager_view_factory import create_settings_manager_view

__module_name__ = "Settings Manager"
__version__ = "1.2.0"


class SettingsManagerController:
    def __init__(
        self,
        parent,
        dispatcher,
        section_mode="full",
        module_name="settings_manager",
        module_title="Settings Manager",
        view_factory=None,
    ):
        self.parent = parent
        self.dispatcher = dispatcher
        self.section_mode = str(section_mode or "full")
        self.module_name = str(module_name or "settings_manager")
        self.module_title = str(module_title or "Settings Manager")
        self.requested_view_backend = "qt"
        self.resolved_view_backend = "tk"
        self.view_backend_fallback_reason = None
        self.runtime_manager = QtModuleRuntimeManager(self.module_name, self.build_qt_session_payload)
        self._last_runtime_event_timestamp = None
        self.model = SettingsManagerModel()
        self.view = None
        self.view_factory = view_factory or create_settings_manager_view
        self._security_listener_registered = False
        self.sync_valid_module_options()
        self.view = self.view_factory(parent, dispatcher, self, section_mode=self.section_mode)
        if self.resolved_view_backend == "tk":
            self.dispatcher.add_security_session_listener(self.on_security_session_changed)
            self._security_listener_registered = True
            self.view.build_form_fields(self.model.get_settings_copy(), self.get_theme_options())
            self.refresh_module_whitelist_summary()
            self.refresh_persistent_modules_summary()
            self.refresh_external_modules_status()
            self.refresh_security_status()
            self.refresh_developer_admin_status()
            self.view.set_theme_status(f"Current theme: {get_theme_label(self.model.saved_theme)}")
            self.view.apply_section_mode()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def build_qt_session_payload(self):
        root = self.parent.winfo_toplevel()
        navigation_modules = list(self.dispatcher.get_navigation_modules())
        persistable_modules = list(self.dispatcher.get_persistable_modules())
        section_label = {
            "developer_admin": "Developer administration",
            "security_admin": "Security administration",
        }.get(self.section_mode, "Settings administration")
        return {
            "window_title": f"{self.module_title} - Production Logging Center",
            "title": self.module_title,
            "subtitle": f"Qt sidecar runtime for {section_label.lower()}.",
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
            "theme_tokens": dict(getattr(root, "_martin_theme_tokens", {}) or {}),
            "external_modules_status": self.format_external_modules_status(),
        }

    def open_or_raise_qt_window(self):
        self.runtime_manager.ensure_running(force_restart=False)

    def restart_qt_window(self):
        self.runtime_manager.ensure_running(force_restart=True)

    def stop_qt_window(self):
        self.runtime_manager.stop_runtime(force=False)

    def read_runtime_state(self):
        return self.runtime_manager.read_state()

    def handle_runtime_state(self, state):
        if self.resolved_view_backend != "qt":
            return
        if not isinstance(state, dict):
            return

        runtime_event = str(state.get("runtime_event") or "").strip().lower()
        if runtime_event != "settings_saved":
            return

        event_timestamp = state.get("updated_at")
        if event_timestamp == self._last_runtime_event_timestamp:
            return
        self._last_runtime_event_timestamp = event_timestamp

        clear_downtime_code_cache()
        requested_theme = normalize_theme(state.get("applied_theme", self.model.saved_theme))
        applied_theme = self.dispatcher.apply_theme(requested_theme)
        self.model.load_settings()
        self.model.preview_theme = applied_theme
        if bool(state.get("refresh_runtime_settings", True)):
            self.dispatcher.refresh_runtime_settings()
        if bool(state.get("apply_external_override_policy_change", False)):
            try:
                self.dispatcher.apply_external_override_policy_change()
            except Exception:
                pass
        active_module = getattr(self.dispatcher, "active_module_instance", None)
        if bool(state.get("refresh_downtime_codes", True)) and hasattr(active_module, "refresh_downtime_codes"):
            try:
                active_module.refresh_downtime_codes()
            except Exception:
                pass

    def apply_theme(self):
        if self.resolved_view_backend == "tk":
            self.view.apply_theme()

    def on_security_session_changed(self, _event_name=None):
        self.sync_valid_module_options()
        self.refresh_module_whitelist_summary()
        self.refresh_persistent_modules_summary()
        self.refresh_session_state()

    def get_theme_options(self):
        return get_theme_labels()

    def sync_valid_module_options(self):
        navigation_modules = [module_name for _display_name, module_name in self.dispatcher.get_navigation_modules()]
        persistent_modules = [module_name for _display_name, module_name in self.dispatcher.get_persistable_modules()]
        self.model.set_valid_modules(navigation_modules, persistent_modules)

    def format_persistent_modules_summary(self):
        selected_modules = list(self.model.settings.get("persistent_modules", []))
        display_lookup = {module_name: display_name for display_name, module_name in self.dispatcher.get_persistable_modules()}
        selected_labels = [display_lookup[module_name] for module_name in selected_modules if module_name in display_lookup]
        if not selected_labels:
            return "Disabled"
        return ", ".join(selected_labels)

    def format_module_whitelist_summary(self):
        selected_modules = list(self.model.settings.get("module_whitelist", []))
        display_lookup = {module_name: display_name for display_name, module_name in self.dispatcher.get_navigation_modules()}
        selected_labels = [display_lookup[module_name] for module_name in selected_modules if module_name in display_lookup]
        if not selected_labels:
            return "All visible modules"
        return ", ".join(selected_labels)

    def refresh_module_whitelist_summary(self):
        self.sync_valid_module_options()
        self.view.set_module_whitelist_summary(self.format_module_whitelist_summary())

    def refresh_persistent_modules_summary(self):
        self.sync_valid_module_options()
        self.view.set_persistent_modules_summary(self.format_persistent_modules_summary())

    def format_external_modules_status(self):
        if not self.dispatcher.has_external_modules_directory():
            return "External module overrides are unavailable until override files exist next to the app."
        module_names = self.dispatcher.get_external_module_override_names()
        if module_names:
            if self.dispatcher.is_external_module_override_trust_enabled():
                return f"External overrides are trusted and active. Available overrides: {', '.join(module_names)}"
            return f"External overrides exist but are inactive until an admin enables override trust. Available files: {', '.join(module_names)}"
        return "Override-capable application folder detected. No module override files were found, so bundled modules stay in use."

    def refresh_external_modules_status(self):
        self.view.set_external_modules_status(self.format_external_modules_status())

    def refresh_session_state(self):
        self.refresh_security_status()
        self.refresh_developer_admin_status()
        self.refresh_external_modules_status()

    def format_developer_admin_status(self):
        override_count = len(self.dispatcher.get_external_module_override_names()) if self.dispatcher.has_external_modules_directory() else 0
        repo_url = self.model.settings.get("update_repository_url", "")
        advanced_enabled = bool(self.model.settings.get("enable_advanced_dev_updates", False))
        advanced_label = "Advanced dev updates enabled" if advanced_enabled else "Advanced dev updates disabled"
        trust_label = "Override trust enabled" if gatekeeper.is_external_module_override_trust_enabled() else "Override trust disabled"
        if override_count:
            return f"{advanced_label} | {trust_label} | {override_count} external override(s) | {repo_url}"
        return f"{advanced_label} | {trust_label} | No external overrides | {repo_url}"

    def refresh_developer_admin_status(self):
        is_visible = gatekeeper.has_admin_session()
        self.view.set_developer_admin_visible(is_visible)
        if is_visible:
            self.view.set_developer_admin_status(self.format_developer_admin_status())
            self.view.configure_developer_admin_tools(self.get_developer_admin_settings_state())

    def refresh_security_status(self):
        if hasattr(gatekeeper, "get_session_summary"):
            self.view.set_security_status(gatekeeper.get_session_summary())
        else:
            self.view.set_security_status("Unlocked for this session" if getattr(gatekeeper, "_authenticated", False) else "Locked")
        is_visible = gatekeeper.has_admin_session()
        self.view.set_security_admin_visible(is_visible)
        if is_visible:
            self.view.configure_security_admin_panel(self.get_security_admin_state())

    def _refresh_security_ui(self):
        self.refresh_session_state()
        if hasattr(self.dispatcher, "refresh_navigation"):
            self.dispatcher.refresh_navigation()

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

    def open_security_admin_dialog(self):
        try:
            if not gatekeeper.authenticate(
                required_right="security:manage_vaults",
                parent=self.view.parent,
                reason="Security administration requires an admin or developer vault.",
            ):
                return
            self._refresh_security_ui()
        except Exception as exc:
            self.view.show_error("Security", f"Could not open security administration: {exc}")

    def load_selected_security_vault(self, _event=None):
        self.view.set_security_vault_form(self.view.get_selected_security_vault_record())

    def start_new_security_vault(self):
        self.view.clear_security_vault_selection()
        self.view.set_security_vault_form(None)

    def on_security_role_selected(self, _event=None):
        self.view.update_security_role_note()

    def apply_selected_security_role_defaults(self):
        self.view.apply_security_role_defaults()

    def save_current_security_vault(self, reset_password=False):
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

    def delete_selected_security_vault(self):
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

    def rotate_selected_security_vault_password(self):
        vault_name = self.view.get_selected_security_vault_name()
        if not vault_name:
            self.view.show_error("Security", "Select an existing vault before rotating its password.")
            return
        if self.view.security_admin_role_var.get().strip().lower() == "general":
            self.view.show_error("Security", "General vaults do not require passwords in this implementation.")
            return
        try:
            new_state = self.rotate_security_vault_password(vault_name)
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            return
        if new_state is None:
            return
        self.view.configure_security_admin_panel(new_state, preferred_name=vault_name)

    def save_current_security_mode(self):
        desired_state = self.view.get_security_non_secure_mode()
        current_state = gatekeeper.is_non_secure_mode_enabled()
        if desired_state == current_state:
            return
        action_text = "enable" if desired_state else "disable"
        if not self.view.ask_yes_no(
            "Confirm Security Change",
            f"Are you sure you want to {action_text} persisted non-secure mode?",
        ):
            self.view.configure_security_admin_panel(self.get_security_admin_state(), preferred_name=self.view.get_selected_security_vault_name())
            return
        try:
            new_state = self.set_security_non_secure_mode(desired_state)
        except Exception as exc:
            self.view.show_error("Security", str(exc))
            self.view.configure_security_admin_panel(self.get_security_admin_state(), preferred_name=self.view.get_selected_security_vault_name())
            return
        self.view.configure_security_admin_panel(new_state, preferred_name=self.view.get_selected_security_vault_name())

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
        self._refresh_security_ui()
        self.view.show_toast("Security", f"Saved vault {vault_name}.")
        return self.get_security_admin_state()

    def delete_security_vault(self, vault_name):
        if not self.view.ask_yes_no(
            "Delete Vault",
            f"Delete vault {vault_name}? This cannot be undone.",
        ):
            return None
        gatekeeper.delete_vault(vault_name)
        self._refresh_security_ui()
        self.view.show_toast("Security", f"Deleted vault {vault_name}.")
        return self.get_security_admin_state()

    def rotate_security_vault_password(self, vault_name):
        password = self.view.ask_for_password_pair(
            "Rotate Vault Password",
            f"Enter a new password for {vault_name}.",
        )
        if password is None:
            return None
        gatekeeper.change_vault_password(vault_name, password)
        self._refresh_security_ui()
        self.view.show_toast("Security", f"Updated password for {vault_name}.")
        return self.get_security_admin_state()

    def set_security_non_secure_mode(self, enabled):
        gatekeeper.set_non_secure_mode(bool(enabled))
        self._refresh_security_ui()
        message = "Non-secure mode is enabled. Protected-module authentication is bypassed." if enabled else "Non-secure mode is disabled. Protected modules are locked again."
        bootstyle = "warning" if enabled else "success"
        self.view.show_toast("Security", message, bootstyle)
        return self.get_security_admin_state()

    def get_developer_admin_settings_state(self):
        return {
            "update_repository_url": self.model.settings.get("update_repository_url", ""),
            "enable_advanced_dev_updates": bool(self.model.settings.get("enable_advanced_dev_updates", False)),
            "enable_external_override_trust": gatekeeper.is_external_module_override_trust_enabled(),
            "external_modules_status": self.format_external_modules_status(),
        }

    def save_developer_admin_settings(self, update_repository_url, enable_advanced_dev_updates, enable_external_override_trust):
        trust_changed = gatekeeper.is_external_module_override_trust_enabled() != bool(enable_external_override_trust)
        self.model.settings["update_repository_url"] = str(update_repository_url or "").strip()
        self.model.settings["enable_advanced_dev_updates"] = bool(enable_advanced_dev_updates)
        self.model.settings = self.model.normalize_settings(self.model.settings)
        gatekeeper.set_external_module_override_trust(bool(enable_external_override_trust))
        self.persist_settings(
            toast_title="Developer Settings Saved",
            toast_message_prefix="Privileged update settings were saved immediately.",
        )
        if trust_changed:
            self.dispatcher.apply_external_override_policy_change()
            trust_message = "External override trust is enabled. Override files can load when modules are reloaded." if enable_external_override_trust else "External override trust is disabled. Bundled modules are now preferred again."
            self.view.show_toast("Developer Tools", trust_message)
        self.refresh_developer_admin_status()

    def save_current_developer_admin_settings(self):
        values = self.view.get_developer_admin_settings_values()
        self.save_developer_admin_settings(
            values["update_repository_url"],
            values["enable_advanced_dev_updates"],
            values["enable_external_override_trust"],
        )

    def persist_settings(self, toast_title="Settings Saved", toast_message_prefix="Theme changes were applied immediately."):
        clear_downtime_code_cache()
        backup_info = self.model.save_settings_with_backup()
        applied_theme = self.dispatcher.apply_theme(self.model.saved_theme)
        self.model.preview_theme = applied_theme
        self.view.set_theme_selection(applied_theme)
        self.view.set_theme_status(f"Current theme: {get_theme_label(applied_theme)}")
        self.dispatcher.refresh_runtime_settings()

        if hasattr(self.dispatcher.active_module_instance, "refresh_downtime_codes"):
            self.dispatcher.active_module_instance.refresh_downtime_codes()

        backup_note = ""
        if backup_info.get("versioned_backup_path"):
            backup_note = " A recovery copy was stored in data/backups/settings."
        self.view.show_toast(toast_title, f"{toast_message_prefix}{backup_note}")
        self.refresh_module_whitelist_summary()
        self.refresh_session_state()
        self.refresh_persistent_modules_summary()

    def save_settings(self):
        self.model.update_settings(self.model.build_settings_from_form(self.view.collect_form_values()))
        self.persist_settings()

    def preview_selected_theme(self, _event=None):
        theme_entry = self.view.entries.get("theme")
        if theme_entry is None:
            return
        selected_theme = normalize_theme(theme_entry.get())
        applied_theme = self.dispatcher.apply_theme(selected_theme)
        self.model.set_preview_theme(applied_theme)
        self.view.set_theme_status(f"Previewing theme: {get_theme_label(applied_theme)}")

    def revert_theme_preview(self):
        reverted_theme = self.dispatcher.apply_theme(self.model.revert_preview_theme())
        self.view.set_theme_selection(reverted_theme)
        self.view.set_theme_status(f"Theme reverted to: {get_theme_label(reverted_theme)}")

    def browse_export_dir(self):
        directory_path = self.view.ask_for_export_directory()
        if directory_path:
            self.view.set_export_directory(directory_path)

    def open_downtime_codes_dialog(self):
        if self.view.is_downtime_editor_visible():
            self.view.set_downtime_editor_visible(False)
            return
        current_codes = self.model.settings.get("downtime_codes", deepcopy(DEFAULT_DT_CODE_MAP))
        self.view.configure_downtime_codes_editor(current_codes)
        self.view.set_downtime_editor_visible(True)

    def suggest_next_downtime_code(self, rows):
        return self.model.get_next_downtime_code(rows)

    def save_downtime_code_rows(self, rows):
        try:
            updated_codes = self.model.validate_downtime_code_rows(rows)
        except ValueError as exc:
            self.view.show_error("Downtime Codes", str(exc))
            return False
        self.save_downtime_codes(updated_codes)
        return True

    def add_next_downtime_code_editor_row(self):
        self.view.add_downtime_code_row(self.suggest_next_downtime_code(self.view.get_downtime_code_rows()), "")

    def save_current_downtime_codes(self):
        self.save_downtime_code_rows(self.view.get_downtime_code_rows())

    def save_downtime_codes(self, updated_codes):
        self.model.update_downtime_codes(updated_codes)
        self.persist_settings(
            toast_title="Downtime Codes Saved",
            toast_message_prefix="Downtime code labels were updated immediately.",
        )

    def open_persistent_modules_dialog(self):
        if self.view.is_persistent_modules_editor_visible():
            self.view.set_persistent_modules_editor_visible(False)
            return
        self.sync_valid_module_options()
        options = self.dispatcher.get_persistable_modules()
        if not options:
            self.view.show_info("Persistent Modules", "No persistable modules are available.")
            return
        selected_modules = set(self.model.settings.get("persistent_modules", []))
        self.view.configure_persistent_modules_editor(options, selected_modules)
        self.view.set_persistent_modules_editor_visible(True)

    def open_module_whitelist_dialog(self):
        if self.view.is_module_whitelist_editor_visible():
            self.view.set_module_whitelist_editor_visible(False)
            return
        self.sync_valid_module_options()
        options = self.dispatcher.get_navigation_modules()
        if not options:
            self.view.show_info("Sidebar Module Whitelist", "No visible modules are available.")
            return
        selected_modules = set(self.model.settings.get("module_whitelist", []))
        self.view.configure_module_whitelist_editor(options, selected_modules)
        self.view.set_module_whitelist_editor_visible(True)

    def save_persistent_modules_selection(self, selected_modules=None):
        if selected_modules is None:
            selected_modules = self.view.get_persistent_modules_editor_selection()
        self.model.settings["persistent_modules"] = self.model.normalize_module_names(
            selected_modules,
            self.model.valid_persistent_modules or None,
        )
        self.refresh_persistent_modules_summary()

    def save_module_whitelist_selection(self, selected_modules=None):
        if selected_modules is None:
            selected_modules = self.view.get_module_whitelist_editor_selection()
        self.model.settings["module_whitelist"] = self.model.normalize_module_names(
            selected_modules,
            self.model.valid_navigation_modules or None,
        )
        self.refresh_module_whitelist_summary()

    def on_unload(self):
        if self._security_listener_registered:
            self.dispatcher.remove_security_session_listener(self.on_security_session_changed)
            self._security_listener_registered = False
        if self.resolved_view_backend == "qt":
            self.stop_qt_window()
            return None
        if self.model.preview_theme != self.model.saved_theme:
            self.dispatcher.apply_theme(self.model.saved_theme)
