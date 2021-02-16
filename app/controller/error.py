class NotValidManifest(ValueError):
    pass


class ExportNotReachable(Exception):
    pass


class ExportAuthRequired(Exception):
    pass


class WikifactoryAPINoResultPath(Exception):
    pass


class WikifactoryAPINoResult(Exception):
    pass


class WikifactoryAPIUserErrors(Exception):
    pass


class FileUploadError(Exception):
    pass
