from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anyio
from pydantic import SecretStr

from .exec import ExecAuthProvider
from .oidc import OIDCAuthProvider

TOKEN_REFRESH_INTERVAL = 60


def bearer_token(token: SecretStr) -> str:
    return f"Bearer {token.get_secret_value()}"


class BaseRefreshableToken(ABC):
    def __init__(self) -> None:
        self._lock = anyio.Lock()
        self._last_read_token: SecretStr | None = None
        self._expires_at: float = anyio.current_time()
        self._expires_at_wall: datetime = datetime.now(timezone.utc)

    def _is_expiring(self) -> bool:
        # Checked against both clocks: `anyio.current_time()` is monotonic and
        # does not advance across a system suspend, so a suspend spanning a
        # credential's remaining lifetime would otherwise extend it. Wall-clock
        # time can jump (NTP, manual changes), which is what the monotonic
        # check guards against in the normal case.
        if self._expires_at < anyio.current_time() + 10:
            return True
        return self._expires_at_wall <= datetime.now(timezone.utc)

    def _set_expiry(self, deadline: datetime | None) -> None:
        """Record `deadline` (or the default interval, if unknown) on both clocks."""
        now = datetime.now(timezone.utc)
        if deadline is None:
            deadline = now + timedelta(seconds=TOKEN_REFRESH_INTERVAL)
        seconds_remaining = max((deadline - now).total_seconds(), 0.0)
        self._expires_at = anyio.current_time() + seconds_remaining
        self._expires_at_wall = deadline

    def _cached_token(self) -> SecretStr | None:
        if not self._is_expiring():
            return self._last_read_token
        return None

    @abstractmethod
    async def _id_token(self) -> SecretStr: ...

    async def to_header(self) -> str:
        token = self._cached_token()
        if token is not None:
            return bearer_token(token)
        async with self._lock:
            token = self._cached_token()
            if token is None:
                token = await self._id_token()
        return bearer_token(token)


class FileRefreshableToken(BaseRefreshableToken):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    async def _id_token(self) -> SecretStr:
        if self._is_expiring() or self._last_read_token is None:
            raw_token = self.path.read_text().strip()
            if not raw_token:
                raise ValueError("Token is not set")
            self._last_read_token = SecretStr(raw_token)
            self._set_expiry(None)
        return self._last_read_token


def _parse_rfc3339(timestamp: str) -> datetime | None:
    """Parse an RFC 3339 timestamp into an aware UTC `datetime`.

    A timestamp with no UTC offset cannot be interpreted -- it could be local
    time in any zone -- so it is treated the same as an unparseable one
    (`None`) rather than guessed as UTC, which would silently over- or
    under-cache the credential depending on the reader's offset from UTC.
    The caller falls back to the default refresh interval in either case.
    """
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError, OSError):
        return None


class OidcRefreshableToken(BaseRefreshableToken):
    def __init__(self, provider: OIDCAuthProvider) -> None:
        super().__init__()
        self._provider = provider

    def _get_expiration(self, exp_claim: float | None) -> datetime | None:
        if exp_claim is None:
            return None
        try:
            return datetime.fromtimestamp(exp_claim, tz=timezone.utc)
        except (OverflowError, ValueError, OSError):
            # Out-of-range or otherwise unusable `exp` (e.g. emitted in
            # milliseconds by a non-conformant IdP) -- fall back rather than
            # letting the exception escape and break every subsequent request.
            return None

    async def _id_token(self) -> SecretStr:
        if not self._is_expiring() and self._last_read_token is not None:
            return self._last_read_token
        raw_token, exp_claim = await self._provider.refresh_token()
        self._last_read_token = SecretStr(raw_token)
        self._set_expiry(self._get_expiration(exp_claim))
        return self._last_read_token


class ExecRefreshableToken(BaseRefreshableToken):
    def __init__(self, provider: ExecAuthProvider) -> None:
        super().__init__()
        self._provider = provider

    def _get_expiration(self, expiration_timestamp: str | None) -> datetime | None:
        if expiration_timestamp is None:
            return None
        return _parse_rfc3339(expiration_timestamp)

    async def _id_token(self) -> SecretStr:
        if not self._is_expiring() and self._last_read_token is not None:
            return self._last_read_token
        raw_token, expiration_timestamp = await self._provider.refresh_token()
        self._last_read_token = SecretStr(raw_token)
        self._set_expiry(self._get_expiration(expiration_timestamp))
        return self._last_read_token
