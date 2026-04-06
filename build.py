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

import PyInstaller.__main__
import os
import shutil
import stat
import subprocess
from pathlib import Path

from PIL import Image

from app_identity import APP_NAME, LEGACY_EXE_NAME, format_versioned_exe_name, load_version_from_main, normalize_version, parse_version, parse_versioned_exe_name

SPEC_FILE = f"{APP_NAME}.spec"
EXE_NAME = format_versioned_exe_name(load_version_from_main())
PRESERVE_DIST = os.environ.get("MARTIN_KEEP_DIST", "1") != "0"
SKIP_TASKKILL = os.environ.get("MARTIN_SKIP_TASKKILL", "0") == "1"
MAX_OLD_EXE_ARCHIVE = 10
SENSITIVE_RUNTIME_PATHS = [
    ".vault",
    os.path.join("data", "security"),
    os.path.join("data", "backups", "security"),
]
ICON_SOURCE_CANDIDATE_PATHS = [
    Path("icon.png"),
    Path("icon.jpg"),
]
ICON_RUNTIME_PNG_SIZES = [16, 24, 32, 48, 64]
ICON_ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def get_icon_source_path():
    for path in ICON_SOURCE_CANDIDATE_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("No icon source artwork found. Expected icon.png or icon.jpg in the repo root.")


def sync_icon_assets():
    source_path = get_icon_source_path()
    output_directory = source_path.parent

    with Image.open(source_path) as source_image:
        working_image = source_image.convert("RGBA")

        available_ico_sizes = []
        for size in ICON_RUNTIME_PNG_SIZES:
            output_path = output_directory / f"icon-{size}.png"
            resized_image = working_image.resize((size, size), Image.Resampling.LANCZOS)
            resized_image.save(output_path, format="PNG")
            available_ico_sizes.append((size, size))

        if working_image.width >= 128 and working_image.height >= 128:
            available_ico_sizes.append((128, 128))
        if working_image.width >= 256 and working_image.height >= 256:
            available_ico_sizes.append((256, 256))

        icon_ico_path = output_directory / "icon.ico"
        working_image.save(icon_ico_path, format="ICO", sizes=available_ico_sizes or ICON_ICO_SIZES)


def remove_path(path, remove_readonly):
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        shutil.rmtree(path, onexc=remove_readonly)
        return
    os.chmod(path, stat.S_IWRITE)
    os.remove(path)


def scrub_preserved_runtime_state(base_dir, remove_readonly):
    for relative_path in ["modules", *SENSITIVE_RUNTIME_PATHS]:
        remove_path(os.path.join(base_dir, relative_path), remove_readonly)


def clean_previous_builds():
    if os.name == "nt" and not SKIP_TASKKILL:
        for exe_name in {EXE_NAME, LEGACY_EXE_NAME}:
            subprocess.run(["taskkill", "/F", "/IM", exe_name], check=False, capture_output=True)

    def remove_readonly(_func, path, _exc_info):
        os.chmod(path, stat.S_IWRITE)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)

    folders_to_clean = ["build"]
    if not PRESERVE_DIST:
        folders_to_clean.append("dist")

    for folder_name in folders_to_clean:
        folder_path = os.path.abspath(folder_name)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path, onexc=remove_readonly)

    if PRESERVE_DIST:
        # Keep archived builds and editable JSON artifacts, but remove stale external runtime state
        # so preserved dist output never carries forward local overrides or credentials into a new build.
        scrub_preserved_runtime_state(os.path.abspath("dist"), remove_readonly)


def archive_previous_builds():
    if not PRESERVE_DIST:
        return

    dist_dir = os.path.abspath("dist")
    archive_dir = os.path.join(dist_dir, "Old_exe")
    os.makedirs(archive_dir, exist_ok=True)

    for file_name in os.listdir(dist_dir):
        source_path = os.path.join(dist_dir, file_name)
        if not os.path.isfile(source_path):
            continue
        if file_name == EXE_NAME:
            continue
        if parse_versioned_exe_name(file_name) is None:
            continue

        target_path = os.path.join(archive_dir, file_name)
        if os.path.abspath(source_path) == os.path.abspath(target_path):
            continue
        if os.path.exists(target_path):
            os.remove(target_path)
        shutil.move(source_path, target_path)

    archived_entries = []
    for file_name in os.listdir(archive_dir):
        archive_path = os.path.join(archive_dir, file_name)
        if not os.path.isfile(archive_path):
            continue
        version_text = parse_versioned_exe_name(file_name)
        version_key = normalize_version(parse_version(version_text)) if version_text else None
        if version_key is None:
            continue
        archived_entries.append((version_key, file_name, archive_path))

    archived_entries.sort(key=lambda entry: entry[0], reverse=True)
    for _version_key, _file_name, archive_path in archived_entries[MAX_OLD_EXE_ARCHIVE:]:
        os.remove(archive_path)


clean_previous_builds()
sync_icon_assets()

PyInstaller.__main__.run([
    SPEC_FILE,
    '--noconfirm',
    '--clean',
])

archive_previous_builds()

print(f"\n--- Build Complete! Check dist/{EXE_NAME} ---")