from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from kubex.core.json_pointer import JsonPointer
from kubex.core.json_patch import (
    JsonPatch,
    JsonPatchAdd,
    JsonPatchCopy,
    JsonPatchMove,
    JsonPatchOperation,
    JsonPatchRemove,
    JsonPatchReplace,
    JsonPatchTest,
)


_OP_CONSTRUCTION_CASES: list[tuple[type[Any], dict[str, Any], dict[str, Any]]] = [
    (
        JsonPatchAdd,
        {"path": "/a/b", "value": 42},
        {"op": "add", "path": "/a/b", "value": 42},
    ),
    (
        JsonPatchAdd,
        {"path": "/a/b", "value": {"key": "val"}},
        {"op": "add", "path": "/a/b", "value": {"key": "val"}},
    ),
    (JsonPatchRemove, {"path": "/a/b"}, {"op": "remove", "path": "/a/b"}),
    (
        JsonPatchReplace,
        {"path": "/a/b", "value": 99},
        {"op": "replace", "path": "/a/b", "value": 99},
    ),
    (
        JsonPatchMove,
        {"path": "/a/b", "from_": "/c/d"},
        {"op": "move", "path": "/a/b", "from": "/c/d"},
    ),
    (
        JsonPatchCopy,
        {"path": "/a/b", "from_": "/c/d"},
        {"op": "copy", "path": "/a/b", "from": "/c/d"},
    ),
    (
        JsonPatchTest,
        {"path": "/a/b", "value": [1, 2, 3]},
        {"op": "test", "path": "/a/b", "value": [1, 2, 3]},
    ),
]


@pytest.mark.parametrize(
    ("model_cls", "kwargs", "expected_dump"),
    _OP_CONSTRUCTION_CASES,
    ids=[f"{c[0].__name__}-{i}" for i, c in enumerate(_OP_CONSTRUCTION_CASES)],
)
def test_operation_construction_and_serialization(
    model_cls: type[Any], kwargs: dict[str, Any], expected_dump: dict[str, Any]
) -> None:
    op = model_cls(**kwargs)
    assert op.model_dump(by_alias=True) == expected_dump


@pytest.mark.parametrize("value", (None, 1, "str", [1, 2], {"k": "v"}, True))
def test_json_patch_add_value_can_be_any_type(value: Any) -> None:
    assert JsonPatchAdd(path=JsonPointer("/x"), value=value).value == value


def test_json_patch_move_from_alias_in_json() -> None:
    op = JsonPatchMove(path="/a/b", from_="/c/d")  # ty: ignore[missing-argument, unknown-argument, invalid-argument-type]
    raw = json.loads(op.model_dump_json(by_alias=True))
    assert raw["from"] == "/c/d"


_adapter: TypeAdapter[JsonPatchOperation] = TypeAdapter(JsonPatchOperation)

_DISPATCH_CASES: list[tuple[dict[str, Any], type[Any]]] = [
    ({"op": "add", "path": "/x", "value": 1}, JsonPatchAdd),
    ({"op": "remove", "path": "/x"}, JsonPatchRemove),
    ({"op": "replace", "path": "/x", "value": 2}, JsonPatchReplace),
    ({"op": "move", "path": "/x", "from": "/y"}, JsonPatchMove),
    ({"op": "copy", "path": "/x", "from": "/y"}, JsonPatchCopy),
    ({"op": "test", "path": "/x", "value": "v"}, JsonPatchTest),
]


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    _DISPATCH_CASES,
    ids=[c[1].__name__ for c in _DISPATCH_CASES],
)
def test_discriminated_union_dispatch(
    raw: dict[str, Any], expected_type: type[Any]
) -> None:
    result = _adapter.validate_python(raw)
    assert isinstance(result, expected_type)


def test_discriminated_union_move_preserves_from() -> None:
    result = _adapter.validate_python({"op": "move", "path": "/x", "from": "/y"})
    assert isinstance(result, JsonPatchMove)
    assert result.from_ == "/y"


