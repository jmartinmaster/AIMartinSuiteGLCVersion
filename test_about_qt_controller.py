import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent


class _FakeAboutQtView:
    def __init__(self, *_args, **_kwargs):
        pass

    def show(self):
        return None


sys.modules.setdefault(
    "app.views.about_qt_view",
    types.SimpleNamespace(AboutQtView=_FakeAboutQtView),
)

about_qt_controller = importlib.import_module("app.controllers.about_qt_controller")


class _RegistryStub:
    def __init__(self, modules):
        self._modules = list(modules)

    def list_modules(self):
        return list(self._modules)


class _DispatcherStub:
    def __init__(self, modules, loaded_modules=None):
        self.module_registry = _RegistryStub(modules)
        self.loaded_modules = dict(loaded_modules or {})
        self.external_modules_path = "/tmp/external_modules"

    def is_module_loaded_from_external(self, _module_name, _module_obj=None):
        return False

    def are_external_module_overrides_enabled(self):
        return False


class AboutQtControllerManifestTests(unittest.TestCase):
    def test_manifest_lists_main_and_all_registered_modules(self):
        registered_modules = json.loads((REPO_ROOT / "app" / "module_registry.json").read_text(encoding="utf-8"))["modules"]
        dispatcher = _DispatcherStub(
            registered_modules,
            loaded_modules={
                "main": types.SimpleNamespace(__module_name__="Dispatcher Core", __version__="2.4.4"),
            },
        )
        controller = about_qt_controller.AboutQtController.__new__(about_qt_controller.AboutQtController)
        controller.dispatcher = dispatcher

        manifest_rows = controller.get_manifest_rows()

        self.assertEqual(len(manifest_rows), len(registered_modules) + 1)
        self.assertTrue(any(row["module_name"] == "main" and row["version"] == "2.4.4" for row in manifest_rows))
        self.assertTrue(
            any(
                row["module_name"] == "about"
                and row["display_name"] == "About System"
                and row["version"] == "1.0.1"
                for row in manifest_rows
            )
        )
        self.assertTrue(any(row["module_name"] == "update_manager" for row in manifest_rows))

    def test_manifest_falls_back_to_controller_version_when_shim_version_missing(self):
        dispatcher = _DispatcherStub(
            [
                {
                    "name": "fallback_module",
                    "module_path": "app.fallback_module",
                    "display_name": "Fallback Module",
                }
            ]
        )
        controller = about_qt_controller.AboutQtController.__new__(about_qt_controller.AboutQtController)
        controller.dispatcher = dispatcher

        def fake_read_module_metadata(module_path):
            if module_path == "app.fallback_module":
                return {"display_name": "Fallback Module", "version": ""}
            if module_path == "app.controllers.fallback_module_qt_controller":
                return {"display_name": "Fallback Qt Controller", "version": "9.9.9"}
            return {}

        with mock.patch.object(controller, "_read_module_metadata", side_effect=fake_read_module_metadata):
            manifest_rows = controller.get_manifest_rows()

        self.assertEqual(len(manifest_rows), 1)
        self.assertEqual(manifest_rows[0]["module_name"], "fallback_module")
        self.assertEqual(manifest_rows[0]["display_name"], "Fallback Module")
        self.assertEqual(manifest_rows[0]["version"], "9.9.9")


if __name__ == "__main__":
    unittest.main()
