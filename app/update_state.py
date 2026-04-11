import json
import os

from ttkbootstrap.constants import INFO, SECONDARY, WARNING

from app.app_logging import log_exception
from app.persistence import write_json_with_backup
from app.utils import external_path
from app.update_bindings import UpdateStateBindings
from app.models.update_model import INTERRUPTED_SOURCE_PHASES, RECOVERABLE_SOURCE_PHASES, SOURCE_JOB_BACKUP_RELATIVE_PATH, SOURCE_JOB_STATE_RELATIVE_PATH, SOURCE_UPDATE_PHASES, UpdateStateModel


class UpdateCoordinator:
    def __init__(self, root):
        self.root = root
        self.model = UpdateStateModel()
        self.bindings = UpdateStateBindings(root)
        self.source_state_path = external_path(SOURCE_JOB_STATE_RELATIVE_PATH)
        self._loading_state = False
        self._bind_variable_traces()
        self._sync_bindings()
        self._load_source_job_state()

    @property
    def banner_var(self):
        return self.bindings.banner_var

    @property
    def status_var(self):
        return self.bindings.status_var

    @property
    def branch_var(self):
        return self.bindings.branch_var

    @property
    def repo_var(self):
        return self.bindings.repo_var

    @property
    def target_name_var(self):
        return self.bindings.target_name_var

    @property
    def local_version_var(self):
        return self.bindings.local_version_var

    @property
    def remote_version_var(self):
        return self.bindings.remote_version_var

    @property
    def result_var(self):
        return self.bindings.result_var

    @property
    def note_var(self):
        return self.bindings.note_var

    @property
    def advanced_status_var(self):
        return self.bindings.advanced_status_var

    @property
    def job_phase_var(self):
        return self.bindings.job_phase_var

    @property
    def job_detail_var(self):
        return self.bindings.job_detail_var

    @property
    def build_runtime_var(self):
        return self.bindings.build_runtime_var

    def _bind_variable_traces(self):
        self.bindings.banner_var.trace_add("write", lambda *_args: self._sync_model_text("banner_text", self.bindings.banner_var.get()))
        self.bindings.status_var.trace_add("write", lambda *_args: self._sync_model_text("status_text", self.bindings.status_var.get()))
        self.bindings.branch_var.trace_add("write", lambda *_args: self._sync_model_text("branch_name", self.bindings.branch_var.get() or "main"))
        self.bindings.repo_var.trace_add("write", lambda *_args: self._sync_repo_display(self.bindings.repo_var.get()))
        self.bindings.target_name_var.trace_add("write", lambda *_args: self._sync_model_text("target_name_text", self.bindings.target_name_var.get()))
        self.bindings.local_version_var.trace_add("write", lambda *_args: self._sync_model_text("local_version_text", self.bindings.local_version_var.get()))
        self.bindings.remote_version_var.trace_add("write", lambda *_args: self._sync_model_text("remote_version_text", self.bindings.remote_version_var.get()))
        self.bindings.result_var.trace_add("write", lambda *_args: self._sync_model_text("result_text", self.bindings.result_var.get()))
        self.bindings.note_var.trace_add("write", lambda *_args: self._sync_model_text("note_text", self.bindings.note_var.get()))
        self.bindings.advanced_status_var.trace_add("write", lambda *_args: self._sync_model_text("advanced_status_text", self.bindings.advanced_status_var.get()))
        self.bindings.job_detail_var.trace_add("write", lambda *_args: self._sync_model_text("job_detail", self.bindings.job_detail_var.get()))
        self.bindings.build_runtime_var.trace_add("write", lambda *_args: self._sync_model_text("build_runtime_text", self.bindings.build_runtime_var.get()))

    def _sync_model_text(self, attribute_name, value):
        setattr(self.model, attribute_name, value)

    def _sync_repo_display(self, value):
        self.model.repo_text = value
        remote_info = dict(self.model.remote_info or {})
        remote_info["display"] = value or "Unknown repository"
        self.model.remote_info = remote_info

    def _sync_bindings(self):
        self.model.repo_text = self.model.remote_info.get("display", self.model.repo_text)
        self.bindings.sync_from_model(self.model)

    @property
    def branch_name(self):
        return self.model.branch_name

    @branch_name.setter
    def branch_name(self, value):
        self.model.branch_name = value or "main"
        self._sync_bindings()

    @property
    def remote_info(self):
        return self.model.remote_info

    @remote_info.setter
    def remote_info(self, value):
        self.model.remote_info = value or {"owner": None, "repo": None, "url": None, "display": "Unknown repository"}
        self.model.repo_text = self.model.remote_info.get("display", "Unknown repository")
        self._sync_bindings()

    @property
    def local_manifest(self):
        return self.model.local_manifest

    @local_manifest.setter
    def local_manifest(self, value):
        self.model.local_manifest = value or []

    @property
    def comparison_rows(self):
        return self.model.comparison_rows

    @comparison_rows.setter
    def comparison_rows(self, value):
        self.model.comparison_rows = value or []

    @property
    def download_in_progress(self):
        return self.model.download_in_progress

    @download_in_progress.setter
    def download_in_progress(self, value):
        self.model.download_in_progress = bool(value)

    @property
    def source_job_in_progress(self):
        return self.model.source_job_in_progress

    @source_job_in_progress.setter
    def source_job_in_progress(self, value):
        self.model.source_job_in_progress = bool(value)
        self._persist_source_job_state()

    @property
    def active(self):
        return self.model.active

    @active.setter
    def active(self, value):
        self.model.active = bool(value)

    @property
    def mode(self):
        return self.model.mode

    @mode.setter
    def mode(self, value):
        self.model.mode = value

    @property
    def job_phase(self):
        return self.model.job_phase

    @job_phase.setter
    def job_phase(self, value):
        self.model.job_phase = value or "idle"

    @property
    def job_detail(self):
        return self.model.job_detail

    @job_detail.setter
    def job_detail(self, value):
        self.model.job_detail = value or ""

    @property
    def source_archive_path(self):
        return self.model.source_archive_path

    @source_archive_path.setter
    def source_archive_path(self, value):
        self.model.source_archive_path = value

    @property
    def source_stage_dir(self):
        return self.model.source_stage_dir

    @source_stage_dir.setter
    def source_stage_dir(self, value):
        self.model.source_stage_dir = value

    @property
    def source_extract_dir(self):
        return self.model.source_extract_dir

    @source_extract_dir.setter
    def source_extract_dir(self, value):
        self.model.source_extract_dir = value

    @property
    def source_root_dir(self):
        return self.model.source_root_dir

    @source_root_dir.setter
    def source_root_dir(self, value):
        self.model.source_root_dir = value

    @property
    def source_build_log_path(self):
        return self.model.source_build_log_path

    @source_build_log_path.setter
    def source_build_log_path(self, value):
        self.model.source_build_log_path = value

    @property
    def source_built_exe_path(self):
        return self.model.source_built_exe_path

    @source_built_exe_path.setter
    def source_built_exe_path(self, value):
        self.model.source_built_exe_path = value

    @property
    def source_build_runtime(self):
        return self.model.source_build_runtime

    @source_build_runtime.setter
    def source_build_runtime(self, value):
        self.model.source_build_runtime = value

    @property
    def source_build_runtime_issue(self):
        return self.model.source_build_runtime_issue

    @source_build_runtime_issue.setter
    def source_build_runtime_issue(self, value):
        self.model.source_build_runtime_issue = value

    @property
    def banner_bootstyle(self):
        return self.model.banner_bootstyle

    @banner_bootstyle.setter
    def banner_bootstyle(self, value):
        self.model.banner_bootstyle = value

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
        return self.model.serialize_source_job_state()

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
            self.model.status_text = status_text
            self.set_banner(banner_text, bootstyle=banner_bootstyle, active=active, mode=mode)
            self.source_job_in_progress = False
        finally:
            self._loading_state = False
            self._sync_bindings()

    def set_banner(self, message, bootstyle=INFO, active=True, mode=None):
        self.active = active
        self.mode = mode
        self.banner_bootstyle = bootstyle if active else SECONDARY
        self.model.banner_text = message
        self._sync_bindings()
        self._persist_source_job_state()

    def set_job_phase(self, phase, detail=None, mode=None):
        normalized_phase = str(phase or "idle").strip().lower() or "idle"
        self.job_phase = normalized_phase
        self.job_detail = detail or ""
        self.mode = mode if mode is not None else self.mode
        self._sync_bindings()
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
        self.model.apply_build_runtime(runtime_text, issue_text)
        self._sync_bindings()
        self._persist_source_job_state()

    def clear_source_snapshot(self):
        self.set_source_snapshot()

    def clear_banner(self):
        self.set_banner("Updates idle.", active=False, mode=None)
        self.clear_job_phase()