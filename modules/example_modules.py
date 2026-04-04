# The Martin Suite (GLC Edition)
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
from ttkbootstrap.constants import *

__module_name__ = "Example System"
__version__ = "1.0.0"

def get_ui(parent, dispatcher):
    container = tb.Frame(parent)
    container.pack(fill=BOTH, expand=True)

    tb.Label(container, text="Module Loaded Successfully", font=("Helvetica", 16)).pack(pady=10)
    
    status_label = tb.Label(container, text=f"System Status: {dispatcher.shared_data['system_status']}")
    status_label.pack(pady=5)

    def trigger_update():
        dispatcher.shared_data['system_status'] = "Active"
        status_label.config(text="System Status: Active")

    tb.Button(container, text="Update Shared Data", command=trigger_update, bootstyle=SUCCESS).pack(pady=10)

def handle(shared_data):
    print(f"Module Logic Initialized with: {shared_data['user_info']}")