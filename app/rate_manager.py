from app.controllers.rate_manager_controller import RateManagerController

__module_name__ = "Rate Manager"
__version__ = "1.0.0"


def get_ui(parent, dispatcher):
    return RateManagerController(parent, dispatcher)