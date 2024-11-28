from functools import cached_property
from typing import Any, Iterator, KeysView, Mapping


class HeadersWrapper(Mapping[str, str]):
    def __init__(self, headers: Mapping[str, str]) -> None:
        self._headers = headers

    def __getitem__(self, key: str) -> str:
        return self._headers[key]

    def get_all(self, key: str) -> list[str]:
        if hasattr(self._headers, "get_list"):  # httpx Headers
            return self._headers.get_list(key)  # type: ignore
        if hasattr(self._headers, "get_all"):  # aiohttp CMultiDictProxy
            return self._headers.get_all(key)  # type: ignore
        return [self._headers[key]]

    def keys(self) -> KeysView[str]:
        return self._headers.keys()

    def __iter__(self) -> Iterator[Any]:
        return iter(self.keys())

    def __len__(self) -> int:
        return len(self._headers)


class Response:
    def __init__(
        self,
        content: bytes | None,
        headers: HeadersWrapper,
        status_code: int,
    ) -> None:
        self.content = content or bytes()
        self.headers = headers
        self.status_code = status_code

    @cached_property
    def text(self) -> str:
        return self.content.decode("utf-8")
