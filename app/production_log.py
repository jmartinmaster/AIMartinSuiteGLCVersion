from app.controllers.production_log_controller import ProductionLogController

__module_name__ = "Production Log"
__version__ = "1.2.5"


def get_ui(parent, dispatcher):
    return ProductionLogController(parent, dispatcher)