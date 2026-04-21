# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from app.help_viewer_documents import (
    DOC_GROUPS,
    DOC_INDEX,
    get_doc_group_name,
    get_document_meta_label,
    read_help_document,
)
from app.tk_runtime_removed import raise_tk_runtime_removed

__module_name__ = "Help Viewer"
__version__ = "1.1.0"


class HelpViewerController:
    def __init__(self, parent, dispatcher):
        _ = parent
        _ = dispatcher
        raise_tk_runtime_removed("app/controllers/help_viewer_controller.py")

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def get_doc_group(self, doc_path):
        return get_doc_group_name(self.doc_groups, doc_path)

    def read_doc(self, relative_path):
        return read_help_document(relative_path)

    def show_document(self, doc_name, doc_path):
        self.active_doc_path = doc_path
        self.view.show_document(doc_name, doc_path, self.read_doc(doc_path))

    def open_active_document(self):
        target_path = self.active_doc_path or getattr(self.view, "active_doc_path", None)
        if target_path:
            self.dispatcher.open_help_document(target_path)

    def on_hide(self):
        on_hide = getattr(self.view, "on_hide", None)
        if callable(on_hide):
            return on_hide()
        return None

    def on_unload(self):
        on_unload = getattr(self.view, "on_unload", None)
        if callable(on_unload):
            return on_unload()
        return None
