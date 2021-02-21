class BaseExporter:
    def __init__(self, db, job_id):
        raise NotImplementedError()

    def process(self):
        raise NotImplementedError()


class AuthRequired(Exception):
    pass


class NotReachable(Exception):
    pass
