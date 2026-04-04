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
import re
import sys
import tempfile
import urllib.error
import urllib.request
from tkinter import messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

__module_name__ = "Update Manager"
__version__ = "1.0.0"

GITHUB_REMOTE_PATTERN = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+?)(?:\.git)?$")
MODULE_NAME_PATTERN = re.compile(r"__module_name__\s*=\s*[\"']([^\"']+)[\"']")
VERSION_PATTERN = re.compile(r"__version__\s*=\s*[\"']([^\"']+)[\"']")
MASTER_VERSION_PATH = "main.py"
REMOTE_EXE_PATH = "dist/TheMartinSuite_GLC.exe"


def _parse_module_metadata(file_text, fallback_name):
    module_name_match = MODULE_NAME_PATTERN.search(file_text)
    version_match = VERSION_PATTERN.search(file_text)
    return {
        "module_name": module_name_match.group(1) if module_name_match else fallback_name,
        "version": version_match.group(1) if version_match else "Unknown",
    }


def _parse_version(version_text):
    if not version_text:
        return None
    parts = [part.strip() for part in str(version_text).split(".") if part.strip()]
    if len(parts) in (2, 3) and all(part.isdigit() for part in parts):
        return tuple(int(part) for part in parts)
    return None


def _normalize_version(version_parts):
    if version_parts is None:
        return None
    return version_parts + (0,) * (3 - len(version_parts))


def _is_supported_update_version(version_parts):
    if version_parts is None:
        return False
    if len(version_parts) == 2:
        return True
    return len(version_parts) == 3 and version_parts[2] % 2 == 0