@pytest.mark.parametrize(
    "raw",
    (
        {"op": "invalid", "path": "/x"},
        {"path": "/x", "value": 1},
        {"op": "add", "path": "/x"},
        {"op": "move", "path": "/x"},
    ),
    ids=["invalid-op", "missing-op", "add-missing-value", "move-missing-from"],
)
def test_discriminated_union_rejects_invalid(raw: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _adapter.validate_python(raw)


def test_serialize_produces_json_array() -> None:
    patch = JsonPatch(
        [
            JsonPatchAdd(path="/a", value=1),  # ty: ignore[invalid-argument-type]
            JsonPatchRemove(path="/b"),  # ty: ignore[invalid-argument-type]
        ]
    )
    result = json.loads(patch.serialize())
    assert result == [
        {"op": "add", "path": "/a", "value": 1},
        {"op": "remove", "path": "/b"},
    ]


def test_serialize_with_move_uses_from_alias() -> None:
    patch = JsonPatch([JsonPatchMove(path="/a", from_="/b")])  # ty: ignore[missing-argument, unknown-argument, invalid-argument-type]

    result = json.loads(patch.serialize())
    assert result == [{"op": "move", "path": "/a", "from": "/b"}]


def test_serialize_empty_list() -> None:
    assert json.loads(JsonPatch([]).serialize()) == []


def test_serialize_all_operations() -> None:
    patch = JsonPatch(
        [
            JsonPatchAdd(path="/a", value="v"),  # ty: ignore[invalid-argument-type]
            JsonPatchRemove(path="/b"),  # ty: ignore[invalid-argument-type]
            JsonPatchReplace(path="/c", value=3),  # ty: ignore[invalid-argument-type]
            JsonPatchMove(path="/d", from_="/e"),  # ty: ignore[missing-argument, unknown-argument, invalid-argument-type]
            JsonPatchCopy(path="/f", from_="/g"),  # ty: ignore[missing-argument, unknown-argument, invalid-argument-type]
            JsonPatchTest(path="/h", value=True),  # ty: ignore[invalid-argument-type]
        ]
    )
    result = json.loads(patch.serialize())
    assert result == [
        {"op": "add", "path": "/a", "value": "v"},
        {"op": "remove", "path": "/b"},
        {"op": "replace", "path": "/c", "value": 3},
        {"op": "move", "path": "/d", "from": "/e"},
        {"op": "copy", "path": "/f", "from": "/g"},
        {"op": "test", "path": "/h", "value": True},
    ]


def test_serialize_by_alias_false_still_uses_from_alias() -> None:
    """by_alias=False must not produce 'from_' — RFC 6902 requires 'from'."""
    patch = JsonPatch([JsonPatchMove(path="/a", from_="/b")])  # ty: ignore[missing-argument, unknown-argument, invalid-argument-type]
    result = json.loads(patch.serialize(by_alias=False))
    assert result == [{"op": "move", "path": "/a", "from": "/b"}]


def test_content_type_header() -> None:
    assert JsonPatch.content_type_header == "application/json-patch+json"


@pytest.mark.parametrize(
    "body",
    (
        [{"op": "bad", "path": "/x"}],
        [{"op": "add", "path": "/x"}],
    ),
    ids=["invalid-op", "missing-value"],
)
def test_json_patch_rejects_invalid_dicts(body: list[dict[str, Any]]) -> None:
    with pytest.raises(ValidationError):
        JsonPatch(body)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]


def test_json_patch_accepts_valid_dicts() -> None:
    patch = JsonPatch([{"op": "add", "path": "/x", "value": 1}])  # type: ignore[list-item]  # ty: ignore[invalid-argument-type]
    result = json.loads(patch.serialize())
    assert result == [{"op": "add", "path": "/x", "value": 1}]


def test_json_patch_accepts_model_instances() -> None:
    patch = JsonPatch([JsonPatchAdd(path="/x", value=1)])  # ty: ignore[invalid-argument-type]
    result = json.loads(patch.serialize())
    assert result == [{"op": "add", "path": "/x", "value": 1}]


_BUILDER_CASES: list[tuple[str, JsonPatch, list[dict[str, Any]]]] = [
    ("add", JsonPatch().add("/a", 1), [{"op": "add", "path": "/a", "value": 1}]),
    ("remove", JsonPatch().remove("/a"), [{"op": "remove", "path": "/a"}]),
    (
        "replace",
        JsonPatch().replace("/a", "new"),
        [{"op": "replace", "path": "/a", "value": "new"}],
    ),
    (
        "move",
        JsonPatch().move("/a", from_="/b"),
        [{"op": "move", "path": "/a", "from": "/b"}],
    ),
    (
        "copy",
        JsonPatch().copy("/a", from_="/b"),
        [{"op": "copy", "path": "/a", "from": "/b"}],
    ),
    (
        "test",
        JsonPatch().test("/a", "expected"),
        [{"op": "test", "path": "/a", "value": "expected"}],
    ),
]


@pytest.mark.parametrize(
    ("label", "patch", "expected"),
    _BUILDER_CASES,
    ids=[c[0] for c in _BUILDER_CASES],
)
def test_builder_single_operation(
    _: str, patch: JsonPatch, expected: list[dict[str, Any]]
) -> None:
    assert json.loads(patch.serialize()) == expected


