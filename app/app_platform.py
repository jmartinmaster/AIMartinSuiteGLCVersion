import os
import sys
import ctypes
import subprocess
from ctypes import wintypes
from tkinter import PhotoImage

from PIL import Image

from app.app_identity import LEGACY_EXE_NAME, normalize_version, parse_version, parse_versioned_exe_name
from app.app_logging import log_exception
from app.utils import resource_path

WINDOWS_APP_ID = "JamieMartin.TheMartinSuite.GLC"
APP_ICON_RELATIVE_PATH = "assets/icons/icon.ico"
APP_ICON_IMAGE_RELATIVE_PATHS = [
    "assets/icons/icon-16.png",
    "assets/icons/icon-24.png",
    "assets/icons/icon-32.png",
    "assets/icons/icon-48.png",
    "assets/icons/icon-64.png",
]
APP_ICON_SOURCE_RELATIVE_PATHS = [
    "assets/icons/icon.png",
    "assets/icons/icon.jpg",
]
SPLASH_LOGO_RELATIVE_PATH = "assets/images/splash-logo.png"
WM_SETICON = 0x0080
WM_GETICON = 0x007F
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040
GCLP_HICON = -14
GCLP_HICONSM = -34
RUNTIME_PLATFORM_WINDOWS = "windows"
RUNTIME_PLATFORM_UBUNTU = "ubuntu"
RUNTIME_PLATFORM_OTHER = "other"


def get_runtime_platform():
    if sys.platform.startswith("win"):
        return RUNTIME_PLATFORM_WINDOWS
    if sys.platform.startswith("linux"):
        return RUNTIME_PLATFORM_UBUNTU
    return RUNTIME_PLATFORM_OTHER


def is_windows_runtime():
    return get_runtime_platform() == RUNTIME_PLATFORM_WINDOWS


def is_ubuntu_runtime():
    return get_runtime_platform() == RUNTIME_PLATFORM_UBUNTU


def get_platform_update_artifact_kind():
    if is_windows_runtime():
        return "exe"
    if is_ubuntu_runtime():
        return "deb"
    return "release"


def get_platform_update_artifact_label():
    artifact_kind = get_platform_update_artifact_kind()
    if artifact_kind == "exe":
        return "Windows EXE"
    if artifact_kind == "deb":
        return "Ubuntu DEB"
    return "Release Artifact"


def open_with_system_default(target_path):
    if is_windows_runtime():
        os.startfile(target_path)
        return

    opener = "xdg-open" if is_ubuntu_runtime() else "open" if sys.platform == "darwin" else None
    if opener is None:
        raise RuntimeError(f"No system opener is configured for platform {sys.platform}.")

    subprocess.Popen(
        [opener, target_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


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
            images[0].save(output_ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            return True
        log_exception("convert_png_to_ico", "No valid PNG files found to convert.")
        return False
    except Exception as exc:
        log_exception("convert_png_to_ico", exc)
        return False


def apply_app_icon(window, icon_path=APP_ICON_SOURCE_RELATIVE_PATHS[0]):
    try:
        resolved_icon_path = icon_path if os.path.exists(icon_path) else resource_path(icon_path)
        if os.path.exists(resolved_icon_path):
            try:
                icon_image = PhotoImage(file=resolved_icon_path)
                window.iconphoto(False, icon_image)
                window._martin_icon_image = icon_image
            except Exception as exc:
                print(f"Failed to apply icon using iconphoto: {exc}")
        else:
            print(f"Icon file not found: {icon_path}")
    except Exception as exc:
        print(f"Failed to apply icon: {exc}")