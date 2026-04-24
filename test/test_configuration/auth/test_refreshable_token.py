from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import anyio
import pytest
from pydantic import SecretStr

from kubex.configuration.auth.exec import ExecAuthProvider
from kubex.configuration.auth.refreshable_token import (
    TOKEN_REFRESH_INTERVAL,
    ExecRefreshableToken,
    FileRefreshableToken,
    _AsyncRWLock,
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
    mock_provider.refresh_token = AsyncMock(return_value="exec-token")
    et = ExecRefreshableToken(mock_provider)
    await et._id_token()
    et._expires_at = anyio.current_time() + TOKEN_REFRESH_INTERVAL
    second = await et._id_token()
    assert second.get_secret_value() == "exec-token"
    mock_provider.refresh_token.assert_called_once()


@pytest.mark.anyio
async def test_exec_refreshable_token_id_token_refreshes_when_expired() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(side_effect=["token-1", "token-2"])
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
    mock_provider.refresh_token = AsyncMock(return_value="exec-header-token")
    et = ExecRefreshableToken(mock_provider)
    header = await et.to_header()
    assert header == "Bearer exec-header-token"


@pytest.mark.anyio
async def test_exec_refreshable_token_sets_expiry() -> None:
    mock_provider = AsyncMock(spec=ExecAuthProvider)
    mock_provider.refresh_token = AsyncMock(return_value="some-token")
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
async def test_async_rw_lock_read_lock_basic() -> None:
    lock = _AsyncRWLock()
    async with lock.read_lock():
        assert lock._readers == 1


@pytest.mark.anyio
async def test_async_rw_lock_write_lock_basic() -> None:
    lock = _AsyncRWLock()
    async with lock.write_lock():
        assert lock._readers == 0


@pytest.mark.anyio
async def test_async_rw_lock_multiple_nested_readers() -> None:
    lock = _AsyncRWLock()
    async with lock.read_lock():
        assert lock._readers == 1
        async with lock.read_lock():
            assert lock._readers == 2
            async with lock.read_lock():
                assert lock._readers == 3
            assert lock._readers == 2
        assert lock._readers == 1
    assert lock._readers == 0


@pytest.mark.anyio
async def test_async_rw_lock_writer_blocks_readers() -> None:
    lock = _AsyncRWLock()
    events: list[str] = []
    writer_acquired = anyio.Event()

    async def writer() -> None:
        async with lock.write_lock():
            events.append("writer_acquired")
            writer_acquired.set()
            await anyio.sleep(0.05)
            events.append("writer_released")

    async def reader() -> None:
        await writer_acquired.wait()
        async with lock.read_lock():
            events.append("reader_acquired")

    async with anyio.create_task_group() as tg:
        tg.start_soon(writer)
        tg.start_soon(reader)

    assert events.index("writer_released") < events.index("reader_acquired")


@pytest.mark.anyio
async def test_async_rw_lock_readers_release_count() -> None:
    lock = _AsyncRWLock()
    async with lock.read_lock():
        assert lock._readers == 1
        async with lock.read_lock():
            assert lock._readers == 2
        assert lock._readers == 1
    assert lock._readers == 0
