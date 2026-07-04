import sys
import types
import unittest
from unittest.mock import patch


if "PIL" not in sys.modules:
    # update_manager_model imports app_platform, which imports PIL at module load time.
    pil_module = types.ModuleType("PIL")
    image_module = types.ModuleType("PIL.Image")
    pil_module.Image = image_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = image_module


from app.models.update_manager_model import _build_raw_github_url, probe_remote_executable


class _DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestUpdateManagerModel(unittest.TestCase):
    def test_build_raw_github_url_percent_encodes_spaced_artifact(self):
        url = _build_raw_github_url(
            "jmartinmaster",
            "AIMartinSuiteGLCVersion",
            "main",
            "dist/Production Logging Center_GLC_v2.4.4.exe",
        )

        self.assertIn("dist/Production%20Logging%20Center_GLC_v2.4.4.exe", url)
        self.assertNotIn("dist/Production Logging Center_GLC_v2.4.4.exe", url)

    @patch("app.models.update_manager_model.urllib.request.urlopen", return_value=_DummyResponse())
    def test_probe_remote_executable_uses_encoded_head_url(self, mock_urlopen):
        row = {
            "remote_version": "2.4.4",
            "remote_exe_name": "Production Logging Center_GLC_v2.4.4.exe",
        }

        remote_path, resolved_name = probe_remote_executable(
            {"owner": "jmartinmaster", "repo": "AIMartinSuiteGLCVersion"},
            "main",
            row,
            "exe",
            lambda version_text: f"Production Logging Center_GLC_v{version_text}.exe",
        )

        self.assertEqual(remote_path, "dist/Production Logging Center_GLC_v2.4.4.exe")
        self.assertEqual(resolved_name, "Production Logging Center_GLC_v2.4.4.exe")

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


if __name__ == "__main__":
    unittest.main()
