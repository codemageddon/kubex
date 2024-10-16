from __future__ import annotations

from typing import Any


class Request:
    def __init__(
        self,
        method: str,
        url: str,
        query_params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.query_params = query_params
        self.method = method
        self.body = body
        self.headers = headers

    def __repr__(self) -> str:
        return f"Request(method={self.method}, url={self.url}, query_params={self.query_params}, body={self.body}, headers={self.headers})"
