from enum import Enum
import json


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"


class Element:
    def __init__(self, id=None, type=None, children=None, path=None, name=None):
        self.id = id or ""
        self.type = type or ElementType.UNKNOWN
        self.children = children or []
        self.path = path or ""
        self.name = name or ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
