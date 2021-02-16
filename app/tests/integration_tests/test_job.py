import uuid

import pytest

from app.controller.exporter_proxy import ExporterProxy
from app.controller.importer_proxy import ImporterProxy
from app.models import Job, JobStatus, Session, StatusEnum, add_job_to_db, get_job
from app.tests.conftest import WIKIFACTORY_TEST_PROJECT_URL, WIKIFACTORY_TOKEN

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


@pytest.mark.needs_alpha
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


def test_job_overall_status_not_completed():

    session = Session()

    (job_id, job) = create_job(
        import_url="testurl",
        import_service="googledrive",
        export_url="testurl",
        export_service="googledrive",
        export_token="testtoken",
    )

    # Add the job to the db
    add_job_to_db(job, job_id)

    # Add to the db the following statuses

    # importing
    importing_status = JobStatus()
    importing_status.job_id = job_id
    importing_status.status = StatusEnum.importing.value
    session.add(importing_status)

    # importing_succesfully
    importing_succesfully_status = JobStatus()
    importing_succesfully_status.job_id = job_id
    importing_succesfully_status.status = StatusEnum.importing_successfully.value
    session.add(importing_succesfully_status)
    session.commit()

    # The created job should appear in the db
    retrieved_job = get_job(job_id)

    assert retrieved_job["job_id"] == job_id

    # Check the last status
    assert retrieved_job["job_status"] == StatusEnum.importing_successfully.value

    assert retrieved_job["overall_process"] == pytest.approx(3 / 5 * 100)


def test_job_overall_status_complete_job():

    session = Session()

    (job_id, job) = create_job(
        import_url="testurl",
        import_service="googledrive",
        export_url="testurl",
        export_service="googledrive",
        export_token="testtoken",
    )

    # Add the job to the db
    add_job_to_db(job, job_id)

    # Add to the db the following statuses

    # importing
    importing_status = JobStatus()
    importing_status.job_id = job_id
    importing_status.status = StatusEnum.importing.value
    session.add(importing_status)

    # importing_succesfully
    importing_succesfully_status = JobStatus()
    importing_succesfully_status.job_id = job_id
    importing_succesfully_status.status = StatusEnum.importing_successfully.value
    session.add(importing_succesfully_status)

    # exporting
    exporting_status = JobStatus()
    exporting_status.job_id = job_id
    exporting_status.status = StatusEnum.exporting.value
    session.add(exporting_status)

    # exporting_succesfully
    exporting_succesfully_status = JobStatus()
    exporting_succesfully_status.job_id = job_id
    exporting_succesfully_status.status = StatusEnum.exporting_successfully.value
    session.add(exporting_succesfully_status)

    session.commit()

    # The created job should appear in the db
    retrieved_job = get_job(job_id)
    print(job_id)

    assert retrieved_job["job_id"] == job_id

    # Check the last status
    assert retrieved_job["job_status"] == StatusEnum.exporting_successfully.value

    assert retrieved_job["overall_process"] == pytest.approx(100)


def test_export_error_status_change():

    session = Session()
    # Try to import from git, with a non-valid url
    # That should first add an "auth_required" status to the db for that job
    # and then if the user retries the process, a "data_not_reachable" one

    (job_id, job) = create_job(
        import_url="https://github.com/rievo/icosphere"[::-1],  # Unexisting url
        import_service="git",
    )  # default export parameters

    # Add the job to the db as well as the "pending" status
    add_job_to_db(job, job_id)

    # Start the importing process
    processing_prx = ImporterProxy(job_id)

    manifest = processing_prx.handle_request(job)

    # Since there was an error, the manifest couldn't be generated
    assert manifest is None

    base_query = session.query(JobStatus).filter(JobStatus.job_id == job_id)

    # Additionally, since this is the first try of importing it,
    # we should be able to see in the db the auth required status
    auth_result = base_query.filter(
        JobStatus.status == StatusEnum.importing_error_authorization_required.value
    ).one_or_none()

    assert auth_result is not None  # The auth required status is in the db

    unreachable_result = base_query.filter(
        JobStatus.status == StatusEnum.importing_error_data_unreachable.value
    ).one_or_none()
    assert unreachable_result is None  # The data unreachable is there

    # If we try to handle the request again:
    manifest = processing_prx.handle_request(job)

    assert manifest is None  # Manifest not generated again

    # Check if we still have only auth required status
    auth_result = base_query.filter(
        JobStatus.status == StatusEnum.importing_error_authorization_required.value
    ).one_or_none()

    assert auth_result is not None  # The auth required status is in the db

    # Finally, test if we have the unreachabler result in the db
    unreachable_result = base_query.filter(
        JobStatus.status == StatusEnum.importing_error_data_unreachable.value
    ).one_or_none()
    assert auth_result is not None  # The data unreachable is there
