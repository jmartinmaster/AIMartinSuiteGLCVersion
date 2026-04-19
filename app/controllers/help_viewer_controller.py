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

from app.views.help_viewer_view import HelpViewerView
from app.utils import local_or_resource_path

__module_name__ = "Help Viewer"
__version__ = "1.1.0"

DOC_GROUPS = {
    "user_guide": {
        "sections": [
            ("Overview", "docs/help/user_guide.md"),
            ("Production Log", "docs/help/user_guide_production_log.md"),
            ("Rate Manager", "docs/help/user_guide_rate_manager.md"),
            ("Layout Manager", "docs/help/user_guide_layout_manager.md"),
            ("Settings Manager", "docs/help/user_guide_settings_manager.md"),
            ("Backup / Recovery", "docs/help/user_guide_recovery_viewer.md"),
            ("Update Manager", "docs/help/user_guide_update_manager.md"),
        ],
    },
}

DOC_INDEX = [
    ("User Guide", "docs/help/user_guide.md"),
    ("App Icons", "docs/help/app_icons.md"),
    ("Form Definitions", "docs/help/form_definitions.md"),
    ("Layout JSON", "docs/help/layout_config.md"),
    ("Production Log Calculations", "docs/help/production_log_calculations.md"),
    ("Production Log JSON Architecture", "docs/production_log_json_architecture.md"),
    ("Settings JSON", "docs/help/settings_json.md"),
    ("Rates JSON", "docs/help/rates_json.md"),
    ("Draft JSON", "docs/help/draft_json.md"),
    ("Hidden Modules", "docs/help/hidden_modules.md"),
    ("License", "docs/legal/LICENSE.txt"),
]


def get_doc_group_name(doc_groups, doc_path):
    for group_name, group in (doc_groups or {}).items():
        for _section_name, section_path in group.get("sections", []):
            if section_path == doc_path:
                return group_name
    return None


def get_document_meta_label(doc_path, group_name=None):
    if os.path.basename(doc_path).lower() == "license.txt":
        return "Bundled license"
    if group_name == "user_guide":
        return "User Guide section"
    return "Bundled guide"


def read_help_document(relative_path):
    candidate = local_or_resource_path(relative_path)
    if os.path.exists(candidate):
        with open(candidate, "r", encoding="utf-8") as handle:
            return handle.read()
    return f"Missing help document: {relative_path}"


class HelpViewerController:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.doc_groups = DOC_GROUPS
        self.doc_index = DOC_INDEX
        self.active_doc_path = None
        self.view = HelpViewerView(parent, dispatcher, self)

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
