"""Tests for hand-written kubex-core models: unknown-field round-trips,
metadata, Scale and Status."""

from __future__ import annotations

import datetime
import json
from typing import Any

from kubex_core.models.base import BaseK8sModel
from kubex_core.models.metadata import ListMetadata, ManagedFieldsEntry, ObjectMetadata
from kubex_core.models.partial_object_meta import PartialObjectMetadata
from kubex_core.models.scale import Scale, ScaleSpec
from kubex_core.models.status import Status


class _Spec(BaseK8sModel):
    size: int | None = None


class _Thing(BaseK8sModel):
    api_version: str | None = None
    spec: _Spec | None = None


def test_unknown_fields_round_trip_with_wire_keys() -> None:
    raw: dict[str, Any] = {
        "apiVersion": "example.io/v1",
        "futureTopLevel": {"nested": [1, 2]},
        "spec": {"size": 1, "futureSpecField": "x", "podIP": "10.0.0.1"},
    }
    thing = _Thing.model_validate(raw)
    assert thing.spec is not None
    assert thing.spec.size == 1
    # As Api.create/replace serialize request bodies.
    assert json.loads(thing.model_dump_json(by_alias=True, exclude_none=True)) == raw
    assert thing.model_dump(by_alias=True, exclude_none=True) == raw


def test_unknown_fields_survive_modification() -> None:
    thing = _Thing.model_validate({"spec": {"size": 1, "color": "red"}})
    assert thing.spec is not None
    thing.spec.size = 2
    assert thing.model_dump(by_alias=True, exclude_none=True) == {
        "spec": {"size": 2, "color": "red"}
    }


def test_unknown_null_fields_follow_exclude_none() -> None:
    thing = _Thing.model_validate({"futureField": None})
    assert thing.model_dump(by_alias=True, exclude_none=True) == {}
    assert thing.model_dump(by_alias=True) == {
        "apiVersion": None,
        "spec": None,
        "futureField": None,
    }


def test_object_metadata_managed_fields_and_self_link() -> None:
    raw: dict[str, Any] = {
        "name": "p",
        "creationTimestamp": "2024-05-01T10:00:00Z",
        "selfLink": "/api/v1/namespaces/default/pods/p",
        "managedFields": [
            {
                "manager": "kubectl",
                "operation": "Update",
                "apiVersion": "v1",
                "time": "2024-05-01T10:00:00Z",
                "fieldsType": "FieldsV1",
                "fieldsV1": {"f:spec": {"f:containers": {}}},
                "subresource": "status",
            }
        ],
    }
    meta = ObjectMetadata.model_validate(raw)
    assert meta.self_link == "/api/v1/namespaces/default/pods/p"
    assert meta.managed_fields is not None
    entry = meta.managed_fields[0]
    assert isinstance(entry, ManagedFieldsEntry)
    assert entry.fields_v1 == {"f:spec": {"f:containers": {}}}
    assert entry.time == datetime.datetime(2024, 5, 1, 10, tzinfo=datetime.timezone.utc)
    assert meta.model_extra == {}
    assert json.loads(meta.model_dump_json(by_alias=True, exclude_none=True)) == raw


def test_object_metadata_timestamps_serialize_like_metav1_time() -> None:
    meta = ObjectMetadata(
        name="p",
        creation_timestamp=datetime.datetime(2024, 5, 1, 10, 0, 0, 999),
        deletion_timestamp=datetime.datetime(
            2024, 5, 1, 12, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        ),
    )
    assert meta.model_dump(mode="json", by_alias=True, exclude_none=True) == {
        "name": "p",
        "creationTimestamp": "2024-05-01T10:00:00Z",
        "deletionTimestamp": "2024-05-01T10:00:00Z",
    }


def test_list_metadata_shard_info() -> None:
    meta = ListMetadata.model_validate(
        {"resourceVersion": "1", "shardInfo": {"selector": "shard=1"}}
    )
    assert meta.shard_info is not None
    assert meta.shard_info.selector == "shard=1"


def test_partial_object_metadata_keeps_unknown_metadata() -> None:
    obj = PartialObjectMetadata.model_validate(
        {"metadata": {"name": "x", "futureMetaField": 1}}
    )
    dumped = obj.model_dump(by_alias=True, exclude_none=True)
    assert dumped["metadata"] == {"name": "x", "futureMetaField": 1}


def test_scale_at_zero_replicas() -> None:
    # The API server omits `replicas: 0` (omitempty), sending `spec: {}`.
    scale = Scale.model_validate_json(
        '{"kind":"Scale","apiVersion":"autoscaling/v1",'
        '"metadata":{"name":"d","namespace":"default"},'
        '"spec":{},"status":{"replicas":0,"selector":"app=x"}}'
    )
    assert scale.spec.replicas == 0
    assert scale.status is not None
    assert scale.status.replicas == 0
    status_only = Scale.model_validate(
        {"metadata": {"name": "d"}, "status": {"selector": "app=x"}}
    )
    assert status_only.spec == ScaleSpec(replicas=0)
    assert status_only.status is not None
    assert status_only.status.replicas == 0


def test_scale_replace_body_carries_zero() -> None:
    scale = Scale(metadata=ObjectMetadata(name="d"), spec=ScaleSpec(replicas=0))
    body = json.loads(scale.model_dump_json(by_alias=True, exclude_none=True))
    assert body["spec"] == {"replicas": 0}


def test_status_without_metadata() -> None:
    # Exec error-channel frames and many error bodies carry no metadata.
    status = Status.model_validate_json('{"status":"Success"}')
    assert status.status == "Success"
    assert status.metadata == ObjectMetadata()
    failure = Status.model_validate(
        {
            "metadata": {},
            "status": "Failure",
            "reason": "NonZeroExitCode",
            "details": {"causes": [{"reason": "ExitCode", "message": "2"}]},
        }
    )
    assert failure.details is not None
    assert failure.details.causes is not None
    assert failure.details.causes[0].message == "2"


def test_status_list_metadata_fields_are_kept() -> None:
    status = Status.model_validate(
        {
            "kind": "Status",
            "apiVersion": "v1",
            "metadata": {"resourceVersion": "5", "continue": "tok"},
            "status": "Failure",
            "code": 410,
        }
    )
    assert status.metadata.resource_version == "5"
    assert status.metadata.model_extra == {"continue": "tok"}