class UpdateManager:
    def __init__(self, parent, dispatcher):
        self.parent = parent
        self.dispatcher = dispatcher
        self.branch_name = self._detect_branch_name()
        self.remote_info = self._detect_remote_info()
        self.local_manifest = []
        self.comparison_rows = []
        self.status_var = tb.StringVar(value="Ready to check for updates.")
        self.branch_var = tb.StringVar(value=self.branch_name or "Unknown")
        self.repo_var = tb.StringVar(value=self.remote_info.get("display", "Unknown repository"))
        self.target_name_var = tb.StringVar(value="Dispatcher Core")
        self.local_version_var = tb.StringVar(value="Unknown")
        self.remote_version_var = tb.StringVar(value="Not checked")
        self.result_var = tb.StringVar(value="Pending")
        self.note_var = tb.StringVar(value="Run a repository check to compare the packaged release target.")
        self.setup_ui()
        self.refresh_local_manifest()
        self.refresh_summary()

    def _detect_branch_name(self):
        return "main"

    def _detect_remote_info(self):
        remote_url = None
        git_config_path = os.path.join(os.path.abspath("."), ".git", "config")
        if os.path.exists(git_config_path):
            try:
                with open(git_config_path, "r", encoding="utf-8") as handle:
                    config_text = handle.read()
                match = re.search(r"url\s*=\s*(.+)", config_text)
                if match:
                    remote_url = match.group(1).strip()
            except Exception:
                remote_url = None
        remote_url = remote_url or "https://github.com/jmartinmaster/AIMartinSuiteGLCVersion.git"
        match = GITHUB_REMOTE_PATTERN.search(remote_url)
        if not match:
            return {"owner": None, "repo": None, "url": remote_url, "display": remote_url}
        owner = match.group("owner")
        repo = match.group("repo")
        return {
            "owner": owner,
            "repo": repo,
            "url": remote_url,
            "display": f"{owner}/{repo}",
        }

    def refresh_local_manifest(self):
        dispatcher_module = self.dispatcher.loaded_modules.get("main") or sys.modules.get("main") or sys.modules.get("__main__")
        self.local_manifest = [{
            "relative_path": MASTER_VERSION_PATH,
            "module_name": getattr(dispatcher_module, "__module_name__", "Dispatcher Core"),
            "local_version": getattr(dispatcher_module, "__version__", "Unknown"),
        }]

    def refresh_summary(self):
        entry = self.local_manifest[0] if self.local_manifest else {
            "module_name": "Dispatcher Core",
            "local_version": "Unknown",
        }
        row = self.comparison_rows[0] if self.comparison_rows else None
        self.target_name_var.set(entry["module_name"])
        self.local_version_var.set(entry.get("local_version", "Unknown"))
        self.remote_version_var.set(row.get("remote_version", "Not checked") if row else "Not checked")
        self.result_var.set(row.get("status", "Pending") if row else "Pending")
        if row and row.get("update_available"):
            self.note_var.set("A newer stable executable target is available from the repository branch.")
        elif row:
            self.note_var.set("No newer stable executable target is available right now.")
        else:
            self.note_var.set("Run a repository check to compare the packaged release target.")

    def _fetch_remote_file(self, relative_path):
        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            raise RuntimeError("Repository origin or branch could not be determined.")

        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{self.branch_name}/{relative_path}"
        request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")

    def _fetch_remote_bytes(self, relative_path):
        owner = self.remote_info.get("owner")
        repo = self.remote_info.get("repo")
        if not owner or not repo or not self.branch_name:
            raise RuntimeError("Repository origin or branch could not be determined.")

        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{self.branch_name}/{relative_path}"
        request = urllib.request.Request(url, headers={"User-Agent": "MartinSuiteUpdater/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()

    def check_for_updates(self):
        self.refresh_local_manifest()
        comparison_rows = []

        for entry in self.local_manifest:
            try:
                remote_text = self._fetch_remote_file(entry["relative_path"])
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    comparison_rows.append({
                        **entry,
                        "remote_version": "Missing",
                        "status": "Not in repository branch",
                        "update_available": False,
                    })
                    continue
                raise

            remote_metadata = _parse_module_metadata(remote_text, entry["module_name"])
            remote_version = remote_metadata["version"]
            remote_compare = _parse_version(remote_version)
            local_compare = _parse_version(entry["local_version"])

            if remote_compare is None:
                status = "Remote version unreadable"
                update_available = False
            elif len(remote_compare) == 3 and remote_compare[2] % 2 != 0:
                status = "Remote odd patch ignored"
                update_available = False
            elif not _is_supported_update_version(remote_compare):
                status = "Remote version ignored"
                update_available = False
            elif local_compare is None:
                status = "Local version unreadable"
                update_available = False
            elif _normalize_version(remote_compare) > _normalize_version(local_compare):
                status = "EXE update available"
                update_available = True
            else:
                status = "Up to date"
                update_available = False

            comparison_rows.append({
                **entry,
                "module_name": remote_metadata["module_name"],
                "remote_version": remote_version,
                "status": status,
                "update_available": update_available,
            })

        self.comparison_rows = comparison_rows
        self.refresh_summary()
        available_count = sum(1 for row in comparison_rows if row["update_available"])
        self.status_var.set(f"Checked Dispatcher Core on branch '{self.branch_name}'. {available_count} executable update(s) available.")

    def _start_detached_exe_swap(self, downloaded_exe_path):
        current_exe_path = os.path.abspath(sys.executable)
        replacement_exe_path = f"{current_exe_path}.new"
        backup_exe_path = f"{current_exe_path}.bak"
        current_pid = os.getpid()
        batch_path = os.path.join(tempfile.gettempdir(), "martin_suite_update_swap.bat")
        with open(batch_path, "w", encoding="utf-8") as handle:
            handle.write(
                "@echo off\n"
                "setlocal EnableExtensions\n"
                f'set "TARGET={current_exe_path}"\n'
                f'set "DOWNLOAD={downloaded_exe_path}"\n'
                f'set "REPLACEMENT={replacement_exe_path}"\n'
                f'set "BACKUP={backup_exe_path}"\n'
                f'set "TARGET_PID={current_pid}"\n'
                "set /a ATTEMPTS=0\n"
                ":wait_for_exit\n"
                'tasklist /FI "PID eq %TARGET_PID%" | find "%TARGET_PID%" > nul\n'
                "if errorlevel 1 goto replace_exe\n"
                "timeout /t 1 /nobreak > nul\n"
                "goto wait_for_exit\n"
                ":replace_exe\n"
                "set /a ATTEMPTS+=1\n"
                "if %ATTEMPTS% GTR 20 goto failed\n"
                'if exist "%REPLACEMENT%" del /Q "%REPLACEMENT%"\n'
                'if exist "%BACKUP%" del /Q "%BACKUP%"\n'
                'copy /Y "%DOWNLOAD%" "%REPLACEMENT%" > nul\n'
                "if errorlevel 1 goto retry\n"
                'move /Y "%TARGET%" "%BACKUP%" > nul\n'
                "if errorlevel 1 goto retry\n"
                'move /Y "%REPLACEMENT%" "%TARGET%" > nul\n'
                "if errorlevel 1 goto restore_backup\n"
                'start "" "%TARGET%"\n'
                'del /Q "%DOWNLOAD%" "%BACKUP%"\n'
                'del "%~f0"\n'
                "exit /b 0\n"
                ":restore_backup\n"
                'if exist "%BACKUP%" move /Y "%BACKUP%" "%TARGET%" > nul\n'
                ":retry\n"
                "timeout /t 1 /nobreak > nul\n"
                "goto replace_exe\n"
                ":failed\n"
                'if exist "%BACKUP%" move /Y "%BACKUP%" "%TARGET%" > nul\n'
                'if exist "%REPLACEMENT%" del /Q "%REPLACEMENT%"\n'
                'del "%~f0"\n'
            )
        os.startfile(batch_path)

    def _apply_frozen_executable_update(self):
        try:
            remote_exe_bytes = self._fetch_remote_bytes(REMOTE_EXE_PATH)
        except Exception as exc:
            Messagebox.show_error(f"Could not download the updated executable:\n\n{exc}", "Update Error")
            return

        temp_exe_path = os.path.join(tempfile.gettempdir(), "TheMartinSuite_GLC.update.exe")
        try:
            with open(temp_exe_path, "wb") as handle:
                handle.write(remote_exe_bytes)
        except Exception as exc:
            Messagebox.show_error(f"Could not write the downloaded executable:\n\n{exc}", "Update Error")
            return

        if not messagebox.askyesno(
            "Apply Update",
            "Executable update found. The application will close, replace its executable, and restart. Continue?",
        ):
            return
        self._start_detached_exe_swap(temp_exe_path)
        self.dispatcher.root.after(200, self.dispatcher.root.destroy)

    def apply_updates(self):
        if not self.comparison_rows:
            self.check_for_updates()

        update_rows = [row for row in self.comparison_rows if row.get("update_available")]
        if not update_rows:
            self.dispatcher.show_toast("Update Manager", "No executable updates are available from Dispatcher Core.", INFO)
            return

        if getattr(sys, "frozen", False):
            self._apply_frozen_executable_update()
            return

        self.dispatcher.show_toast(
            "Source Mode",
            "Executable updates are only applied from the packaged application. Build a new EXE manually when working from source.",
            WARNING,
        )

    def setup_ui(self):
        container = tb.Frame(self.parent, padding=20)
        container.pack(fill=BOTH, expand=True)

        tb.Label(container, text="Update Manager", font=("Helvetica", 18, "bold")).pack(anchor=W, pady=(0, 10))
        tb.Label(
            container,
            text=(
                "Compare the local Dispatcher Core version with the repository branch release target. "
                "Odd third patch numbers stay in-progress and are ignored by the updater."
            ),
            wraplength=760,
            justify=LEFT,
        ).pack(anchor=W, pady=(0, 12))

        summary = tb.Labelframe(container, text=" Release Target ", padding=14)
        summary.pack(fill=X, pady=(0, 12))
        tb.Label(summary, textvariable=self.target_name_var, font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 8))
        tb.Label(summary, text="Repository", bootstyle=SECONDARY).grid(row=1, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.repo_var).grid(row=1, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Branch", bootstyle=SECONDARY).grid(row=2, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.branch_var).grid(row=2, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Local Version", bootstyle=SECONDARY).grid(row=3, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.local_version_var).grid(row=3, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Repository Version", bootstyle=SECONDARY).grid(row=4, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.remote_version_var).grid(row=4, column=1, sticky=W, pady=2)
        tb.Label(summary, text="Status", bootstyle=SECONDARY).grid(row=5, column=0, sticky=W, padx=(0, 12), pady=2)
        tb.Label(summary, textvariable=self.result_var).grid(row=5, column=1, sticky=W, pady=2)
        tb.Label(summary, textvariable=self.note_var, bootstyle=INFO, wraplength=720, justify=LEFT).grid(row=6, column=0, columnspan=2, sticky=W, pady=(10, 0))

        controls = tb.Frame(container)
        controls.pack(fill=X, pady=(12, 0))
        tb.Button(controls, text="Check Repository", bootstyle=PRIMARY, command=self.check_for_updates).pack(side=LEFT)
        tb.Button(controls, text="Apply Stable Updates", bootstyle=SUCCESS, command=self.apply_updates).pack(side=LEFT, padx=8)

        tb.Label(container, textvariable=self.status_var, bootstyle=SECONDARY).pack(anchor=W, pady=(12, 0))


def get_ui(parent, dispatcher):
    return UpdateManager(parent, dispatcher)