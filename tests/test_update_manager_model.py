import importlib
import sys
import types
import unittest
from unittest.mock import patch


def _load_update_manager_model():
    # update_manager_model imports app_platform, which imports PIL at module load time.
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


if __name__ == "__main__":
    unittest.main()
