from functools import cached_property
from typing import MutableMapping


class Response:
    def __init__(
        self,
        content: bytes | None,
        headers: MutableMapping[str, str] | None,
        status_code: int,
    ) -> None:
        self.content = content or bytes()
        self.headers = headers or {}
        self.status_code = status_code

    @cached_property
    def text(self) -> str:
        return self.content.decode("utf-8")
