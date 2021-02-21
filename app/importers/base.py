class BaseImporter:
    def __init__(self, db, job_id):
        raise NotImplementedError()

    def process(self):
        raise NotImplementedError()
