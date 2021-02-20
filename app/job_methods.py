from app.controller.exporter_proxy import ExporterProxy
from app.controller.importer_proxy import ImporterProxy
from app.models import set_retry_job


def generate_manifest(body: dict, job_id):

    processing_prx = ImporterProxy(job_id)
    manifest = processing_prx.handle_request(body)
    return manifest.toJson()


def export_job(body: dict, job_id):
    # body contains the parameters for this request (tokens and so on)

    print("Starting the import process...")

    # Configure the importer
    processing_prx = ImporterProxy(job_id)
    manifest = processing_prx.handle_request(body)

    if manifest is None:
        return {"error": "The manifest could not be generated"}

    print("Importing process finished!")
    # logger.info(manifest)
    print("Starting the export Process...")
    # Configure the exporter
    export_proxy = ExporterProxy(job_id)
    result = export_proxy.export_manifest(manifest, body)

    print("Process done!")
    return result


def retry_job(body: dict, job_id):
    # We can now proceed to the whole process
    print("Retrying job: {}".format(job_id))

    # Add the "retry" status to the db
    set_retry_job(job_id)

    # And now we can do the whole import-export process again
    processing_prx = ImporterProxy(job_id)

    manifest = processing_prx.handle_request(body)

    if manifest is None:
        return {
            "error": "The manifest for job {} could not be generated".format(job_id)
        }

    print("Importing process finished!")

    print("Starting the export Process...")
    # Configure the exporter
    export_proxy = ExporterProxy(job_id)
    result = export_proxy.export_manifest(manifest, body)

    print("The retry process succeded!")
    return result
