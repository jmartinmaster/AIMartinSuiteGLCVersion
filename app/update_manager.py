from app.controllers.update_manager_controller import UpdateManagerController, scan_available_module_payload_updates

__module_name__ = "Update Manager"
__version__ = "2.1.2"


def get_ui(parent, dispatcher):
    return UpdateManagerController(parent, dispatcher)