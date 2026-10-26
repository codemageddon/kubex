from pathlib import Path

import pytest

from kubex.configuration import ClientConfiguration


def test_timeout_param_removed() -> None:
    with pytest.raises(TypeError, match="timeout"):
        ClientConfiguration(url="https://example.com", timeout=30)  # type: ignore[call-arg]


def test_log_api_warnings_param_removed() -> None:
    with pytest.raises(TypeError, match="log_api_warnings"):
        ClientConfiguration(url="https://example.com", log_api_warnings=False)  # type: ignore[call-arg]


def test_token_reads_file_once_on_first_access(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("first-token")
    config = ClientConfiguration(url="https://example.com", token_file=token_file)
    assert config.token == "first-token"


def test_token_refreshes_when_try_refresh_token_true(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("first-token")
    config = ClientConfiguration(
        url="https://example.com", token_file=token_file, try_refresh_token=True
    )
    assert config.token == "first-token"

    token_file.write_text("second-token")
    config._last_token_read = 0.0  # force the cache to be treated as expired
    assert config.token == "second-token"


def test_token_does_not_refresh_when_try_refresh_token_false(tmp_path: Path) -> None:
    """try_refresh_token=False pins the token read on first access."""
    token_file = tmp_path / "token"
    token_file.write_text("first-token")
    config = ClientConfiguration(
        url="https://example.com", token_file=token_file, try_refresh_token=False
    )
    assert config.token == "first-token"

    token_file.write_text("second-token")
    config._last_token_read = 0.0  # would force a refresh if the flag were consulted
    assert config.token == "first-token"


def test_token_file_wins_over_inline_token(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("file-token\n")
    config = ClientConfiguration(
        url="https://example.com",
        token="inline-token",
        token_file=token_file,
        try_refresh_token=True,
    )
    assert config.token == "file-token"

    token_file.write_text("renewed-token")
    config._last_token_read = 0.0
    assert config.token == "renewed-token"


@pytest.mark.parametrize(
    "content", [None, "", "  \n"], ids=["missing", "empty", "blank"]
)
def test_inline_token_is_the_fallback_until_the_file_is_read(
    tmp_path: Path, content: str | None
) -> None:
    token_file = tmp_path / "token"
    if content is not None:
        token_file.write_text(content)
    config = ClientConfiguration(
        url="https://example.com",
        token="inline-token",
        token_file=token_file,
        try_refresh_token=True,
    )
    assert config.token == "inline-token"

    token_file.write_text("file-token")
    config._last_token_read = 0.0
    assert config.token == "file-token"


@pytest.mark.parametrize("inline", [None, "inline-token"], ids=["file-only", "both"])
@pytest.mark.parametrize("broken", ["missing", "empty"])
def test_failed_reread_keeps_last_file_token(
    tmp_path: Path, inline: str | None, broken: str
) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("file-token")
    config = ClientConfiguration(
        url="https://example.com",
        token=inline,
        token_file=token_file,
        try_refresh_token=True,
    )
    assert config.token == "file-token"

    if broken == "missing":
        token_file.unlink()
    else:
        token_file.write_text("")
    config._last_token_read = 0.0
    assert config.token == "file-token"


def test_unreadable_token_file_without_fallback_raises(tmp_path: Path) -> None:
    config = ClientConfiguration(
        url="https://example.com", token_file=tmp_path / "missing"
    )
    with pytest.raises(FileNotFoundError):
        _ = config.token


def test_impersonation_headers_empty_by_default() -> None:
    assert ClientConfiguration(url="https://example.com").impersonation_headers == []


def test_impersonation_headers_user_uid_groups_extra() -> None:
    config = ClientConfiguration(
        url="https://example.com",
        impersonate_user="jane",
        impersonate_uid="1234",
        impersonate_groups=["dev", "ops"],
        impersonate_extra={"scopes": ["view", "edit"], "example.org/team": ["a b"]},
    )
    assert config.impersonation_headers == [
        ("Impersonate-User", "jane"),
        ("Impersonate-Uid", "1234"),
        ("Impersonate-Group", "dev"),
        ("Impersonate-Group", "ops"),
        ("Impersonate-Extra-scopes", "view"),
        ("Impersonate-Extra-scopes", "edit"),
        # Bytes that are not legal in a header name are percent-encoded.
        ("Impersonate-Extra-example.org%2Fteam", "a b"),
    ]


def test_impersonation_groups_without_user_rejected() -> None:
    with pytest.raises(ValueError, match="impersonate_user"):
        ClientConfiguration(url="https://example.com", impersonate_groups=["dev"])


@pytest.mark.anyio
async def test_basic_auth_header() -> None:
    config = ClientConfiguration(
        url="https://example.com", username="admin", password="s3cret"
    )
    # base64("admin:s3cret")
    assert await config.get_authorization_header() == "Basic YWRtaW46czNjcmV0"


@pytest.mark.anyio
async def test_token_takes_precedence_over_basic_auth() -> None:
    config = ClientConfiguration(
        url="https://example.com", token="tok", username="admin", password="pw"
    )
    assert await config.get_authorization_header() == "Bearer tok"


def test_username_without_password_rejected() -> None:
    with pytest.raises(ValueError, match="together"):
        ClientConfiguration(url="https://example.com", username="admin")


def test_tls_server_name_empty_string_means_unset() -> None:
    assert (
        ClientConfiguration(url="https://e.com", tls_server_name="").tls_server_name
        is None
    )
    assert (
        ClientConfiguration(
            url="https://e.com", tls_server_name="kubernetes"
        ).tls_server_name
        == "kubernetes"
    )
