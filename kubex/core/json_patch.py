from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from kubex.core.json_pointer import JsonPointer


class JsonPatchAdd(BaseModel):
    op: Literal["add"] = "add"
    path: JsonPointer
    value: Any


class JsonPatchRemove(BaseModel):
    op: Literal["remove"] = "remove"
    path: JsonPointer


class JsonPatchReplace(BaseModel):
    op: Literal["replace"] = "replace"
    path: JsonPointer
    value: Any


class JsonPatchMove(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    op: Literal["move"] = "move"
    path: JsonPointer
    from_: JsonPointer = Field(alias="from")

    @model_validator(mode="after")
    def _check_from_not_prefix_of_path(self) -> JsonPatchMove:
        from_tokens = self.from_.tokens
        path_tokens = self.path.tokens
        if (
            len(from_tokens) < len(path_tokens)
            and path_tokens[: len(from_tokens)] == from_tokens
        ):
            msg = f"'from' ({self.from_}) must not be a proper prefix of 'path' ({self.path})"
            raise ValueError(msg)
        return self


class JsonPatchCopy(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    op: Literal["copy"] = "copy"
    path: JsonPointer
    from_: JsonPointer = Field(alias="from")


class JsonPatchTest(BaseModel):
    op: Literal["test"] = "test"
    path: JsonPointer
    value: Any


JsonPatchOperation = Annotated[
    Union[
        JsonPatchAdd,
        JsonPatchRemove,
        JsonPatchReplace,
        JsonPatchMove,
        JsonPatchCopy,
        JsonPatchTest,
    ],
    Field(discriminator="op"),
]


class JsonPatch(RootModel[list[JsonPatchOperation]]):
    """RFC 6902 JSON Patch document.

    Can be constructed directly or built incrementally via chaining::

        patch = JsonPatch().add("/a", 1).remove("/b").replace("/c", "new")
    """

    content_type_header: ClassVar[str] = "application/json-patch+json"

    root: list[JsonPatchOperation] = []

    def add(self, path: str, value: Any) -> JsonPatch:
        self.root.append(JsonPatchAdd(path=path, value=value))  # ty: ignore[invalid-argument-type]
        return self

    def remove(self, path: str) -> JsonPatch:
        self.root.append(JsonPatchRemove(path=path))  # ty: ignore[invalid-argument-type]
        return self

    def replace(self, path: str, value: Any) -> JsonPatch:
        self.root.append(JsonPatchReplace(path=path, value=value))  # ty: ignore[invalid-argument-type]

        return self

    def move(self, path: str, *, from_: str) -> JsonPatch:
        self.root.append(
            JsonPatchMove(path=path, from_=from_)  # ty: ignore[invalid-argument-type,missing-argument, unknown-argument]
        )
        return self

    def copy(  # type: ignore[override]  # ty: ignore[invalid-method-override]
        self, path: str, *, from_: str
    ) -> JsonPatch:
        self.root.append(
            JsonPatchCopy(path=path, from_=from_)  # ty: ignore[invalid-argument-type, missing-argument, unknown-argument]
        )
        return self

    def test(self, path: str, value: Any) -> JsonPatch:
        self.root.append(JsonPatchTest(path=path, value=value))  # ty: ignore[invalid-argument-type]
        return self

    def serialize(
        self,
        *,
        by_alias: bool = True,  # noqa: ARG002
        exclude_unset: bool = True,  # noqa: ARG002
        exclude_none: bool = True,  # noqa: ARG002
    ) -> str:
        # by_alias is always True for JSON Patch: the "from" field on move/copy
        # operations uses Field(alias="from") and by_alias=False would emit
        # the Python name "from_", producing invalid RFC 6902 output.
        # exclude_unset and exclude_none are intentionally not forwarded:
        # JSON Patch operations have a fixed schema where all fields (including
        # op defaults and value=null) must be present for valid RFC 6902 output.
        return self.model_dump_json(by_alias=True)
