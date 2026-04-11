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
from dataclasses import dataclass, field


@dataclass
class AppModel:
    modules_path: str
    external_modules_path: str
    layout_config: str
    rate_config: str
    settings_path: str
    shared_data: dict = field(default_factory=dict)
    loaded_modules: dict = field(default_factory=dict)
    persistent_module_instances: dict = field(default_factory=dict)
    runtime_settings_listeners: list = field(default_factory=list)
    active_module_instance: object = None
    active_module_name: str = None
    active_module_frame: object = None
    runtime_settings: dict = field(default_factory=dict)
    window_alpha_supported: bool = False
    transition_duration_ms: int = 360
    transitions_enabled: bool = True
    transition_min_alpha: float = 0.82
    transition_in_progress: bool = False
    module_update_check_in_progress: bool = False
    last_module_update_notification_signature: tuple = None