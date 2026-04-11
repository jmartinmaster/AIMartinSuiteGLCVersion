from app.controllers.help_viewer_controller import HelpViewerController

__module_name__ = "Help Viewer"
__version__ = "1.0.0"


def get_ui(parent, dispatcher):
    return HelpViewerController(parent, dispatcher)