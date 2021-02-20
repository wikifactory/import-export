# from certification import Certification
import json
from typing import List

from pydantic.dataclasses import dataclass

from app.model.certification import Certification


@dataclass
class Standard:

    id: str = ""
    title: str = ""
    reference: str = ""
    certifications: List[Certification] = []

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
        pass
