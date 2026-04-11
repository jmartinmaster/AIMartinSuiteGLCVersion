from copy import deepcopy
import os

from app.app_logging import log_exception
from app.downtime_codes import DEFAULT_DT_CODE_MAP, clear_downtime_code_cache
from app.persistence import write_json_with_backup
from app.security import gatekeeper
from app.theme_manager import DEFAULT_THEME, get_theme_label, get_theme_labels, normalize_theme
from app.utils import external_path
from app.models.security_model import ACCESS_RIGHTS, ROLE_DEFAULT_RIGHTS, ROLE_LIMITS, normalize_role, role_requires_password
from app.models.settings_manager_model import SettingsManagerModel
from app.views.settings_manager_view import SettingsManagerView


class SettingsManagerController:
    def __init__(self, parent, dispatcher):
        self.dispatcher = dispatcher
        self.model = SettingsManagerModel(dispatcher)
        self.view = SettingsManagerView(parent, dispatcher, self)
        self.view.build_form_fields(self.model.get_settings_copy(), self.get_theme_options())
        self.refresh_module_whitelist_summary()
        self.refresh_persistent_modules_summary()
        self.refresh_external_modules_status()
        self.refresh_security_status()
        self.refresh_developer_admin_status()
        self.view.set_theme_status(f"Current theme: {get_theme_label(self.model.saved_theme)}")

    def __getattr__(self, attribute_name):
        return getattr(self.view, attribute_name)

    def get_theme_options(self):
        return get_theme_labels()

    def format_persistent_modules_summary(self):
        selected_modules = self.dispatcher.normalize_persistent_modules(self.model.settings.get("persistent_modules", []))
        display_lookup = {module_name: display_name for display_name, module_name in self.dispatcher.get_persistable_modules()}
        selected_labels = [display_lookup[module_name] for module_name in selected_modules if module_name in display_lookup]
        if not selected_labels:
            return "Disabled"
        return ", ".join(selected_labels)

    def format_module_whitelist_summary(self):
        selected_modules = self.dispatcher.normalize_module_whitelist(self.model.settings.get("module_whitelist", []))
        display_lookup = {module_name: display_name for display_name, module_name in self.dispatcher.get_navigation_modules()}
        selected_labels = [display_lookup[module_name] for module_name in selected_modules if module_name in display_lookup]
        if not selected_labels:
            return "All visible modules"
        return ", ".join(selected_labels)

    def refresh_module_whitelist_summary(self):
        self.model.settings["module_whitelist"] = self.dispatcher.normalize_module_whitelist(self.model.settings.get("module_whitelist", []))
        self.view.set_module_whitelist_summary(self.format_module_whitelist_summary())

    def refresh_persistent_modules_summary(self):
        self.model.settings["persistent_modules"] = self.dispatcher.normalize_persistent_modules(self.model.settings.get("persistent_modules", []))
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

    def refresh_security_status(self):
        if hasattr(gatekeeper, "get_session_summary"):
            self.view.set_security_status(gatekeeper.get_session_summary())
        else:
            self.view.set_security_status("Unlocked for this session" if getattr(gatekeeper, "_authenticated", False) else "Locked")

    def _refresh_security_ui(self):
        self.refresh_security_status()
        self.refresh_developer_admin_status()
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
            self.view.show_security_admin_dialog(self.get_security_admin_state())
            self._refresh_security_ui()
        except Exception as exc:
            self.view.show_error("Security", f"Could not open security administration: {exc}")

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

    def open_developer_admin_dialog(self):
        if not gatekeeper.has_admin_session():
            self.view.show_error("Developer Tools", "An admin session is required to open developer tools.")
            return

        self.view.show_developer_admin_dialog(
            {
                "update_repository_url": self.model.settings.get("update_repository_url", ""),
                "enable_advanced_dev_updates": bool(self.model.settings.get("enable_advanced_dev_updates", False)),
                "enable_external_override_trust": gatekeeper.is_external_module_override_trust_enabled(),
            },
            self.dispatcher.get_bundled_module_names(),
        )

    def get_external_module_editor_state(self, module_name):
        if not module_name:
            return {
                "text": "",
                "status": "Choose a bundled module to inspect or override.",
                "source": "None",
            }

        override_path = self.dispatcher.get_external_module_override_path(module_name)
        if override_path and os.path.exists(override_path):
            with open(override_path, "r", encoding="utf-8") as handle:
                status = f"Editing external override: {override_path}"
                if not self.dispatcher.is_external_module_override_trust_enabled():
                    status = f"Editing external override: {override_path}. This file is currently inactive until an admin enables override trust."
                return {
                    "text": handle.read(),
                    "status": status,
                    "source": "External override",
                }

        bundled_path = os.path.join(self.dispatcher.modules_path, f"{module_name}.py")
        if os.path.exists(bundled_path):
            with open(bundled_path, "r", encoding="utf-8") as handle:
                return {
                    "text": handle.read(),
                    "status": f"Editing bundled source preview for {module_name}. Saving will create an external override.",
                    "source": "Bundled module",
                }

        return {
            "text": "",
            "status": f"No bundled module source was found for {module_name}.",
            "source": "Unavailable",
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

    def save_external_module_override(self, module_name, module_text):
        if not module_name:
            self.view.show_error("Developer Tools", "Choose a module before saving an override.")
            return False
        self.dispatcher.install_module_override(module_name, module_text)
        self.refresh_external_modules_status()
        self.refresh_developer_admin_status()
        if self.dispatcher.is_external_module_override_trust_enabled():
            self.view.show_toast("Developer Tools", f"Saved external override for {module_name}. It is eligible to load on module reload.")
        else:
            self.view.show_toast("Developer Tools", f"Saved external override for {module_name}. It will stay inactive until override trust is enabled.")
        return True

    def remove_external_module_override(self, module_name):
        if not module_name:
            self.view.show_error("Developer Tools", "Choose a module before removing an override.")
            return False
        removed_paths = self.dispatcher.remove_external_module_overrides([module_name])
        self.refresh_external_modules_status()
        self.refresh_developer_admin_status()
        if removed_paths:
            self.view.show_toast("Developer Tools", f"Removed external override for {module_name}.")
            return True
        self.view.show_info("Developer Tools", f"No external override exists for {module_name}.")
        return False

    def _build_settings_from_form(self):
        form_values = self.view.collect_form_values()
        settings = self.model.get_settings_copy()
        settings.update(form_values)

        numeric_fields = [
            "auto_save_interval_min",
            "default_shift_hours",
            "default_goal_mph",
            "toast_duration_sec",
            "screen_transition_duration_ms",
        ]
        for key in numeric_fields:
            value = settings.get(key)
            try:
                settings[key] = float(value) if isinstance(value, str) and "." in value else int(value)
            except Exception as exc:
                log_exception(f"settings_manager.invalid_numeric.{key}", exc)

        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
        return self.model.normalize_settings(settings)

    def persist_settings(self, toast_title="Settings Saved", toast_message_prefix="Theme changes were applied immediately."):
        clear_downtime_code_cache()
        backup_info = write_json_with_backup(
            self.model.settings_path,
            self.model.settings,
            backup_dir=external_path("data/backups/settings"),
            keep_count=12,
        )

        self.model.commit_theme()
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
        self.refresh_external_modules_status()
        self.refresh_security_status()
        self.refresh_developer_admin_status()
        self.refresh_persistent_modules_summary()

    def save_settings(self):
        self.model.update_settings(self._build_settings_from_form())
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
        current_codes = self.model.settings.get("downtime_codes", deepcopy(DEFAULT_DT_CODE_MAP))
        self.view.show_downtime_codes_dialog(current_codes)

    def save_downtime_codes(self, updated_codes):
        self.model.update_downtime_codes(updated_codes)
        self.persist_settings(
            toast_title="Downtime Codes Saved",
            toast_message_prefix="Downtime code labels were updated immediately.",
        )

    def open_persistent_modules_dialog(self):
        options = self.dispatcher.get_persistable_modules()
        selected_modules = set(self.dispatcher.normalize_persistent_modules(self.model.settings.get("persistent_modules", [])))
        self.view.show_persistent_modules_dialog(options, selected_modules)

    def open_module_whitelist_dialog(self):
        options = self.dispatcher.get_navigation_modules()
        selected_modules = set(self.dispatcher.normalize_module_whitelist(self.model.settings.get("module_whitelist", [])))
        self.view.show_module_whitelist_dialog(options, selected_modules)

    def save_persistent_modules_selection(self, selected_modules):
        self.model.settings["persistent_modules"] = self.dispatcher.normalize_persistent_modules(selected_modules)
        self.refresh_persistent_modules_summary()

    def save_module_whitelist_selection(self, selected_modules):
        self.model.settings["module_whitelist"] = self.dispatcher.normalize_module_whitelist(selected_modules)
        self.refresh_module_whitelist_summary()

    def on_unload(self):
        if self.model.preview_theme != self.model.saved_theme:
            self.dispatcher.apply_theme(self.model.saved_theme)
