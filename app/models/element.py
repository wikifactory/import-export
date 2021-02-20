import json
from dataclasses import field
from enum import Enum
from typing import List

from pydantic.dataclasses import dataclass


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"


@dataclass
class Element:

    id: str = ""
    type: ElementType = ElementType.UNKNOWN
    children: List["Element"] = field(default_factory=list)
    path: str = ""
    name: str = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)


Element.__pydantic_model__.update_forward_refs()
