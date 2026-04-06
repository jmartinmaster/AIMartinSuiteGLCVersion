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

import os
import sys
import importlib
import json
import ctypes
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, PhotoImage
from ctypes import wintypes
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToastNotification
from app_identity import DEFAULT_UPDATE_REPOSITORY_URL, LEGACY_EXE_NAME, normalize_version, parse_version, parse_versioned_exe_name
from modules.app_logging import log_exception
from modules.persistence import write_json_with_backup
from modules.theme_manager import apply_readability_overrides, get_theme_tokens, normalize_theme, resolve_base_theme, DEFAULT_THEME
from modules.utils import external_path, local_or_resource_path, resource_path
from PIL import Image

BOTH = tk.BOTH
LEFT = tk.LEFT
RIGHT = tk.RIGHT
TOP = tk.TOP
BOTTOM = tk.BOTTOM
X = tk.X
Y = tk.Y
W = tk.W
VERTICAL = tk.VERTICAL
HORIZONTAL = tk.HORIZONTAL
INFO = "info"
SUCCESS = "success"
WARNING = "warning"
DANGER = "danger"
SECONDARY = "secondary"
DARK = "dark"
LIGHT = "light"

__module_name__ = "Dispatcher Core"
__version__ = "1.5.8"
ISSUE_REPORT_URL = "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion/issues/new/choose"
WINDOWS_APP_ID = "JamieMartin.TheMartinSuite.GLC"
APP_ICON_RELATIVE_PATH = "icon.ico"
APP_ICON_IMAGE_RELATIVE_PATHS = [
    "icon-16.png",
    "icon-24.png",
    "icon-32.png",
    "icon-48.png",
    "icon-64.png",
]
APP_ICON_SOURCE_RELATIVE_PATHS = [
    "icon.png",
    "icon.jpg",
]
SPLASH_LOGO_RELATIVE_PATH = "splash-logo.png"
WM_SETICON = 0x0080
WM_GETICON = 0x007F
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
GCLP_HICON = -14
GCLP_HICONSM = -34

UPDATE_PHASE_LABELS = {
    "idle": "Idle",
    "checking": "Checking",
    "ready": "Ready",
    "downloading": "Downloading",
    "handoff": "Handoff",
    "failed": "Failed",
    "source_armed": "Source Armed",
    "source_manifest": "Source Manifest",
    "source_downloading": "Source Downloading",
    "source_staging": "Source Staging",
    "source_extracting": "Source Extracting",
    "source_validating": "Source Validating",
    "source_building": "Source Building",
    "source_packaging": "Source Packaging",
    "source_cleanup": "Source Cleanup",
    "source_relaunch": "Source Relaunch",
    "source_complete": "Source Complete",
}

SOURCE_UPDATE_PHASES = {
    "source_armed",
    "source_manifest",
    "source_downloading",
    "source_staging",
    "source_extracting",
    "source_validating",
    "source_building",
    "source_packaging",
    "source_cleanup",
    "source_relaunch",
    "source_complete",
}

RECOVERABLE_SOURCE_PHASES = SOURCE_UPDATE_PHASES | {"failed"}
INTERRUPTED_SOURCE_PHASES = SOURCE_UPDATE_PHASES - {"source_armed", "source_complete"}
SOURCE_JOB_STATE_RELATIVE_PATH = os.path.join("data", "updater", "state", "source-job.json")
SOURCE_JOB_BACKUP_RELATIVE_PATH = os.path.join("data", "backups", "updater")


def get_obsolete_local_executables(current_exe_path, current_version):
    if not getattr(sys, "frozen", False):
        return []

    current_version_parts = normalize_version(parse_version(current_version))
    if current_version_parts is None:
        return []

    current_name = os.path.basename(current_exe_path)
    current_directory = os.path.dirname(current_exe_path)
    obsolete_entries = []

    try:
        directory_entries = os.listdir(current_directory)
    except OSError:
        return []

    for file_name in directory_entries:
        if file_name.lower() == current_name.lower() or not file_name.lower().endswith(".exe"):
            continue

        file_path = os.path.join(current_directory, file_name)
        if not os.path.isfile(file_path):
            continue

        if file_name.lower() == LEGACY_EXE_NAME.lower():
            obsolete_entries.append({
                "name": file_name,
                "path": file_path,
                "version": "Legacy",
            })
            continue

        version_text = parse_versioned_exe_name(file_name)
        candidate_version = normalize_version(parse_version(version_text)) if version_text else None
        if candidate_version is None or candidate_version >= current_version_parts:
            continue

        obsolete_entries.append({
            "name": file_name,
            "path": file_path,
            "version": version_text,
        })

    return sorted(
        obsolete_entries,
        key=lambda entry: (
            0 if entry["version"] == "Legacy" else 1,
            normalize_version(parse_version(entry["version"])) or (0, 0, 0),
        ),
    )


def get_work_area_insets(root):
    right_inset = 0
    bottom_inset = 0
    if sys.platform.startswith("win"):
        try:
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                right_inset = max(0, root.winfo_screenwidth() - rect.right)
                bottom_inset = max(0, root.winfo_screenheight() - rect.bottom)
        except Exception:
            pass
    return right_inset, bottom_inset


def apply_windows_app_id():
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


def apply_windows_window_icons(root):
    if not sys.platform.startswith("win"):
        return

    icon_path = resource_path(APP_ICON_RELATIVE_PATH)
    if not os.path.exists(icon_path):
        return

    try:
        root.update_idletasks()
        hwnd = root.winfo_id()
        if not hwnd:
            return

        user32 = ctypes.windll.user32
        small_icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        big_icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE)

        if small_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
            user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, small_icon)
        if big_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big_icon)
            user32.SetClassLongPtrW(hwnd, GCLP_HICON, big_icon)

        root._windows_small_icon_handle = small_icon
        root._windows_big_icon_handle = big_icon
    except Exception as exc:
        log_exception("apply_windows_window_icons", exc)


