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

from app.utils import local_or_resource_path

__module_name__ = "Help Viewer Documents"
__version__ = "1.0.0"

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