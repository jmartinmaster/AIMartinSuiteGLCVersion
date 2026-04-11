import os
from dataclasses import dataclass, field

from ttkbootstrap.constants import SECONDARY

UPDATE_PHASE_LABELS = {
    "idle": "Idle",
    "checking": "Checking",
    "ready": "Ready",
    "downloading": "Downloading",
    "handoff": "Handoff",
    "failed": "Failed",
    "source_armed": "Source Armed",
    "source_manifest": "Source Manifest",
    "source_downloading": "Source Downloading",
    "source_staging": "Source Staging",
    "source_extracting": "Source Extracting",
    "source_validating": "Source Validating",
    "source_building": "Source Building",
    "source_packaging": "Source Packaging",
    "source_cleanup": "Source Cleanup",
    "source_relaunch": "Source Relaunch",
    "source_complete": "Source Complete",
}

SOURCE_UPDATE_PHASES = {
    "source_armed",
    "source_manifest",
    "source_downloading",
    "source_staging",
    "source_extracting",
    "source_validating",
    "source_building",
    "source_packaging",
    "source_cleanup",
    "source_relaunch",
    "source_complete",
}

RECOVERABLE_SOURCE_PHASES = SOURCE_UPDATE_PHASES | {"failed"}
INTERRUPTED_SOURCE_PHASES = SOURCE_UPDATE_PHASES - {"source_armed", "source_complete"}
SOURCE_JOB_STATE_RELATIVE_PATH = os.path.join("data", "updater", "state", "source-job.json")
SOURCE_JOB_BACKUP_RELATIVE_PATH = os.path.join("data", "backups", "updater")


@dataclass
class UpdateStateModel:
    branch_name: str = "main"
    remote_info: dict = field(default_factory=lambda: {"owner": None, "repo": None, "url": None, "display": "Unknown repository"})
    local_manifest: list = field(default_factory=list)
    comparison_rows: list = field(default_factory=list)
    download_in_progress: bool = False
    source_job_in_progress: bool = False
    active: bool = False
    mode: str = None
    job_phase: str = "idle"
    job_detail: str = "No update job is running."
    source_archive_path: str = None
    source_stage_dir: str = None
    source_extract_dir: str = None
    source_root_dir: str = None
    source_build_log_path: str = None
    source_built_exe_path: str = None
    source_build_runtime: str = None
    source_build_runtime_issue: str = None
    banner_bootstyle: str = SECONDARY
    banner_text: str = "Updates idle."
    status_text: str = "Ready to check for updates."
    repo_text: str = "Unknown repository"
    target_name_text: str = "Dispatcher Core"
    local_version_text: str = "Unknown"
    remote_version_text: str = "Not checked"
    result_text: str = "Pending"
    note_text: str = "Run a repository check to compare the packaged release target."
    advanced_status_text: str = "Advanced dev updates are Windows-only on packaged builds; Ubuntu uses the stable package update path."
    build_runtime_text: str = "Build runtime not resolved yet."

    def phase_label(self):
        normalized_phase = str(self.job_phase or "idle").strip().lower() or "idle"
        return UPDATE_PHASE_LABELS.get(normalized_phase, normalized_phase.replace("_", " ").title())

    def has_recoverable_source_state(self):
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

    def serialize_source_job_state(self):
        if not self.has_recoverable_source_state():
            return None
        return {
            "metadata_version": 1,
            "branch_name": self.branch_name,
            "remote_info": self.remote_info,
            "job_phase": self.job_phase,
            "job_detail": self.job_detail,
            "mode": self.mode,
            "active": self.active,
            "banner_text": self.banner_text,
            "banner_bootstyle": self.banner_bootstyle,
            "status_text": self.status_text,
            "source_job_in_progress": self.source_job_in_progress,
            "source_archive_path": self.source_archive_path,
            "source_stage_dir": self.source_stage_dir,
            "source_extract_dir": self.source_extract_dir,
            "source_root_dir": self.source_root_dir,
            "source_build_log_path": self.source_build_log_path,
            "source_built_exe_path": self.source_built_exe_path,
            "source_build_runtime": self.source_build_runtime,
            "source_build_runtime_issue": self.source_build_runtime_issue,
        }

    def apply_build_runtime(self, runtime_text=None, issue_text=None):
        self.source_build_runtime = str(runtime_text).strip() if runtime_text else None
        self.source_build_runtime_issue = str(issue_text).strip() if issue_text else None
        if self.source_build_runtime:
            self.build_runtime_text = f"Build runtime: {self.source_build_runtime}"
        elif self.source_build_runtime_issue:
            self.build_runtime_text = f"Build runtime unavailable: {self.source_build_runtime_issue}"
        else:
            self.build_runtime_text = "Build runtime not resolved yet."
