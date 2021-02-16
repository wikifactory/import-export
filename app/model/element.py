from enum import Enum
import json
from pydantic import BaseModel
from typing import List


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"



class Element(BaseModel):
    def __init__(
        self, id=None, type=None, children=None, path=None, name=None
    ):
        self.id: str = id or ""
        self.type: ElementType = type or ElementType.UNKNOWN
        self.children: List["Element"] = children or []
        self.path: str = path or ""
        self.name: str = name or ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)


Element.update_forward_refs()
