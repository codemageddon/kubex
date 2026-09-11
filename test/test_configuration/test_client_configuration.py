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
