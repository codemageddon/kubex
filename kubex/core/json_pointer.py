from __future__ import annotations

import re
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

_INVALID_TILDE_RE = re.compile(r"~(?![01])")


def _escape_token(token: str) -> str:
    """Escape a reference token per RFC 6901 section 3."""
    return token.replace("~", "~0").replace("/", "~1")


def _unescape_token(token: str) -> str:
    """Unescape a reference token per RFC 6901 section 3."""
    return token.replace("~1", "/").replace("~0", "~")


class JsonPointer(str):
    """RFC 6901 JSON Pointer.

    A JSON Pointer is either the empty string (referencing the whole document)
    or a sequence of reference tokens each prefixed by ``/``.

    Construct from a raw string, from individual tokens, or by chaining
    the ``/`` operator::

        ptr = JsonPointer("/foo/0")
        ptr = JsonPointer.from_tokens("foo", 0)
        ptr = JsonPointer() / "foo" / 0
    """

    def __new__(cls, value: str = "") -> JsonPointer:
        if value != "" and not value.startswith("/"):
            msg = f"JSON Pointer must be empty or start with '/': {value!r}"
            raise ValueError(msg)
        if _INVALID_TILDE_RE.search(value):
            msg = f"Invalid escape in JSON Pointer (~ must be followed by 0 or 1): {value!r}"
            raise ValueError(msg)
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.no_info_wrap_validator_function(
            cls._pydantic_validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())

    @classmethod
    def _pydantic_validate(cls, value: Any, handler: Any) -> JsonPointer:
        if isinstance(value, cls):
            return value
        raw = handler(value)
        return cls(raw)

    @classmethod
    def from_tokens(cls, *tokens: str | int) -> JsonPointer:
        """Build a pointer from unescaped reference tokens.

        Tokens are escaped per RFC 6901 (``~`` -> ``~0``, ``/`` -> ``~1``).
        """
        if not tokens:
            return cls("")
        return cls("/" + "/".join(_escape_token(str(t)) for t in tokens))

    def __truediv__(self, token: str | int) -> JsonPointer:
        """Append a reference token: ``ptr / "key" / 0``."""
        return JsonPointer(str(self) + "/" + _escape_token(str(token)))

    @property
    def tokens(self) -> list[str]:
        """Decompose into unescaped reference tokens."""
        if not self:
            return []
        return [_unescape_token(t) for t in str(self)[1:].split("/")]
