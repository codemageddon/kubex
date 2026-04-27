from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self

__all__ = ["WebSocketConnection"]


class WebSocketConnection(ABC):
    """Async WebSocket connection abstraction used by exec/attach/port-forward.

    Implementations adapt a concrete WebSocket client (e.g. ``aiohttp`` or
    ``httpx-ws``) to a uniform binary-frame interface. ``receive_bytes`` raises
    ``StopAsyncIteration`` once the peer closes the connection. Non-binary
    frames (e.g. text frames) are a protocol violation for the v5 channel
    protocol; implementations must surface them as ``KubexClientException``
    rather than leaking backend-specific exceptions or silently coercing
    them to bytes.
    """

    @property
    @abstractmethod
    def closed(self) -> bool: ...

    @property
    @abstractmethod
    def negotiated_subprotocol(self) -> str | None: ...

    @abstractmethod
    async def send_bytes(self, data: bytes) -> None: ...

    @abstractmethod
    async def receive_bytes(self) -> bytes: ...

    @abstractmethod
    async def close(self) -> None: ...

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()
