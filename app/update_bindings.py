import ttkbootstrap as tb


class UpdateStateBindings:
    def __init__(self, root):
        self.banner_var = tb.StringVar(master=root, value="Updates idle.")
        self.status_var = tb.StringVar(master=root, value="Ready to check for updates.")
        self.branch_var = tb.StringVar(master=root, value="main")
        self.repo_var = tb.StringVar(master=root, value="Unknown repository")
        self.target_name_var = tb.StringVar(master=root, value="Dispatcher Core")
        self.local_version_var = tb.StringVar(master=root, value="Unknown")
        self.remote_version_var = tb.StringVar(master=root, value="Not checked")
        self.result_var = tb.StringVar(master=root, value="Pending")
        self.note_var = tb.StringVar(master=root, value="Run a repository check to compare the packaged release target.")
        self.advanced_status_var = tb.StringVar(master=root, value="Advanced dev updates are Windows-only on packaged builds; Ubuntu uses the stable package update path.")
        self.job_phase_var = tb.StringVar(master=root, value="Idle")
        self.job_detail_var = tb.StringVar(master=root, value="No update job is running.")
        self.build_runtime_var = tb.StringVar(master=root, value="Build runtime not resolved yet.")

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
