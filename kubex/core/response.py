from typing import MutableMapping


class Response:
    def __init__(
        self,
        content: str | bytes | None,
        headers: MutableMapping[str, str] | None,
        status_code: int,
    ) -> None:
        self.content = content or ""
        self.headers = headers or {}
        self.status_code = status_code
