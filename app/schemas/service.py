from typing import Optional

from pydantic import BaseModel, HttpUrl


class Service(BaseModel):
    name: Optional[str]
    url: HttpUrl