def convert_png_to_ico(png_paths, output_ico_path):
    try:
        images = [Image.open(png_path) for png_path in png_paths if os.path.exists(png_path)]
        if images:
            images[0].save(output_ico_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            return True
        else:
            log_exception("convert_png_to_ico", "No valid PNG files found to convert.")
            return False
    except Exception as exc:
        log_exception("convert_png_to_ico", exc)
        return False


def apply_app_icon(window, icon_path="icon.png"):
    try:
        icon_images = []

        for relative_path in APP_ICON_IMAGE_RELATIVE_PATHS:
            icon_image_path = resource_path(relative_path)
            if not os.path.exists(icon_image_path):
                continue
            try:
                icon_images.append(PhotoImage(file=icon_image_path))
            except Exception as exc:
                log_exception("apply_app_icon.iconphoto_image", exc)

        if not icon_images:
            for relative_path in APP_ICON_SOURCE_RELATIVE_PATHS:
                icon_image_path = resource_path(relative_path)
                if not os.path.exists(icon_image_path):
                    continue
                try:
                    icon_images.append(PhotoImage(file=icon_image_path))
                    break
                except Exception as exc:
                    log_exception("apply_app_icon.iconphoto_source", exc)

        if icon_images:
            window.iconphoto(False, *icon_images)
            window._app_icon_images = icon_images

        apply_windows_window_icons(window)
    except Exception as exc:
        log_exception("apply_app_icon", exc)


class UpdateCoordinator:
    def __init__(self, root):
        self.root = root
        self.source_state_path = external_path(SOURCE_JOB_STATE_RELATIVE_PATH)
        self._loading_state = False
        self.branch_name = "main"
        self.remote_info = {"owner": None, "repo": None, "url": None, "display": "Unknown repository"}
        self.local_manifest = []
        self.comparison_rows = []
        self.download_in_progress = False
        self.source_job_in_progress = False
        self.active = False
        self.mode = None
        self.job_phase = "idle"
        self.job_detail = "No update job is running."
        self.source_archive_path = None
        self.source_stage_dir = None
        self.source_extract_dir = None
        self.source_root_dir = None
        self.source_build_log_path = None
        self.source_built_exe_path = None
        self.source_build_runtime = None
        self.source_build_runtime_issue = None
        self.banner_bootstyle = SECONDARY
        self.banner_var = tb.StringVar(master=root, value="Updates idle.")
        self.status_var = tb.StringVar(master=root, value="Ready to check for updates.")
        self.branch_var = tb.StringVar(master=root, value="main")
        self.repo_var = tb.StringVar(master=root, value="Unknown repository")
        self.target_name_var = tb.StringVar(master=root, value="Dispatcher Core")
        self.local_version_var = tb.StringVar(master=root, value="Unknown")
        self.remote_version_var = tb.StringVar(master=root, value="Not checked")
        self.result_var = tb.StringVar(master=root, value="Pending")
        self.note_var = tb.StringVar(master=root, value="Run a repository check to compare the packaged release target.")
        self.advanced_status_var = tb.StringVar(master=root, value="Advanced dev updates are available for packaged builds only.")
        self.job_phase_var = tb.StringVar(master=root, value="Idle")
        self.job_detail_var = tb.StringVar(master=root, value="No update job is running.")
        self.build_runtime_var = tb.StringVar(master=root, value="Build runtime not resolved yet.")
        self._load_source_job_state()

    def _normalize_existing_path(self, path_text):
        if not path_text:
            return None
        absolute_path = os.path.abspath(path_text)
        return absolute_path if os.path.exists(absolute_path) else None

    def _has_recoverable_source_state(self):
        return any([
            self.mode == "advanced",
            self.job_phase in RECOVERABLE_SOURCE_PHASES,
            self.source_archive_path,
            self.source_stage_dir,
            self.source_extract_dir,
            self.source_root_dir,
            self.source_build_log_path,
            self.source_built_exe_path,
            self.source_build_runtime,
            self.source_build_runtime_issue,
        ])

    def _serialize_source_job_state(self):
        if not self._has_recoverable_source_state():
            return None
        return {
            "metadata_version": 1,
            "branch_name": self.branch_name,
            "remote_info": self.remote_info,
            "job_phase": self.job_phase,
            "job_detail": self.job_detail,
            "mode": self.mode,
            "active": self.active,
            "banner_text": self.banner_var.get(),
            "banner_bootstyle": self.banner_bootstyle,
            "status_text": self.status_var.get(),
            "source_job_in_progress": self.source_job_in_progress,
            "source_archive_path": self.source_archive_path,
            "source_stage_dir": self.source_stage_dir,
            "source_extract_dir": self.source_extract_dir,
            "source_root_dir": self.source_root_dir,
            "source_build_log_path": self.source_build_log_path,
            "source_built_exe_path": self.source_built_exe_path,
            "source_build_runtime": self.source_build_runtime,
            "source_build_runtime_issue": self.source_build_runtime_issue,
        }

    def _persist_source_job_state(self):
        if self._loading_state:
            return

        payload = self._serialize_source_job_state()
        if payload is None:
            try:
                if os.path.exists(self.source_state_path):
                    os.remove(self.source_state_path)
            except OSError:
                pass
            return

        write_json_with_backup(
            self.source_state_path,
            payload,
            backup_dir=external_path(SOURCE_JOB_BACKUP_RELATIVE_PATH),
            keep_count=10,
        )

    def _load_source_job_state(self):
        if not os.path.exists(self.source_state_path):
            return

        try:
            with open(self.source_state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            log_exception("update_coordinator.load_source_job_state", exc)
            return

        if not isinstance(payload, dict):
            return

        phase = str(payload.get("job_phase") or "idle")
        mode = payload.get("mode")
        if mode == "advanced" or phase in SOURCE_UPDATE_PHASES:
            try:
                os.remove(self.source_state_path)
            except OSError:
                pass
            return

        self._loading_state = True
        try:
            remote_info = payload.get("remote_info")
            if isinstance(remote_info, dict):
                self.remote_info = remote_info
            self.branch_name = str(payload.get("branch_name") or self.branch_name)
            self.set_source_snapshot(
                archive_path=self._normalize_existing_path(payload.get("source_archive_path")),
                stage_dir=self._normalize_existing_path(payload.get("source_stage_dir")),
                extract_dir=self._normalize_existing_path(payload.get("source_extract_dir")),
                root_dir=self._normalize_existing_path(payload.get("source_root_dir")),
                build_log_path=self._normalize_existing_path(payload.get("source_build_log_path")),
                built_exe_path=self._normalize_existing_path(payload.get("source_built_exe_path")),
            )
            self.set_build_runtime(
                payload.get("source_build_runtime"),
                payload.get("source_build_runtime_issue"),
            )

            phase = str(payload.get("job_phase") or "idle")
            detail = str(payload.get("job_detail") or "Recovered source job state.")
            mode = payload.get("mode")
            active = bool(payload.get("active", False))
            banner_text = str(payload.get("banner_text") or "Recovered source job state.")
            banner_bootstyle = payload.get("banner_bootstyle", SECONDARY)
            status_text = str(payload.get("status_text") or "Recovered source job state.")
            was_in_progress = bool(payload.get("source_job_in_progress", False))

            if phase in INTERRUPTED_SOURCE_PHASES or was_in_progress:
                phase = "failed"
                mode = "advanced"
                active = True
                banner_bootstyle = WARNING
                detail = "Recovered an interrupted source update session. Staged files and logs are available for retry or cleanup."
                banner_text = "Recovered interrupted source update session."
                status_text = "Recovered interrupted source update session."

            self.set_job_phase(phase, detail, mode=mode)
            self.status_var.set(status_text)
            self.set_banner(banner_text, bootstyle=banner_bootstyle, active=active, mode=mode)
            self.source_job_in_progress = False
        finally:
            self._loading_state = False

    def set_banner(self, message, bootstyle=INFO, active=True, mode=None):
        self.active = active
        self.mode = mode
        self.banner_bootstyle = bootstyle if active else SECONDARY
        self.banner_var.set(message)
        self._persist_source_job_state()

    def set_job_phase(self, phase, detail=None, mode=None):
        normalized_phase = str(phase or "idle").strip().lower() or "idle"
        self.job_phase = normalized_phase
        self.job_detail = detail or ""
        self.mode = mode if mode is not None else self.mode
        self.job_phase_var.set(UPDATE_PHASE_LABELS.get(normalized_phase, normalized_phase.replace("_", " ").title()))
        self.job_detail_var.set(detail or "")
        self._persist_source_job_state()

    def set_source_phase(self, phase, detail=None):
        normalized_phase = str(phase or "source_armed").strip().lower() or "source_armed"
        if normalized_phase not in SOURCE_UPDATE_PHASES:
            raise ValueError(f"Unsupported source update phase: {phase}")
        self.set_job_phase(normalized_phase, detail=detail, mode="advanced")

    def is_source_phase_active(self):
        return self.job_phase in SOURCE_UPDATE_PHASES

    def clear_job_phase(self):
        self.set_job_phase("idle", "No update job is running.", mode=None)

    def set_source_snapshot(self, archive_path=None, stage_dir=None, extract_dir=None, root_dir=None, build_log_path=None, built_exe_path=None):
        self.source_archive_path = archive_path
        self.source_stage_dir = stage_dir
        self.source_extract_dir = extract_dir
        self.source_root_dir = root_dir
        self.source_build_log_path = build_log_path
        self.source_built_exe_path = built_exe_path
        self._persist_source_job_state()

    def set_build_runtime(self, runtime_text=None, issue_text=None):
        self.source_build_runtime = str(runtime_text).strip() if runtime_text else None
        self.source_build_runtime_issue = str(issue_text).strip() if issue_text else None
        if self.source_build_runtime:
            display_text = f"Build runtime: {self.source_build_runtime}"
        elif self.source_build_runtime_issue:
            display_text = f"Build runtime unavailable: {self.source_build_runtime_issue}"
        else:
            display_text = "Build runtime not resolved yet."
        self.build_runtime_var.set(display_text)
        self._persist_source_job_state()

    def clear_source_snapshot(self):
        self.set_source_snapshot()

    def clear_banner(self):
        self.set_banner("Updates idle.", active=False, mode=None)
        self.clear_job_phase()

class Dispatcher:
    def __init__(self, root):
        apply_windows_app_id()
        self.root = root
        self.root.title(f"The Martin Suite - {__version__}")
        screen_width = max(1, self.root.winfo_screenwidth())
        screen_height = max(1, self.root.winfo_screenheight())
        initial_width = max(1040, min(1440, int(screen_width * 0.78)))
        initial_height = max(620, min(920, int(screen_height * 0.82)))
        self.root.geometry(f"{initial_width}x{initial_height}")
        self.root.minsize(max(820, int(screen_width * 0.5)), max(520, int(screen_height * 0.5)))
        apply_app_icon(self.root)

        self.modules_path = resource_path("modules")
        self.external_modules_path = external_path("modules")

        self.layout_config = local_or_resource_path("layout_config.json")
        self.rate_config = local_or_resource_path("rates.json")

        self._configure_module_import_paths()

        self.shared_data = {}
        self.loaded_modules = {"main": sys.modules[__name__]}
        self.persistent_module_instances = {}
        self.active_module_instance = None
        self.active_module_name = None
        self.active_module_frame = None
        self.settings_path = external_path("settings.json")
        self.runtime_settings = self.load_runtime_settings()
        self.window_alpha_supported = self._supports_window_alpha()
        self.transition_duration_ms = 360
        self.transitions_enabled = True
        self.transition_min_alpha = 0.82
        self._transition_in_progress = False
        self.transition_slide_distance_px = 34
        self._update_status_hide_after_id = None
        self.update_coordinator = UpdateCoordinator(self.root)
        self.runtime_settings_listeners = []
        self.module_update_check_in_progress = False
        self.last_module_update_notification_signature = None
        self.nav_buttons = {}
        self.refresh_animation_settings()

        self._setup_ui()
        self._setup_menu()
        self.pre_load_manifest()
        self._load_modules_list()
        self._bind_mousewheel()
        self.refresh_update_status_visibility()
        self.load_module("production_log", use_transition=False)
        self.root.after(900, self.prompt_old_executable_cleanup)
        self.root.after(1800, self.check_for_available_module_updates)

    def _configure_module_import_paths(self):
        bundled_base_dir = os.path.dirname(self.modules_path)
        external_base_dir = os.path.dirname(self.external_modules_path)

        if external_base_dir not in sys.path:
            sys.path.insert(0, external_base_dir)
        if bundled_base_dir not in sys.path:
            sys.path.append(bundled_base_dir)

        modules_package = sys.modules.get("modules")
        if modules_package is not None and hasattr(modules_package, "__path__"):
            package_paths = []
            candidate_paths = [self.modules_path, self.external_modules_path]
            if self.has_external_module_overrides():
                candidate_paths = [self.external_modules_path, self.modules_path]

            for candidate in candidate_paths:
                if candidate == self.external_modules_path and not self.has_external_modules_directory():
                    continue
                if candidate not in package_paths:
                    package_paths.append(candidate)
            for candidate in list(modules_package.__path__):
                if candidate not in package_paths:
                    package_paths.append(candidate)
            modules_package.__path__ = package_paths

        importlib.invalidate_caches()

    def ensure_external_modules_package(self):
        os.makedirs(self.external_modules_path, exist_ok=True)
        self._configure_module_import_paths()

    def import_managed_module(self, module_name, force_fresh=True):
        module_path = f"modules.{module_name}"
        self._configure_module_import_paths()
        if force_fresh and module_path in sys.modules:
            del sys.modules[module_path]
        importlib.invalidate_caches()
        module = importlib.import_module(module_path)
        self.loaded_modules[module_name] = module
        return module

    def get_external_module_override_path(self, module_name):
        candidate = os.path.join(self.external_modules_path, f"{module_name}.py")
        return candidate if os.path.exists(candidate) else None

    def has_external_modules_directory(self):
        return os.path.isdir(self.external_modules_path) and os.path.abspath(self.external_modules_path) != os.path.abspath(self.modules_path)

    def get_external_module_override_names(self):
        if not self.has_external_modules_directory():
            return []

        module_names = []
        for file_name in os.listdir(self.external_modules_path):
            if not file_name.endswith(".py") or file_name == "__init__.py":
                continue
            module_name = os.path.splitext(file_name)[0]
            if module_name not in module_names:
                module_names.append(module_name)
        return sorted(module_names)

    def get_bundled_module_names(self):
        if not os.path.isdir(self.modules_path):
            return []

        module_names = []
        for file_name in os.listdir(self.modules_path):
            if not file_name.endswith(".py") or file_name == "__init__.py":
                continue
            module_name = os.path.splitext(file_name)[0]
            if module_name not in module_names:
                module_names.append(module_name)
        return sorted(module_names)

    def has_external_module_overrides(self):
        return bool(self.get_external_module_override_names())

    def are_external_module_overrides_enabled(self):
        return self.has_external_module_overrides()

    def is_module_loaded_from_external(self, module_name, module_obj=None):
        if module_name == "main":
            return False
        if not self.has_external_modules_directory():
            return False
        candidate_module = module_obj or self.loaded_modules.get(module_name)
        module_file = getattr(candidate_module, "__file__", "") if candidate_module is not None else ""
        if not module_file:
            return False
        normalized_file = os.path.abspath(module_file)
        normalized_external_root = os.path.abspath(self.external_modules_path)
        try:
            return os.path.commonpath([normalized_file, normalized_external_root]) == normalized_external_root
        except Exception:
            return False

    def reset_module_import_state(self, keep_active=True):
        active_name = self.active_module_name if keep_active else None
        for module_name, session in list(self.persistent_module_instances.items()):
            if keep_active and module_name == active_name:
                continue
            instance = session.get("instance")
            frame = session.get("frame")
            if hasattr(instance, 'on_unload'):
                try:
                    instance.on_unload()
                except Exception as exc:
                    log_exception(f"reset_module_import_state.{module_name}", exc)
            if frame is not None and frame.winfo_exists():
                frame.destroy()
            self.persistent_module_instances.pop(module_name, None)

        for module_name in list(self.loaded_modules):
            if module_name == "main" or (keep_active and module_name == active_name):
                continue
            self.loaded_modules.pop(module_name, None)
            sys.modules.pop(f"modules.{module_name}", None)

    def install_module_override(self, module_name, module_text):
        self.ensure_external_modules_package()
        target_path = os.path.join(self.external_modules_path, f"{module_name}.py")
        temp_path = f"{target_path}.tmp"
        with open(temp_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(module_text)
        os.replace(temp_path, target_path)
        module = self.import_managed_module(module_name, force_fresh=True)
        return target_path, module

    def remove_external_module_overrides(self, module_names=None, include_bytecode=True):
        if not self.has_external_modules_directory():
            return []

        managed_names = module_names or self.get_bundled_module_names()
        removed_paths = []
        pycache_dir = os.path.join(self.external_modules_path, "__pycache__")

        for module_name in managed_names:
            override_path = os.path.join(self.external_modules_path, f"{module_name}.py")
            if os.path.isfile(override_path):
                os.remove(override_path)
                removed_paths.append(override_path)

            if include_bytecode and os.path.isdir(pycache_dir):
                cache_prefix = f"{module_name}."
                for cache_name in os.listdir(pycache_dir):
                    if not cache_name.startswith(cache_prefix):
                        continue
                    cache_path = os.path.join(pycache_dir, cache_name)
                    if os.path.isfile(cache_path):
                        os.remove(cache_path)
                        removed_paths.append(cache_path)

        if include_bytecode and os.path.isdir(pycache_dir):
            try:
                if not os.listdir(pycache_dir):
                    os.rmdir(pycache_dir)
            except OSError:
                pass

        return removed_paths

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Draft", command=self.menu_open, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Draft", command=self.menu_save, accelerator="Ctrl+S")
        file_menu.add_command(label="Export to Excel", command=self.menu_export, accelerator="Ctrl+E")
        file_menu.add_command(label="Import Excel", command=self.menu_import, accelerator="Ctrl+I")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        self.root.bind('<Control-o>', self.menu_open)
        self.root.bind('<Control-s>', self.menu_save)
        self.root.bind('<Control-e>', self.menu_export)
        self.root.bind('<Control-i>', self.menu_import)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="User Guide", command=lambda: self.load_module("help_viewer"))
        help_menu.add_command(label="Report A Problem", command=self.open_issue_report_page)
        help_menu.add_command(label="About", command=lambda: self.load_module("about"))
        menubar.add_cascade(label="Help", menu=help_menu)

    def open_issue_report_page(self):
        try:
            webbrowser.open(ISSUE_REPORT_URL)
        except Exception as exc:
            log_exception("open_issue_report_page", exc)
            messagebox.showerror("Report A Problem", f"Could not open the GitHub issue page:\n\n{exc}")

    def menu_open(self, event=None):
        self.load_module("production_log")
        if hasattr(self.active_module_instance, 'show_pending'):
            self.active_module_instance.show_pending()

    def menu_save(self, event=None):
        if hasattr(self.active_module_instance, 'save_draft'):
            self.active_module_instance.save_draft()
        else:
            self.show_toast("Action Unavailable", "Save action is not supported on this page.", WARNING)

    def menu_export(self, event=None):
        if hasattr(self.active_module_instance, 'export_to_excel'):
            self.active_module_instance.export_to_excel()
        else:
            self.show_toast("Action Unavailable", "Export action is not supported on this page.", WARNING)
            
    def menu_import(self, event=None):
        self.load_module("production_log")
        if hasattr(self.active_module_instance, 'import_from_excel_ui'):
            self.active_module_instance.import_from_excel_ui()

    def pre_load_manifest(self):
        module_list = ["production_log", "layout_manager", "data_handler", "about", "settings_manager", "theme_manager", "help_viewer", "update_manager", "recovery_viewer"]
        for mod_name in module_list:
            try:
                if mod_name not in self.loaded_modules:
                    self.import_managed_module(mod_name, force_fresh=False)
            except Exception as e:
                log_exception(f"pre_load_manifest.{mod_name}", e)

    def _setup_ui(self):
        self.main_container = tb.Frame(self.root, style="Martin.App.TFrame")
        self.main_container.pack(fill=BOTH, expand=True)

        self.sidebar = tb.Frame(self.main_container, style="Martin.Sidebar.TFrame", width=184, padding=(8, 14, 8, 12))
        self.sidebar.pack(side=LEFT, fill=Y)
        self.sidebar.pack_propagate(False)

        self.sidebar_title = tb.Label(
            self.sidebar,
            text="MARTIN SUITE",
            style="Martin.SidebarTitle.TLabel",
            anchor=W,
            justify=LEFT,
        )
        self.sidebar_title.pack(fill=X, pady=(6, 14), padx=(2, 2))

        self.nav_container = tb.Frame(self.sidebar, style="Martin.Sidebar.TFrame")
        self.nav_container.pack(fill=BOTH, expand=True)

        self.right_container = tb.Frame(self.main_container, style="Martin.Content.TFrame", padding=(10, 10, 10, 10))
        self.right_container.pack(side=RIGHT, fill=BOTH, expand=True)

        self.update_status_frame = tb.Frame(self.right_container, padding=(14, 8), style="Martin.Status.TFrame")
        self.update_status_frame.pack(side=TOP, fill=X, pady=(0, 8))
        self.update_status_label = tb.Label(
            self.update_status_frame,
            textvariable=self.update_coordinator.banner_var,
            style="Martin.Status.TLabel",
            anchor=W,
        )
        self.update_status_label.pack(fill=X)

        self.canvas = tk.Canvas(self.right_container, highlightthickness=0, bd=0)
        self.scrollbar = tb.Scrollbar(self.right_container, orient=VERTICAL, command=self.canvas.yview)
        self.x_scrollbar = tb.Scrollbar(self.right_container, orient=HORIZONTAL, command=self.canvas.xview)
        
        self.content_area = tb.Frame(self.canvas, style="Martin.Content.TFrame")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_area, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.x_scrollbar.set)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.x_scrollbar.pack(side=BOTTOM, fill=X)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)

        self.content_area.bind("<Configure>", self.sync_content_canvas_layout)
        self.canvas.bind("<Configure>", self.sync_content_canvas_layout)
        self._apply_shell_theme()

    def _load_modules_list(self):
        self.nav_buttons = {}
        for display_name, module_name in self.get_navigation_modules():
            button = tb.Button(
                self.nav_container,
                text=display_name,
                style="Martin.Nav.TButton",
                command=lambda m=module_name: self.secure_load(m),
            )
            button.pack(fill=X, pady=3)
            self.nav_buttons[module_name] = button
        self._set_active_navigation_button(self.active_module_name)

    def _apply_shell_theme(self):
        tokens = get_theme_tokens(root=self.root)
        self.main_container.configure(style="Martin.App.TFrame")
        self.sidebar.configure(style="Martin.Sidebar.TFrame")
        self.sidebar_title.configure(style="Martin.SidebarTitle.TLabel")
        self.nav_container.configure(style="Martin.Sidebar.TFrame")
        self.right_container.configure(style="Martin.Content.TFrame")
        self.update_status_frame.configure(style="Martin.Status.TFrame")
        self.update_status_label.configure(style="Martin.Status.TLabel")
        self.content_area.configure(style="Martin.Content.TFrame")
        self.canvas.configure(background=tokens["canvas_bg"])
        self.root.configure(bg=tokens["app_bg"])
        self._set_active_navigation_button(self.active_module_name)

    def _set_active_navigation_button(self, module_name):
        for button_module_name, button in self.nav_buttons.items():
            button.configure(style="Martin.NavActive.TButton" if button_module_name == module_name else "Martin.Nav.TButton")

    def _animate_module_frame(self, module_frame):
        if (
            module_frame is None
            or not module_frame.winfo_exists()
            or not self.transitions_enabled
            or self.transition_duration_ms <= 0
            or self._transition_in_progress
        ):
            return

        self._transition_in_progress = True
        steps = 8
        step_delay = max(0.008, self.transition_duration_ms / 1000 / steps)

        try:
            self.root.update_idletasks()
            viewport_width = max(self.canvas.winfo_width(), 1)
            viewport_height = max(self.canvas.winfo_height(), 1)
            start_x = min(self.transition_slide_distance_px, max(18, viewport_width // 22))
            start_y = 8

            module_frame.pack_forget()
            module_frame.place(in_=self.content_area, x=start_x, y=start_y, width=viewport_width, height=viewport_height)

            for step in range(steps):
                progress = (step + 1) / steps
                eased = 1 - pow(1 - progress, 3)
                offset_x = round(start_x * (1 - eased))
                offset_y = round(start_y * (1 - eased))
                module_frame.place_configure(x=offset_x, y=offset_y)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(step_delay)
        finally:
            if module_frame.winfo_exists():
                module_frame.place_forget()
                module_frame.pack(fill=BOTH, expand=True)
            self._transition_in_progress = False

    def secure_load(self, module_name):
        try:
            from modules.security import gatekeeper
            if not gatekeeper.require_module_access(module_name, parent=self.root):
                return
        except Exception as exc:
            log_exception(f"secure_load.error.{module_name}", exc)
            messagebox.showerror("Security Error", f"Auth failed: {exc}")
            return

        self.load_module(module_name)
        
    def get_navigation_modules(self):
        if not os.path.exists(self.modules_path):
            return []

        hidden_modules = {"about", "security", "app_logging", "data_handler", "downtime_codes", "help_viewer", "persistence", "splash", "theme_manager", "utils"}
        nav_modules = []

        for filename in os.listdir(self.modules_path):
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            module_name = filename[:-3]
            if module_name in hidden_modules:
                continue
            nav_modules.append((module_name.replace("_", " ").title(), module_name))

        return sorted(nav_modules, key=lambda item: item[0].lower())

    def get_persistable_modules(self):
        return [(display_name, module_name) for display_name, module_name in self.get_navigation_modules() if module_name != "update_manager"]

    def normalize_persistent_modules(self, raw_value):
        if isinstance(raw_value, str):
            candidates = [part.strip() for part in raw_value.split(",")]
        elif isinstance(raw_value, (list, tuple, set)):
            candidates = [str(part).strip() for part in raw_value]
        else:
            candidates = []

        valid_modules = {module_name for _display_name, module_name in self.get_persistable_modules()}
        normalized = []
        for module_name in candidates:
            if module_name and module_name in valid_modules and module_name not in normalized:
                normalized.append(module_name)
        return normalized

    def is_module_persistent(self, module_name):
        if not module_name:
            return False
        if module_name == "update_manager":
            return True
        return module_name in self.runtime_settings.get("persistent_modules", [])

    def prune_persistent_module_instances(self):
        allowed_modules = set(self.runtime_settings.get("persistent_modules", [])) | {"update_manager"}
        for module_name in list(self.persistent_module_instances):
            if module_name in allowed_modules or module_name == self.active_module_name:
                continue
            session = self.persistent_module_instances.pop(module_name, None)
            if not session:
                continue
            instance = session.get("instance")
            frame = session.get("frame")
            if hasattr(instance, "on_unload"):
                try:
                    instance.on_unload()
                except Exception as exc:
                    log_exception(f"persistent_module_unload.{module_name}", exc)
            if frame is not None and frame.winfo_exists():
                frame.destroy()

    def _supports_window_alpha(self):
        try:
            current_alpha = float(self.root.attributes("-alpha"))
            self.root.attributes("-alpha", current_alpha)
            return True
        except Exception:
            return False

    def _set_window_alpha(self, alpha_value):
        if not self.window_alpha_supported:
            return
        try:
            self.root.attributes("-alpha", alpha_value)
        except Exception as exc:
            self.window_alpha_supported = False
            log_exception("set_window_alpha", exc)

    def _run_window_transition(self, action):
        if (
            not self.window_alpha_supported
            or not self.transitions_enabled
            or self.transition_duration_ms <= 0
            or self._transition_in_progress
        ):
            return action()

        self._transition_in_progress = True
        steps = 6
        half_duration = max(0.12, self.transition_duration_ms / 2000)
        step_delay = half_duration / steps
        alpha_values = [1.0 - ((1.0 - self.transition_min_alpha) * (index + 1) / steps) for index in range(steps)]

        try:
            for alpha_value in alpha_values:
                self._set_window_alpha(alpha_value)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(step_delay)

            result = action()

            for alpha_value in reversed(alpha_values[:-1]):
                self._set_window_alpha(alpha_value)
                self.root.update_idletasks()
                self.root.update()
                time.sleep(step_delay)

            self._set_window_alpha(1.0)
            self.root.update_idletasks()
            return result
        finally:
            self._set_window_alpha(1.0)
            self._transition_in_progress = False

    def load_module(self, module_name, use_transition=True):
        def perform_load():
            previous_module_name = self.active_module_name
            previous_module_instance = self.active_module_instance
            previous_module_frame = self.active_module_frame

            if previous_module_instance is not None:
                if self.is_module_persistent(previous_module_name):
                    if hasattr(previous_module_instance, 'on_hide'):
                        previous_module_instance.on_hide()
                    if previous_module_frame is not None and previous_module_frame.winfo_exists():
                        previous_module_frame.pack_forget()
                else:
                    if hasattr(previous_module_instance, 'on_unload'):
                        previous_module_instance.on_unload()
                    if previous_module_frame is not None and previous_module_frame.winfo_exists():
                        previous_module_frame.destroy()
                    self.persistent_module_instances.pop(previous_module_name, None)

            self.active_module_name = None
            self.active_module_instance = None
            self.active_module_frame = None
            
            self.canvas.yview_moveto(0)

            if self.is_module_persistent(module_name) and module_name in self.persistent_module_instances:
                session = self.persistent_module_instances[module_name]
                cached_frame = session.get("frame")
                if cached_frame is not None and cached_frame.winfo_exists():
                    self.active_module_name = module_name
                    self.active_module_instance = session.get("instance")
                    self.active_module_frame = cached_frame
                    cached_frame.pack(fill=BOTH, expand=True)
                    self.content_area.update_idletasks()
                    if use_transition and previous_module_name is not None:
                        self._animate_module_frame(cached_frame)
                    self._set_active_navigation_button(module_name)
                    return
                self.persistent_module_instances.pop(module_name, None)

            module_frame = tb.Frame(self.content_area, style="Martin.Surface.TFrame")
            module_frame.pack(fill=BOTH, expand=True)

            module = self.import_managed_module(module_name, force_fresh=True)

            if hasattr(module, 'get_ui'):
                self.active_module_name = module_name
                self.active_module_instance = module.get_ui(module_frame, self)
                self.active_module_frame = module_frame
                if self.is_module_persistent(module_name):
                    self.persistent_module_instances[module_name] = {
                        "instance": self.active_module_instance,
                        "frame": module_frame,
                    }
                self.content_area.update_idletasks()
                if use_transition and previous_module_name is not None:
                    self._animate_module_frame(module_frame)
                self._set_active_navigation_button(module_name)

        try:
            perform_load()
        except Exception as e:
            log_exception(f"load_module.{module_name}", e)
            tb.Label(self.content_area, text=f"Error loading {module_name}: {e}", bootstyle=DANGER).pack(pady=20)

    def open_help_document(self, relative_path):
        try:
            candidate = local_or_resource_path(relative_path)
            if os.path.exists(candidate):
                os.startfile(candidate)
                return

            raise FileNotFoundError(relative_path)
        except Exception as e:
            messagebox.showerror("Help Document Error", f"Could not open help document: {e}")

    def load_runtime_settings(self):
        settings = {
            "theme": DEFAULT_THEME,
            "enable_screen_transitions": True,
            "screen_transition_duration_ms": 360,
            "toast_duration_sec": 5,
            "enable_module_update_notifications": True,
            "update_repository_url": DEFAULT_UPDATE_REPOSITORY_URL,
            "module_update_notifications_legacy_checked": False,
            "persistent_modules": [],
        }
        loaded = None
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass

        try:
            settings["toast_duration_sec"] = max(1, int(settings.get("toast_duration_sec", 5)))
        except Exception:
            settings["toast_duration_sec"] = 5
        settings["enable_screen_transitions"] = bool(settings.get("enable_screen_transitions", True))
        settings["enable_module_update_notifications"] = bool(settings.get("enable_module_update_notifications", True))
        settings["update_repository_url"] = str(settings.get("update_repository_url", DEFAULT_UPDATE_REPOSITORY_URL) or "").strip()
        try:
            settings["screen_transition_duration_ms"] = max(0, min(500, int(settings.get("screen_transition_duration_ms", 360))))
        except Exception:
            settings["screen_transition_duration_ms"] = 360
        settings["theme"] = normalize_theme(settings.get("theme", DEFAULT_THEME))
        settings["persistent_modules"] = self.normalize_persistent_modules(settings.get("persistent_modules", []))
        settings["module_update_notifications_legacy_checked"] = bool(settings.get("module_update_notifications_legacy_checked", False))
        settings["_module_update_notifications_explicit"] = isinstance(loaded, dict) and "enable_module_update_notifications" in loaded
        return settings

    def refresh_runtime_settings(self):
        self.runtime_settings = self.load_runtime_settings()
        self._configure_module_import_paths()
        self.refresh_animation_settings()
        self.prune_persistent_module_instances()
        for listener in list(self.runtime_settings_listeners):
            try:
                listener(self.runtime_settings)
            except Exception as exc:
                log_exception("dispatcher.refresh_runtime_settings.listener", exc)
        return self.runtime_settings

    def register_runtime_settings_listener(self, listener):
        if listener not in self.runtime_settings_listeners:
            self.runtime_settings_listeners.append(listener)

    def unregister_runtime_settings_listener(self, listener):
        if listener in self.runtime_settings_listeners:
            self.runtime_settings_listeners.remove(listener)

    def refresh_animation_settings(self):
        self.transitions_enabled = bool(self.runtime_settings.get("enable_screen_transitions", True))
        try:
            duration = int(self.runtime_settings.get("screen_transition_duration_ms", 360))
        except Exception:
            duration = 360
        self.transition_duration_ms = max(0, min(duration, 500))

    def get_setting(self, key, default=None):
        return self.runtime_settings.get(key, default)

    def _has_explicit_module_update_notification_setting(self):
        return bool(self.runtime_settings.get("_module_update_notifications_explicit", False))

    def _has_completed_legacy_module_update_check(self):
        return bool(self.runtime_settings.get("module_update_notifications_legacy_checked", False))

    def _mark_legacy_module_update_check_complete(self):
        if self._has_explicit_module_update_notification_setting() or self._has_completed_legacy_module_update_check():
            return

        settings_payload = {}
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    settings_payload = loaded
            except Exception:
                settings_payload = {}

        settings_payload["module_update_notifications_legacy_checked"] = True

        try:
            write_json_with_backup(
                self.settings_path,
                settings_payload,
                backup_dir=external_path("data/backups/settings"),
                keep_count=12,
            )
        except Exception as exc:
            log_exception("dispatcher.mark_legacy_module_update_check_complete", exc)
            return

        self.runtime_settings["module_update_notifications_legacy_checked"] = True

    def check_for_available_module_updates(self, force=False):
        if self.module_update_check_in_progress:
            return
        if not force:
            if self._has_explicit_module_update_notification_setting():
                if not bool(self.get_setting("enable_module_update_notifications", True)):
                    return
            elif self._has_completed_legacy_module_update_check():
                return

        if not force and not self._has_explicit_module_update_notification_setting():
            self._mark_legacy_module_update_check_complete()

        self.module_update_check_in_progress = True

        def worker():
            try:
                update_manager_module = self.loaded_modules.get("update_manager") or sys.modules.get("modules.update_manager")
                if update_manager_module is None:
                    update_manager_module = importlib.import_module("modules.update_manager")
                scan_result = update_manager_module.scan_available_module_payload_updates(self)
            except Exception as exc:
                self.root.after(0, lambda error=exc: self._finish_module_update_check(error=error))
                return

            self.root.after(0, lambda result=scan_result: self._finish_module_update_check(result=result))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_module_update_check(self, result=None, error=None):
        self.module_update_check_in_progress = False
        if error is not None:
            log_exception("dispatcher.check_for_available_module_updates", error)
            return
        if not result:
            return

        available_results = result.get("available_results", [])
        if not available_results:
            return

        signature = tuple(sorted(item["option"].get("relative_path", "") for item in available_results))
        if signature == self.last_module_update_notification_signature:
            return
        self.last_module_update_notification_signature = signature

        available_names = []
        for item in available_results:
            label = item.get("module_name") or item["option"].get("module_name") or item["option"].get("fallback_name")
            if label and label not in available_names:
                available_names.append(label)

        preview = ", ".join(available_names[:3])
        if len(available_names) > 3:
            preview = f"{preview}, and {len(available_names) - 3} more"

        if len(available_results) == 1:
            message = f"A module payload update is available for {preview}. Open Update Manager to review or install it."
        else:
            message = f"{len(available_results)} module payload updates are available: {preview}. Open Update Manager to review or install them all."

        self.show_toast("Update Manager", message, INFO)

    def get_mousewheel_units(self, event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        if getattr(event, "delta", 0):
            return int(-1 * (event.delta / 120))
        return 0

    def bind_mousewheel_to_widget_tree(self, root_widget, scroll_target, axis="y"):
        def on_mousewheel(event):
            step = self.get_mousewheel_units(event)
            if not step:
                return None
            if axis == "x":
                scroll_target.xview_scroll(step, "units")
            else:
                scroll_target.yview_scroll(step, "units")
            return "break"

        def bind_widget(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", on_mousewheel)
            widget.bind("<Button-5>", on_mousewheel)
            for child in widget.winfo_children():
                bind_widget(child)

        bind_widget(root_widget)

    def show_toast(self, title, message, bootstyle=INFO, duration_ms=None):
        duration = duration_ms
        if duration is None:
            duration = int(self.get_setting("toast_duration_sec", 5)) * 1000
        right_inset, bottom_inset = get_work_area_insets(self.root)
        toast = ToastNotification(
            title=title,
            message=message,
            duration=duration,
            bootstyle=bootstyle,
            position=(24 + right_inset, 24 + bottom_inset, "se"),
        )
        toast.show_toast()

    def refresh_update_status_visibility(self):
        if self.update_coordinator.active:
            if not self.update_status_frame.winfo_manager():
                self.update_status_frame.pack(side=TOP, fill=X, pady=(0, 8), before=self.canvas)
            self.update_status_frame.configure(bootstyle=INFO)
            self.update_status_label.configure(bootstyle=self.update_coordinator.banner_bootstyle)
            return

        if self.update_status_frame.winfo_manager():
            self.update_status_frame.pack_forget()

    def _cancel_update_status_autohide(self):
        if self._update_status_hide_after_id is not None:
            try:
                self.root.after_cancel(self._update_status_hide_after_id)
            except Exception:
                pass
            self._update_status_hide_after_id = None

    def _schedule_update_status_autohide(self, expected_message, delay_ms=4200):
        self._cancel_update_status_autohide()

        def clear_if_unchanged():
            self._update_status_hide_after_id = None
            if self.update_coordinator.banner_var.get() == expected_message and self.update_coordinator.active:
                self.clear_update_status()

        self._update_status_hide_after_id = self.root.after(delay_ms, clear_if_unchanged)

    def set_update_status(self, message, bootstyle=INFO, active=True, mode=None):
        self._cancel_update_status_autohide()
        self.update_coordinator.set_banner(message, bootstyle=bootstyle, active=active, mode=mode)
        self.refresh_update_status_visibility()
        if active and bootstyle == SUCCESS and mode == "module":
            self._schedule_update_status_autohide(message)

    def clear_update_status(self):
        self._cancel_update_status_autohide()
        self.update_coordinator.clear_banner()
        self.refresh_update_status_visibility()

    def prompt_old_executable_cleanup(self):
        obsolete_executables = get_obsolete_local_executables(os.path.abspath(sys.executable), __version__)
        if not obsolete_executables:
            return

        file_list = "\n".join(f"- {entry['name']}" for entry in obsolete_executables)
        if not messagebox.askyesno(
            "Remove Older Versions",
            (
                "Older local EXE versions were found next to the current build:\n\n"
                f"{file_list}\n\n"
                "Remove them now?"
            ),
        ):
            return

        removed = []
        failed = []
        for entry in obsolete_executables:
            try:
                os.remove(entry["path"])
                removed.append(entry["name"])
            except OSError:
                failed.append(entry["name"])

        if removed:
            self.show_toast("Cleanup Complete", f"Removed {len(removed)} older EXE file(s).", SUCCESS)
        if failed:
            failure_list = "\n".join(f"- {name}" for name in failed)
            messagebox.showwarning(
                "Cleanup Incomplete",
                f"These EXE files could not be removed:\n\n{failure_list}",
            )

    def apply_theme(self, theme_name, redraw=False):
        normalized_theme = normalize_theme(theme_name)
        style = tb.Style.get_instance() or tb.Style()
        style.theme_use(resolve_base_theme(normalized_theme))
        apply_readability_overrides(self.root, normalized_theme)
        self._apply_shell_theme()
        self.root.update_idletasks()

        return normalized_theme

    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_horizontal_mousewheel)

    def _on_mousewheel(self, event):
        step = self.get_mousewheel_units(event)
        if step:
            self.canvas.yview_scroll(step, "units")

    def _on_horizontal_mousewheel(self, event):
        step = self.get_mousewheel_units(event)
        if step:
            self.canvas.xview_scroll(step, "units")

    def sync_content_canvas_layout(self, _event=None):
        viewport_width = max(self.canvas.winfo_width(), 1)
        requested_width = max(self.content_area.winfo_reqwidth(), 1)
        self.canvas.itemconfigure(self.canvas_window, width=max(viewport_width, requested_width))
        scroll_region = self.canvas.bbox("all")
        if scroll_region is not None:
            self.canvas.configure(scrollregion=scroll_region)

if __name__ == "__main__":
    settings_path = external_path("settings.json")
    theme_name = DEFAULT_THEME
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                theme_name = normalize_theme(json.load(f).get("theme", DEFAULT_THEME))
        except Exception as exc:
            log_exception("main.__main__.load_theme", exc)
    
    apply_windows_app_id()
    app_root = tb.Window(themename=resolve_base_theme(theme_name))
    apply_readability_overrides(app_root, theme_name)
    apply_app_icon(app_root)
    from modules.splash import show_splash_screen
    show_splash_screen(app_root, duration=5000, logo_path=resource_path(SPLASH_LOGO_RELATIVE_PATH))
        
    app = Dispatcher(app_root)
    app_root.mainloop()
