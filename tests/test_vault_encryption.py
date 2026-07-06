import json
import os
import tempfile
import unittest
from unittest import mock

from app.security import Gatekeeper
from app.security_service import SecurityService


class TestVaultEncryption(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_dir = os.path.join(self.temp_dir.name, "vaults")
        self.security_backup_dir = os.path.join(self.temp_dir.name, "backups", "settings")
        os.makedirs(self.vault_dir, exist_ok=True)
        self.key_path = os.path.join(self.temp_dir.name, "vaults.key")
        self.security_settings_path = os.path.join(self.temp_dir.name, "security_settings.json")
        self.backup_policy_patcher = mock.patch(
            "app.persistence._load_backup_policy",
            return_value={
                "enabled": True,
                "interval_min": 30,
                "keep_count": 12,
                "draft_auto_save_interval_min": 5,
                "draft_history_keep_count": 20,
                "target_overrides": {},
            },
        )
        self.backup_policy_patcher.start()

        Gatekeeper._instance = None
        self.gatekeeper = Gatekeeper()
        self.gatekeeper._vault_directory = lambda: self.vault_dir
        self.gatekeeper._vault_key_path = lambda: self.key_path
        self.gatekeeper._security_settings_path = self.security_settings_path
        self.gatekeeper._security_settings_backup_directory = lambda: self.security_backup_dir
        self.gatekeeper._security_settings = self.gatekeeper._load_security_settings()

    def tearDown(self):
        self.gatekeeper.logout()
        Gatekeeper._instance = None
        self.backup_policy_patcher.stop()
        self.temp_dir.cleanup()

    def test_new_vault_is_written_encrypted(self):
        rights = self.gatekeeper.get_role_default_rights("admin")
        vault_record = self.gatekeeper.create_or_update_vault(
            "admin_1",
            "admin",
            rights,
            "StrongAA!123",
            enabled=True,
        )

        self.assertTrue(vault_record.path and os.path.exists(vault_record.path))
        with open(vault_record.path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertEqual(payload.get("encoding"), "fernet-json-v1")
        self.assertTrue(str(payload.get("ciphertext") or "").strip())
        self.assertNotIn("vault_name", payload)
        self.assertTrue(os.path.exists(self.key_path))

        loaded = self.gatekeeper._load_vault_record(vault_record.path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.vault_name, "admin_1")

    def test_plaintext_vault_is_migrated_to_encrypted_storage(self):
        hashed = self.gatekeeper._hash_password("StrongAA!123")
        plaintext_payload = {
            "version": 2,
            "vault_name": "admin_1",
            "display_name": "admin_1",
            "role": "admin",
            "enabled": True,
            "password_required": True,
            "requires_yubikey": False,
            "rights": self.gatekeeper.get_role_default_rights("admin"),
            "hash_scheme": hashed["hash_scheme"],
            "password_hash": hashed["password_hash"],
            "password_salt": hashed["password_salt"],
            "password_iterations": hashed["password_iterations"],
            "created_at": "2026-07-05T00:00:00Z",
            "updated_at": "2026-07-05T00:00:00Z",
        }
        vault_path = os.path.join(self.vault_dir, "admin_1.vault")
        with open(vault_path, "w", encoding="utf-8") as handle:
            json.dump(plaintext_payload, handle, indent=2)

        loaded = self.gatekeeper._load_vault_record(vault_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.vault_name, "admin_1")

        with open(vault_path, "r", encoding="utf-8") as handle:
            migrated_payload = json.load(handle)
        self.assertEqual(migrated_payload.get("encoding"), "fernet-json-v1")
        self.assertTrue(str(migrated_payload.get("ciphertext") or "").strip())
        self.assertNotIn("vault_name", migrated_payload)

    def test_security_settings_are_written_encrypted(self):
        self.gatekeeper._save_security_settings(
            {
                "non_secure_mode": False,
                "external_module_override_trust": True,
                "non_secure_bypass_modules": ["settings_manager"],
                "role_default_rights": {"developer": ["developer:update_configuration"]},
            }
        )

        with open(self.security_settings_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertEqual(payload.get("encoding"), "fernet-json-v1")
        self.assertTrue(str(payload.get("ciphertext") or "").strip())
        self.assertNotIn("non_secure_mode", payload)

    def test_plaintext_security_settings_are_migrated_to_encrypted_storage(self):
        with open(self.security_settings_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "non_secure_mode": False,
                    "external_module_override_trust": True,
                    "non_secure_bypass_modules": ["settings_manager"],
                    "role_default_rights": {"developer": ["developer:update_configuration"]},
                },
                handle,
                indent=2,
            )

        settings = self.gatekeeper._load_security_settings()
        self.assertFalse(settings["non_secure_mode"])
        self.assertTrue(settings["external_module_override_trust"])
        self.assertEqual(settings["non_secure_bypass_modules"], ["settings_manager"])

        with open(self.security_settings_path, "r", encoding="utf-8") as handle:
            migrated_payload = json.load(handle)
        self.assertEqual(migrated_payload.get("encoding"), "fernet-json-v1")
        self.assertTrue(str(migrated_payload.get("ciphertext") or "").strip())
        self.assertNotIn("non_secure_mode", migrated_payload)

    def test_security_defaults_to_non_secure_mode(self):
        self.assertTrue(self.gatekeeper.is_non_secure_mode_enabled())

    def test_non_secure_mode_grants_full_access(self):
        self.gatekeeper.logout()
        self.gatekeeper.set_non_secure_mode(True)

        self.assertTrue(self.gatekeeper.has_right("security:manage_vaults"))
        self.assertTrue(self.gatekeeper.authenticate(required_right="developer:update_configuration"))

        service = SecurityService(protected_modules={"settings_manager"})
        self.assertTrue(service.can_access_module("settings_manager"))
        self.assertTrue(service.authenticate_module("settings_manager"))

    def test_secure_mode_auto_logs_into_passwordless_general_vault(self):
        self.gatekeeper.create_or_update_vault(
            "general_open",
            "general",
            self.gatekeeper.get_role_default_rights("general"),
            "StrongAA!123",
            enabled=True,
            password_required=False,
        )
        self.gatekeeper.set_non_secure_mode(False)
        self.gatekeeper.logout()

        authenticated = self.gatekeeper.authenticate(required_right=None)
        self.assertTrue(authenticated)
        session = self.gatekeeper.get_session()
        self.assertIsNotNone(session)
        self.assertEqual(session.vault_name, "general_open")
        self.assertEqual(session.role, "general")

    def test_non_secure_mode_converts_default_general_vault_to_passwordless(self):
        self.gatekeeper.create_or_update_vault(
            "general_default",
            "general",
            self.gatekeeper.get_role_default_rights("general"),
            "StrongAA!123",
            enabled=True,
            password_required=True,
        )

        self.gatekeeper.set_non_secure_mode(True)

        default_vault = self.gatekeeper._find_vault("general_default")
        self.assertIsNotNone(default_vault)
        self.assertFalse(bool(default_vault.password_required))


if __name__ == "__main__":
    unittest.main()
