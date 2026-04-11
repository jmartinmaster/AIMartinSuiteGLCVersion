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