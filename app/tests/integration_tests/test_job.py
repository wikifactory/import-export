from app.models import add_job_to_db, get_job
from app.models import Session, Job, JobStatus, StatusEnum
from app.tests.conftest import WIKIFACTORY_TOKEN, WIKIFACTORY_TEST_PROJECT_URL
from app.controller.importer_proxy import ImporterProxy
from app.controller.exporter_proxy import ExporterProxy

import uuid

test_url = "http://testurl.com"


def create_job(
    import_service="git",
    import_token="",
    import_url="",
    export_service="git",
    export_token="",
    export_url="",
):

    job_id = str(uuid.uuid4())

    job = {
        "import_service": import_service,
        "import_token": import_token,
        "import_url": import_url,
        "export_service": export_service,
        "export_token": export_token,
        "export_url": export_url,
    }

    return (job_id, job)


def test_get_job_success():

    (job_id, job) = create_job(import_url=test_url)

    # Add the job to the db directly, not using the add_job_to_db method
    session = Session()
    new_job = Job()
    new_job.job_id = job_id
    new_job.import_service = job["import_service"]
    new_job.import_token = job["import_token"]
    new_job.import_url = job["import_url"]
    new_job.export_service = job["export_service"]
    new_job.export_token = job["export_token"]
    new_job.export_url = job["export_url"]

    new_job.processed_elements = 0
    new_job.file_elements = 0

    new_status = JobStatus()
    new_status.job_id = new_job.job_id
    new_status.status = StatusEnum.pending.value

    session.add(new_job)
    session.add(new_status)
    session.commit()

    found_job = get_job(job_id)

    assert found_job is not None
    assert found_job["job_id"] == job_id
    assert "job_status" in found_job
    assert found_job["job_status"] == new_status.status
    assert "job_progress" in found_job
    assert found_job["job_progress"] == 0  # because is a newly created one


def test_get_job_fail():
    unexisting_job_id = "00000000-0000-0000-0000-000000000000"
    found_job = get_job(unexisting_job_id)
    assert found_job is None


def test_add_job_to_db():

    (job_id, job) = create_job(import_url=test_url)

    # Add the job to the db
    add_job_to_db(
        job,
        job_id,
    )

    # The created job should appear in the db
    job = get_job(job_id)

    assert job["job_id"] == job_id
    assert job["job_progress"] == 0  # Newly created


def test_import_from_git_to_wikifactory_fail():

    (job_id, job) = create_job(
        # import_url="https://github.com/CollectiveOpenSourceHardware/LibreSolar_System_Simulation",
        import_url="https://github.com/rievo/icosphere",
        import_service="git",
        export_url=WIKIFACTORY_TEST_PROJECT_URL[
            ::-1
        ],  # Using a not valid wikifactory url will cause the process to fail
        export_service="wikifactory",
        export_token=WIKIFACTORY_TOKEN,
    )

    # Add the job to the db
    add_job_to_db(job, job_id)

    processing_prx = ImporterProxy(job_id)
    manifest = processing_prx.handle_request(job)

    assert manifest is not None

    export_proxy = ExporterProxy(job_id)
    result = export_proxy.export_manifest(manifest, job)

    assert result is None


def test_import_from_git_to_wikifactory_success():

    (job_id, job) = create_job(
        # import_url="https://github.com/CollectiveOpenSourceHardware/LibreSolar_System_Simulation",
        import_url="https://github.com/rievo/icosphere",
        import_service="git",
        export_url=WIKIFACTORY_TEST_PROJECT_URL,
        export_service="wikifactory",
        export_token=WIKIFACTORY_TOKEN,
    )

    # Add the job to the db
    add_job_to_db(job, job_id)

    # result_manifest = handle_post_export.delay(job, job_id).get()

    processing_prx = ImporterProxy(job_id)
    manifest = processing_prx.handle_request(job)

    assert manifest is not None

    export_proxy = ExporterProxy(job_id)
    result = export_proxy.export_manifest(manifest, job)

    assert result is not None