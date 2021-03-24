from re import search
from typing import List, Optional, Pattern


def regex_validator(
    url: str, *, service_id: str, regexes: List[Pattern]
) -> Optional[str]:
    return service_id if any(search(regex, url) for regex in regexes) else None