def test_builder_empty() -> None:
    assert json.loads(JsonPatch().serialize()) == []


def test_builder_chaining() -> None:
    patch = (
        JsonPatch()
        .add("/a", 1)
        .remove("/b")
        .replace("/c", 3)
        .move("/d", from_="/e")
        .copy("/f", from_="/g")
        .test("/h", True)
    )
    result = json.loads(patch.serialize())
    assert result == [
        {"op": "add", "path": "/a", "value": 1},
        {"op": "remove", "path": "/b"},
        {"op": "replace", "path": "/c", "value": 3},
        {"op": "move", "path": "/d", "from": "/e"},
        {"op": "copy", "path": "/f", "from": "/g"},
        {"op": "test", "path": "/h", "value": True},
    ]


def test_builder_chaining_returns_same_instance() -> None:
    patch = JsonPatch()
    assert patch.add("/a", 1) is patch


@pytest.mark.parametrize(
    "invalid_path",
    ("no-slash", "relative/path", "missing"),
    ids=["no-slash", "relative-path", "bare-word"],
)
def test_operation_rejects_invalid_json_pointer(invalid_path: str) -> None:
    with pytest.raises(ValidationError):
        JsonPatchAdd(path=invalid_path, value=1)  # ty: ignore[invalid-argument-type]


def test_operation_rejects_invalid_from_pointer() -> None:
    with pytest.raises(ValidationError):
        JsonPatchMove(path="/valid", from_="not-a-pointer")  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]


@pytest.mark.parametrize(
    "invalid_path",
    ("no-slash", "relative/path"),
)
def test_builder_rejects_invalid_path(invalid_path: str) -> None:
    with pytest.raises(ValidationError):
        JsonPatch().add(invalid_path, 1)


def test_builder_move_rejects_invalid_from() -> None:
    with pytest.raises(ValidationError):
        JsonPatch().move("/valid", from_="bad")


def test_json_patch_from_dicts_rejects_invalid_path() -> None:
    with pytest.raises(ValidationError):
        JsonPatch([{"op": "add", "path": "bad", "value": 1}])  # type: ignore[list-item]  # ty: ignore[invalid-argument-type]


def test_serialize_preserves_none_value() -> None:
    patch = JsonPatch([JsonPatchAdd(path="/x", value=None)])  # ty: ignore[invalid-argument-type]
    result = json.loads(patch.serialize())
    assert result == [{"op": "add", "path": "/x", "value": None}]


def test_serialize_exclude_unset_still_includes_op() -> None:
    """exclude_unset is ignored: op defaults must still appear in output."""
    patch = JsonPatch([JsonPatchAdd(path="/x", value=1)])  # ty: ignore[invalid-argument-type]
    result = json.loads(patch.serialize(exclude_unset=True))
    assert result[0]["op"] == "add"


def test_builder_instances_are_independent() -> None:
    a = JsonPatch()
    b = JsonPatch()
    a.add("/x", 1)
    assert json.loads(b.serialize()) == []


def test_move_rejects_from_proper_prefix_of_path() -> None:
    with pytest.raises(ValidationError, match="must not be a proper prefix"):
        JsonPatchMove(path="/a/b", from_="/a")  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]


def test_move_rejects_from_deep_prefix_of_path() -> None:
    with pytest.raises(ValidationError, match="must not be a proper prefix"):
        JsonPatchMove(path="/a/b/c", from_="/a/b")  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]


def test_move_allows_equal_paths() -> None:
    m = JsonPatchMove(path="/a", from_="/a")  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]
    assert m.path == "/a"


def test_move_allows_non_prefix_paths() -> None:
    m = JsonPatchMove(path="/a/b", from_="/c/d")  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]
    assert m.from_ == "/c/d"


def test_move_allows_reverse_prefix() -> None:
    m = JsonPatchMove(path="/a", from_="/a/b")  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]
    assert m.path == "/a"


def test_builder_move_rejects_from_prefix() -> None:
    with pytest.raises(ValidationError, match="must not be a proper prefix"):
        JsonPatch().move("/a/b", from_="/a")


def test_json_patch_model_json_schema() -> None:
    schema = JsonPatchAdd.model_json_schema()
    assert schema["properties"]["path"]["type"] == "string"


def test_json_patch_round_trip() -> None:
    original = JsonPatch(
        [
            JsonPatchAdd(path="/a", value=1),  # ty: ignore[invalid-argument-type]
            JsonPatchMove(path="/b", from_="/c"),  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]
        ]
    )
    serialized = original.serialize()
    restored = JsonPatch.model_validate_json(serialized)
    assert json.loads(restored.serialize()) == json.loads(serialized)
