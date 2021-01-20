from enum import Enum


class ImporterStatus(Enum):
    INITIALIZED = 0
    STARTED = 1
    URL_PROCESSED = 2
    ABORTED = -1


class Importer:

    status = ImporterStatus.INITIALIZED

    hooks_for_status = {}

    def __init__(self, job_id):
        raise NotImplementedError

    def process_url(self, url):
        raise NotImplementedError

    def validate_url(url):
        raise NotImplementedError

    def set_status(self, new_status):
        self.status = new_status

        # Callbacks for the change
        if self.status in self.hooks_for_status:
            hooks = self.hooks_for_status[self.status]

            if len(hooks) > 0:
                for h in hooks:
                    h()  # Call the method. QUESTION: PARAMS?

    def add_hook_for_status(self, status, action):
        # If this is the first time that we will register an action for that status
        if status not in self.hooks_for_status:
            self.hooks_for_status[status] = []

        self.hooks_for_status[status].append(action)

    def remove_hook_for_status(self, status, action):
        # Remove the hook for that status
        if action in self.hooks_for_status[status]:
            self.hooks_for_status[status].remove(action)


class NotValidURLForImportException(Exception):
    pass
