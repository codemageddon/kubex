import pytest

from kubex.configuration import ClientConfiguration


def test_timeout_param_removed() -> None:
    with pytest.raises(TypeError, match="timeout"):
        ClientConfiguration(url="https://example.com", timeout=30)  # type: ignore[call-arg]


def test_log_api_warnings_param_removed() -> None:
    with pytest.raises(TypeError, match="log_api_warnings"):
        ClientConfiguration(url="https://example.com", log_api_warnings=False)  # type: ignore[call-arg]
