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
__version__ = "1.0.2"

FORM_LABEL_WIDTH = 22
FORM_INPUT_WIDTH = 30
FORM_COMBO_WIDTH = 28
FORM_LABEL_COLUMN_MIN = 340
FORM_LABEL_WRAP = 320


class SettingsManagerView:
    def __init__(self, parent, dispatcher, controller, section_mode="full"):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.section_mode = str(section_mode or "full")
        self.controller.view = self
        self._active_modal_parent = None
        self.entries = {}
        self.module_whitelist_var = tk.StringVar(value="All visible modules")
        self.persistent_modules_var = tk.StringVar(value="Disabled")
        self.external_modules_status_var = tk.StringVar(value="External module overrides are unavailable.")
        self.security_status_var = tk.StringVar(value="Locked")
        self.security_admin_session_var = tk.StringVar(value="Locked")
        self.security_admin_note_var = tk.StringVar(value="Configured vaults: 0")
        self.security_admin_name_var = tk.StringVar(value="")
        self.security_admin_role_var = tk.StringVar(value="general")
        self.security_admin_enabled_var = tk.BooleanVar(value=True)
        self.security_admin_non_secure_var = tk.BooleanVar(value=False)
        self.security_admin_password_note_var = tk.StringVar(value="General vaults can remain passwordless.")
        self.developer_admin_status_var = tk.StringVar(value="Admin or developer session required")
        self.theme_status_var = tk.StringVar(value="Current theme")
        self.developer_admin_repo_var = tk.StringVar(value="")
        self.developer_admin_advanced_var = tk.BooleanVar(value=False)
        self.developer_admin_override_trust_var = tk.BooleanVar(value=False)
        self._security_admin_state = {}
        self.security_admin_right_vars = {}
        self.module_whitelist_option_vars = {}
        self.persistent_module_option_vars = {}
        self.downtime_code_rows = []
        self.setup_ui()

    def setup_ui(self):
        self.content_frame = tb.Frame(self.parent, padding=20)
        self.content_frame.pack(fill=BOTH, expand=True)

        self.page_title_label = tb.Label(self.content_frame, text="Application Settings", font=("-size 16 -weight bold"))
        self.page_title_label.pack(anchor=W, pady=(0, 20))

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

        self.whitelist_help_label = tb.Label(
            self.content_frame,
            text="When the whitelist is empty, the sidebar shows all visible modules. If you choose modules here, only listed modules that are actually present will be shown.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=680,
        )
        self.whitelist_help_label.pack(anchor=W, pady=(0, 8))

        self.whitelist_editor_frame = tb.Labelframe(self.content_frame, text=" Sidebar Whitelist Editor ", padding=12)
        tb.Label(
            self.whitelist_editor_frame,
            text="Edit the sidebar whitelist inline. Leave everything unchecked to allow all visible modules. Use Save Settings afterward to persist the change.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))
        self.whitelist_editor_list_frame = tb.Frame(self.whitelist_editor_frame)
        self.whitelist_editor_list_frame.pack(fill=X)
        whitelist_actions = tb.Frame(self.whitelist_editor_frame)
        whitelist_actions.pack(fill=X, pady=(12, 0))
        tb.Button(whitelist_actions, text="Clear Whitelist", bootstyle=SECONDARY, command=self.clear_module_whitelist_editor_selection).pack(side=LEFT)
        tb.Button(whitelist_actions, text="Apply Selection", bootstyle=SUCCESS, command=self.controller.save_module_whitelist_selection).pack(side=LEFT, padx=(8, 0))
        tb.Button(whitelist_actions, text="Hide Editor", bootstyle=SECONDARY, command=self.controller.open_module_whitelist_dialog).pack(side=RIGHT)

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

        self.persistent_help_label = tb.Label(
            self.content_frame,
            text="Modules selected here stay live while the app is open, so returning to them keeps the same in-progress screen state.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=680,
        )
        self.persistent_help_label.pack(anchor=W, pady=(0, 8))

        self.persistent_modules_editor_frame = tb.Labelframe(self.content_frame, text=" Persistent Modules Editor ", padding=12)
        tb.Label(
            self.persistent_modules_editor_frame,
            text="Choose which modules stay live inline. Update Manager remains persistent automatically. Use Save Settings afterward to persist the change.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))
        self.persistent_modules_editor_list_frame = tb.Frame(self.persistent_modules_editor_frame)
        self.persistent_modules_editor_list_frame.pack(fill=X)
        persistent_actions = tb.Frame(self.persistent_modules_editor_frame)
        persistent_actions.pack(fill=X, pady=(12, 0))
        tb.Button(persistent_actions, text="Select None", bootstyle=SECONDARY, command=self.clear_persistent_modules_editor_selection).pack(side=LEFT)
        tb.Button(persistent_actions, text="Apply Selection", bootstyle=SUCCESS, command=self.controller.save_persistent_modules_selection).pack(side=LEFT, padx=(8, 0))
        tb.Button(persistent_actions, text="Hide Editor", bootstyle=SECONDARY, command=self.controller.open_persistent_modules_dialog).pack(side=RIGHT)

        self.theme_controls = tb.Frame(self.content_frame)
        self.theme_controls.pack(fill=X, pady=(5, 10))
        tb.Button(self.theme_controls, text="Revert Theme Preview", bootstyle=SECONDARY, command=self.controller.revert_theme_preview).pack(side=LEFT)
        tb.Label(self.theme_controls, textvariable=self.theme_status_var, bootstyle=SECONDARY).pack(side=LEFT, padx=10)

        self.theme_help_label = tb.Label(
            self.content_frame,
            text="The modern refresh uses appearance presets and content-area motion. Start with Martin Modern Light for the new industrial look.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        )
        self.theme_help_label.pack(anchor=W, pady=(0, 10))

        self.transition_help_label = tb.Label(
            self.content_frame,
            text="Screen transitions can be disabled or tuned from 0 to 500 ms. Around 180 to 280 ms is a good range for the current subtle slide animation.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        )
        self.transition_help_label.pack(anchor=W, pady=(0, 10))

        self.extras_frame = tb.Frame(self.content_frame)
        self.extras_frame.pack(fill=X, pady=(5, 10))
        tb.Button(self.extras_frame, text="Edit Downtime Codes", bootstyle=INFO, command=self.controller.open_downtime_codes_dialog).pack(side=LEFT)

        self.downtime_editor_frame = tb.Labelframe(self.content_frame, text=" Downtime Codes Editor ", padding=12)
        tb.Label(
            self.downtime_editor_frame,
            text="Edit numeric downtime codes inline. Imports and exports use these code numbers. Use Save Settings afterward to persist the change.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).pack(anchor=W, pady=(0, 10))
        downtime_header = tb.Frame(self.downtime_editor_frame)
        downtime_header.pack(fill=X, pady=(0, 6))
        tb.Label(downtime_header, text="Code", width=8, bootstyle=INFO).pack(side=LEFT)
        tb.Label(downtime_header, text="Label", bootstyle=INFO).pack(side=LEFT)
        self.downtime_editor_rows_frame = tb.Frame(self.downtime_editor_frame)
        self.downtime_editor_rows_frame.pack(fill=X)
        downtime_actions = tb.Frame(self.downtime_editor_frame)
        downtime_actions.pack(fill=X, pady=(12, 0))
        tb.Button(downtime_actions, text="Reset Defaults", bootstyle=SECONDARY, command=self.reset_downtime_codes_editor_defaults).pack(side=LEFT)
        tb.Button(downtime_actions, text="Add Code", bootstyle=INFO, command=self.controller.add_next_downtime_code_editor_row).pack(side=LEFT, padx=(8, 0))
        tb.Button(downtime_actions, text="Apply Codes", bootstyle=SUCCESS, command=self.controller.save_current_downtime_codes).pack(side=LEFT, padx=(8, 0))
        tb.Button(downtime_actions, text="Hide Editor", bootstyle=SECONDARY, command=self.controller.open_downtime_codes_dialog).pack(side=RIGHT)

        self.security_frame = tb.Frame(self.content_frame)
        self.security_frame.pack(fill=X, pady=(5, 10))
        self.security_frame.columnconfigure(0, minsize=FORM_LABEL_COLUMN_MIN)
        self.security_frame.columnconfigure(1, weight=1)
        tb.Label(
            self.security_frame,
            text="Security Session",
            width=FORM_LABEL_WIDTH,
            anchor=W,
            justify=LEFT,
            wraplength=FORM_LABEL_WRAP,
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky=W, padx=(0, 12))
        tb.Entry(self.security_frame, textvariable=self.security_status_var, state="readonly", width=FORM_INPUT_WIDTH).grid(row=0, column=1, sticky=EW)
        self.open_security_tools_button = tb.Button(self.security_frame, text="Open Security Tools", bootstyle="warning", command=self.controller.open_security_admin_dialog)
        self.open_security_tools_button.grid(row=0, column=2, sticky=W, padx=(8, 0))

        self.security_help_label = tb.Label(
            self.content_frame,
            text="Security administration now stays in the main Settings page. Only password and confirmation prompts remain modal for sensitive actions.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        )
        self.security_help_label.pack(anchor=W, pady=(0, 10))

        self.security_admin_tools_frame = tb.Labelframe(self.content_frame, text=" Security Administration ", padding=14)
        self.security_admin_tools_frame.columnconfigure(0, weight=0)
        self.security_admin_tools_frame.columnconfigure(1, weight=1)

        tb.Label(
            self.security_admin_tools_frame,
            text="Current Session",
            bootstyle=SECONDARY,
        ).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=(0, 6))
        tb.Label(
            self.security_admin_tools_frame,
            textvariable=self.security_admin_session_var,
            justify=LEFT,
            wraplength=640,
        ).grid(row=0, column=1, sticky=W, pady=(0, 6))

        tb.Label(
            self.security_admin_tools_frame,
            text="Manage vault accounts, rights, passwords, and persisted non-secure mode here without leaving the Settings page.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        ).grid(row=1, column=0, columnspan=2, sticky=W, pady=(0, 12))

        security_body = tb.Frame(self.security_admin_tools_frame)
        security_body.grid(row=2, column=0, columnspan=2, sticky="nsew")
        security_body.columnconfigure(0, weight=0)
        security_body.columnconfigure(1, weight=1)
        self.security_admin_tools_frame.rowconfigure(2, weight=1)

        left_frame = tb.Labelframe(security_body, text=" Vaults ", padding=14)
        left_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        right_frame = tb.Labelframe(security_body, text=" Vault Details ", padding=14)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(1, weight=1)

        self.security_admin_vault_listbox = tk.Listbox(left_frame, height=14, exportselection=False)
        self.security_admin_vault_listbox.pack(fill=BOTH, expand=True)
        self.security_admin_vault_listbox.bind("<<ListboxSelect>>", self.controller.load_selected_security_vault)
        tb.Label(
            left_frame,
            textvariable=self.security_admin_note_var,
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=220,
        ).pack(anchor=W, pady=(10, 0))

        form_row = 0
        tb.Label(right_frame, text="Vault Name", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        tb.Entry(right_frame, textvariable=self.security_admin_name_var).grid(row=form_row, column=1, sticky=EW, pady=4)
        form_row += 1
        tb.Label(right_frame, text="Role", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        self.security_admin_role_combo = tb.Combobox(
            right_frame,
            textvariable=self.security_admin_role_var,
            values=["general", "admin", "developer"],
            state="readonly",
            width=24,
        )
        self.security_admin_role_combo.grid(row=form_row, column=1, sticky=W, pady=4)
        self.security_admin_role_combo.bind("<<ComboboxSelected>>", self.controller.on_security_role_selected)
        form_row += 1
        tb.Label(right_frame, text="Enabled", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        tb.Checkbutton(right_frame, variable=self.security_admin_enabled_var, bootstyle="round-toggle").grid(row=form_row, column=1, sticky=W, pady=4)
        form_row += 1
        tb.Label(right_frame, text="Password Rule", bootstyle=SECONDARY).grid(row=form_row, column=0, sticky=W, padx=(0, 12), pady=4)
        tb.Label(
            right_frame,
            textvariable=self.security_admin_password_note_var,
            justify=LEFT,
            wraplength=520,
        ).grid(row=form_row, column=1, sticky=W, pady=4)
        form_row += 1

        self.security_admin_rights_frame = tb.Labelframe(right_frame, text=" Access Rights ", padding=12)
        self.security_admin_rights_frame.grid(row=form_row, column=0, columnspan=2, sticky=EW, pady=(12, 0))
        self.security_admin_rights_frame.columnconfigure(0, weight=1)
        form_row += 1

        security_mode_frame = tb.Labelframe(right_frame, text=" Security Mode ", padding=12)
        security_mode_frame.grid(row=form_row, column=0, columnspan=2, sticky=EW, pady=(14, 0))
        tb.Checkbutton(
            security_mode_frame,
            text="Persistently bypass protected-module authentication",
            variable=self.security_admin_non_secure_var,
            bootstyle="round-toggle",
        ).pack(anchor=W)
        tb.Label(
            security_mode_frame,
            text="This is a global persisted setting intended for controlled admin use only.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=540,
        ).pack(anchor=W, pady=(6, 0))
        form_row += 1

        action_row = tb.Frame(right_frame)
        action_row.grid(row=form_row, column=0, columnspan=2, sticky=EW, pady=(14, 0))
        tb.Button(action_row, text="New Vault", bootstyle=SECONDARY, command=self.controller.start_new_security_vault).pack(side=LEFT)
        tb.Button(action_row, text="Role Defaults", bootstyle=INFO, command=self.controller.apply_selected_security_role_defaults).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save Vault", bootstyle=SUCCESS, command=self.controller.save_current_security_vault).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save + Reset Password", bootstyle=INFO, command=lambda: self.controller.save_current_security_vault(reset_password=True)).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save Security Mode", bootstyle="warning", command=self.controller.save_current_security_mode).pack(side=LEFT, padx=(8, 0))
        form_row += 1

        secondary_actions = tb.Frame(right_frame)
        secondary_actions.grid(row=form_row, column=0, columnspan=2, sticky=EW, pady=(10, 0))
        tb.Button(secondary_actions, text="Rotate Password", bootstyle=INFO, command=self.controller.rotate_selected_security_vault_password).pack(side=LEFT)
        tb.Button(secondary_actions, text="Delete Vault", bootstyle=DANGER, command=self.controller.delete_selected_security_vault).pack(side=LEFT, padx=(8, 0))

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
        tb.Button(self.developer_admin_frame, text="Open Internal Code Editor", bootstyle=INFO, command=lambda: self.dispatcher.secure_load("internal_code_editor")).grid(row=0, column=2, sticky=W, padx=(8, 0))

        self.developer_admin_note = tb.Label(
            self.content_frame,
            text="Sign in from the File menu or Security tools to reveal privileged pages in the main navigation, including Internal Code Editor.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=760,
        )

        self.developer_admin_tools_frame = tb.Labelframe(self.content_frame, text=" Developer & Admin Tools ", padding=14)
        self.developer_admin_tools_frame.columnconfigure(1, weight=1)

        tb.Label(self.developer_admin_tools_frame, text="Update Repository URL", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Entry(self.developer_admin_tools_frame, textvariable=self.developer_admin_repo_var).grid(row=0, column=1, sticky=EW, pady=2)
        tb.Label(self.developer_admin_tools_frame, text="Advanced Dev Updates", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Checkbutton(self.developer_admin_tools_frame, variable=self.developer_admin_advanced_var, bootstyle="round-toggle").grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(self.developer_admin_tools_frame, text="External Override Trust", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Checkbutton(self.developer_admin_tools_frame, variable=self.developer_admin_override_trust_var, bootstyle="round-toggle").grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(
            self.developer_admin_tools_frame,
            text="Override files can exist beside the app without executing. Enable trust only when you intentionally want the app to load those external Python files.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=620,
        ).grid(row=3, column=0, columnspan=2, sticky=W, pady=(8, 10))

        tb.Label(self.developer_admin_tools_frame, text="Override Files", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=(4, 0))
        tb.Label(
            self.developer_admin_tools_frame,
            textvariable=self.external_modules_status_var,
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=620,
        ).grid(row=4, column=1, sticky=W, pady=(4, 0))

        developer_actions = tb.Frame(self.developer_admin_tools_frame)
        developer_actions.grid(row=5, column=0, columnspan=2, sticky=EW, pady=(14, 0))
        tb.Button(developer_actions, text="Save Privileged Settings", bootstyle=INFO, command=self.controller.save_current_developer_admin_settings).pack(side=LEFT, padx=(8, 0))

        self.save_settings_button = tb.Button(self.content_frame, text="Save Settings", bootstyle=SUCCESS, command=self.controller.save_settings)
        self.save_settings_button.pack(pady=20)
        self.set_module_whitelist_editor_visible(False)
        self.set_persistent_modules_editor_visible(False)
        self.set_downtime_editor_visible(False)
        self.set_security_admin_visible(False)
        self.set_developer_admin_visible(False)

    def apply_section_mode(self):
        if self.section_mode == "full":
            self._hide_privileged_settings_sections()
            return
        if self.section_mode == "security_admin":
            self.page_title_label.configure(text="Security Administration")
            self._hide_settings_sections()
            self.security_help_label.configure(text="Manage vault accounts, access rights, passwords, and persisted non-secure mode from this dedicated page.")
            self.open_security_tools_button.configure(text="Unlock Security Admin")
            self.open_security_tools_button.grid()
            self.security_frame.pack(fill=X, pady=(5, 10))
            self.security_help_label.pack(anchor=W, pady=(0, 10))
            self.set_security_admin_visible(True)
            return
        if self.section_mode == "developer_admin":
            self.page_title_label.configure(text="Developer Tools")
            self._hide_settings_sections()
            self.security_frame.pack(fill=X, pady=(5, 10))
            self.developer_admin_note.configure(text="Privileged update and override settings now live on this dedicated page. Internal Code Editor remains a separate sidebar module.")
            self.set_developer_admin_visible(True)
            return

    def _hide_privileged_settings_sections(self):
        for widget in (
            self.security_frame,
            self.security_help_label,
            self.security_admin_tools_frame,
            self.developer_admin_frame,
            self.developer_admin_note,
            self.developer_admin_tools_frame,
        ):
            if widget.winfo_manager():
                widget.pack_forget()

    def _hide_settings_sections(self):
        for widget in (
            self.form_frame,
            self.persistent_frame,
            self.whitelist_frame,
            self.whitelist_help_label,
            self.whitelist_editor_frame,
            self.persistent_help_label,
            self.persistent_modules_editor_frame,
            self.theme_controls,
            self.theme_help_label,
            self.transition_help_label,
            self.extras_frame,
            self.downtime_editor_frame,
            self.save_settings_button,
        ):
            if widget.winfo_manager():
                widget.pack_forget()

        if self.section_mode == "security_admin":
            for widget in (self.developer_admin_frame, self.developer_admin_note, self.developer_admin_tools_frame):
                if widget.winfo_manager():
                    widget.pack_forget()

        if self.section_mode == "developer_admin":
            for widget in (self.security_help_label, self.security_admin_tools_frame):
                if widget.winfo_manager():
                    widget.pack_forget()

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

    def set_module_whitelist_editor_visible(self, visible):
        if visible:
            if not self.whitelist_editor_frame.winfo_manager():
                self.whitelist_editor_frame.pack(fill=X, pady=(0, 12))
            return
        if self.whitelist_editor_frame.winfo_manager():
            self.whitelist_editor_frame.pack_forget()

    def is_module_whitelist_editor_visible(self):
        return bool(self.whitelist_editor_frame.winfo_manager())

    def configure_module_whitelist_editor(self, options, selected_modules):
        self.module_whitelist_option_vars = {}
        for child in self.whitelist_editor_list_frame.winfo_children():
            child.destroy()
        for display_name, module_name in options:
            variable = tk.BooleanVar(value=module_name in selected_modules)
            self.module_whitelist_option_vars[module_name] = variable
            tb.Checkbutton(self.whitelist_editor_list_frame, text=display_name, variable=variable, bootstyle="round-toggle").pack(anchor=W, pady=4)

    def clear_module_whitelist_editor_selection(self):
        for variable in self.module_whitelist_option_vars.values():
            variable.set(False)

    def get_module_whitelist_editor_selection(self):
        return [module_name for module_name, variable in self.module_whitelist_option_vars.items() if variable.get()]

    def set_persistent_modules_editor_visible(self, visible):
        if visible:
            if not self.persistent_modules_editor_frame.winfo_manager():
                self.persistent_modules_editor_frame.pack(fill=X, pady=(0, 12))
            return
        if self.persistent_modules_editor_frame.winfo_manager():
            self.persistent_modules_editor_frame.pack_forget()

    def is_persistent_modules_editor_visible(self):
        return bool(self.persistent_modules_editor_frame.winfo_manager())

    def configure_persistent_modules_editor(self, options, selected_modules):
        self.persistent_module_option_vars = {}
        for child in self.persistent_modules_editor_list_frame.winfo_children():
            child.destroy()
        for display_name, module_name in options:
            variable = tk.BooleanVar(value=module_name in selected_modules)
            self.persistent_module_option_vars[module_name] = variable
            tb.Checkbutton(self.persistent_modules_editor_list_frame, text=display_name, variable=variable, bootstyle="round-toggle").pack(anchor=W, pady=4)

    def clear_persistent_modules_editor_selection(self):
        for variable in self.persistent_module_option_vars.values():
            variable.set(False)

    def get_persistent_modules_editor_selection(self):
        return [module_name for module_name, variable in self.persistent_module_option_vars.items() if variable.get()]

    def set_downtime_editor_visible(self, visible):
        if visible:
            if not self.downtime_editor_frame.winfo_manager():
                self.downtime_editor_frame.pack(fill=X, pady=(0, 12))
            return
        if self.downtime_editor_frame.winfo_manager():
            self.downtime_editor_frame.pack_forget()

    def is_downtime_editor_visible(self):
        return bool(self.downtime_editor_frame.winfo_manager())

    def _sort_downtime_code_value(self, code_text):
        return (int(code_text) if str(code_text).isdigit() else 10 ** 9, str(code_text))

    def add_downtime_code_row(self, code_value="", label_value=""):
        row = tb.Frame(self.downtime_editor_rows_frame)
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
            if len(self.downtime_code_rows) <= 1:
                code_entry.delete(0, END)
                label_entry.delete(0, END)
                return
            row.destroy()
            self.downtime_code_rows.remove(row_record)

        remove_button.configure(command=remove_row)
        self.downtime_code_rows.append(row_record)

    def configure_downtime_codes_editor(self, current_codes):
        for row_record in list(self.downtime_code_rows):
            row_record["frame"].destroy()
            self.downtime_code_rows.remove(row_record)
        for code in sorted(current_codes, key=self._sort_downtime_code_value):
            self.add_downtime_code_row(code, current_codes[code])
        if not self.downtime_code_rows:
            self.add_downtime_code_row()

    def reset_downtime_codes_editor_defaults(self):
        self.configure_downtime_codes_editor(DEFAULT_DT_CODE_MAP)

    def get_downtime_code_rows(self):
        return [
            {
                "code": record["code_entry"].get().strip(),
                "label": record["label_entry"].get().strip(),
            }
            for record in self.downtime_code_rows
        ]

    def set_security_admin_visible(self, visible):
        if visible:
            if not self.security_admin_tools_frame.winfo_manager():
                self.security_admin_tools_frame.pack(fill=BOTH, expand=True, pady=(0, 12))
            return
        if self.security_admin_tools_frame.winfo_manager():
            self.security_admin_tools_frame.pack_forget()

    def _build_security_right_controls(self, right_rows):
        for child in self.security_admin_rights_frame.winfo_children():
            child.destroy()
        self.security_admin_right_vars = {}
        for index, right_entry in enumerate(right_rows):
            variable = tk.BooleanVar(value=False)
            self.security_admin_right_vars[right_entry["key"]] = variable
            row = tb.Frame(self.security_admin_rights_frame)
            row.grid(row=index, column=0, sticky=EW, pady=3)
            tb.Checkbutton(row, text=right_entry["label"], variable=variable, bootstyle="round-toggle").pack(anchor=W)
            tb.Label(
                row,
                text=right_entry["description"],
                bootstyle=SECONDARY,
                justify=LEFT,
                wraplength=540,
            ).pack(anchor=W, padx=(26, 0))

    def update_security_role_note(self):
        current_role = self.security_admin_role_var.get().strip().lower() or "general"
        limit = self._security_admin_state.get("role_limits", {}).get(current_role)
        if current_role in {"admin", "developer"}:
            self.security_admin_password_note_var.set(f"{current_role.title()} vaults require a password. Limit: {limit}.")
            return
        self.security_admin_password_note_var.set(f"General vaults can remain passwordless. Limit: {limit}.")

    def apply_security_role_defaults(self):
        current_role = self.security_admin_role_var.get().strip().lower() or "general"
        defaults = set(self._security_admin_state.get("role_defaults", {}).get(current_role, []))
        for key, variable in self.security_admin_right_vars.items():
            variable.set(key in defaults)
        self.update_security_role_note()

    def populate_security_vault_list(self, vaults, preferred_name=None):
        self.security_admin_vault_listbox.delete(0, tk.END)
        target_index = None
        session_name = self._security_admin_state.get("session_vault_name")
        active_name = preferred_name or session_name
        for index, vault_record in enumerate(vaults):
            enabled_text = "enabled" if vault_record.get("enabled", True) else "disabled"
            display_text = f"{vault_record['vault_name']} | {vault_record['role']} | {enabled_text}"
            if vault_record.get("vault_name") == session_name:
                display_text = f"{display_text} | active"
            self.security_admin_vault_listbox.insert(tk.END, display_text)
            if vault_record.get("vault_name") == active_name:
                target_index = index
        self.security_admin_note_var.set(f"Configured vaults: {len(vaults)}")
        self.security_admin_vault_listbox.selection_clear(0, tk.END)
        if target_index is None and vaults:
            target_index = 0
        if target_index is not None:
            self.security_admin_vault_listbox.selection_set(target_index)

    def get_selected_security_vault_name(self):
        selection = self.security_admin_vault_listbox.curselection()
        if not selection:
            return ""
        index = selection[0]
        vaults = self._security_admin_state.get("vaults", [])
        if index >= len(vaults):
            return ""
        return str(vaults[index].get("vault_name", ""))

    def get_selected_security_vault_record(self):
        selection = self.security_admin_vault_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        vaults = self._security_admin_state.get("vaults", [])
        if index >= len(vaults):
            return None
        return vaults[index]

    def clear_security_vault_selection(self):
        self.security_admin_vault_listbox.selection_clear(0, tk.END)

    def set_security_vault_form(self, vault_record=None):
        self.security_admin_name_var.set(vault_record.get("vault_name", "") if vault_record else "")
        self.security_admin_role_var.set(vault_record.get("role", "general") if vault_record else "general")
        self.security_admin_enabled_var.set(bool(vault_record.get("enabled", True)) if vault_record else True)
        rights_to_apply = set(vault_record.get("rights", [])) if vault_record else set(self._security_admin_state.get("role_defaults", {}).get("general", []))
        for key, variable in self.security_admin_right_vars.items():
            variable.set(key in rights_to_apply)
        self.update_security_role_note()

    def configure_security_admin_panel(self, state, preferred_name=None):
        self._security_admin_state = state or {}
        self.security_admin_session_var.set(self._security_admin_state.get("session_summary", "Locked"))
        self.security_admin_non_secure_var.set(bool(self._security_admin_state.get("non_secure_mode", False)))
        self._build_security_right_controls(self._security_admin_state.get("access_rights", []))
        vaults = self._security_admin_state.get("vaults", [])
        self.populate_security_vault_list(vaults, preferred_name=preferred_name)
        self.set_security_vault_form(self.get_selected_security_vault_record())

    def get_security_vault_payload(self, reset_password=False):
        selected_rights = [key for key, variable in self.security_admin_right_vars.items() if variable.get()]
        return {
            "existing_name": self.get_selected_security_vault_name() or None,
            "vault_name": self.security_admin_name_var.get().strip(),
            "role": self.security_admin_role_var.get().strip().lower(),
            "enabled": bool(self.security_admin_enabled_var.get()),
            "rights": selected_rights,
            "reset_password": bool(reset_password),
        }

    def get_security_non_secure_mode(self):
        return bool(self.security_admin_non_secure_var.get())

    def set_developer_admin_status(self, value):
        self.developer_admin_status_var.set(value)

    def set_developer_admin_visible(self, visible):
        if visible:
            if not self.developer_admin_frame.winfo_manager():
                self.developer_admin_frame.pack(fill=X, pady=(5, 10))
            if not self.developer_admin_note.winfo_manager():
                self.developer_admin_note.pack(anchor=W, pady=(0, 10))
            if not self.developer_admin_tools_frame.winfo_manager():
                self.developer_admin_tools_frame.pack(fill=BOTH, expand=True, pady=(0, 12))
            return
        if self.developer_admin_frame.winfo_manager():
            self.developer_admin_frame.pack_forget()
        if self.developer_admin_note.winfo_manager():
            self.developer_admin_note.pack_forget()
        if self.developer_admin_tools_frame.winfo_manager():
            self.developer_admin_tools_frame.pack_forget()

    def configure_developer_admin_tools(self, current_settings):
        self.developer_admin_repo_var.set(current_settings.get("update_repository_url", ""))
        self.developer_admin_advanced_var.set(bool(current_settings.get("enable_advanced_dev_updates", False)))
        self.developer_admin_override_trust_var.set(bool(current_settings.get("enable_external_override_trust", False)))
        self.external_modules_status_var.set(current_settings.get("external_modules_status", ""))

    def get_developer_admin_settings_values(self):
        return {
            "update_repository_url": self.developer_admin_repo_var.get(),
            "enable_advanced_dev_updates": bool(self.developer_admin_advanced_var.get()),
            "enable_external_override_trust": bool(self.developer_admin_override_trust_var.get()),
        }

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

    def _resolve_modal_parent(self, explicit_parent=None):
        if explicit_parent is not None:
            return explicit_parent
        if self._active_modal_parent is not None and self._active_modal_parent.winfo_exists():
            return self._active_modal_parent
        return self.parent

    def ask_for_password_pair(self, title, prompt_text, parent=None):
        modal_parent = self._resolve_modal_parent(parent)
        first = simpledialog.askstring(title, prompt_text, show="*", parent=modal_parent)
        if first is None:
            return None
        second = simpledialog.askstring(title, "Re-enter the password:", show="*", parent=modal_parent)
        if second is None:
            return None
        if first != second:
            self.show_error(title, "The passwords did not match.")
            return None
        if not first.strip():
            self.show_error(title, "A password is required.")
            return None
        return first

    def ask_yes_no(self, title, message, parent=None):
        return bool(messagebox.askyesno(title, message, parent=self._resolve_modal_parent(parent)))

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
        previous_modal_parent = self._active_modal_parent
        self._active_modal_parent = top

        outer = tb.Frame(top, padding=0)
        outer.pack(fill=BOTH, expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = tb.Scrollbar(outer, orient=VERTICAL, command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        container = tb.Frame(canvas, padding=20)
        window_id = canvas.create_window((0, 0), window=container, anchor="nw")
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)

        def sync_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_window_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        container.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_window_width)
        self.dispatcher.bind_mousewheel_to_widget_tree(outer, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(canvas, canvas)
        self.dispatcher.bind_mousewheel_to_widget_tree(scrollbar, canvas)

        session_var = tk.StringVar(value=state.get("session_summary", "Locked"))
        security_note_var = tk.StringVar(value="")
        selected_name_var = tk.StringVar(value="")
        name_var = tk.StringVar(value="")
        role_var = tk.StringVar(value="general")
        enabled_var = tk.BooleanVar(value=True)
        non_secure_var = tk.BooleanVar(value=bool(state.get("non_secure_mode", False)))
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
            if not vault_listbox.winfo_exists():
                return
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

        security_mode_frame = tb.Labelframe(right_frame, text=" Security Mode ", padding=12)
        security_mode_frame.grid(row=form_row + 1, column=0, columnspan=2, sticky=EW, pady=(14, 0))
        tb.Checkbutton(
            security_mode_frame,
            text="Persistently bypass protected-module authentication",
            variable=non_secure_var,
            bootstyle="round-toggle",
        ).pack(anchor=W)
        tb.Label(
            security_mode_frame,
            text="This is a global persisted setting intended for controlled admin use only.",
            bootstyle=SECONDARY,
            justify=LEFT,
            wraplength=540,
        ).pack(anchor=W, pady=(6, 0))

        def handle_save_security_mode():
            desired_state = bool(non_secure_var.get())
            current_mode = bool(current_state["value"].get("non_secure_mode", False))
            if desired_state == current_mode:
                return
            action_text = "enable" if desired_state else "disable"
            if not self.ask_yes_no("Confirm Security Change", f"Are you sure you want to {action_text} persisted non-secure mode?"):
                non_secure_var.set(current_mode)
                return
            try:
                new_state = self.controller.set_security_non_secure_mode(desired_state)
            except Exception as exc:
                self.show_error("Security", str(exc))
                non_secure_var.set(current_mode)
                return
            current_state["value"] = new_state
            session_var.set(new_state.get("session_summary", "Locked"))
            non_secure_var.set(bool(new_state.get("non_secure_mode", False)))

        action_row = tb.Frame(right_frame)
        action_row.grid(row=form_row + 2, column=0, columnspan=2, sticky=EW, pady=(14, 0))
        tb.Button(action_row, text="New Vault", bootstyle=SECONDARY, command=lambda: fill_form(None)).pack(side=LEFT)
        tb.Button(action_row, text="Role Defaults", bootstyle=INFO, command=apply_role_defaults).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save Vault", bootstyle=SUCCESS, command=handle_save).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save + Reset Password", bootstyle=INFO, command=lambda: handle_save(reset_password=True)).pack(side=LEFT, padx=(8, 0))
        tb.Button(action_row, text="Save Security Mode", bootstyle="warning", command=handle_save_security_mode).pack(side=LEFT, padx=(8, 0))

        secondary_actions = tb.Frame(right_frame)
        secondary_actions.grid(row=form_row + 3, column=0, columnspan=2, sticky=EW, pady=(10, 0))
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
        self._active_modal_parent = previous_modal_parent

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

        def collect_code_rows():
            return [
                {
                    "code": record["code_entry"].get().strip(),
                    "label": record["label_entry"].get().strip(),
                }
                for record in code_rows
            ]

        def add_next_code():
            add_code_row(self.controller.suggest_next_downtime_code(collect_code_rows()), "")

        def save_codes():
            if self.controller.save_downtime_code_rows(collect_code_rows()):
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
        self.show_info(
            "Developer & Admin Tools",
            "The legacy Settings-based override editor was removed. Sign in and use the Internal Code Editor from the main navigation instead.",
        )

    def on_hide(self):
        return None

    def on_unload(self):
        return None