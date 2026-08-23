import unittest
from unittest import mock
import os

from app.models.production_log_model import ProductionLogModel
from app.data_handler_service import DataHandlerService
from app.production_log_roles import (
    HEADER_FIELD_ROLE_DEFAULTS,
    HEADER_BLANK_IGNORE_ROLES,
)


class TestHeaderOverride(unittest.TestCase):
    def setUp(self):
        self.model = ProductionLogModel()
        self.data_handler = self.model.data_handler

    def test_header_override_role_registered(self):
        self.assertEqual(HEADER_FIELD_ROLE_DEFAULTS.get("header_override"), "header_override_toggle")
        self.assertIn("header_override_toggle", HEADER_BLANK_IGNORE_ROLES)

    def test_is_header_override_enabled(self):
        self.assertFalse(self.model.is_header_override_enabled({}))
        self.assertFalse(self.model.is_header_override_enabled({"header_override": "False"}))
        self.assertFalse(self.model.is_header_override_enabled({"header_override": False}))
        self.assertTrue(self.model.is_header_override_enabled({"header_override": "True"}))
        self.assertTrue(self.model.is_header_override_enabled({"header_override": True}))
        self.assertTrue(self.model.is_header_override_enabled({"header_override": "1"}))
        self.assertTrue(self.model.is_header_override_enabled({"header_override": "yes"}))

    def test_autofill_when_header_override_disabled(self):
        header_data = {
            "date": "2026-08-23",
            "shift": "1",
            "hours": "8",
            "header_override": "False",
            "start_time": "9999",  # Attempt manual value while override is disabled
            "end_time": "9999",
        }
        normalized = self.data_handler.normalize_header_data(header_data)
        # Shift 1 8 hours standard window is 0600 -> 1400
        self.assertEqual(normalized.get("start_time"), "0600")
        self.assertEqual(normalized.get("end_time"), "1400")
        self.assertEqual(normalized.get("target_time"), "480 min")
        self.assertEqual(normalized.get("header_override"), "False")

    def test_preserve_manual_times_when_header_override_enabled(self):
        header_data = {
            "date": "2026-08-23",
            "shift": "1",
            "hours": "8",
            "header_override": "True",
            "start_time": "07:30",
            "end_time": "15:30",
            "target_time": "450 min",
        }
        normalized = self.data_handler.normalize_header_data(header_data)
        self.assertEqual(normalized.get("start_time"), "0730")
        self.assertEqual(normalized.get("end_time"), "1530")
        self.assertEqual(normalized.get("target_time"), "450 min")
        self.assertEqual(normalized.get("header_override"), "True")

    def test_fallback_to_computed_when_override_enabled_but_blank(self):
        header_data = {
            "date": "2026-08-23",
            "shift": "1",
            "hours": "8",
            "header_override": "True",
            "start_time": "",
            "end_time": "",
            "target_time": "",
        }
        normalized = self.data_handler.normalize_header_data(header_data)
        # Blank inputs fall back to computed shift window
        self.assertEqual(normalized.get("start_time"), "0600")
        self.assertEqual(normalized.get("end_time"), "1400")
        self.assertEqual(normalized.get("target_time"), "480 min")

    def test_form_blank_detection_ignores_header_override_toggle(self):
        # A form containing only header_override set should still be recognized as blank
        payload = {
            "header": {
                "date": "",
                "shift": "",
                "hours": "8",
                "goal_mph": "240",
                "header_override": "True",
            },
            "production": [],
            "downtime": [],
        }
        self.assertTrue(self.model.is_form_blank(payload))

    def test_view_controller_header_override_integration(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from app.views.pyqt6_host_shell_view import PyQt6HostShellView
        from app.controllers.app_controller import Dispatcher
        from launcher import create_qt_application

        app = create_qt_application()
        host_shell = PyQt6HostShellView(theme_name="darkly", runtime_settings={"ui_shell_backend": "pyqt6"})
        dispatcher = Dispatcher(
            host_shell,
            runtime_settings_override={"ui_shell_backend": "pyqt6", "active_ui_shell_backend": "pyqt6"},
            host_ui_adapter_factory=lambda backend, _d: host_shell.host_ui_adapter if backend == "pyqt6" else None,
            shell_view_factory=lambda root, _u, _d: root,
        )

        dispatcher.load_module("production_log", use_transition=False)
        prod_controller = dispatcher.active_module_instance or dispatcher.module_registry.get("production_log")
        prod_view = prod_controller.view

        override_widget = prod_view.header_widgets.get("header_override")
        start_widget = prod_view.header_widgets.get("start_time")
        end_widget = prod_view.header_widgets.get("end_time")

        self.assertIsNotNone(override_widget)
        self.assertFalse(override_widget.isChecked())

        # 1. Override off: autofills 0600 -> 1400
        prod_view.set_header_field_value("shift", "1")
        prod_view.set_header_field_value("hours", "8")
        prod_controller.on_header_field_focus_out()
        self.assertEqual(start_widget.text(), "0600")
        self.assertEqual(end_widget.text(), "1400")

        # 2. Toggle override on: fields become editable
        override_widget.setChecked(True)
        prod_controller.on_header_override_toggled()
        self.assertFalse(start_widget.isReadOnly())

        # 3. User enters custom times
        prod_view.set_header_field_value("start_time", "0730")
        prod_view.set_header_field_value("end_time", "1530")
        prod_controller.on_header_field_focus_out()
        self.assertEqual(start_widget.text(), "0730")
        self.assertEqual(end_widget.text(), "1530")

        # 4. Metrics calculation does not overwrite user's custom times
        prod_controller.calculate_metrics()
        self.assertEqual(start_widget.text(), "0730")
        self.assertEqual(end_widget.text(), "1530")

        # 5. Toggle override off: re-locks and recalculates to shift window
        override_widget.setChecked(False)
        prod_controller.on_header_override_toggled()
        self.assertEqual(start_widget.text(), "0600")
        self.assertEqual(end_widget.text(), "1400")


if __name__ == "__main__":
    unittest.main()

