import threading
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
    managed_source_signature: tuple = field(default_factory=tuple)
    managed_source_generation: int = 0
    preloaded_module_names: set = field(default_factory=set)
    module_import_lock: object = field(default_factory=threading.RLock)
    module_preload_stop_event: object = field(default_factory=threading.Event)
    module_preload_thread: object = None
    module_preload_poll_seconds: float = 1.0