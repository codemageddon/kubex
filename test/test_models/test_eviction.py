from __future__ import annotations

import json
from typing import Any

import pytest

from kubex_core.models.eviction import DeleteOptions, Eviction
from kubex_core.models.metadata import ObjectMetadata


def test_eviction_minimal_construction() -> None:
    eviction = Eviction()
    assert eviction.api_version == "policy/v1"
    assert eviction.kind == "Eviction"
    assert eviction.metadata is None
    assert eviction.delete_options is None


def test_eviction_with_metadata() -> None:
    eviction = Eviction(metadata=ObjectMetadata(name="my-pod", namespace="default"))
    assert eviction.metadata is not None
    assert eviction.metadata.name == "my-pod"
    assert eviction.metadata.namespace == "default"


def test_eviction_with_delete_options() -> None:
    eviction = Eviction(
        metadata=ObjectMetadata(name="my-pod"),
        delete_options=DeleteOptions(grace_period_seconds=30),
    )
    assert eviction.delete_options is not None
    assert eviction.delete_options.grace_period_seconds == 30


def test_eviction_serialization_camel_case() -> None:
    eviction = Eviction(
        metadata=ObjectMetadata(name="my-pod"),
        delete_options=DeleteOptions(
            grace_period_seconds=10,
            propagation_policy="Foreground",
        ),
    )
    data = json.loads(eviction.model_dump_json(by_alias=True, exclude_none=True))
    assert data["apiVersion"] == "policy/v1"
    assert data["kind"] == "Eviction"
    assert data["metadata"]["name"] == "my-pod"
    assert data["deleteOptions"]["gracePeriodSeconds"] == 10
    assert data["deleteOptions"]["propagationPolicy"] == "Foreground"


def test_eviction_serialization_excludes_none_fields() -> None:
    eviction = Eviction()
    data = eviction.model_dump(by_alias=True, exclude_none=True)
    assert "metadata" not in data
    assert "deleteOptions" not in data
    assert data["apiVersion"] == "policy/v1"
    assert data["kind"] == "Eviction"


def test_eviction_deserialization_from_camel_case() -> None:
    raw = {
        "apiVersion": "policy/v1",
        "kind": "Eviction",
        "metadata": {"name": "pod-1", "namespace": "ns"},
        "deleteOptions": {"gracePeriodSeconds": 60},
    }
    eviction = Eviction.model_validate(raw)
    assert eviction.api_version == "policy/v1"
    assert eviction.kind == "Eviction"
    assert eviction.metadata is not None
    assert eviction.metadata.name == "pod-1"
    assert eviction.delete_options is not None
    assert eviction.delete_options.grace_period_seconds == 60


def test_eviction_api_version_is_literal() -> None:
    eviction = Eviction()
    assert eviction.api_version == "policy/v1"


def test_eviction_kind_is_literal() -> None:
    eviction = Eviction()
    assert eviction.kind == "Eviction"


def test_delete_options_all_fields() -> None:
    opts = DeleteOptions(
        dry_run=["All"],
        grace_period_seconds=0,
        propagation_policy="Background",
    )
    assert opts.dry_run == ["All"]
    assert opts.grace_period_seconds == 0
    assert opts.propagation_policy == "Background"


def test_delete_options_empty() -> None:
    opts = DeleteOptions()
    assert opts.dry_run is None
    assert opts.grace_period_seconds is None
    assert opts.propagation_policy is None


def test_delete_options_serialization_camel_case() -> None:
    opts = DeleteOptions(
        dry_run=["All"],
        grace_period_seconds=30,
        propagation_policy="Orphan",
    )
    data = json.loads(opts.model_dump_json(by_alias=True, exclude_none=True))
    assert data["dryRun"] == ["All"]
    assert data["gracePeriodSeconds"] == 30
    assert data["propagationPolicy"] == "Orphan"


_CONSTRUCTION_CASES: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
    (
        "empty",
        {},
        {"apiVersion": "policy/v1", "kind": "Eviction"},
    ),
    (
        "with-metadata",
        {"metadata": ObjectMetadata(name="p")},
        {"apiVersion": "policy/v1", "kind": "Eviction", "metadata": {"name": "p"}},
    ),
    (
        "with-delete-options",
        {"delete_options": DeleteOptions(grace_period_seconds=5)},
        {
            "apiVersion": "policy/v1",
            "kind": "Eviction",
            "deleteOptions": {"gracePeriodSeconds": 5},
        },
    ),
]


@pytest.mark.parametrize(
    ("_id", "kwargs", "expected"),
    _CONSTRUCTION_CASES,
    ids=[c[0] for c in _CONSTRUCTION_CASES],
)
def test_eviction_construction_and_dump(
    _id: str, kwargs: dict[str, Any], expected: dict[str, Any]
) -> None:
    eviction = Eviction(**kwargs)
    data = eviction.model_dump(by_alias=True, exclude_none=True)
    assert data == expected
