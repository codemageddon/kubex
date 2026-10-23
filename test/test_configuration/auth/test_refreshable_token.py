from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import anyio
import pytest
from pydantic import SecretStr

from kubex.configuration.auth.exec import ExecAuthProvider
from kubex.configuration.auth.oidc import OIDCAuthProvider
from kubex.configuration.auth.refreshable_token import (
    TOKEN_REFRESH_INTERVAL,
    ExecRefreshableToken,
    FileRefreshableToken,
    OidcRefreshableToken,
    bearer_token,
)
from kubex.configuration.configuration import ExecConfig, ExecInteractiveMode


def test_bearer_token_formats_correctly() -> None:
    token = SecretStr("my-secret-token")
    assert bearer_token(token) == "Bearer my-secret-token"


def test_bearer_token_empty_string() -> None:
    token = SecretStr("")
    assert bearer_token(token) == "Bearer "


def test_bearer_token_with_special_characters() -> None:
    token = SecretStr("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature")
    assert (
        bearer_token(token)
        == "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
    )


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_reads_from_file(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("test-token-value")
    ft = FileRefreshableToken(token_file)
    result = await ft._id_token()
    assert result.get_secret_value() == "test-token-value"


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_strips_whitespace(
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("  test-token  \n")
    ft = FileRefreshableToken(token_file)
    result = await ft._id_token()
    assert result.get_secret_value() == "test-token"


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_raises_on_empty_file(
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("")
    ft = FileRefreshableToken(token_file)
    with pytest.raises(ValueError, match="Token is not set"):
        await ft._id_token()


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_raises_on_whitespace_only(
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("   \n  ")
    ft = FileRefreshableToken(token_file)
    with pytest.raises(ValueError, match="Token is not set"):
        await ft._id_token()


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_sets_expiry(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("test-token")
    ft = FileRefreshableToken(token_file)
    before = anyio.current_time()
    await ft._id_token()
    after = anyio.current_time()
    assert ft._expires_at >= before + TOKEN_REFRESH_INTERVAL
    assert ft._expires_at <= after + TOKEN_REFRESH_INTERVAL


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_caches_when_not_expired(
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("first-token")
    ft = FileRefreshableToken(token_file)
    first = await ft._id_token()
    token_file.write_text("second-token")
    second = await ft._id_token()
    assert first.get_secret_value() == "first-token"
    assert second.get_secret_value() == "first-token"


@pytest.mark.anyio
async def test_file_refreshable_token_id_token_refreshes_when_expired(
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("first-token")
    ft = FileRefreshableToken(token_file)
    await ft._id_token()
    ft._expires_at = anyio.current_time() - 1
    token_file.write_text("second-token")
    result = await ft._id_token()
    assert result.get_secret_value() == "second-token"


@pytest.mark.anyio
async def test_file_refreshable_token_to_header(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("my-token")
    ft = FileRefreshableToken(token_file)
    header = await ft.to_header()
    assert header == "Bearer my-token"


@pytest.mark.anyio
async def test_file_refreshable_token_to_header_caches(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("cached-token")
    ft = FileRefreshableToken(token_file)
    first = await ft.to_header()
    token_file.write_text("new-token")
    second = await ft.to_header()
    assert first == "Bearer cached-token"
    assert second == "Bearer cached-token"


@pytest.mark.anyio
async def test_file_refreshable_token_to_header_refreshes_when_expired(
    tmp_path: Path,
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("old-token")
    ft = FileRefreshableToken(token_file)
    await ft.to_header()
    ft._expires_at = anyio.current_time() - 1
    token_file.write_text("fresh-token")
    header = await ft.to_header()
    assert header == "Bearer fresh-token"


@pytest.mark.anyio
async def test_exec_refreshable_token_id_token_delegates_to_provider() -> None:
    provider = ExecAuthProvider(
        config=ExecConfig(
            api_version="client.authentication.k8s.io/v1",
            kind="ExecCredential",
            command="echo",
            args=[
                "-n",
                '{"apiVersion":"client.authentication.k8s.io/v1","kind":"ExecCredential","status":{"token":"exec-token"}}',
            ],
            interactive_mode=ExecInteractiveMode.IF_AVAILABLE,
        )
    )
    et = ExecRefreshableToken(provider)
    result = await et._id_token()
    assert result.get_secret_value() == "exec-token"


@pytest.mark.anyio
async def test_exec_refreshable_token_id_token_caches_when_not_expired() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("exec-token", None))
    et = ExecRefreshableToken(mock_provider)
    await et._id_token()
    et._expires_at = anyio.current_time() + TOKEN_REFRESH_INTERVAL
    second = await et._id_token()
    assert second.get_secret_value() == "exec-token"
    mock_provider.refresh_token.assert_called_once()


@pytest.mark.anyio
async def test_exec_refreshable_token_id_token_refreshes_when_expired() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        side_effect=[("token-1", None), ("token-2", None)]
    )
    et = ExecRefreshableToken(mock_provider)
    first = await et._id_token()
    assert first.get_secret_value() == "token-1"
    et._expires_at = anyio.current_time() - 1
    second = await et._id_token()
    assert second.get_secret_value() == "token-2"
    assert mock_provider.refresh_token.call_count == 2


@pytest.mark.anyio
async def test_exec_refreshable_token_to_header() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("exec-header-token", None))
    et = ExecRefreshableToken(mock_provider)
    header = await et.to_header()
    assert header == "Bearer exec-header-token"


@pytest.mark.anyio
async def test_exec_refreshable_token_sets_expiry() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("some-token", None))
    et = ExecRefreshableToken(mock_provider)
    before = anyio.current_time()
    await et._id_token()
    after = anyio.current_time()
    assert (
        before + TOKEN_REFRESH_INTERVAL
        <= et._expires_at
        <= after + TOKEN_REFRESH_INTERVAL
    )


@pytest.mark.anyio
async def test_exec_refreshable_token_uses_reported_expiration_timestamp() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        return_value=("some-token", "2999-01-01T00:00:00Z")
    )
    et = ExecRefreshableToken(mock_provider)
    await et._id_token()
    # Far beyond the 60s default fallback, since the plugin reported a real expiry.
    assert et._expires_at > anyio.current_time() + TOKEN_REFRESH_INTERVAL * 100


@pytest.mark.anyio
async def test_exec_refreshable_token_naive_timestamp_falls_back() -> None:
    """A plugin that omits the UTC offset cannot be interpreted as any specific
    zone -- guessing UTC would silently over- or under-cache depending on the
    reader's real offset, so it must fall back to the default interval instead,
    the same as an unparseable timestamp (and, above all, not raise)."""
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        return_value=("some-token", "2999-01-01T00:00:00")
    )
    et = ExecRefreshableToken(mock_provider)
    before = anyio.current_time()
    await et._id_token()
    after = anyio.current_time()
    assert (
        before + TOKEN_REFRESH_INTERVAL
        <= et._expires_at
        <= after + TOKEN_REFRESH_INTERVAL
    )


@pytest.mark.anyio
async def test_exec_refreshable_token_unparseable_timestamp_falls_back() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        return_value=("some-token", "not-a-timestamp")
    )
    et = ExecRefreshableToken(mock_provider)
    before = anyio.current_time()
    await et._id_token()
    after = anyio.current_time()
    assert (
        before + TOKEN_REFRESH_INTERVAL
        <= et._expires_at
        <= after + TOKEN_REFRESH_INTERVAL
    )


@pytest.mark.anyio
async def test_exec_refreshable_token_out_of_range_timestamp_falls_back() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        return_value=("some-token", "0001-01-01T00:00:00+14:00")
    )
    et = ExecRefreshableToken(mock_provider)
    before = anyio.current_time()
    await et._id_token()
    after = anyio.current_time()
    assert (
        before + TOKEN_REFRESH_INTERVAL
        <= et._expires_at
        <= after + TOKEN_REFRESH_INTERVAL
    )


@pytest.mark.anyio
async def test_is_expiring_true_when_wall_clock_deadline_has_passed() -> None:
    """A system suspend advances wall-clock time without advancing the monotonic
    clock; the wall-clock deadline must independently trigger expiry."""
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("some-token", None))
    et = ExecRefreshableToken(mock_provider)
    await et._id_token()
    assert not et._is_expiring()

    et._expires_at_wall = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert et._is_expiring()


@pytest.mark.anyio
async def test_oidc_refreshable_token_id_token_delegates_to_provider() -> None:
    mock_provider = AsyncMock(spec=OIDCAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("oidc-token", None))
    ot = OidcRefreshableToken(mock_provider)
    result = await ot._id_token()
    assert result.get_secret_value() == "oidc-token"


@pytest.mark.anyio
async def test_oidc_refreshable_token_uses_exp_claim() -> None:
    far_future_exp = (datetime.now(timezone.utc) + timedelta(days=3650)).timestamp()
    mock_provider = AsyncMock(spec=OIDCAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("oidc-token", far_future_exp))
    ot = OidcRefreshableToken(mock_provider)
    await ot._id_token()
    # Far beyond the 60s default fallback, since a real exp claim was reported.
    assert ot._expires_at > anyio.current_time() + TOKEN_REFRESH_INTERVAL * 100


@pytest.mark.anyio
async def test_oidc_refreshable_token_falls_back_without_exp_claim() -> None:
    mock_provider = AsyncMock(spec=OIDCAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("oidc-token", None))
    ot = OidcRefreshableToken(mock_provider)
    before = anyio.current_time()
    await ot._id_token()
    after = anyio.current_time()
    assert (
        before + TOKEN_REFRESH_INTERVAL
        <= ot._expires_at
        <= after + TOKEN_REFRESH_INTERVAL
    )


@pytest.mark.anyio
async def test_oidc_refreshable_token_out_of_range_exp_claim_falls_back() -> None:
    """An `exp` claim emitted in milliseconds (a known non-conformant IdP bug)
    or otherwise out of `datetime`'s range must not raise; it must be treated
    as unusable and fall back to the default interval."""
    mock_provider = AsyncMock(spec=OIDCAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        return_value=("oidc-token", 1_767_225_600_000.0)
    )
    ot = OidcRefreshableToken(mock_provider)
    before = anyio.current_time()
    await ot._id_token()
    after = anyio.current_time()
    assert (
        before + TOKEN_REFRESH_INTERVAL
        <= ot._expires_at
        <= after + TOKEN_REFRESH_INTERVAL
    )


@pytest.mark.anyio
async def test_oidc_refreshable_token_id_token_caches_when_not_expired() -> None:
    mock_provider = AsyncMock(spec=OIDCAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("oidc-token", None))
    ot = OidcRefreshableToken(mock_provider)
    await ot._id_token()
    ot._expires_at = anyio.current_time() + TOKEN_REFRESH_INTERVAL
    second = await ot._id_token()
    assert second.get_secret_value() == "oidc-token"
    mock_provider.refresh_token.assert_called_once()


@pytest.mark.anyio
async def test_to_header_concurrent_callers_do_not_race(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("concurrent-token")
    ft = FileRefreshableToken(token_file)

    async with anyio.create_task_group() as tg:
        tg.start_soon(ft.to_header)
        tg.start_soon(ft.to_header)


@pytest.mark.anyio
async def test_to_header_concurrent_refresh_calls_id_token_once() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value=("exec-token", None))
    et = ExecRefreshableToken(mock_provider)

    async with anyio.create_task_group() as tg:
        tg.start_soon(et.to_header)
        tg.start_soon(et.to_header)
        tg.start_soon(et.to_header)

    mock_provider.refresh_token.assert_called_once()


@pytest.mark.anyio
async def test_to_header_repeated_refresh_survives_many_concurrent_callers() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(
        side_effect=[("token-1", None), ("token-2", None)]
    )
    et = ExecRefreshableToken(mock_provider)

    async with anyio.create_task_group() as tg:
        tg.start_soon(et.to_header)
        tg.start_soon(et.to_header)

    et._expires_at = anyio.current_time() - 1

    async with anyio.create_task_group() as tg:
        tg.start_soon(et.to_header)
        tg.start_soon(et.to_header)

    assert mock_provider.refresh_token.call_count == 2
