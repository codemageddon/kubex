import pytest
from pydantic import ValidationError

from kubex.client import ClientOptions
from kubex.core.params import Timeout


def test_defaults() -> None:
    opts = ClientOptions()
    assert opts.timeout is Ellipsis
    assert opts.log_api_warnings is True


def test_explicit_none_preserved() -> None:
    opts = ClientOptions(timeout=None)
    assert opts.timeout is None


def test_log_api_warnings_false() -> None:
    opts = ClientOptions(log_api_warnings=False)
    assert opts.log_api_warnings is False


_NORMALIZE_CASES = [
    pytest.param(3, Timeout(total=3.0), id="int"),
    pytest.param(2.5, Timeout(total=2.5), id="float"),
    pytest.param(
        Timeout(connect=1, read=2), Timeout(connect=1, read=2), id="timeout_instance"
    ),
]


@pytest.mark.parametrize("input_val,expected", _NORMALIZE_CASES)
def test_timeout_normalized(input_val: object, expected: Timeout) -> None:
    opts = ClientOptions(timeout=input_val)
    if isinstance(input_val, Timeout):
        assert opts.timeout is input_val
    else:
        assert opts.timeout == expected


def test_ellipsis_sentinel_roundtrip() -> None:
    opts = ClientOptions(timeout=...)
    assert opts.timeout is Ellipsis


def test_bogus_timeout_raises() -> None:
    with pytest.raises(ValidationError):
        ClientOptions(timeout="bogus")
