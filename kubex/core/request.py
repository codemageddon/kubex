from __future__ import annotations

from types import EllipsisType

from kubex.core.params import Timeout, TimeoutTypes


class Request:
    def __init__(
        self,
        method: str,
        url: str,
        query_params: dict[str, str] | None = None,
        body: str | bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: TimeoutTypes | EllipsisType = ...,
        query_param_pairs: list[tuple[str, str]] | None = None,
    ) -> None:
        self.url = url
        self.query_params = query_params
        self.query_param_pairs = query_param_pairs
        self.method = method
        self.body = body
        self.headers = headers
        self.timeout: Timeout | None | EllipsisType = (
            timeout if timeout is Ellipsis else Timeout.coerce(timeout)
        )

    def __repr__(self) -> str:
        return (
            f"Request(method={self.method}, url={self.url}, "
            f"query_params={self.query_params}, "
            f"query_param_pairs={self.query_param_pairs}, body={self.body!r}, "
            f"headers={self.headers}, timeout={self.timeout!r})"
        )
