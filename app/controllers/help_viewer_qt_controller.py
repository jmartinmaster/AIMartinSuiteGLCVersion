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
import os

from app.controllers.help_viewer_controller import DOC_GROUPS, DOC_INDEX, get_doc_group_name, get_document_meta_label, read_help_document
from app.views.help_viewer_qt_view import HelpViewerQtView

__module_name__ = "Help Viewer Qt Controller"
__version__ = "1.0.0"


class HelpViewerQtController:
    def __init__(self, parent=None, dispatcher=None):
        self.parent = parent
        self.dispatcher = dispatcher
        self.active_doc_path = None
        self.payload = self._build_view_payload()
        self.doc_groups = dict(self.payload.get("doc_groups") or {})
        self.doc_index = list(self.payload.get("doc_index") or [])
        self.view = HelpViewerQtView(self, self.payload, parent_widget=parent)
        initial_doc = self.payload.get("initial_doc") or (self.doc_index[0][1] if self.doc_index else None)
        if initial_doc:
            self.show_document_by_path(initial_doc)
        self.view.show()

    def __getattr__(self, attribute_name):
        view = self.__dict__.get("view")
        if view is None:
            raise AttributeError(attribute_name)
        return getattr(view, attribute_name)

    def _build_view_payload(self):
        dispatcher = self.dispatcher
        theme_tokens = dict(getattr(getattr(dispatcher, "view", None), "theme_tokens", {}) or {})
        return {
            "window_title": "Help Viewer - Production Logging Center",
            "title": "Help Center",
            "subtitle": "Bundled guides, release references, and editable JSON documentation.",
            "doc_groups": DOC_GROUPS,
            "doc_index": DOC_INDEX,
            "initial_doc": self.active_doc_path or (DOC_INDEX[0][1] if DOC_INDEX else None),
            "theme_tokens": theme_tokens,
        }

    def _sync_active_document_path(self):
        if self.active_doc_path:
            return self.active_doc_path
        view_active_doc_path = getattr(self.view, "active_doc_path", None)
        if view_active_doc_path:
            self.active_doc_path = str(view_active_doc_path)
        return self.active_doc_path

    def _build_document_context(self, doc_path):
        group_name = self.get_doc_group(doc_path)
        sections = list((self.doc_groups.get(group_name) or {}).get("sections") or [])
        meta_label = get_document_meta_label(doc_path, group_name)
        return {
            "group_name": group_name,
            "sections": sections,
            "meta_label": meta_label,
        }

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def get_doc_group(self, doc_path):
        return get_doc_group_name(self.doc_groups, doc_path)

    def show_document(self, doc_name, doc_path, restore_scroll=None):
        self.active_doc_path = doc_path
        content = read_help_document(doc_path)
        document_context = self._build_document_context(doc_path)
        self.view.show_document(
            doc_name,
            doc_path,
            content,
            document_context["meta_label"],
            document_context["sections"],
            restore_scroll=restore_scroll,
        )

    def show_document_by_path(self, doc_path, restore_scroll=None):
        for doc_name, candidate_path in self.doc_index:
            if candidate_path == doc_path:
                self.show_document(doc_name, candidate_path, restore_scroll=restore_scroll)
                return
        self.show_document(os.path.basename(doc_path), doc_path, restore_scroll=restore_scroll)

    def open_active_document(self):
        if not self.active_doc_path:
            return
        if self.dispatcher is not None:
            self.dispatcher.open_help_document(self.active_doc_path)
            return
        self.view.show_error("Open Document", "Help document dispatch is unavailable.")

    def handle_close(self):
        return None

    def apply_theme(self):
        if self.dispatcher is not None:
            self.payload["theme_tokens"] = dict(getattr(getattr(self.dispatcher, "view", None), "theme_tokens", {}) or {})
        active_doc_path = self._sync_active_document_path()
        document_scroll = None
        if hasattr(self.view, "get_document_scroll"):
            document_scroll = self.view.get_document_scroll()
        if hasattr(self.view, "apply_theme"):
            self.view.apply_theme(theme_tokens=self.payload.get("theme_tokens") or {})
        if active_doc_path:
            self.show_document_by_path(active_doc_path, restore_scroll=document_scroll)

    def on_hide(self):
        self._sync_active_document_path()
        return None

    def on_unload(self):
        self._sync_active_document_path()
        try:
            self.view.close()
        except Exception:
            pass