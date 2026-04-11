from app.controllers.recovery_viewer_controller import RecoveryViewerController

__module_name__ = "Backup / Recovery"
__version__ = "1.0.0"


def get_ui(parent, dispatcher):
    return RecoveryViewerController(parent, dispatcher)