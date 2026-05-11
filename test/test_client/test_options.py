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
    assert opts.trust_env is False


def test_log_api_warnings_false() -> None:
    assert ClientOptions(log_api_warnings=False).log_api_warnings is False


# Fields that share the ``... | None | <type>`` shape: ``...`` (default)
# means "use library default", ``None`` means "explicitly disable / unlimited",
# and a positive value is the explicit override.
_OPTIONAL_OVERRIDE_FIELDS = [
    "timeout",
    "keep_alive_timeout",
    "buffer_size",
    "ws_max_message_size",
    "pool_size",
    "pool_size_per_host",
]


@pytest.mark.parametrize("field", _OPTIONAL_OVERRIDE_FIELDS)
def test_optional_override_field_defaults_to_ellipsis(field: str) -> None:
    assert getattr(ClientOptions(), field) is Ellipsis


@pytest.mark.parametrize("field", _OPTIONAL_OVERRIDE_FIELDS)
def test_optional_override_field_explicit_ellipsis_roundtrip(field: str) -> None:
    assert getattr(ClientOptions(**{field: ...}), field) is Ellipsis


@pytest.mark.parametrize("field", _OPTIONAL_OVERRIDE_FIELDS)
def test_optional_override_field_none_preserved(field: str) -> None:
    assert getattr(ClientOptions(**{field: None}), field) is None


@pytest.mark.parametrize(
    "field,value,expected",
    [
        pytest.param("keep_alive_timeout", 30, 30.0, id="keep_alive_timeout_int"),
        pytest.param("keep_alive_timeout", 60.5, 60.5, id="keep_alive_timeout_float"),
        pytest.param("keep_alive_timeout", 0, 0.0, id="keep_alive_timeout_zero"),
        pytest.param("buffer_size", 4096, 4096, id="buffer_size"),
        pytest.param("ws_max_message_size", 2**21, 2**21, id="ws_max_message_size"),
        pytest.param("pool_size", 50, 50, id="pool_size"),
        pytest.param("pool_size_per_host", 10, 10, id="pool_size_per_host"),
    ],
)
def test_optional_override_field_positive_value_preserved(
    field: str, value: object, expected: object
) -> None:
    assert getattr(ClientOptions(**{field: value}), field) == expected


_TIMEOUT_NORMALIZE_CASES = [
    pytest.param(3, Timeout(total=3.0), id="int"),
    pytest.param(2.5, Timeout(total=2.5), id="float"),
    pytest.param(
        Timeout(connect=1, read=2), Timeout(connect=1, read=2), id="timeout_instance"
    ),
]


@pytest.mark.parametrize("input_val,expected", _TIMEOUT_NORMALIZE_CASES)
def test_timeout_normalized(input_val: object, expected: Timeout) -> None:
    opts = ClientOptions(timeout=input_val)
    if isinstance(input_val, Timeout):
        assert opts.timeout is input_val
    else:
        assert opts.timeout == expected


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param("bogus", id="non_numeric_string"),
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
    ],
)
def test_timeout_invalid_raises(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(timeout=bad_val)


@pytest.mark.parametrize(
    "proxy",
    [
        pytest.param(None, id="none"),
        pytest.param("http://proxy.example.com:8080", id="str_no_userinfo"),
        pytest.param("http://user:pass@proxy.example.com:8080", id="str_with_userinfo"),
        pytest.param({"http": "http://p.example.com"}, id="dict_http_only"),
        pytest.param({"https": "http://p.example.com"}, id="dict_https_only"),
        pytest.param(
            {"http": "http://p.example.com", "https": "http://p.example.com"},
            id="dict_both_schemes",
        ),
    ],
)
def test_proxy_valid(proxy: object) -> None:
    assert ClientOptions(proxy=proxy).proxy == proxy


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


@pytest.mark.parametrize("value", [True, False])
def test_keep_alive_valid(value: bool) -> None:
    assert ClientOptions(keep_alive=value).keep_alive is value


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


# ``buffer_size``, ``ws_max_message_size``, ``pool_size`` and
# ``pool_size_per_host`` share the same positive-int-or-sentinel validator.
_POSITIVE_INT_FIELDS = [
    "buffer_size",
    "ws_max_message_size",
    "pool_size",
    "pool_size_per_host",
]
_POSITIVE_INT_INVALID = [
    pytest.param(True, id="bool_true"),
    pytest.param(False, id="bool_false"),
    pytest.param(0, id="zero"),
    pytest.param(-1, id="negative"),
    pytest.param(3.14, id="float"),
    pytest.param("4096", id="string"),
]


@pytest.mark.parametrize("field", _POSITIVE_INT_FIELDS)
@pytest.mark.parametrize("bad_val", _POSITIVE_INT_INVALID)
def test_positive_int_field_rejects_invalid(field: str, bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(**{field: bad_val})


@pytest.mark.parametrize("value", [True, False])
def test_trust_env_valid(value: bool) -> None:
    assert ClientOptions(trust_env=value).trust_env is value


@pytest.mark.parametrize(
    "bad_val",
    [
        pytest.param("true", id="str_true"),
        pytest.param(1, id="int_one"),
        pytest.param(1.0, id="float_one"),
    ],
)
def test_trust_env_rejects_non_bool(bad_val: object) -> None:
    with pytest.raises(ValidationError):
        ClientOptions(trust_env=bad_val)
