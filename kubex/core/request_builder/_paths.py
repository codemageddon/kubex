"""URL path helpers shared by every request builder.

`ResourceConfig.url()` interpolates the namespace and name verbatim, so every
builder method goes through `collection_url()` / `object_url()` instead of
calling it directly. That is the single place where a name or namespace is
validated and percent-encoded: a missing name would otherwise silently turn a
single-object request into a collection request (`DELETE` of the collection
URL is DELETECOLLECTION), and an unescaped `../`, `#` or `?` would address a
different object than the one asked for.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from kubex_core.models.resource_config import ResourceConfig

# Mirrors client-go's `path.IsValidPathSegmentName`.
_NAME_MAY_NOT_BE = (".", "..")
_NAME_MAY_NOT_CONTAIN = ("/", "%")


def path_segment(value: object, what: str) -> str:
    """Validate `value` as a single URL path segment and percent-encode it.

    Raises `ValueError` for `None`, `""`, `"."`, `".."` and anything containing
    `/` or `%` (same rules as client-go), `TypeError` for non-strings.
    """
    if value is None or value == "":
        raise ValueError(f"{what} may not be empty")
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str, got {type(value).__name__}")
    if value in _NAME_MAY_NOT_BE:
        raise ValueError(f"invalid {what} {value!r}: may not be {value!r}")
    illegal = [c for c in _NAME_MAY_NOT_CONTAIN if c in value]
    if illegal:
        raise ValueError(
            f"invalid {what} {value!r}: may not contain "
            + " or ".join(repr(c) for c in illegal)
        )
    return quote(value, safe="")


def _namespace_segment(namespace: str | None) -> str | None:
    if namespace is None:
        return None
    return path_segment(namespace, "namespace")


def collection_url(config: ResourceConfig[Any], namespace: str | None) -> str:
    """URL of a resource collection (list, watch, create, delete_collection)."""
    return config.url(_namespace_segment(namespace))


def object_url(
    config: ResourceConfig[Any],
    namespace: str | None,
    name: str | None,
    subresource: str | None = None,
) -> str:
    """URL of a single named object, optionally of one of its subresources.

    The name is mandatory: `None`/`""` raises `ValueError` instead of falling
    back to the collection URL.
    """
    url = config.url(_namespace_segment(namespace), path_segment(name, "resource name"))
    if subresource is not None:
        url = f"{url}/{path_segment(subresource, 'subresource')}"
    return url
