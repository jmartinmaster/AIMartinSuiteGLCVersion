import os
import sys

__module_name__ = "Path Helpers"
__version__ = "1.1.5"


def bundled_base_path():
    try:
        return sys._MEIPASS
    except Exception:
        return os.path.abspath(".")


def external_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def resource_path(relative_path):
    return os.path.join(bundled_base_path(), relative_path)


def external_path(relative_path):
    return os.path.join(external_base_path(), relative_path)


def local_or_resource_path(relative_path):
    local_path = external_path(relative_path)
    if os.path.exists(local_path):
        return local_path
    return resource_path(relative_path)


def ensure_external_directory(relative_path):
    directory_path = external_path(relative_path)
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def resolve_local_venv_python(base_path=None):
    root_path = os.path.abspath(base_path or external_base_path())
    candidate = os.path.join(root_path, ".venv", "Scripts", "python.exe")
    return candidate if os.path.exists(candidate) else None