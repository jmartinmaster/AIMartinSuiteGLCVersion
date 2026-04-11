from app.controllers.settings_manager_controller import SettingsManagerController

__module_name__ = "Settings Manager"
__version__ = "1.0.0"


def get_ui(parent, dispatcher):
    return SettingsManagerController(parent, dispatcher)