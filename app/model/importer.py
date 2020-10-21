class Importer:

    def __init__(self):
        raise NotImplementedError

    async def process_url(self, url):
        raise NotImplementedError
