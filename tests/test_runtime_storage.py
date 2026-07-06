import json
import os
import tempfile
import unittest
from unittest import mock

from app import utils as path_utils
from app.models.app_model import AppModel


class TestRuntimeStorage(unittest.TestCase):
    def _backup_policy(self):
        return {
            "enabled": True,
            "interval_min": 30,
            "keep_count": 12,
            "draft_auto_save_interval_min": 5,
            "draft_history_keep_count": 20,
            "target_overrides": {},
        }

    def _build_app_model(self):
        return AppModel(
            modules_path="bundled-app",
            external_modules_path="external-modules",
            layout_config="layout-config",
            rate_config="rate-config",
            settings_path="settings-path",
        )

    def test_windows_external_base_uses_local_app_data(self):
        with mock.patch.object(path_utils.sys, "platform", "win32"):
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"}, clear=False):
                expected_path = os.path.join(r"C:\Users\Test\AppData\Local", "production-logging-center-glc")
                self.assertEqual(path_utils.external_base_path(), expected_path)

    def test_linux_external_base_uses_xdg_data_home(self):
        with mock.patch.object(path_utils.sys, "platform", "linux"):
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/runtime-data-home"}, clear=False):
                expected_path = os.path.join("/tmp/runtime-data-home", "production-logging-center-glc")
                self.assertEqual(path_utils.external_base_path(), expected_path)

    def test_external_path_migrates_legacy_runtime_data(self):
        with tempfile.TemporaryDirectory() as legacy_root, tempfile.TemporaryDirectory() as appdata_home:
            legacy_path = os.path.join(legacy_root, "data", "config", "settings.json")
            os.makedirs(os.path.dirname(legacy_path), exist_ok=True)
            with open(legacy_path, "w", encoding="utf-8") as handle:
                json.dump({"theme": "martin_modern_light"}, handle)

            with mock.patch.object(path_utils.sys, "platform", "win32"):
                with mock.patch.object(path_utils, "source_root_path", return_value=legacy_root):
                    with mock.patch.dict(os.environ, {"LOCALAPPDATA": appdata_home}, clear=False):
                        migrated_path = path_utils.external_path(os.path.join("data", "config", "settings.json"))

            self.assertTrue(os.path.exists(migrated_path))
            self.assertFalse(os.path.exists(legacy_path))
            with open(migrated_path, "r", encoding="utf-8") as handle:
                self.assertEqual(json.load(handle), {"theme": "martin_modern_light"})

    def test_integrity_policy_is_written_encrypted(self):
        with tempfile.TemporaryDirectory() as legacy_root, tempfile.TemporaryDirectory() as appdata_home:
            with mock.patch.object(path_utils.sys, "platform", "win32"):
                with mock.patch.object(path_utils, "source_root_path", return_value=legacy_root):
                    with mock.patch.dict(os.environ, {"LOCALAPPDATA": appdata_home}, clear=False):
                        with mock.patch("app.persistence._load_backup_policy", return_value=self._backup_policy()):
                            model = self._build_app_model()
                            policy_path = model._save_integrity_policy({"module_records": {"about": {"hashes": {"app/about.py": "abc"}}}})

                            with open(policy_path, "r", encoding="utf-8") as handle:
                                payload = json.load(handle)

                            self.assertEqual(payload.get("encoding"), "fernet-json-v1")
                            self.assertTrue(str(payload.get("ciphertext") or "").strip())
                            self.assertNotIn("module_records", payload)
                            self.assertEqual(
                                model._load_integrity_policy(),
                                {"module_records": {"about": {"hashes": {"app/about.py": "abc"}}}},
                            )

    def test_plaintext_integrity_policy_is_migrated_to_encrypted_storage(self):
        with tempfile.TemporaryDirectory() as legacy_root, tempfile.TemporaryDirectory() as appdata_home:
            with mock.patch.object(path_utils.sys, "platform", "win32"):
                with mock.patch.object(path_utils, "source_root_path", return_value=legacy_root):
                    with mock.patch.dict(os.environ, {"LOCALAPPDATA": appdata_home}, clear=False):
                        with mock.patch("app.persistence._load_backup_policy", return_value=self._backup_policy()):
                            model = self._build_app_model()
                            policy_path = model._integrity_policy_path()
                            os.makedirs(os.path.dirname(policy_path), exist_ok=True)
                            with open(policy_path, "w", encoding="utf-8") as handle:
                                json.dump({"module_records": {"about": {"hashes": {"app/about.py": "abc"}}}}, handle, indent=2)

                            self.assertEqual(
                                model._load_integrity_policy(),
                                {"module_records": {"about": {"hashes": {"app/about.py": "abc"}}}},
                            )
                            with open(policy_path, "r", encoding="utf-8") as handle:
                                payload = json.load(handle)
                            self.assertEqual(payload.get("encoding"), "fernet-json-v1")
                            self.assertTrue(str(payload.get("ciphertext") or "").strip())
                            self.assertNotIn("module_records", payload)


if __name__ == "__main__":
    unittest.main()
