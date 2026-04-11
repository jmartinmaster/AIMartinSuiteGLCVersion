from app.models.production_log_model import ProductionLogModel
from app.views.production_log_view import ProductionLogView


class ProductionLogController:
    def __init__(self, parent, dispatcher):
        self.model = ProductionLogModel()
        self.view = ProductionLogView(parent, dispatcher, self.model)

    def __getattr__(self, attribute_name):
        return getattr(self.view, attribute_name)
