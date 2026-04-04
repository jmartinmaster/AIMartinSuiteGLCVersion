import os
import re


APP_NAME = "TheMartinSuite_GLC"
LEGACY_EXE_NAME = f"{APP_NAME}.exe"
MAIN_FILE_NAME = "main.py"
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
VERSIONED_EXE_PATTERN = re.compile(
    rf"^{re.escape(APP_NAME)}_v(?P<version>\d+\.\d+(?:\.\d+)?)\.exe$",
    re.IGNORECASE,
)


def parse_version(version_text):
    if not version_text:
        return None
    parts = [part.strip() for part in str(version_text).split(".") if part.strip()]
    if len(parts) in (2, 3) and all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return None


def normalize_version(version_parts):
    if version_parts is None:
        return None
    return version_parts + (0,) * (3 - len(version_parts))


def sanitize_version_for_filename(version_text):
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "-", str(version_text).strip())
    return cleaned.strip("-._") or "0.0.0"


def format_versioned_exe_stem(version_text):
    return f"{APP_NAME}_v{sanitize_version_for_filename(version_text)}"


def format_versioned_exe_name(version_text):
    return f"{format_versioned_exe_stem(version_text)}.exe"


def parse_versioned_exe_name(file_name):
    match = VERSIONED_EXE_PATTERN.match(file_name)
    if not match:
        return None
    return match.group("version")


def load_version_from_main(main_file_path=None, default="0.0.0"):
    file_path = main_file_path or os.path.join(os.path.dirname(__file__), MAIN_FILE_NAME)
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            file_text = handle.read()
    except OSError:
        return default

    match = VERSION_PATTERN.search(file_text)
    if not match:
        return default
    return match.group(1)