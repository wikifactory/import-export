
from enum import Enum
import json


class ElementType(str, Enum):
    FILE = "1"
    FOLDER = "2"
    UNKNOWN = "-99"


class Element:

    def __init__(self):
        self.id = ""
        self.type = ElementType.UNKNOWN
        self.children = []
        self.path = ""

    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)