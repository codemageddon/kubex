from __future__ import annotations

import pytest
from pydantic import ValidationError

from kubex.client import ClientOptions
from kubex.core.params import Timeout


def test_defaults() -> None:
    opts = ClientOptions()
    assert opts.timeout is Ellipsis
    assert opts.log_api_warnings is True
    assert opts.proxy is None
    assert opts.keep_alive is True
    assert opts.keep_alive_timeout is Ellipsis
    assert opts.buffer_size is Ellipsis
    assert opts.ws_max_message_size is Ellipsis
    assert opts.pool_size is Ellipsis
    assert opts.pool_size_per_host is Ellipsis


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


@pytest.mark.parametrize("value", [True, False])
def test_bool_timeout_raises(value: bool) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(timeout=value)


# ---------------------------------------------------------------------------
# proxy field
# ---------------------------------------------------------------------------


def test_proxy_default_none() -> None:
    assert ClientOptions().proxy is None


def test_proxy_none_preserved() -> None:
    assert ClientOptions(proxy=None).proxy is None


def test_proxy_str_preserved() -> None:
    url = "http://proxy.example.com:8080"
    assert ClientOptions(proxy=url).proxy == url


def test_proxy_str_with_userinfo() -> None:
    url = "http://user:pass@proxy.example.com:8080"
    assert ClientOptions(proxy=url).proxy == url


@pytest.mark.parametrize(
    "proxy_dict",
    [
        pytest.param({"http": "http://p.example.com"}, id="http_only"),
        pytest.param({"https": "http://p.example.com"}, id="https_only"),
        pytest.param(
            {"http": "http://p.example.com", "https": "http://p.example.com"},
            id="both_schemes",
        ),
    ],
)
def test_proxy_dict_valid(proxy_dict: dict[str, str]) -> None:
    opts = ClientOptions(proxy=proxy_dict)
    assert opts.proxy == proxy_dict


@pytest.mark.parametrize(
    "bad_proxy",
    [
        pytest.param(42, id="int"),
        pytest.param(3.14, id="float"),
        pytest.param(["http://p.com"], id="list"),
        pytest.param({}, id="empty_dict"),
        pytest.param({"ftp": "ftp://p.example.com"}, id="unknown_scheme"),
        pytest.param(
            {"http": "http://p.com", "ftp": "ftp://p.com"}, id="mixed_unknown_scheme"
        ),
        pytest.param({1: "http://p.com"}, id="non_str_key"),
        pytest.param({"http": 123}, id="non_str_value"),
    ],
)
def test_proxy_invalid_raises(bad_proxy: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(proxy=bad_proxy)


# ---------------------------------------------------------------------------
# keep_alive field
# ---------------------------------------------------------------------------


def test_keep_alive_default_true() -> None:
    assert ClientOptions().keep_alive is True


def test_keep_alive_false() -> None:
    assert ClientOptions(keep_alive=False).keep_alive is False


# ---------------------------------------------------------------------------
# keep_alive_timeout field
# ---------------------------------------------------------------------------


def test_keep_alive_timeout_default_ellipsis() -> None:
    assert ClientOptions().keep_alive_timeout is Ellipsis


def test_keep_alive_timeout_ellipsis_roundtrip() -> None:
    assert ClientOptions(keep_alive_timeout=...).keep_alive_timeout is Ellipsis


def test_keep_alive_timeout_none_preserved() -> None:
    assert ClientOptions(keep_alive_timeout=None).keep_alive_timeout is None


@pytest.mark.parametrize(
    "val,expected",
    [
        pytest.param(30, 30.0, id="int_coerced_to_float"),
        pytest.param(60.5, 60.5, id="float_preserved"),
        pytest.param(0.0, 0.0, id="zero_allowed"),
        pytest.param(0, 0.0, id="zero_int_allowed"),
    ],
)
def test_keep_alive_timeout_valid(val: object, expected: float) -> None:
    opts = ClientOptions(keep_alive_timeout=val)
    assert opts.keep_alive_timeout == expected


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
        pytest.param(-1.0, id="negative"),
        pytest.param(-0.1, id="small_negative"),
        pytest.param("30", id="string"),
    ],
)
def test_keep_alive_timeout_invalid_raises(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(keep_alive_timeout=bad_val)


# ---------------------------------------------------------------------------
# buffer_size field
# ---------------------------------------------------------------------------


def test_buffer_size_default_ellipsis() -> None:
    assert ClientOptions().buffer_size is Ellipsis


def test_buffer_size_ellipsis_roundtrip() -> None:
    assert ClientOptions(buffer_size=...).buffer_size is Ellipsis


def test_buffer_size_none_preserved() -> None:
    assert ClientOptions(buffer_size=None).buffer_size is None


def test_buffer_size_positive_int_preserved() -> None:
    assert ClientOptions(buffer_size=4096).buffer_size == 4096


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(3.14, id="float"),
        pytest.param("4096", id="string"),
    ],
)
def test_buffer_size_invalid_raises(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(buffer_size=bad_val)


# ---------------------------------------------------------------------------
# ws_max_message_size field
# ---------------------------------------------------------------------------


def test_ws_max_message_size_default_ellipsis() -> None:
    assert ClientOptions().ws_max_message_size is Ellipsis


def test_ws_max_message_size_ellipsis_roundtrip() -> None:
    assert ClientOptions(ws_max_message_size=...).ws_max_message_size is Ellipsis


def test_ws_max_message_size_none_preserved() -> None:
    assert ClientOptions(ws_max_message_size=None).ws_max_message_size is None


def test_ws_max_message_size_positive_int_preserved() -> None:
    assert ClientOptions(ws_max_message_size=2**21).ws_max_message_size == 2**21


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(1.5, id="float"),
        pytest.param("big", id="string"),
    ],
)
def test_ws_max_message_size_invalid_raises(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(ws_max_message_size=bad_val)


# ---------------------------------------------------------------------------
# pool_size field
# ---------------------------------------------------------------------------


def test_pool_size_default_ellipsis() -> None:
    assert ClientOptions().pool_size is Ellipsis


def test_pool_size_ellipsis_roundtrip() -> None:
    assert ClientOptions(pool_size=...).pool_size is Ellipsis


def test_pool_size_none_preserved() -> None:
    assert ClientOptions(pool_size=None).pool_size is None


def test_pool_size_positive_int_preserved() -> None:
    assert ClientOptions(pool_size=50).pool_size == 50


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
        pytest.param(0, id="zero"),
        pytest.param(-5, id="negative"),
        pytest.param(2.0, id="float"),
        pytest.param("100", id="string"),
    ],
)
def test_pool_size_invalid_raises(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(pool_size=bad_val)


# ---------------------------------------------------------------------------
# pool_size_per_host field
# ---------------------------------------------------------------------------


def test_pool_size_per_host_default_ellipsis() -> None:
    assert ClientOptions().pool_size_per_host is Ellipsis


def test_pool_size_per_host_ellipsis_roundtrip() -> None:
    assert ClientOptions(pool_size_per_host=...).pool_size_per_host is Ellipsis


def test_pool_size_per_host_none_preserved() -> None:
    assert ClientOptions(pool_size_per_host=None).pool_size_per_host is None


def test_pool_size_per_host_positive_int_preserved() -> None:
    assert ClientOptions(pool_size_per_host=10).pool_size_per_host == 10


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
        pytest.param(0, id="zero_rejected_use_none_instead"),
        pytest.param(-1, id="negative"),
        pytest.param(2.5, id="float"),
        pytest.param("10", id="string"),
    ],
)
def test_pool_size_per_host_invalid_raises(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(pool_size_per_host=bad_val)
