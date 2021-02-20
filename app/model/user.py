import json

from pydantic.dataclasses import dataclass


@dataclass
class User:

    id: str = ""
    name: str = ""
    affiliation: str = ""
    email: str = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
