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

# Define your project name
APP_NAME = "TheMartinSuite_GLC"
SPEC_FILE = f"{APP_NAME}.spec"


def clean_previous_builds():
    exe_name = f"{APP_NAME}.exe"
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", exe_name], check=False, capture_output=True)

    def remove_readonly(_func, path, _exc_info):
        os.chmod(path, stat.S_IWRITE)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)

    for folder_name in ("build", "dist"):
        folder_path = os.path.abspath(folder_name)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path, onexc=remove_readonly)


clean_previous_builds()

PyInstaller.__main__.run([
    SPEC_FILE,
    '--noconfirm',
])

print(f"\n--- Build Complete! Check dist/{APP_NAME} ---")