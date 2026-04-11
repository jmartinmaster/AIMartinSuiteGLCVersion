import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, INFO, LEFT, PRIMARY, SECONDARY, SUCCESS, WARNING, W, X

__module_name__ = "Update Manager"
__version__ = "1.0.0"


class UpdateManagerView:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.container = None
        self.setup_ui()

    def setup_ui(self):
        if self.container is not None and self.container.winfo_exists():
            self.container.destroy()

        container = tb.Frame(self.parent, padding=20)
        container.pack(fill=BOTH, expand=True)
        self.container = container

        tb.Label(container, text="Update Manager", font=("Helvetica", 18, "bold")).pack(anchor=W, pady=(0, 10))
        tb.Label(
            container,
            text=(
                "Compare the local Dispatcher Core version with the repository branch release target. "
                "Odd third patch numbers stay in-progress and are ignored by the updater. "
                "Stable updates follow the current runtime platform: Windows downloads and launches versioned EXEs, while Ubuntu downloads and opens versioned DEB packages."
            ),
            wraplength=760,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 12))

        summary = tb.Labelframe(container, text=" Release Target ", padding=14)
        summary.pack(fill=X, pady=(0, 12))
        tb.Label(summary, textvariable=self.controller.target_name_var, font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 8))
        tb.Label(summary, text="Repository", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.controller.repo_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Branch", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.controller.branch_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Local Version", bootstyle=SECONDARY).grid(row=3, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.controller.local_version_var).grid(row=3, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Repository Version", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.controller.remote_version_var).grid(row=4, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Status", bootstyle=SECONDARY).grid(row=5, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.controller.result_var).grid(row=5, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Job Phase", bootstyle=SECONDARY).grid(row=6, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.controller.job_phase_var).grid(row=6, column=1, sticky=W, pady=2)
        tb.Label(summary, textvariable=self.controller.note_var, bootstyle=INFO, wraplength=720, justify=LEFT).grid(row=7, column=0, columnspan=2, sticky=W, pady=(10, 0))
        tb.Label(summary, textvariable=self.controller.job_detail_var, bootstyle=SECONDARY, wraplength=720, justify=LEFT).grid(row=8, column=0, columnspan=2, sticky=W, pady=(8, 0))

        controls = tb.Frame(container)
        controls.pack(fill=X, pady=(12, 0))
        tb.Button(controls, text="Check Repository", bootstyle=PRIMARY, command=self.controller.check_for_updates).pack(side=LEFT)
        tb.Button(controls, text="Apply Stable Updates", bootstyle=SUCCESS, command=self.controller.apply_updates).pack(side=LEFT, padx=8)

        module_payload = tb.Labelframe(container, text=" Payload Restores ", padding=14)
        module_payload.pack(fill=X, pady=(12, 0))
        tb.Label(
            module_payload,
            text="Choose a single module or tracked config payload to compare and restore without rebuilding the EXE. Dispatcher Core stays outside this list and continues to update through the stable EXE path above.",
            wraplength=720,
            justify=LEFT,
        ).pack(anchor=W)
        payload_grid = tb.Frame(module_payload)
        payload_grid.pack(fill=X, pady=(10, 0))
        tb.Label(payload_grid, text="Payload", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        module_payload_selector = tb.Combobox(
            payload_grid,
            textvariable=self.controller.module_payload_selection_var,
            values=[option["display"] for option in self.controller.module_payload_options],
            state="readonly" if self.controller.module_payload_options else "disabled",
            width=42,
        )
        module_payload_selector.grid(row=0, column=1, sticky=W, pady=2)
        module_payload_selector.bind("<<ComboboxSelected>>", self.controller.handle_module_payload_selection_change)
        tb.Label(payload_grid, text="Name", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.controller.module_payload_name_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Repository Path", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.controller.module_payload_path_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Local State", bootstyle=SECONDARY).grid(row=3, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.controller.module_payload_local_version_var).grid(row=3, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Repository State", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.controller.module_payload_remote_version_var).grid(row=4, column=1, sticky=W, pady=2)
        tb.Label(payload_grid, text="Status", bootstyle=SECONDARY).grid(row=5, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(payload_grid, textvariable=self.controller.module_payload_status_var).grid(row=5, column=1, sticky=W, pady=2)
        tb.Label(module_payload, textvariable=self.controller.module_payload_note_var, bootstyle=INFO, wraplength=720, justify=LEFT).pack(anchor=W, pady=(10, 0))
        payload_controls = tb.Frame(module_payload)
        payload_controls.pack(anchor=W, pady=(10, 0))
        tb.Button(payload_controls, text="Check Selected Payload", bootstyle=PRIMARY, command=self.controller.check_module_payload_update).pack(side=LEFT)
        tb.Button(payload_controls, text="Install Selected Payload", bootstyle=SUCCESS, command=self.controller.apply_module_payload_update).pack(side=LEFT, padx=(8, 0))
        tb.Button(payload_controls, text="Install All Available Module/Config Payloads", bootstyle=WARNING, command=self.controller.apply_all_module_payload_updates).pack(side=LEFT, padx=(8, 0))

        documentation_payload = tb.Labelframe(container, text=" Documentation Restores ", padding=14)
        documentation_payload.pack(fill=X, pady=(12, 0))
        tb.Label(
            documentation_payload,
            text="Restore the bundled Help Center documents as one grouped update. Individual documentation files are not selectable here.",
            wraplength=720,
            justify=LEFT,
        ).pack(anchor=W)
        documentation_grid = tb.Frame(documentation_payload)
        documentation_grid.pack(fill=X, pady=(10, 0))
        tb.Label(documentation_grid, text="Tracked Files", bootstyle=SECONDARY).grid(row=0, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(documentation_grid, textvariable=self.controller.documentation_payload_tracked_var).grid(row=0, column=1, sticky=W, pady=2)
        tb.Label(documentation_grid, text="Repository State", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(documentation_grid, textvariable=self.controller.documentation_payload_remote_state_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(documentation_grid, text="Status", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(documentation_grid, textvariable=self.controller.documentation_payload_status_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(documentation_payload, textvariable=self.controller.documentation_payload_note_var, bootstyle=INFO, wraplength=720, justify=LEFT).pack(anchor=W, pady=(10, 0))
        documentation_controls = tb.Frame(documentation_payload)
        documentation_controls.pack(anchor=W, pady=(10, 0))
        tb.Button(documentation_controls, text="Check Documentation Updates", bootstyle=PRIMARY, command=self.controller.check_documentation_payload_updates).pack(side=LEFT)
        tb.Button(documentation_controls, text="Install Documentation Updates", bootstyle=SUCCESS, command=self.controller.apply_documentation_payload_updates).pack(side=LEFT, padx=(8, 0))

        tb.Label(container, textvariable=self.controller.status_var, bootstyle=SECONDARY).pack(anchor=W, pady=(12, 0))
