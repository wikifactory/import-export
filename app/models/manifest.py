import json
import os

from pydantic.dataclasses import dataclass


@dataclass
class Manifest:
    project_name: str = ""
    project_description: str = ""
    path: str = ""
    source_url: str = ""

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__)
