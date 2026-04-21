from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from kubex.core.json_pointer import JsonPointer


@pytest.mark.parametrize(
    ("input_val", "expected"),
    (
        ("", ""),
        ("/", "/"),
        ("/foo/bar", "/foo/bar"),
        ("/foo/0", "/foo/0"),
    ),
)
def test_json_pointer_construction(input_val: str, expected: str) -> None:
    assert JsonPointer(input_val) == expected


def test_json_pointer_default_is_empty() -> None:
    assert JsonPointer() == ""


def test_json_pointer_rejects_no_leading_slash() -> None:
    with pytest.raises(ValueError, match="start with '/'"):
        JsonPointer("foo/bar")


def test_json_pointer_is_str_subclass() -> None:
    assert isinstance(JsonPointer("/a/b"), str)


@pytest.mark.parametrize(
    ("tokens", "expected"),
    (
        ((), ""),
        (("foo",), "/foo"),
        (("foo", "bar", "baz"), "/foo/bar/baz"),
        (("foo", 0), "/foo/0"),
        (("a~b",), "/a~0b"),
        (("a/b",), "/a~1b"),
        (("~a/b~",), "/~0a~1b~0"),
    ),
)
def test_json_pointer_from_tokens(tokens: tuple[str | int, ...], expected: str) -> None:
    assert JsonPointer.from_tokens(*tokens) == expected


@pytest.mark.parametrize(
    ("base", "token", "expected"),
    (
        ("", "foo", "/foo"),
        ("/a", "b", "/a/b"),
        ("/a", 0, "/a/0"),
        ("", "a/b", "/a~1b"),
        ("", "c~d", "/c~0d"),
    ),
)
def test_json_pointer_div_operator(base: str, token: str | int, expected: str) -> None:
    assert JsonPointer(base) / token == expected


def test_json_pointer_div_chaining() -> None:
    assert JsonPointer() / "foo" / "bar" / 0 == "/foo/bar/0"


def test_json_pointer_div_returns_json_pointer() -> None:
    assert isinstance(JsonPointer("/a") / "b", JsonPointer)


@pytest.mark.parametrize(
    ("pointer", "expected"),
    (
        ("", []),
        ("/foo", ["foo"]),
        ("/foo/bar/baz", ["foo", "bar", "baz"]),
        ("/", [""]),
        ("/a~0b", ["a~b"]),
        ("/a~1b", ["a/b"]),
    ),
)
def test_json_pointer_tokens(pointer: str, expected: list[str]) -> None:
    assert JsonPointer(pointer).tokens == expected


def test_json_pointer_tokens_roundtrip() -> None:
    original = JsonPointer.from_tokens("a/b", "c~d", 0)
    reconstructed = JsonPointer.from_tokens(*original.tokens)
    assert original == reconstructed


@pytest.mark.parametrize(
    ("pointer", "expected_tokens"),
    (
        ("", []),
        ("/", [""]),
        ("/a~1b", ["a/b"]),
        ("/m~0n", ["m~n"]),
    ),
)
def test_json_pointer_rfc6901_examples(
    pointer: str, expected_tokens: list[str]
) -> None:
    assert JsonPointer(pointer).tokens == expected_tokens


class _PointerModel(BaseModel):
    path: JsonPointer


def test_json_pointer_pydantic_accepts_valid_string() -> None:
    m = _PointerModel(path="/a/b")  # ty: ignore[invalid-argument-type]
    assert isinstance(m.path, JsonPointer)
    assert m.path == "/a/b"


def test_json_pointer_pydantic_accepts_empty_string() -> None:
    m = _PointerModel(path="")  # ty: ignore[invalid-argument-type]
    assert isinstance(m.path, JsonPointer)


def test_json_pointer_pydantic_preserves_instance() -> None:
    ptr = JsonPointer("/a/b")
    m = _PointerModel(path=ptr)
    assert m.path is ptr


def test_json_pointer_pydantic_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        _PointerModel(path="no-slash")  # ty: ignore[invalid-argument-type]


def test_json_pointer_pydantic_serialization() -> None:
    m = _PointerModel(path="/a/b")  # ty: ignore[invalid-argument-type]
    assert m.model_dump() == {"path": "/a/b"}


def test_json_pointer_pydantic_json_serialization() -> None:
    m = _PointerModel(path="/a/b")  # ty: ignore[invalid-argument-type]
    assert '"path":"/a/b"' in m.model_dump_json()


def test_json_pointer_pydantic_rejects_non_string() -> None:
    with pytest.raises(ValidationError):
        _PointerModel(path=123)  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    "invalid",
    ("/bad~", "/bad~2", "/a~", "/a~3b", "/~~"),
    ids=["trailing-tilde", "tilde-2", "trailing-tilde-mid", "tilde-3", "double-tilde"],
)
def test_json_pointer_rejects_invalid_tilde_escape(invalid: str) -> None:
    with pytest.raises(ValueError, match="must be followed by 0 or 1"):
        JsonPointer(invalid)


@pytest.mark.parametrize(
    "valid",
    ("/a~0b", "/a~1b", "/~0~1", "/foo~01"),
    ids=["tilde-0", "tilde-1", "tilde-0-tilde-1", "tilde-01"],
)
def test_json_pointer_accepts_valid_tilde_escape(valid: str) -> None:
    assert JsonPointer(valid) == valid


def test_json_pointer_pydantic_rejects_invalid_tilde_escape() -> None:
    with pytest.raises(ValidationError):
        _PointerModel(path="/bad~2")  # ty: ignore[invalid-argument-type]


def test_json_pointer_model_json_schema() -> None:
    schema = _PointerModel.model_json_schema()
    assert schema["properties"]["path"]["type"] == "string"
