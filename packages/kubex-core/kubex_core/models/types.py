"""Reusable annotated field types matching Kubernetes wire semantics.

Use these in hand-written models (e.g. CRDs) the same way the generated
`kubex-k8s-*` models do:

- `Time` / `MicroTime`: `datetime.datetime` fields serialized the way the API
  server expects (`metav1.Time` / `metav1.MicroTime`). Naive datetimes are
  treated as UTC.
- `Quantity`: a `resource.Quantity` string that also accepts the numeric
  values YAML manifests commonly carry (`cpu: 1`, `cpu: 0.5`).
- `NullAsEmptyList[T]` / `NullAsEmptyDict[T]`: required collections that the
  API server may send as `null` (Go nil slices/maps); `null` is read as an
  empty collection.

Serializers only apply in JSON mode (`model_dump(mode="json")`,
`model_dump_json()`); python-mode dumps keep `datetime` objects.
"""

from __future__ import annotations

import datetime
import decimal
from typing import Annotated, Any, TypeVar

from pydantic import BeforeValidator, PlainSerializer

__all__ = [
    "MicroTime",
    "NullAsEmptyDict",
    "NullAsEmptyList",
    "Quantity",
    "Time",
]

_T = TypeVar("_T")


def _as_utc(value: datetime.datetime) -> datetime.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def serialize_time(value: Any) -> Any:
    """Format like `metav1.Time`: RFC 3339, UTC, second precision.

    Non-datetime values (e.g. a string assigned after validation or set via
    `model_construct`) are passed through unchanged.
    """
    if not isinstance(value, datetime.datetime):
        return value
    return _as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def serialize_micro_time(value: Any) -> Any:
    """Format like `metav1.MicroTime`: RFC 3339, UTC, always six fractional digits.

    The API server parses MicroTime with a fixed `.000000` layout, so the
    fraction must be present even when it is zero. Non-datetime values are
    passed through unchanged.
    """
    if not isinstance(value, datetime.datetime):
        return value
    return _as_utc(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _coerce_quantity(value: Any) -> Any:
    # bool is an int subclass, but `cpu: true` is a mistake, not a quantity.
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, decimal.Decimal)):
        return str(value)
    return value


def _none_to_list(value: Any) -> Any:
    return [] if value is None else value


def _none_to_dict(value: Any) -> Any:
    return {} if value is None else value


Time = Annotated[
    datetime.datetime,
    PlainSerializer(serialize_time, return_type=str, when_used="json"),
]
"""`metav1.Time`: emitted as `2006-01-02T15:04:05Z` (UTC, seconds)."""

MicroTime = Annotated[
    datetime.datetime,
    PlainSerializer(serialize_micro_time, return_type=str, when_used="json"),
]
"""`metav1.MicroTime`: emitted as `2006-01-02T15:04:05.000000Z` (UTC, microseconds)."""

Quantity = Annotated[str, BeforeValidator(_coerce_quantity)]
"""`resource.Quantity`: a string; int/float/Decimal inputs are converted to str."""

NullAsEmptyList = Annotated[list[_T], BeforeValidator(_none_to_list)]
"""`list[T]` that reads `null` as `[]`."""

NullAsEmptyDict = Annotated[dict[str, _T], BeforeValidator(_none_to_dict)]
"""`dict[str, T]` that reads `null` as `{}`."""
