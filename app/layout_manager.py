from app.controllers.layout_manager_controller import LayoutManagerController

__module_name__ = "Layout Manager"
__version__ = "1.0.4"


def get_ui(parent, dispatcher):
    return LayoutManagerController(parent, dispatcher)