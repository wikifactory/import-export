from app.controller.importers.git_importer import GitImporter


def test_git_manifest_generation():

    params = {
        "import_url": "https://github.com/rievo/icosphere",
        "import_token": "",
        "import_service": "git",
    }

    importer = GitImporter("test_job_id")

    manifest = importer.process_url(
        params["import_url"], params["import_token"]
    )

    print(manifest)