import pytest

from kubex.configuration import ClientConfiguration
from kubex.core.params import Timeout


def _base_config(**kwargs: object) -> ClientConfiguration:
    return ClientConfiguration(
        url="https://example.invalid",
        insecure_skip_tls_verify=True,
        **kwargs,  # type: ignore[arg-type]
    )


def test_default_timeout_is_ellipsis() -> None:
    config = _base_config()
    assert config.timeout is Ellipsis


def test_explicit_none_preserved() -> None:
    config = _base_config(timeout=None)
    assert config.timeout is None


_NORMALIZE_CASES = [
    pytest.param(3, Timeout(total=3.0), id="int"),
    pytest.param(2.5, Timeout(total=2.5), id="float"),
    pytest.param(
        Timeout(connect=1, read=2), Timeout(connect=1, read=2), id="timeout_instance"
    ),
]


@pytest.mark.parametrize("input_val,expected", _NORMALIZE_CASES)
def test_timeout_normalized(input_val: object, expected: Timeout) -> None:
    config = _base_config(timeout=input_val)
    if isinstance(input_val, Timeout):
        assert config.timeout is input_val
    else:
        assert config.timeout == expected
