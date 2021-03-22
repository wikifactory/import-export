import shutil


def remove_job_downloaded_files(job_path: str) -> None:
    try:
        shutil.rmtree(job_path, ignore_errors=False, onerror=None)
    except OSError as e:
        print(e)
