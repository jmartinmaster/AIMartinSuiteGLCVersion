import os

from app.utils import local_or_resource_path
from app.views.help_viewer_view import HelpViewerView


class HelpViewerController:
    def __init__(self, parent, dispatcher):
        self.dispatcher = dispatcher
        self.view = HelpViewerView(parent, dispatcher, self)

    def __getattr__(self, attribute_name):
        return getattr(self.view, attribute_name)

    def get_doc_group(self, doc_path):
        for group_name, group in self.view.doc_groups.items():
            for _section_name, section_path in group.get("sections", []):
                if section_path == doc_path:
                    return group_name
        return None

    def read_doc(self, relative_path):
        candidate = local_or_resource_path(relative_path)
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return handle.read()
        return f"Missing help document: {relative_path}"

    def show_document(self, doc_name, doc_path):
        self.view.show_document(doc_name, doc_path, self.read_doc(doc_path))

    def open_active_document(self):
        if self.view.active_doc_path:
            self.dispatcher.open_help_document(self.view.active_doc_path)
