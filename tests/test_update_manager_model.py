import importlib
import sys
import types
import urllib.error
import unittest
from unittest.mock import patch


def _load_update_manager_model():
    # update_manager_model imports app_platform, which imports PIL at module load time.
    # These URL-construction tests never touch PIL APIs, so a minimal stub keeps the
    # import isolated without requiring the full imaging dependency in test envs.
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")
    pil_module.Image = image_module
    with patch.dict(sys.modules, {"PIL": pil_module, "PIL.Image": image_module}):
        return importlib.import_module("app.models.update_manager_model")


update_manager_model = _load_update_manager_model()


class _MockContextManagerResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestUpdateManagerModel(unittest.TestCase):
    def test_detect_branch_name_defaults_to_main_for_stable_channel(self):
        with patch.object(update_manager_model, "_load_external_settings_payload", return_value={"release_channel": "stable"}):
            self.assertEqual(update_manager_model._detect_branch_name(), "main")

    def test_detect_branch_name_uses_development_branch_for_dev_channel(self):
        with patch.object(update_manager_model, "_load_external_settings_payload", return_value={"release_channel": "dev"}):
            self.assertEqual(update_manager_model._detect_branch_name(), "Development")

    def test_detect_branch_name_falls_back_to_stable_for_unknown_channel(self):
        with patch.object(update_manager_model, "_load_external_settings_payload", return_value={"release_channel": "preview"}):
            self.assertEqual(update_manager_model._detect_branch_name(), "main")

    def test_build_raw_github_url_percent_encodes_spaced_artifact(self):
        url = update_manager_model._build_raw_github_url(
            "jmartinmaster",
            "AIMartinSuiteGLCVersion",
            "main",
            "dist/Production Logging Center_GLC_v2.4.4.exe",
        )

        self.assertIn("dist/Production%20Logging%20Center_GLC_v2.4.4.exe", url)
        self.assertNotIn("dist/Production Logging Center_GLC_v2.4.4.exe", url)

    def test_probe_remote_executable_uses_encoded_head_url(self):
        row = {
            "remote_version": "2.4.4",
            "remote_exe_name": "Production Logging Center_GLC_v2.4.4.exe",
        }

        with patch.object(
            update_manager_model.urllib.request,
            "urlopen",
            return_value=_MockContextManagerResponse(),
        ) as mock_urlopen:
            remote_path, resolved_name = update_manager_model.probe_remote_executable(
                {"owner": "jmartinmaster", "repo": "AIMartinSuiteGLCVersion"},
                "main",
                row,
                "exe",
                lambda version_text: f"Production Logging Center_GLC_v{version_text}.exe",
            )

            self.assertEqual(remote_path, "dist/Production Logging Center_GLC_v2.4.4.exe")
            self.assertEqual(resolved_name, "Production Logging Center_GLC_v2.4.4.exe")

            mock_urlopen.assert_called_once()
            request = mock_urlopen.call_args.args[0]
            self.assertEqual(request.get_method(), "HEAD")
            self.assertIn(
                "dist/Production%20Logging%20Center_GLC_v2.4.4.exe",
                request.full_url,
            )
            self.assertNotIn(
                "dist/Production Logging Center_GLC_v2.4.4.exe",
                request.full_url,
            )

    def test_probe_remote_executable_falls_back_to_variants_public_path(self):
        row = {
            "remote_version": "2.4.7",
            "remote_exe_name": "Production Logging Center_GLC_v2.4.7.exe",
        }
        not_found = urllib.error.HTTPError(
            url="https://raw.githubusercontent.com/example",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )
        requests = []

        def _mock_urlopen(request, timeout=15):
            requests.append(request.full_url)
            if len(requests) == 1:
                raise not_found
            return _MockContextManagerResponse()

        with patch.object(update_manager_model.urllib.request, "urlopen", side_effect=_mock_urlopen):
            remote_path, resolved_name = update_manager_model.probe_remote_executable(
                {"owner": "jmartinmaster", "repo": "AIMartinSuiteGLCVersion"},
                "main",
                row,
                "exe",
                lambda version_text: f"Production Logging Center_GLC_v{version_text}.exe",
            )

        self.assertEqual(
            remote_path,
            "dist/variants/public/Production Logging Center_GLC_v2.4.7.exe",
        )
        self.assertEqual(resolved_name, "Production Logging Center_GLC_v2.4.7.exe")
        self.assertEqual(len(requests), 2)
        self.assertIn(
            "dist/Production%20Logging%20Center_GLC_v2.4.7.exe",
            requests[0],
        )
        self.assertIn(
            "dist/variants/public/Production%20Logging%20Center_GLC_v2.4.7.exe",
            requests[1],
        )


if __name__ == "__main__":
    unittest.main()
