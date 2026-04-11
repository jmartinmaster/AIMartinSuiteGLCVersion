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
from copy import deepcopy
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, DANGER, END, EW, INFO, LEFT, RIGHT, SECONDARY, SUCCESS, VERTICAL, W, X, Y
from ttkbootstrap.dialogs import Messagebox

from app.downtime_codes import DEFAULT_DT_CODE_MAP
from app.theme_manager import DEFAULT_THEME, get_theme_label

__module_name__ = "Settings Manager"
__version__ = "1.0.0"

FORM_LABEL_WIDTH = 22
FORM_INPUT_WIDTH = 30
FORM_COMBO_WIDTH = 28
FORM_LABEL_COLUMN_MIN = 340
FORM_LABEL_WRAP = 320


class SettingsManagerView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.entries = {}
        self.module_whitelist_var = tk.StringVar(value="All visible modules")
        self.persistent_modules_var = tk.StringVar(value="Disabled")
        self.external_modules_status_var = tk.StringVar(value="External module overrides are unavailable.")
        self.security_status_var = tk.StringVar(value="Locked")
        self.developer_admin_status_var = tk.StringVar(value="Admin session required")
        self.theme_status_var = tk.StringVar(value="Current theme")
        self.setup_ui()

    def setup_ui(self):
        self.content_frame = tb.Frame(self.parent, padding=20)
        self.content_frame.pack(fill=BOTH, expand=True)

        tb.Label(self.content_frame, text="Application Settings", font=("-size 16 -weight bold")).pack(anchor=W, pady=(0, 20))

        self.form_frame = tb.Frame(self.content_frame)
        self.form_frame.pack(fill=X)

        self.persistent_frame = tb.Frame(self.content_frame)
        self.persistent_frame.pack(fill=X, pady=5)
        self.persistent_frame.columnconfigure(0, minsize=FORM_LABEL_COLUMN_MIN)
        self.persistent_frame.columnconfigure(1, weight=1)

        self.whitelist_frame = tb.Frame(self.content_frame)
        self.whitelist_frame.pack(fill=X, pady=5)
        self.whitelist_frame.columnconfigure(0, minsize=FORM_LABEL_COLUMN_MIN)
        self.whitelist_frame.columnconfigure(1, weight=1)

        tb.Label(
            self.whitelist_frame,
            text="Sidebar Module Whitelist",
            width=FORM_LABEL_WIDTH,
            anchor=W,
            justify=LEFT,
            wraplength=FORM_LABEL_WRAP,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky=W, padx=(0, 12))
        tb.Entry(self.whitelist_frame, textvariable=self.module_whitelist_var, state="readonly", width=FORM_INPUT_WIDTH).grid(row=0, column=1, sticky=EW)
        tb.Button(self.whitelist_frame, text="Edit Whitelist", bootstyle=INFO, command=self.controller.open_module_whitelist_dialog).grid(row=0, column=2, sticky=W, padx=(8, 0))

        tb.Label(
            self.content_frame,
            text="When the whitelist is empty, the sidebar shows all visible modules. If you choose modules here, only listed modules that are actually present will be shown.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=680,
        ).pack(anchor=W, pady=(0, 8))

        tb.Label(
            self.persistent_frame,
            text="Persistent Modules",
            width=FORM_LABEL_WIDTH,
            anchor=W,
            justify=LEFT,
            wraplength=FORM_LABEL_WRAP,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky=W, padx=(0, 12))
        tb.Entry(self.persistent_frame, textvariable=self.persistent_modules_var, state="readonly", width=FORM_INPUT_WIDTH).grid(row=0, column=1, sticky=EW)
        tb.Button(self.persistent_frame, text="Choose", bootstyle=INFO, command=self.controller.open_persistent_modules_dialog).grid(row=0, column=2, sticky=W, padx=(8, 0))

        tb.Label(
            self.content_frame,
            text="Modules selected here stay live while the app is open, so returning to them keeps the same in-progress screen state.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=680,
        ).pack(anchor=W, pady=(0, 8))

        theme_controls = tb.Frame(self.content_frame)
        theme_controls.pack(fill=X, pady=(5, 10))
        tb.Button(theme_controls, text="Revert Theme Preview", bootstyle=SECONDARY, command=self.controller.revert_theme_preview).pack(side=LEFT)
        tb.Label(theme_controls, textvariable=self.theme_status_var, bootstyle=SECONDARY).pack(side=LEFT, padx=10)

        tb.Label(
            self.content_frame,
            text="The modern refresh uses appearance presets and content-area motion. Start with Martin Modern Light for the new industrial look.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))

        tb.Label(
            self.content_frame,
            text="Screen transitions can be disabled or tuned from 0 to 500 ms. Around 180 to 280 ms is a good range for the current subtle slide animation.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))

        extras = tb.Frame(self.content_frame)
        extras.pack(fill=X, pady=(5, 10))
        tb.Button(extras, text="Edit Downtime Codes", bootstyle=INFO, command=self.controller.open_downtime_codes_dialog).pack(side=LEFT)

        security_frame = tb.Frame(self.content_frame)
        security_frame.pack(fill=X, pady=(5, 10))
        security_frame.columnconfigure(0, minsize=FORM_LABEL_COLUMN_MIN)
        security_frame.columnconfigure(1, weight=1)
        tb.Label(
            security_frame,
            text="Security Session",
            width=FORM_LABEL_WIDTH,
            anchor=W,
            justify=LEFT,
            wraplength=FORM_LABEL_WRAP,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky=W, padx=(0, 12))
        tb.Entry(security_frame, textvariable=self.security_status_var, state="readonly", width=FORM_INPUT_WIDTH).grid(row=0, column=1, sticky=EW)
        tb.Button(security_frame, text="Manage Security", bootstyle="warning", command=self.controller.open_security_admin_dialog).grid(row=0, column=2, sticky=W, padx=(8, 0))

        tb.Label(
            self.content_frame,
            text="Security administration manages vault accounts, role rights, passwords, and the current session state for protected screens.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))

        self.developer_admin_frame = tb.Frame(self.content_frame)
        self.developer_admin_frame.columnconfigure(0, minsize=FORM_LABEL_COLUMN_MIN)
        self.developer_admin_frame.columnconfigure(1, weight=1)
        tb.Label(
            self.developer_admin_frame,
            text="Developer & Admin",
            width=FORM_LABEL_WIDTH,
            anchor=W,
            justify=LEFT,
            wraplength=FORM_LABEL_WRAP,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky=W, padx=(0, 12))
        tb.Entry(self.developer_admin_frame, textvariable=self.developer_admin_status_var, state="readonly", width=FORM_INPUT_WIDTH).grid(row=0, column=1, sticky=EW)
        tb.Button(self.developer_admin_frame, text="Open Tools", bootstyle=INFO, command=self.controller.open_developer_admin_dialog).grid(row=0, column=2, sticky=W, padx=(8, 0))

        self.developer_admin_note = tb.Label(
            self.content_frame,
            text="Developer tools include repository controls, advanced dev update settings, and external module override management.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        )

        tb.Button(self.content_frame, text="Save Settings", bootstyle=SUCCESS, command=self.controller.save_settings).pack(pady=20)
        self.set_developer_admin_visible(False)

    def build_form_fields(self, settings, theme_options):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.entries = {}

        fields = [
            ("export_directory", "Base Export Directory", "entry_browse"),
            ("organize_exports_by_date", "Organize Exports by Year/Month", "check"),
            ("default_export_prefix", "Default Export Prefix", "entry"),
            ("theme", "Appearance Theme", "combo", theme_options),
            ("enable_screen_transitions", "Enable Screen Transitions", "check"),
            ("enable_module_update_notifications", "Check Module Updates On Startup", "check"),
            ("screen_transition_duration_ms", "Transition Duration (ms)", "entry"),
            ("toast_duration_sec", "Toast Duration (Seconds)", "entry"),
            ("auto_save_interval_min", "Auto-Save Interval (Minutes)", "entry"),
            ("default_shift_hours", "Default Shift Hours", "entry"),
            ("default_goal_mph", "Default Goal MPH", "entry"),
        ]

        for item in fields:
            key, label, field_type = item[:3]
            row_frame = tb.Frame(self.form_frame)
            row_frame.pack(fill=X, pady=5)
            row_frame.columnconfigure(0, minsize=FORM_LABEL_COLUMN_MIN)
            row_frame.columnconfigure(1, weight=1)

            tb.Label(
                row_frame,
                text=label,
                width=FORM_LABEL_WIDTH,
                anchor=W,
                justify=LEFT,
                wraplength=FORM_LABEL_WRAP,
                font=("Segoe UI", 9),
            ).grid(row=0, column=0, sticky=W, padx=(0, 12))

            if field_type == "entry":
                entry = tb.Entry(row_frame, width=FORM_INPUT_WIDTH)
                entry.insert(0, str(settings.get(key, "")))
                entry.grid(row=0, column=1, sticky=EW)
                self.entries[key] = entry
            elif field_type == "entry_browse":
                entry = tb.Entry(row_frame, width=FORM_INPUT_WIDTH)
                entry.insert(0, str(settings.get(key, "")))
                entry.grid(row=0, column=1, sticky=EW)
                tb.Button(row_frame, text="Browse", bootstyle=SECONDARY, command=self.controller.browse_export_dir).grid(row=0, column=2, sticky=W, padx=(8, 0))
                self.entries[key] = entry
            elif field_type == "check":
                variable = tk.BooleanVar(value=bool(settings.get(key, False)))
                checkbutton = tb.Checkbutton(row_frame, variable=variable, bootstyle="round-toggle")
                checkbutton.grid(row=0, column=1, sticky=W)
                self.entries[key] = variable
            elif field_type == "combo":
                options = item[3]
                combobox = tb.Combobox(row_frame, values=options, state="readonly", width=FORM_COMBO_WIDTH)
                combobox.set(get_theme_label(settings.get(key, DEFAULT_THEME)))
                combobox.grid(row=0, column=1, sticky=EW)
                combobox.bind("<<ComboboxSelected>>", self.controller.preview_selected_theme)
                self.entries[key] = combobox

    def collect_form_values(self):
        values = {}
        for key, widget in self.entries.items():
            if isinstance(widget, tk.BooleanVar):
                values[key] = bool(widget.get())
            else:
                values[key] = widget.get()
        return values

    def set_persistent_modules_summary(self, value):
        self.persistent_modules_var.set(value)

    def set_module_whitelist_summary(self, value):
        self.module_whitelist_var.set(value)

    def set_external_modules_status(self, value):
        self.external_modules_status_var.set(value)

    def set_security_status(self, value):
        self.security_status_var.set(value)

    def set_developer_admin_status(self, value):
        self.developer_admin_status_var.set(value)

    def set_developer_admin_visible(self, visible):
        if visible:
            if not self.developer_admin_frame.winfo_manager():
                self.developer_admin_frame.pack(fill=X, pady=(5, 10))
            if not self.developer_admin_note.winfo_manager():
                self.developer_admin_note.pack(anchor=W, pady=(0, 10))
            return
        if self.developer_admin_frame.winfo_manager():
            self.developer_admin_frame.pack_forget()
        if self.developer_admin_note.winfo_manager():
            self.developer_admin_note.pack_forget()

    def set_theme_status(self, value):
        self.theme_status_var.set(value)

    def set_export_directory(self, directory_path):
        entry = self.entries.get("export_directory")
        if entry is None:
            return
        entry.delete(0, END)
        entry.insert(0, directory_path)

    def set_theme_selection(self, theme_name):
        entry = self.entries.get("theme")
        if entry is not None:
            entry.set(get_theme_label(theme_name))

    def ask_for_export_directory(self):
        return filedialog.askdirectory()

    def ask_for_password_pair(self, title, prompt_text):
        first = simpledialog.askstring(title, prompt_text, show="*", parent=self.parent)
        if first is None:
            return None
        second = simpledialog.askstring(title, "Re-enter the password:", show="*", parent=self.parent)
        if second is None:
            return None
        if first != second:
            self.show_error(title, "The passwords did not match.")
            return None
        if not first.strip():
            self.show_error(title, "A password is required.")
            return None
        return first

    def ask_yes_no(self, title, message):
        return bool(messagebox.askyesno(title, message, parent=self.parent))

    def show_error(self, title, message):
        Messagebox.show_error(message, title)

    def show_info(self, title, message):
        Messagebox.show_info(message, title)

    def show_toast(self, title, message, bootstyle=SUCCESS):
        self.dispatcher.show_toast(title, message, bootstyle)

    def show_security_admin_dialog(self, state):
        top = tb.Toplevel(title="Security Administration")
        top.geometry("980x720")
        top.minsize(900, 640)

        container = tb.Frame(top, padding=20)
        container.pack(fill=BOTH, expand=True)
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        session_var = tk.StringVar(value=state.get("session_summary", "Locked"))
        security_note_var = tk.StringVar(value="")
        selected_name_var = tk.StringVar(value="")
        name_var = tk.StringVar(value="")
        role_var = tk.StringVar(value="general")
        enabled_var = tk.BooleanVar(value=True)
        password_note_var = tk.StringVar(value="General vaults can remain passwordless.")

        tb.Label(container, text="Security Administration", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, sticky=W)
        tb.Label(
            container,
            text="Manage vault accounts here while keeping Settings Manager as the main security entry point. Admin and developer vaults require passwords. General vaults can stay passwordless in this first release.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=860,
        ).grid(row=1, column=0, columnspan=2, sticky=W, pady=(6, 16))

        body = tb.Frame(container)
        body.grid(row=2, column=0, columnspan=2, sticky="nsew")
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left_frame = tb.Labelframe(body, text=" Vaults ", padding=14)
        left_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        right_frame = tb.Labelframe(body, text=" Vault Details ", padding=14)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(1, weight=1)

        tb.Label(left_frame, text="Current session", bootstyle=SECONDARY).pack(anchor=W)
        tb.Label(left_frame, textvariable=session_var, justify=LEFT, wraplength=230).pack(anchor=W, pady=(0, 10))

        vault_listbox = tk.Listbox(left_frame, height=18, exportselection=False)
        vault_listbox.pack(fill=BOTH, expand=True)
        tb.Label(left_frame, textvariable=security_note_var, bootstyle=SECONDARY, justify=LEFT, wraplength=230).pack(anchor=W, pady=(10, 0))

        form_row = 0
        tb.Label(right_frame, text="Vault Name", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        tb.Entry(right_frame, textvariable=name_var).grid(row=form_row, column=1, sticky=EW, pady=4)
        form_row += 1
        tb.Label(right_frame, text="Role", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        role_combo = tb.Combobox(right_frame, textvariable=role_var, values=["general", "admin", "developer"], state="readonly", width=24)
        role_combo.grid(row=form_row, column=1, sticky=W, pady=4)
        form_row += 1
        tb.Label(right_frame, text="Enabled", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        tb.Checkbutton(right_frame, variable=enabled_var, bootstyle="round-toggle").grid(row=form_row, column=1, sticky=W, pady=4)
        form_row += 1
        tb.Label(right_frame, text="Password Rule", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        tb.Label(right_frame, textvariable=password_note_var, justify=LEFT, wraplength=520).grid(row=form_row, column=1, sticky=W, pady=4)
        form_row += 1

        rights_frame = tb.Labelframe(right_frame, text=" Access Rights ", padding=12)
        rights_frame.grid(row=form_row, column=0, columnspan=2, sticky=EW, pady=(12, 0))
        rights_frame.columnconfigure(0, weight=1)
        right_vars = {}
        current_state = {"value": state}
        right_rows = state.get("access_rights", [])

        for index, right_entry in enumerate(right_rows):
            variable = tk.BooleanVar(value=False)
            right_vars[right_entry["key"]] = variable
            row = tb.Frame(rights_frame)
            row.grid(row=index, column=0, sticky=EW, pady=3)
            tb.Checkbutton(row, text=right_entry["label"], variable=variable, bootstyle="round-toggle").pack(anchor=W)
            tb.Label(row, text=right_entry["description"], bootstyle=SECONDARY, justify=LEFT, wraplength=540).pack(anchor=W, padx=(26, 0))

        selected_record = {"existing_name": None}

        def role_defaults_for(role_name):
            return set(current_state["value"].get("role_defaults", {}).get(role_name, []))

        def update_role_note(_event=None):
            current_role = role_var.get().strip().lower() or "general"
            limit = current_state["value"].get("role_limits", {}).get(current_role)
            if current_role in {"admin", "developer"}:
                password_note_var.set(f"{current_role.title()} vaults require a password. Limit: {limit}.")
            else:
                password_note_var.set(f"General vaults can remain passwordless. Limit: {limit}.")

        def apply_role_defaults():
            selected_rights = role_defaults_for(role_var.get().strip().lower())
            for key, variable in right_vars.items():
                variable.set(key in selected_rights)

        def fill_form(vault_record=None):
            selected_record["existing_name"] = vault_record.get("vault_name") if vault_record else None
            selected_name_var.set(selected_record["existing_name"] or "")
            name_var.set(vault_record.get("vault_name", "") if vault_record else "")
            role_var.set(vault_record.get("role", "general") if vault_record else "general")
            enabled_var.set(bool(vault_record.get("enabled", True)) if vault_record else True)
            rights_to_apply = set(vault_record.get("rights", [])) if vault_record else role_defaults_for("general")
            for key, variable in right_vars.items():
                variable.set(key in rights_to_apply)
            update_role_note()

        def rebuild_vault_list(preferred_name=None):
            vaults = current_state["value"].get("vaults", [])
            vault_listbox.delete(0, tk.END)
            target_index = None
            for index, vault_record in enumerate(vaults):
                enabled_text = "enabled" if vault_record.get("enabled", True) else "disabled"
                display_text = f"{vault_record['vault_name']} | {vault_record['role']} | {enabled_text}"
                if vault_record.get("vault_name") == current_state["value"].get("session_vault_name"):
                    display_text = f"{display_text} | active"
                vault_listbox.insert(tk.END, display_text)
                if preferred_name and vault_record.get("vault_name") == preferred_name:
                    target_index = index
            security_note_var.set(f"Configured vaults: {len(vaults)}")
            if target_index is not None:
                vault_listbox.selection_clear(0, tk.END)
                vault_listbox.selection_set(target_index)
                vault_listbox.event_generate("<<ListboxSelect>>")

        def selected_vault_record():
            selection = vault_listbox.curselection()
            if not selection:
                return None
            index = selection[0]
            vaults = current_state["value"].get("vaults", [])
            if index >= len(vaults):
                return None
            return vaults[index]

        def handle_selection(_event=None):
            vault_record = selected_vault_record()
            if vault_record is None:
                return
            fill_form(vault_record)

        def collect_payload(reset_password=False):
            selected_rights = [key for key, variable in right_vars.items() if variable.get()]
            return {
                "existing_name": selected_record["existing_name"],
                "vault_name": name_var.get().strip(),
                "role": role_var.get().strip().lower(),
                "enabled": bool(enabled_var.get()),
                "rights": selected_rights,
                "reset_password": bool(reset_password),
            }

        def handle_save(reset_password=False):
            try:
                new_state = self.controller.save_security_vault(collect_payload(reset_password=reset_password))
            except Exception as exc:
                self.show_error("Security", str(exc))
                return
            if new_state is None:
                return
            current_state["value"] = new_state
            session_var.set(new_state.get("session_summary", "Locked"))
            rebuild_vault_list(preferred_name=name_var.get().strip())

        def handle_delete():
            if not selected_record["existing_name"]:
                self.show_error("Security", "Select an existing vault before deleting it.")
                return
            try:
                new_state = self.controller.delete_security_vault(selected_record["existing_name"])
            except Exception as exc:
                self.show_error("Security", str(exc))
                return
            if new_state is None:
                return
            current_state["value"] = new_state
            session_var.set(new_state.get("session_summary", "Locked"))
            fill_form(None)
            rebuild_vault_list()

        def handle_rotate_password():
            if not selected_record["existing_name"]:
                self.show_error("Security", "Select an existing vault before rotating its password.")
                return
            if role_var.get().strip().lower() == "general":
                self.show_error("Security", "General vaults do not require passwords in this implementation.")
                return
            try:
                new_state = self.controller.rotate_security_vault_password(selected_record["existing_name"])
            except Exception as exc:
                self.show_error("Security", str(exc))
                return
            if new_state is None:
                return
            current_state["value"] = new_state
            session_var.set(new_state.get("session_summary", "Locked"))
            rebuild_vault_list(preferred_name=selected_record["existing_name"])

        action_row = tb.Frame(right_frame)
        action_row.grid(row=form_row + 1, column=0, columnspan=2, sticky=EW, pady=(14, 0))
        tb.Button(action_row, text="New Vault", bootstyle=SECONDARY, command=lambda: fill_form(None)).pack(side=LEFT)
        tb.Button(action_row, text="Role Defaults", bootstyle=INFO, command=apply_role_defaults).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save Vault", bootstyle=SUCCESS, command=handle_save).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save + Reset Password", bootstyle=INFO, command=lambda: handle_save(reset_password=True)).pack(side=LEFT, padx=(8, 0))

        secondary_actions = tb.Frame(right_frame)
        secondary_actions.grid(row=form_row + 2, column=0, columnspan=2, sticky=EW, pady=(10, 0))
        tb.Button(secondary_actions, text="Rotate Password", bootstyle=INFO, command=handle_rotate_password).pack(side=LEFT)
        tb.Button(secondary_actions, text="Delete Vault", bootstyle=DANGER, command=handle_delete).pack(side=LEFT, padx=(8, 0))
        tb.Button(secondary_actions, text="Close", bootstyle=SECONDARY, command=top.destroy).pack(side=RIGHT)

        role_combo.bind("<<ComboboxSelected>>", update_role_note)
        vault_listbox.bind("<<ListboxSelect>>", handle_selection)
        fill_form(None)
        rebuild_vault_list(preferred_name=current_state["value"].get("session_vault_name"))

        if current_state["value"].get("session_vault_name"):
            matching_names = [entry.get("vault_name") for entry in current_state["value"].get("vaults", [])]
            session_name = current_state["value"].get("session_vault_name")
            if session_name in matching_names:
                fill_form(current_state["value"]["vaults"][matching_names.index(session_name)])

        top.wait_window()

    def show_downtime_codes_dialog(self, current_codes):
        top = tb.Toplevel(title="Downtime Codes")
        top.geometry("520x520")
        top.minsize(420, 420)

        container = tb.Frame(top, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Downtime Codes", font=("-size 14 -weight bold")).pack(anchor=W)
        tb.Label(
            container,
            text="Edit existing codes or add new ones. Numeric codes are what import and export use.",
            bootstyle=SECONDARY,
            justify=LEFT,
        ).pack(anchor=W, pady=(4, 16))

        list_outer = tb.Frame(container)
        list_outer.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(list_outer, highlightthickness=0)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(list_outer, orient=VERTICAL, command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        list_frame = tb.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=list_frame, anchor="nw")

        def sync_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_window_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        list_frame.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_window_width)
        self.dispatcher.bind_mousewheel_to_widget_tree(list_outer, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(list_frame, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(canvas, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(scrollbar, canvas)

        header = tb.Frame(list_frame)
        header.pack(fill=X, pady=(0, 6))
        tb.Label(header, text="Code", width=8, bootstyle=INFO).pack(side=LEFT)
        tb.Label(header, text="Label", bootstyle=INFO).pack(side=LEFT)

        code_rows = []

        def sort_key(code_text):
            return (int(code_text) if str(code_text).isdigit() else 10 ** 9, str(code_text))

        def add_code_row(code_value="", label_value=""):
            row = tb.Frame(list_frame)
            row.pack(fill=X, pady=4)

            code_entry = tb.Entry(row, width=8)
            code_entry.insert(0, str(code_value))
            code_entry.pack(side=LEFT)

            label_entry = tb.Entry(row)
            label_entry.insert(0, str(label_value))
            label_entry.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))

            remove_button = tb.Button(row, text="Remove", bootstyle=DANGER, width=8)
            remove_button.pack(side=RIGHT, padx=(8, 0))

            row_record = {
                "frame": row,
                "code_entry": code_entry,
                "label_entry": label_entry,
            }

            def remove_row():
                if len(code_rows) <= 1:
                    code_entry.delete(0, END)
                    label_entry.delete(0, END)
                    return
                row.destroy()
                code_rows.remove(row_record)
                sync_scroll_region()

            remove_button.configure(command=remove_row)
            code_rows.append(row_record)
            self.dispatcher.bind_mousewheel_to_widget_tree(row, canvas)
            sync_scroll_region()

        for code in sorted(current_codes, key=sort_key):
            add_code_row(code, current_codes[code])

        actions = tb.Frame(container)
        actions.pack(fill=X, pady=(18, 0))

        def reset_defaults():
            for row_record in list(code_rows):
                row_record["frame"].destroy()
                code_rows.remove(row_record)
            for code in sorted(DEFAULT_DT_CODE_MAP, key=sort_key):
                add_code_row(code, DEFAULT_DT_CODE_MAP[code])

        def add_next_code():
            numeric_codes = [
                int(record["code_entry"].get().strip())
                for record in code_rows
                if record["code_entry"].get().strip().isdigit()
            ]
            add_code_row(str(max(numeric_codes, default=0) + 1), "")

        def save_codes():
            updated_codes = {}
            for row_record in code_rows:
                code = row_record["code_entry"].get().strip()
                label = row_record["label_entry"].get().strip()
                if not code and not label:
                    continue
                if not code:
                    self.show_error("Downtime Codes", "Each downtime code row needs a code number.")
                    return
                if not code.isdigit():
                    self.show_error("Downtime Codes", f"Code '{code}' must be numeric.")
                    return
                if not label:
                    self.show_error("Downtime Codes", f"Code {code} cannot be blank.")
                    return
                if code in updated_codes:
                    self.show_error("Downtime Codes", f"Code {code} is duplicated.")
                    return
                updated_codes[code] = label

            if not updated_codes:
                self.show_error("Downtime Codes", "At least one downtime code is required.")
                return
            self.controller.save_downtime_codes(updated_codes)
            top.destroy()

        tb.Button(actions, text="Reset Defaults", bootstyle=SECONDARY, command=reset_defaults).pack(side=LEFT)
        tb.Button(actions, text="Add Code", bootstyle=INFO, command=add_next_code).pack(side=LEFT, padx=(8, 0))
        tb.Button(actions, text="Cancel", bootstyle=SECONDARY, command=top.destroy).pack(side=RIGHT)
        tb.Button(actions, text="Save Codes", bootstyle=SUCCESS, command=save_codes).pack(side=RIGHT, padx=(0, 8))

    def show_persistent_modules_dialog(self, options, selected_modules):
        if not options:
            self.show_info("Persistent Modules", "No persistable modules are available.")
            return

        top = tb.Toplevel(title="Persistent Modules")
        top.geometry("460x420")
        top.minsize(400, 360)

        container = tb.Frame(top, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Persistent Modules", font=("-size 14 -weight bold")).pack(anchor=W)
        tb.Label(
            container,
            text="Choose which modules stay live when you navigate away. Update Manager is always kept alive automatically.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=400,
        ).pack(anchor=W, pady=(4, 16))

        option_vars = {}
        list_frame = tb.Frame(container)
        list_frame.pack(fill=BOTH, expand=True)

        for display_name, module_name in options:
            variable = tk.BooleanVar(value=module_name in selected_modules)
            option_vars[module_name] = variable
            tb.Checkbutton(list_frame, text=display_name, variable=variable, bootstyle="round-toggle").pack(anchor=W, pady=4)

        actions = tb.Frame(container)
        actions.pack(fill=X, pady=(18, 0))

        def save_selection():
            self.controller.save_persistent_modules_selection([
                module_name
                for _display_name, module_name in options
                if option_vars[module_name].get()
            ])
            top.destroy()

        tb.Button(actions, text="Cancel", bootstyle=SECONDARY, command=top.destroy).pack(side=RIGHT)
        tb.Button(actions, text="Apply Selection", bootstyle=SUCCESS, command=save_selection).pack(side=RIGHT, padx=(0, 8))

    def show_module_whitelist_dialog(self, options, selected_modules):
        if not options:
            self.show_info("Sidebar Module Whitelist", "No visible modules are available.")
            return

        top = tb.Toplevel(title="Sidebar Module Whitelist")
        top.geometry("460x420")
        top.minsize(400, 360)

        container = tb.Frame(top, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Sidebar Module Whitelist", font=("-size 14 -weight bold")).pack(anchor=W)
        tb.Label(
            container,
            text="Leave every option unchecked to allow all visible modules. When one or more modules are selected, the sidebar will only show those modules if they are present.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=400,
        ).pack(anchor=W, pady=(4, 16))

        option_vars = {}
        list_frame = tb.Frame(container)
        list_frame.pack(fill=BOTH, expand=True)

        for display_name, module_name in options:
            variable = tk.BooleanVar(value=module_name in selected_modules)
            option_vars[module_name] = variable
            tb.Checkbutton(list_frame, text=display_name, variable=variable, bootstyle="round-toggle").pack(anchor=W, pady=4)

        actions = tb.Frame(container)
        actions.pack(fill=X, pady=(18, 0))

        def clear_selection():
            for variable in option_vars.values():
                variable.set(False)

        def save_selection():
            self.controller.save_module_whitelist_selection([
                module_name
                for _display_name, module_name in options
                if option_vars[module_name].get()
            ])
            top.destroy()

        tb.Button(actions, text="Clear Whitelist", bootstyle=SECONDARY, command=clear_selection).pack(side=LEFT)
        tb.Button(actions, text="Cancel", bootstyle=SECONDARY, command=top.destroy).pack(side=RIGHT)
        tb.Button(actions, text="Apply Selection", bootstyle=SUCCESS, command=save_selection).pack(side=RIGHT, padx=(0, 8))

    def show_developer_admin_dialog(self, current_settings, module_names):
        top = tb.Toplevel(title="Developer & Admin Tools")
        top.geometry("900x760")
        top.minsize(780, 640)

        container = tb.Frame(top, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Developer & Admin Tools", font=("-size 14 -weight bold")).pack(anchor=W)
        tb.Label(
            container,
            text="These controls are privileged. Repository configuration, advanced packaged dev updates, and external module overrides are managed here instead of the general settings form.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=820,
        ).pack(anchor=W, pady=(4, 16))

        settings_frame = tb.Labelframe(container, text=" Privileged Update Settings ", padding=14)
        settings_frame.pack(fill=X, pady=(0, 12))
        settings_frame.columnconfigure(1, weight=1)

        repo_var = tk.StringVar(value=current_settings.get("update_repository_url", ""))
        advanced_var = tk.BooleanVar(value=bool(current_settings.get("enable_advanced_dev_updates", False)))
        override_trust_var = tk.BooleanVar(value=bool(current_settings.get("enable_external_override_trust", False)))
        editor_source_var = tk.StringVar(value="")
        editor_status_var = tk.StringVar(value="Choose a module to inspect or override.")

        tb.Label(settings_frame, text="Update Repository URL", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Entry(settings_frame, textvariable=repo_var).grid(row=0, column=1, sticky=EW, pady=2)
        tb.Label(settings_frame, text="Advanced Dev Updates", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Checkbutton(settings_frame, variable=advanced_var, bootstyle="round-toggle").grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(settings_frame, text="External Override Trust", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Checkbutton(settings_frame, variable=override_trust_var, bootstyle="round-toggle").grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(
            settings_frame,
            text="Override files can exist beside the app without executing. Enable trust only when you intentionally want the app to load those external Python files.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=620,
        ).grid(row=3, column=0, columnspan=2, sticky=W, pady=(8, 0))

        editor_frame = tb.Labelframe(container, text=" External Module Overrides ", padding=14)
        editor_frame.pack(fill=BOTH, expand=True)
        editor_frame.columnconfigure(1, weight=1)
        editor_frame.rowconfigure(2, weight=1)

        module_var = tk.StringVar(value=module_names[0] if module_names else "")
        tb.Label(editor_frame, text="Module", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        selector = tb.Combobox(editor_frame, textvariable=module_var, values=module_names, state="readonly" if module_names else "disabled", width=36)
        selector.grid(row=0, column=1, sticky=EW, pady=2)
        tb.Label(editor_frame, text="Source", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(editor_frame, textvariable=editor_source_var).grid(row=1, column=1, sticky=W, pady=2)

        text_outer = tb.Frame(editor_frame)
        text_outer.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        text_outer.rowconfigure(0, weight=1)
        text_outer.columnconfigure(0, weight=1)
        text_widget = tk.Text(text_outer, wrap="none", undo=True)
        y_scroll = tb.Scrollbar(text_outer, orient=VERTICAL, command=text_widget.yview)
        x_scroll = tb.Scrollbar(text_outer, orient="horizontal", command=text_widget.xview)
        text_widget.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        text_widget.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        tb.Label(editor_frame, textvariable=editor_status_var, bootstyle=SECONDARY, justify=LEFT, wraplength=780).grid(row=3, column=0, columnspan=2, sticky=W, pady=(10, 0))

        def load_selected_module(_event=None):
            module_name = module_var.get().strip()
            state = self.controller.get_external_module_editor_state(module_name)
            editor_source_var.set(state.get("source", ""))
            editor_status_var.set(state.get("status", ""))
            text_widget.delete("1.0", END)
            text_widget.insert("1.0", state.get("text", ""))

        selector.bind("<<ComboboxSelected>>", load_selected_module)
        load_selected_module()

        action_row = tb.Frame(container)
        action_row.pack(fill=X, pady=(14, 0))

        def save_override():
            module_name = module_var.get().strip()
            if self.controller.save_external_module_override(module_name, text_widget.get("1.0", "end-1c")):
                load_selected_module()

        def remove_override():
            module_name = module_var.get().strip()
            if self.controller.remove_external_module_override(module_name):
                load_selected_module()

        def save_privileged_settings():
            self.controller.save_developer_admin_settings(repo_var.get(), advanced_var.get(), override_trust_var.get())

        tb.Button(action_row, text="Save Override", bootstyle=SUCCESS, command=save_override).pack(side=LEFT)
        tb.Button(action_row, text="Remove Override", bootstyle="danger", command=remove_override).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save Privileged Settings", bootstyle=INFO, command=save_privileged_settings).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Close", bootstyle=SECONDARY, command=top.destroy).pack(side=RIGHT)

    def on_hide(self):
        return None

    def on_unload(self):
        return None