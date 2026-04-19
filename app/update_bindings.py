# Production Logging Center (GLC Edition)
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
import ttkbootstrap as tb


class ObservableValue:
    _trace_sequence = 0

    def __init__(self, value=""):
        self._value = value
        self._traces = {}

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for trace_mode, callback in list(self._traces.values()):
            try:
                callback("observable", "", trace_mode)
            except TypeError:
                callback()

    def trace_add(self, mode, callback):
        ObservableValue._trace_sequence += 1
        callback_name = f"observable_trace_{ObservableValue._trace_sequence}"
        self._traces[callback_name] = (mode, callback)
        return callback_name

    def trace_remove(self, mode, callback_name):
        stored = self._traces.get(callback_name)
        if stored is None:
            return
        stored_mode, _callback = stored
        if stored_mode == mode:
            self._traces.pop(callback_name, None)


def _create_binding(master, value=""):
    if hasattr(master, "tk"):
        return tb.StringVar(master=master, value=value)
    return ObservableValue(value=value)


class UpdateStateBindings:
    def __init__(self, root):
        self.banner_var = _create_binding(root, value="Updates idle.")
        self.status_var = _create_binding(root, value="Ready to check for updates.")
        self.branch_var = _create_binding(root, value="main")
        self.repo_var = _create_binding(root, value="Unknown repository")
        self.target_name_var = _create_binding(root, value="Dispatcher Core")
        self.local_version_var = _create_binding(root, value="Unknown")
        self.remote_version_var = _create_binding(root, value="Not checked")
        self.result_var = _create_binding(root, value="Pending")
        self.note_var = _create_binding(root, value="Run a repository check to compare the packaged release target.")
        self.advanced_status_var = _create_binding(root, value="Advanced dev updates are Windows-only on packaged builds; Ubuntu uses the stable package update path.")
        self.job_phase_var = _create_binding(root, value="Idle")
        self.job_detail_var = _create_binding(root, value="No update job is running.")
        self.build_runtime_var = _create_binding(root, value="Build runtime not resolved yet.")

    def sync_from_model(self, model):
        self.banner_var.set(model.banner_text)
        self.status_var.set(model.status_text)
        self.branch_var.set(model.branch_name)
        self.repo_var.set(model.repo_text)
        self.target_name_var.set(model.target_name_text)
        self.local_version_var.set(model.local_version_text)
        self.remote_version_var.set(model.remote_version_text)
        self.result_var.set(model.result_text)
        self.note_var.set(model.note_text)
        self.advanced_status_var.set(model.advanced_status_text)
        self.job_phase_var.set(model.phase_label())
        self.job_detail_var.set(model.job_detail)
        self.build_runtime_var.set(model.build_runtime_text)
