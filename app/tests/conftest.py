from app.models import Session, JobStatus, Job

WIKIFACTORY_TOKEN = "eyJfcGVybWFuZW50Ijp0cnVlLCJ1c2VybmFtZSI6InRlc3R1c2VyMyJ9.YButtw.ksOvNRFeFmq5BHU1JjcS3AiVilg"
WIKIFACTORY_TEST_PROJECT_URL = "http://frontend:8080/@testuser3/newyork"


def pytest_sessionfinish(session, exitstatus):
    session = Session()
    session.query(JobStatus).delete()
    session.query(Job).delete()

    session.commit()
