import pytest

from kubex.core.params import Timeout

_ORIGINAL = Timeout(connect=2)

_COERCE_CASES = [
    pytest.param(None, None, id="none_returns_none"),
    pytest.param(5, Timeout(total=5.0), id="int_becomes_total"),
    pytest.param(1.5, Timeout(total=1.5), id="float_becomes_total"),
    pytest.param(_ORIGINAL, _ORIGINAL, id="timeout_returns_same_instance"),
]


@pytest.mark.parametrize("input_val,expected", _COERCE_CASES)
def test_coerce(input_val: object, expected: Timeout | None) -> None:
    result = Timeout.coerce(input_val)  # type: ignore[arg-type]
    if isinstance(input_val, Timeout):
        assert result is input_val
    else:
        assert result == expected


def test_timeout_repr_includes_all_fields() -> None:
    text = repr(Timeout(total=1, connect=2, read=3, write=4, pool=5))
    assert "total=1" in text
    assert "connect=2" in text
    assert "read=3" in text
    assert "write=4" in text
    assert "pool=5" in text


def test_timeout_equality_by_fields() -> None:
    assert Timeout(total=1, connect=2) == Timeout(total=1, connect=2)
    assert Timeout(total=1) != Timeout(total=2)


def test_timeout_not_equal_to_non_timeout() -> None:
    assert Timeout(total=1) != "Timeout(total=1)"
