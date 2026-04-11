from app.controllers.about_controller import AboutController

__module_name__ = "About System"
__version__ = "1.0.0"


def get_ui(parent, dispatcher):
    return AboutController(parent, dispatcher)