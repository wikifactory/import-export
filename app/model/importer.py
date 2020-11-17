class Importer:
    def __init__(self, request_id):
        raise NotImplementedError

    async def process_url(self, url):
        raise NotImplementedError
