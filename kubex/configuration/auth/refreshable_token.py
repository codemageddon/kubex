from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import anyio
from pydantic import SecretStr

from .exec import ExecAuthProvider
from .oidc import OIDCAuthProvider

FILE_TOKEN_REFRRESH_INTERVAL = 60


def bearer_token(token: SecretStr) -> str:
    return f"Bearer {token.get_secret_value()}"


class _AsyncRWLock:
    def __init__(self) -> None:
        self._readers = 0
        self._reader_lock = anyio.Lock()  # Protects the readers count
        self._writer_lock = anyio.Lock()  # Blocks writers when active

    @asynccontextmanager
    async def read_lock(self) -> AsyncGenerator[None, None]:
        """Acquire a read lock. Multiple readers can hold the lock simultaneously.
        Writers are blocked while any readers hold the lock.
        """
        async with self._reader_lock:
            self._readers += 1
            if self._readers == 1:
                await self._writer_lock.acquire()  # Block writers if first reader
        try:
            yield
        finally:
            async with self._reader_lock:
                self._readers -= 1
                if self._readers == 0:
                    self._writer_lock.release()  # Release writer lock if last reader

    @asynccontextmanager
    async def write_lock(self) -> AsyncGenerator[None, None]:
        """
        Acquire a write lock. Only one writer can hold the lock,
        and all readers are blocked while the writer holds the lock.
        """
        async with self._writer_lock:
            yield


class BaseRefreachableToken(ABC):
    def __init__(self) -> None:
        self._lock = _AsyncRWLock()
        self._last_read_token: SecretStr | None = None
        self._expires_at: float = anyio.current_time()

    def _is_expiring(self) -> bool:
        return self._expires_at < anyio.current_time() + 10

    def _cached_token(self) -> SecretStr | None:
        if not self._is_expiring():
            return self._last_read_token
        return None

    @abstractmethod
    async def _id_token(self) -> SecretStr: ...

    async def to_header(self) -> str:
        token: SecretStr | None = None
        async with self._lock.read_lock():
            token = self._cached_token()
        if token is None:
            async with self._lock.write_lock():
                token = await self._id_token()
        return bearer_token(token)


class FileRefreachableToken(BaseRefreachableToken):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    async def _id_token(self) -> SecretStr:
        if self._is_expiring() or self._last_read_token is None:
            raw_token = self.path.read_text().strip()
            if not raw_token:
                raise ValueError("Token is not set")
            self._last_read_token = SecretStr(raw_token)
            self._expires_at = anyio.current_time() + FILE_TOKEN_REFRRESH_INTERVAL
        return self._last_read_token


class OidcRefreachableToken(BaseRefreachableToken):
    def __init__(self, provider: OIDCAuthProvider) -> None:
        super().__init__()
        self._provider = provider

    def _get_expiration(self, token: str) -> float:
        # TODO: Implement this
        return float(FILE_TOKEN_REFRRESH_INTERVAL)

    async def _id_token(self) -> SecretStr:
        if not self._is_expiring() and self._last_read_token is not None:
            return self._last_read_token
        raw_token = await self._provider.refresh_token()
        self._last_read_token = SecretStr(raw_token)
        self._expires_at = self._get_expiration(raw_token)
        return self._last_read_token


class ExecRefreachableToken(BaseRefreachableToken):
    def __init__(self, provider: ExecAuthProvider) -> None:
        super().__init__()
        self._provider = provider

    async def _id_token(self) -> SecretStr:
        if not self._is_expiring() and self._last_read_token is not None:
            return self._last_read_token
        raw_token = await self._provider.refresh_token()
        self._last_read_token = SecretStr(raw_token)
        self._expires_at = self._get_expiration(raw_token)
        return self._last_read_token
