from app.models import StatusEnum, Session, JobStatus
from app.models import set_job_status
from sqlalchemy.orm.exc import NoResultFound


class Importer:

    status = StatusEnum.importing.value

    hooks_for_status = {}

    job_id = ""

    def __init__(self, job_id):
        raise NotImplementedError()

    def process_url(self, url):
        self.set_status(StatusEnum.importing)

    def validate_url(url):
        raise NotImplementedError()

    def set_status(self, new_status):
        self.status = new_status

        set_job_status(self.job_id, new_status)

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

    def on_import_error_found(self, exception):

        session = Session()

        # First, check in the db if the job has the login_required status

        try:

            session.query(JobStatus.job_id, JobStatus.status).filter(
                JobStatus.job_id == self.job_id
            ).filter(
                JobStatus.status.in_(
                    [StatusEnum.importing_error_authorization_required.value]
                )
            ).one()

            # At this point, we know that for that job_id, we have the
            # authorization_required status and the user is retrying the process
            # Then, we set the status to data_unreachable
            set_job_status(
                self.job_id, StatusEnum.importing_error_data_unreachable.value
            )
        except NoResultFound as e:
            print(e)
            # First time trying to find the auth_required status,
            # Since we didn't find it, we must create it
            set_job_status(
                self.job_id,
                StatusEnum.importing_error_authorization_required.value,
            )


class NotValidURLForImportException(ValueError):
    pass
