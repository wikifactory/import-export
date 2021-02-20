import json
from pydantic.dataclasses import dataclass


@dataclass
class Certification:
    certifier_id: str = ""
    data_awarded: str = ""
    url: str = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
