from enum import Enum
import json
from pydantic import BaseModel
from typing import List


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"


class Element(BaseModel):
    id: str = ""
    type: ElementType = ElementType.UNKNOWN
    children: List["Element"] = []
    path: str = ""
    name: str = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)


Element.update_forward_refs()
