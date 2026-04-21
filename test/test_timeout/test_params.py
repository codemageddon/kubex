from kubex.core.params import Timeout


def test_coerce_none_returns_none() -> None:
    assert Timeout.coerce(None) is None


def test_coerce_int_becomes_total() -> None:
    result = Timeout.coerce(5)
    assert result == Timeout(total=5.0)


def test_coerce_float_becomes_total() -> None:
    result = Timeout.coerce(1.5)
    assert result == Timeout(total=1.5)


def test_coerce_timeout_returns_same_instance() -> None:
    original = Timeout(connect=2)
    assert Timeout.coerce(original) is original


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
