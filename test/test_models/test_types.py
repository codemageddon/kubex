from __future__ import annotations

import datetime
import decimal
import json
from typing import Any

import pytest
from pydantic import Field, ValidationError

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.types import (
    MicroTime,
    NullAsEmptyDict,
    NullAsEmptyList,
    Quantity,
    Time,
)

UTC = datetime.timezone.utc


class _Times(BaseK8sModel):
    time: Time | None = None
    micro_time: MicroTime | None = None


class _Quantities(BaseK8sModel):
    quantity: Quantity | None = None
    resources: dict[str, Quantity] | None = None


class _Item(BaseK8sModel):
    name: str | None = None


class _Collections(BaseK8sModel):
    items: NullAsEmptyList[_Item] = Field(..., alias="items")
    counters: NullAsEmptyDict[Quantity] = Field(..., alias="counters")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime.datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC), "2024-05-01T10:00:00Z"),
        # Time has second precision on the wire, like metav1.Time.
        (
            datetime.datetime(2024, 5, 1, 10, 0, 0, 123456, tzinfo=UTC),
            "2024-05-01T10:00:00Z",
        ),
        # Naive datetimes are treated as UTC rather than emitted without a zone.
        (datetime.datetime(2024, 5, 1, 10, 0, 0), "2024-05-01T10:00:00Z"),
        # Offsets are converted to UTC.
        (
            datetime.datetime(
                2024,
                5,
                1,
                12,
                0,
                0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
            ),
            "2024-05-01T10:00:00Z",
        ),
    ],
)
def test_time_serializes_as_rfc3339_utc(
    value: datetime.datetime, expected: str
) -> None:
    model = _Times(time=value)
    assert model.model_dump(mode="json", exclude_none=True) == {"time": expected}
    assert json.loads(model.model_dump_json(exclude_none=True)) == {"time": expected}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Zero microseconds must still carry the `.000000` fraction: the API
        # server parses MicroTime with a fixed `2006-01-02T15:04:05.000000Z07:00`
        # layout.
        (
            datetime.datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC),
            "2024-05-01T10:00:00.000000Z",
        ),
        (
            datetime.datetime(2024, 5, 1, 10, 0, 0, 5, tzinfo=UTC),
            "2024-05-01T10:00:00.000005Z",
        ),
        (datetime.datetime(2024, 5, 1, 10, 0, 0, 5), "2024-05-01T10:00:00.000005Z"),
        (
            datetime.datetime(
                2024,
                5,
                1,
                4,
                30,
                0,
                1,
                tzinfo=datetime.timezone(-datetime.timedelta(hours=5, minutes=30)),
            ),
            "2024-05-01T10:00:00.000001Z",
        ),
    ],
)
def test_micro_time_always_emits_six_fraction_digits(
    value: datetime.datetime, expected: str
) -> None:
    model = _Times(micro_time=value)
    assert model.model_dump(mode="json", by_alias=True, exclude_none=True) == {
        "microTime": expected
    }
    assert json.loads(model.model_dump_json(by_alias=True, exclude_none=True)) == {
        "microTime": expected
    }


def test_times_parse_server_formats_and_keep_datetimes_in_python_mode() -> None:
    model = _Times.model_validate(
        {"time": "2024-05-01T10:00:00Z", "microTime": "2024-05-01T10:00:00.000000Z"}
    )
    expected = datetime.datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC)
    assert model.time == expected
    assert model.micro_time == expected
    # Python-mode dumps keep datetime objects; only JSON mode formats them.
    dumped = model.model_dump()
    assert dumped == {"time": expected, "micro_time": expected}


def test_times_round_trip_through_json() -> None:
    raw = '{"time":"2024-05-01T10:00:00Z","microTime":"2024-05-01T10:00:00.250000Z"}'
    model = _Times.model_validate_json(raw)
    assert model.model_dump_json(by_alias=True) == raw


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "1"),
        (0.5, "0.5"),
        (decimal.Decimal("1.5"), "1.5"),
        ("500m", "500m"),
        ("1Gi", "1Gi"),
    ],
)
def test_quantity_accepts_numbers(value: Any, expected: str) -> None:
    assert _Quantities(quantity=value).quantity == expected


def test_quantity_map_accepts_yaml_style_numbers() -> None:
    model = _Quantities.model_validate(
        {"resources": {"cpu": 1, "nvidia.com/gpu": 1, "memory": "512Mi", "eph": 0.5}}
    )
    assert model.resources == {
        "cpu": "1",
        "nvidia.com/gpu": "1",
        "memory": "512Mi",
        "eph": "0.5",
    }
    assert model.model_dump(mode="json", exclude_none=True) == {
        "resources": {
            "cpu": "1",
            "nvidia.com/gpu": "1",
            "memory": "512Mi",
            "eph": "0.5",
        }
    }


def test_quantity_rejects_bool() -> None:
    with pytest.raises(ValidationError):
        _Quantities(quantity=True)


def test_null_collections_read_as_empty() -> None:
    model = _Collections.model_validate({"items": None, "counters": None})
    assert model.items == []
    assert model.counters == {}
    assert model.model_dump(by_alias=True) == {"items": [], "counters": {}}


def test_null_collections_still_validate_items() -> None:
    model = _Collections.model_validate(
        {"items": [{"name": "a"}], "counters": {"cpu": 2}}
    )
    assert model.items == [_Item(name="a")]
    assert model.counters == {"cpu": "2"}
    with pytest.raises(ValidationError):
        _Collections.model_validate({"items": "nope", "counters": {}})


def test_null_collections_remain_required() -> None:
    with pytest.raises(ValidationError) as exc_info:
        _Collections.model_validate({"counters": {}})
    assert exc_info.value.errors()[0]["type"] == "missing"
