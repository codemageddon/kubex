"""Acronym-aware camelCase <-> snake_case conversion for K8s field names.

The two-step regex used by Pydantic's `to_snake` is insufficient: it turns
`podIPs` into `pod_i_ps`. This module uses a single-regex word splitter that
handles leading, trailing, and plural acronyms correctly.
"""

from __future__ import annotations

import keyword
import re

_WORD = re.compile(
    r"""
    [A-Z]+s(?=[A-Z]|$)          # plural acronym followed by next word or end: IPs, URLs
  | [A-Z]+(?=[A-Z][a-z])        # leading acronym before a capitalized word: HTTPS in HTTPSProxy
  | [A-Z]?[a-z0-9]+             # normal word, optionally starting with one capital
  | [A-Z]+                      # trailing all-caps acronym: API, IP
    """,
    re.VERBOSE,
)

_RESERVED_EXTRAS: frozenset[str] = frozenset(
    {
        # Soft keywords / common attribute clashes we don't want to shadow.
        "class",
        "continue",
        "global",
        "type",
        "from",
        "import",
        "match",
        "case",
        # Pydantic BaseModel has a deprecated `schema()` classmethod that
        # clashes with the K8s `$schema` / `schema` JSON properties.
        "schema",
    }
)


def camel_to_snake(name: str) -> str:
    """Convert a K8s camelCase/PascalCase field name to snake_case."""
    return "_".join(m.group(0).lower() for m in _WORD.finditer(name))


def py_field_name(name: str) -> str:
    """Turn a JSON/schema field name into a valid Python attribute name."""
    snake = camel_to_snake(name)
    if keyword.iskeyword(snake) or snake in _RESERVED_EXTRAS:
        snake += "_"
    return snake


def screaming_snake(value: str) -> str:
    """Turn an enum string value into a Python-valid SCREAMING_SNAKE_CASE member name.

    Non-identifier characters collapse to `_`; if the result begins with a digit,
    it's prefixed with `_` so the final name stays a valid identifier.
    """
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_")
    if not cleaned:
        return "_"
    snake = camel_to_snake(cleaned).upper()
    if snake and snake[0].isdigit():
        snake = "_" + snake
    return snake


def class_name_for_enum(definition_short: str, property_name: str) -> str:
    """Stable PascalCase name for a generated enum.

    Example: ContainerStateWaiting.reason -> ContainerStateWaitingReason.
    """
    return definition_short + _pascal(property_name)


def _pascal(name: str) -> str:
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", name) if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)
