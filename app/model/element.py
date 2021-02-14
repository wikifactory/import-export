from enum import Enum
import json


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"


class Element:
    def __init__(
        self, id="", type=ElementType.UNKNOWN, children=[], path="", name=""
    ):
        self.id = id
        self.type = type
        self.children = children
        self.path = path
        self.name = name

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)
