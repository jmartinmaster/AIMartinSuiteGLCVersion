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
import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, BOTTOM, CENTER, HORIZONTAL, INFO, LEFT, RIGHT, SECONDARY, WARNING, X

__module_name__ = "About System"
__version__ = "1.0.0"


class AboutView:
    def __init__(self, parent, dispatcher, controller):
        self.parent = parent
        self.dispatcher = dispatcher
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=30)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="PRODUCTION LOGGING CENTER", font=("-size 24 -weight bold")).pack()
        tb.Label(container, text="GLC Edition", font=("-size 14 -slant italic"), bootstyle=INFO).pack(pady=5)

        tb.Separator(container, orient=HORIZONTAL).pack(fill=X, pady=20)

        info_text = (
            "Author: Jamie Martin\n"
            "License: GNU General Public License v3.0\n"
            "Location: Ludington, MI\n"
            "Environment: Windows / Portable Python 3.12"
        )
        tb.Label(container, text=info_text, justify=CENTER).pack(pady=10)

        tb.Button(
            container,
            text="Open License",
            bootstyle=SECONDARY,
            command=self.controller.open_license,
        ).pack(pady=(0, 10))

        version_frame = tb.Labelframe(container, text=" Module Manifest ", padding=15)
        version_frame.pack(fill=X, pady=20)
        self.controller.render_module_manifest(version_frame)

        if self.controller.can_repack():
            repack_frame = tb.Frame(container, padding=10)
            repack_frame.pack(fill=X, side=BOTTOM, pady=20)

            tb.Separator(repack_frame, orient=HORIZONTAL).pack(fill=X, pady=10)
            tb.Button(
                repack_frame,
                text="REPACK SUITE (Bake Changes)",
                bootstyle="warning-outline",
                command=self.controller.confirm_repack,
            ).pack(pady=10)
            tb.Label(
                repack_frame,
                text="Note: This will bake current JSON/Module changes into a new EXE and restart.",
                font=("-size 8"),
                bootstyle=SECONDARY,
            ).pack()

        tb.Label(container, text="Copyright © 2026 Jamie Martin", font=("-size 8")).pack(side=BOTTOM)

    def render_module_row(self, parent, display_name, version, source_suffix):
        row = tb.Frame(parent)
        row.pack(fill=X, pady=2)
        tb.Label(row, text=f"{display_name}{source_suffix}", font=("-weight bold")).pack(side=LEFT)
        tb.Label(row, text=f"v{version}", bootstyle=SECONDARY).pack(side=RIGHT)

    def render_empty_manifest(self, parent):
        tb.Label(parent, text="No active modules loaded.", bootstyle=WARNING).pack()

    def on_hide(self):
        return None

    def on_unload(self):
        return None
