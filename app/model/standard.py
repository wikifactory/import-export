import json

from pydantic.dataclasses import dataclass


@dataclass
class Standard:

    id: str = ""
    title: str = ""
    reference: str = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
