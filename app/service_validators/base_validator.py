from re import search
from typing import List, Optional, Pattern


class ServiceValidator:
    def __init__(self) -> None:
        self.valid_regexes: List[Pattern] = []
        self.service_id = ""

    def validate_url(self, url: str) -> Optional[str]:

        if len(self.valid_regexes) == 0:
            return None

        for regex in self.valid_regexes:
            is_valid = bool(search(regex, url))

            if is_valid is False:
                return None

        return self.service_id
