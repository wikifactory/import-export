import json

from typing import List
from pydantic import BaseModel
from .manifest_metadata import ManifestMetadata
from app.model.element import ElementType, Element
from app.model.user import User

class Manifest(BaseModel):
    def __init__(
        self,
        project_id=None,
        project_name=None,
        project_description=None,
        source_url=None,
        elements=None,
    ):
        self.metatadata: ManifestMetadata = ManifestMetadata()
        self.project_name: str = project_name or ""
        self.project_id: str = project_id or ""
        self.project_description: str = project_description or ""
        self.elements: List[Element] = elements or []
        self.collaborators: List[User] = []
        self.source_url: str = source_url or ""
        self.file_elements: int = 0


    def toJson(self):
        return json.dumps(self, default=lambda o: o.__dict__)

    def iterate_through_elements(
        self, handler_exporter, on_file_cb, on_folder_cb, on_finished_cb
    ):

        root_element = self.elements[0]

        # Init the queue for the files
        elements_queue = []

        elements_queue.append(root_element)

        while len(elements_queue) > 0:

            element = elements_queue.pop(0)

            if element.type == ElementType.FOLDER:

                # If the user has specified a callback for the folder
                if on_folder_cb is not None:
                    on_folder_cb(element)

                # In any case its files to the queue
                for ch_element in element.children:
                    elements_queue.append(ch_element)

            else:
                # It is a file

                # Perform all the steps for this element / file

                if on_file_cb is not None:
                    on_file_cb(element)

        # Once finished with all the contributions

        if on_finished_cb is not None:
            on_finished_cb()
