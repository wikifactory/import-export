from enum import Enum
import json
from pydantic.dataclasses import dataclass
from typing import List
import dataclasses


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"


@dataclass
class Element:


    id: str = ""
    type: ElementType = ElementType.UNKNOWN
    children: List["Element"] = dataclasses.field(default_factory=lambda: [0])
    path: str = ""
    name: str = ""

    def __init__(
        self, id=None, type=None, children=None, path=None, name=None
    ):
        self.id = id or ""
        self.type = type or ElementType.UNKNOWN
        self.children = children or []
        self.path = path or ""
        self.name = name or ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)


Element.__pydantic_model__.update_forward_refs()
