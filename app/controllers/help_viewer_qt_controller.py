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
import json
import os
import time
import webbrowser

from app.controllers.help_viewer_controller import get_doc_group_name, get_document_meta_label, read_help_document
from app.views.help_viewer_qt_view import HelpViewerQtView

__module_name__ = "Help Viewer Qt Controller"
__version__ = "1.0.0"


class HelpViewerQtController:
    def __init__(self, payload):
        self.payload = dict(payload or {})
        self.state_path = self.payload.get("state_path")
        self.command_path = self.payload.get("command_path")
        self.doc_groups = dict(self.payload.get("doc_groups") or {})
        self.doc_index = list(self.payload.get("doc_index") or [])
        self.active_doc_path = None
        self.view = HelpViewerQtView(self, self.payload)
        initial_doc = self.payload.get("initial_doc") or (self.doc_index[0][1] if self.doc_index else None)
        if initial_doc:
            self.show_document_by_path(initial_doc)
        self.write_state(status="ready", message="Help Viewer Qt window ready.")

    def show(self):
        self.view.show()
        self.view.raise_()
        self.view.activateWindow()

    def write_state(self, status="ready", message="", dirty=False):
        if not self.state_path:
            return
        payload = {
            "status": status,
            "dirty": bool(dirty),
            "message": str(message or ""),
            "module": "help_viewer",
            "active_doc_path": self.active_doc_path,
            "updated_at": time.time(),
        }
        try:
            with open(self.state_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            return

    def get_doc_group(self, doc_path):
        return get_doc_group_name(self.doc_groups, doc_path)

    def show_document(self, doc_name, doc_path):
        self.active_doc_path = doc_path
        content = read_help_document(doc_path)
        sections = list((self.doc_groups.get(self.get_doc_group(doc_path)) or {}).get("sections") or [])
        self.view.show_document(doc_name, doc_path, content, get_document_meta_label(doc_path, self.get_doc_group(doc_path)), sections)
        self.write_state(status="ready", message=f"Viewing {doc_name}.")

    def show_document_by_path(self, doc_path):
        for doc_name, candidate_path in self.doc_index:
            if candidate_path == doc_path:
                self.show_document(doc_name, candidate_path)
                return
        self.show_document(os.path.basename(doc_path), doc_path)

    def open_active_document(self):
        if not self.active_doc_path:
            return
        document_path = self.payload.get("resolved_paths", {}).get(self.active_doc_path)
        if not document_path or not os.path.exists(document_path):
            self.view.show_error("Open Document", "The selected help document could not be found.")
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(document_path)
            else:
                webbrowser.open(f"file://{document_path}")
            self.write_state(status="ready", message="Opened active help document.")
        except Exception as exc:
            self.view.show_error("Open Document", f"Could not open the selected document:\n{exc}")

    def poll_commands(self):
        if not self.command_path or not os.path.exists(self.command_path):
            return
        try:
            with open(self.command_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            payload = {}
        try:
            os.remove(self.command_path)
        except OSError:
            pass
        action = str(payload.get("action") or "").strip().lower()
        if action == "raise_window":
            self.show()
            self.write_state(status="ready", message="Raised Help Viewer Qt window.")
        elif action == "close_window":
            self.handle_close()
            self.view.close()

    def handle_close(self):
        self.write_state(status="closed", message="Help Viewer Qt window closed.")