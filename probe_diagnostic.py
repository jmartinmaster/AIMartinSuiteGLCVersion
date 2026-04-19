import sys
import os
import traceback
import types
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.abspath(os.getcwd())
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout

# Import actual components from the project based on validator
try:
    import launcher
    from app.controllers.app_controller import Dispatcher
    from app.security import gatekeeper
    from app.views.pyqt6_host_shell_view import PyQt6HostShellView
except ImportError:
    print("Failed to import host components from the current path.")
    traceback.print_exc()
    sys.exit(1)

PHASE_GATE_PERSISTENT = "__phase_gate_persistent__"
PROBE_MODULE_NAMES = {PHASE_GATE_PERSISTENT}
PROBE_DISPLAY_NAMES = {PHASE_GATE_PERSISTENT: "Phase Gate Persistent"}

def build_probe_module(module_name, event_log):
    module = types.SimpleNamespace()
    module.__module_name__ = PROBE_DISPLAY_NAMES[module_name]
    module.__version__ = "0.1.0"
    def get_ui(parent, dispatcher, _module_name=module_name):
        event_log.append(f"get_ui called for {_module_name}")
        label = QLabel(f"Probe module: {_module_name}", parent)
        if parent.layout():
            parent.layout().addWidget(label)
        return MagicMock() # Return a mock controller
    module.get_ui = get_ui
    return module

def run_diagnostic():
    # Use launcher to create app as in validator
    app = launcher.create_qt_application(theme_name="martin_modern_light")
    
    runtime_settings = {
        "ui_shell_backend": "pyqt6",
        "active_ui_shell_backend": "pyqt6",
        "persistent_modules": [PHASE_GATE_PERSISTENT],
    }

    # Patch items exactly like the validator
    with patch.object(Dispatcher, 'notify_non_secure_mode_state'), \
         patch.object(Dispatcher, 'notify_external_override_policy_state'), \
         patch.object(Dispatcher, 'prompt_old_executable_cleanup'), \
         patch.object(Dispatcher, 'check_for_available_module_updates'), \
         patch.object(Dispatcher, 'start_module_preloader'), \
         patch.object(Dispatcher, 'schedule_layout_manager_preload'):
        
        gatekeeper.logout()
        
        host_shell = PyQt6HostShellView(
            theme_name="martin_modern_light",
            runtime_settings=runtime_settings,
            initial_module_name="about",
        )
        
        dispatcher = Dispatcher(
            host_shell,
            initial_module_name="about",
            runtime_settings_override=runtime_settings,
            host_ui_adapter_factory=lambda backend, _dispatcher: host_shell.host_ui_adapter if backend == "pyqt6" else None,
            shell_view_factory=lambda root, _update_coordinator, _dispatcher: root,
        )

        # Event log for probe module
        event_log = []

        # Patch dispatcher methods for diagnostics
        dispatcher._show_notification = MagicMock()
        dispatcher._clear_notification = MagicMock()
        dispatcher._show_preloader = MagicMock()
        dispatcher._hide_preloader = MagicMock()

        original_import = dispatcher.import_managed_module
        def patched_import(module_name, **kwargs):
            if module_name == PHASE_GATE_PERSISTENT:
                return build_probe_module(module_name, event_log)
            return original_import(module_name, **kwargs)
        
        dispatcher.import_managed_module = patched_import
        dispatcher.should_use_qt_in_viewport = lambda m: m == PHASE_GATE_PERSISTENT or False
        dispatcher.get_module_display_name = lambda m: PROBE_DISPLAY_NAMES.get(m, m)
        host_shell._ensure_runtime_manager = MagicMock()

        try:
            # Load the module
            dispatcher.load_module(PHASE_GATE_PERSISTENT, use_transition=False, ensure_authorized=False)
            app.processEvents()
        except Exception:
            print("Traceback during load_module:")
            traceback.print_exc()

        # Print diagnostics
        print(f"dispatcher.active_module_name: {dispatcher.active_module_name}")
        print(f"repr(dispatcher.active_module_instance): {repr(dispatcher.active_module_instance)}")
        print(f"repr(dispatcher.active_module_container): {repr(dispatcher.active_module_container)}")
        
        # event_log for this diagnostic is a list of events from the probe
        exists_in_event_log = any(PHASE_GATE_PERSISTENT in entry for entry in event_log)
        print(f"exists_in_event_log: {exists_in_event_log}")
        
        try:
            print(f"host_shell.viewport_title_label.text(): {host_shell.viewport_title_label.text()}")
            print(f"host_shell.viewport_subtitle_label.text(): {host_shell.viewport_subtitle_label.text()}")
            print(f"host_shell.viewport_hint_label.text(): {host_shell.viewport_hint_label.text()}")
        except AttributeError as e:
            print(f"Error accessing labels: {e}")

if __name__ == '__main__':
    run_diagnostic()
