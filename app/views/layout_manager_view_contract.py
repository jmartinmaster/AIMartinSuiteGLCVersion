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
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

__module_name__ = "Layout Manager View Contract"
__version__ = "1.0.0"

FormInfo = Mapping[str, Any]
FormList = Sequence[FormInfo]


@runtime_checkable
class LayoutManagerViewContract(Protocol):
    def get_selected_form_id(self) -> str | None:
        ...

    def get_selected_form_info(self) -> FormInfo | None:
        ...

    def set_form_options(self, forms: FormList, active_form_id: str | None = None, selected_form_id: str | None = None) -> None:
        ...

    def update_status(self, message: str, source_name: str, is_dirty: bool, bootstyle: str = "secondary") -> None:
        ...

    def update_source_label(self, source_text: str) -> None:
        ...

    def get_active_editor_tab(self) -> str:
        ...

    def apply_theme(self, theme_tokens: Mapping[str, Any]) -> None:
        ...

    def set_editor_text(self, serialized_text: str) -> None:
        ...

    def reset_editor_modified(self) -> None:
        ...

    def get_editor_text(self) -> str:
        ...

    def render_block_view(
        self,
        config: Mapping[str, Any],
        protected_field_ids: Any,
        protected_row_field_ids: Any,
        selected_item: str | None = None,
        guardrail_summary: Mapping[str, Any] | None = None,
    ) -> None:
        ...

    def render_import_export(
        self,
        config: Mapping[str, Any],
        selected_item: str | None = None,
        guardrail_summary: Mapping[str, Any] | None = None,
    ) -> None:
        ...

    def render_preview(self, preview_grid: Mapping[str, Any], selected_item: str | None = None) -> None:
        ...

    def apply_selection(self, item_key: str | None, scroll: bool = False) -> None:
        ...

    def confirm_discard_changes(self, is_dirty: bool) -> bool:
        ...

    def confirm_delete_form(self, form_info: FormInfo) -> bool:
        ...

    def ask_form_name(self, title: str = "Create Form", prompt: str = "", initialvalue: str = "") -> str | None:
        ...

    def ask_form_details(
        self,
        title: str,
        name_prompt: str,
        initial_name: str = "",
        initial_description: str = "",
        default_activate: bool = True,
    ) -> Mapping[str, Any] | None:
        ...

    def show_preview_error(self, message: str) -> None:
        ...

    def show_error(self, title: str, message: str) -> None:
        ...

    def show_validation_success(self, message: str = "Layout JSON is valid.") -> None:
        ...

    def show_form_created(self, form_info: FormInfo) -> None:
        ...

    def show_form_activated(self, form_info: FormInfo) -> None:
        ...

    def show_form_renamed(self, form_info: FormInfo) -> None:
        ...

    def show_form_duplicated(self, form_info: FormInfo) -> None:
        ...

    def show_form_deleted(self, deleted_form: FormInfo, active_form: FormInfo | None = None, active_changed: bool = False) -> None:
        ...

    def show_save_success(self, save_path: str, backup_info: Mapping[str, Any] | None) -> None:
        ...

    def on_hide(self) -> None:
        ...

    def on_unload(self) -> None:
        ...