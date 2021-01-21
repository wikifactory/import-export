from app.models import StatusEnum

from app.models import set_job_status


class Exporter:

    status = StatusEnum.exporting.value

    hooks_for_status = {}

    job_id = ""

    def __init__(self, job_id):
        raise NotImplementedError

    def export_manifest(self, manifest, export_url, export_token):
        raise NotImplementedError

    def validate_url(url):
        raise NotImplementedError

    def set_status(self, new_status: str):
        self.status = new_status

        set_job_status(self.job_id, new_status)

        # Callbacks for the change
        if self.status in self.hooks_for_status:
            hooks = self.hooks_for_status[self.status]

            if len(hooks) > 0:
                for h in hooks:
                    h()  # Call the method. QUESTION: PARAMS?

    def add_hook_for_status(self, status: str, action):
        # If this is the first time that we will register an action for that status
        if status not in self.hooks_for_status:
            self.hooks_for_status[status] = []

        self.hooks_for_status[status].append(action)

    def remove_hook_for_status(self, status: str, action):
        # Remove the hook for that status
        if action in self.hooks_for_status[status]:
            self.hooks_for_status[status].remove(action)


class NotValidURLForExportException(Exception):
    pass


class NotValidManifest(Exception):
    pass
