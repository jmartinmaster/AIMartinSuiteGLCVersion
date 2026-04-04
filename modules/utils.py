import os
import sys

__module_name__ = "Path Helpers"
__version__ = "1.1.4"


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