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

from app_identity import APP_NAME, LEGACY_EXE_NAME, format_versioned_exe_name, load_version_from_main

SPEC_FILE = f"{APP_NAME}.spec"
EXE_NAME = format_versioned_exe_name(load_version_from_main())
PRESERVE_DIST = os.environ.get("MARTIN_KEEP_DIST", "1") != "0"


def clean_previous_builds():
    if os.name == "nt":
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


clean_previous_builds()

PyInstaller.__main__.run([
    SPEC_FILE,
    '--noconfirm',
])

print(f"\n--- Build Complete! Check dist/{EXE_NAME} ---")