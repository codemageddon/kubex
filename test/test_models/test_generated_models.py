"""Generated-model behaviour against payloads the API server actually sends."""

from __future__ import annotations

import datetime
import json
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from kubex.k8s.v1_35.apiextensions_k8s_io.v1.custom_resource_definition import (
    CustomResourceDefinition,
)
from kubex.k8s.v1_35.apiextensions_k8s_io.v1.json_schema_props import JSONSchemaProps
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.authorization.v1.self_subject_rules_review import (
    SelfSubjectRulesReview,
)
from kubex.k8s.v1_35.certificates.v1.certificate_signing_request import (
    CertificateSigningRequest,
)
from kubex.k8s.v1_35.coordination.v1.lease import Lease
from kubex.k8s.v1_35.discovery.v1.endpoint_slice import EndpointSlice
from kubex.k8s.v1_35.discovery.v1.endpoint_slice_list import EndpointSliceList
from kubex.k8s.v1_35.events.v1.event import Event
from kubex.k8s.v1_35.meta.v1.condition import Condition
from kubex.k8s.v1_35.storage.v1.csi_node import CSINode


def test_endpoint_slice_with_null_endpoints() -> None:
    # A Service with no ready endpoints gets `endpoints: null`.
    raw = {
        "apiVersion": "discovery.k8s.io/v1",
        "kind": "EndpointSliceList",
        "metadata": {"resourceVersion": "1"},
        "items": [
            {
                "metadata": {"name": "empty-p2mpl", "namespace": "default"},
                "addressType": "IPv4",
                "endpoints": None,
                "ports": None,
            }
        ],
    }
    listed = EndpointSliceList.model_validate_json(json.dumps(raw))
    assert listed.items[0].endpoints == []
    assert listed.items[0].ports is None
    with pytest.raises(ValidationError):
        # Still required: a missing key is not silently defaulted.
        EndpointSlice.model_validate({"metadata": {}, "addressType": "IPv4"})


def test_csi_node_with_null_drivers() -> None:
    node = CSINode.model_validate(
        {"metadata": {"name": "n1"}, "spec": {"drivers": None}}
    )
    assert node.spec.drivers == []


def test_events_v1_event_with_null_event_time() -> None:
    event = Event.model_validate(
        {
            "metadata": {"name": "e", "namespace": "default"},
            "eventTime": None,
            "reason": "Started",
            "deprecatedFirstTimestamp": "2024-05-01T10:00:00Z",
        }
    )
    assert event.event_time is None
    assert event.deprecated_first_timestamp == datetime.datetime(
        2024, 5, 1, 10, tzinfo=datetime.timezone.utc
    )
    with pytest.raises(ValidationError):
        # Required (may be null, but must be present).
        Event.model_validate({"metadata": {}})


def test_meta_condition_with_null_last_transition_time() -> None:
    condition = Condition.model_validate(
        {
            "type": "Ready",
            "status": "True",
            "reason": "R",
            "message": "",
            "lastTransitionTime": None,
        }
    )
    assert condition.last_transition_time is None


def test_csr_with_null_request_bytes() -> None:
    csr = CertificateSigningRequest.model_validate(
        {"metadata": {"name": "c"}, "spec": {"request": None, "signerName": "x"}}
    )
    assert csr.spec.request is None


def test_self_subject_rules_review_with_null_rules() -> None:
    review = SelfSubjectRulesReview.model_validate(
        {
            "metadata": {},
            "spec": {"namespace": "default"},
            "status": {
                "resourceRules": None,
                "nonResourceRules": None,
                "incomplete": False,
            },
        }
    )
    assert review.status is not None
    assert review.status.resource_rules == []
    assert review.status.non_resource_rules == []


def test_lease_micro_time_wire_format() -> None:
    lease = Lease.model_validate(
        {
            "metadata": {"name": "l0"},
            "spec": {"holderIdentity": "me", "renewTime": "2024-05-01T10:00:00Z"},
        }
    )
    body = json.loads(lease.model_dump_json(by_alias=True, exclude_none=True))
    assert body["spec"]["renewTime"] == "2024-05-01T10:00:00.000000Z"
    naive = Lease.model_validate(
        {
            "metadata": {"name": "l1"},
            "spec": {"renewTime": datetime.datetime(2024, 5, 1, 10, 0, 0, 5)},
        }
    )
    body = naive.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert body["spec"]["renewTime"] == "2024-05-01T10:00:00.000005Z"


def test_deployment_manifest_with_numeric_quantities() -> None:
    manifest = """
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
      - name: web
        image: nginx
        resources:
          limits: {cpu: 1, nvidia.com/gpu: 1, memory: 512Mi}
          requests: {cpu: 0.5}
"""
    deployment = Deployment.model_validate(yaml.safe_load(manifest))
    assert deployment.spec is not None
    resources = deployment.spec.template.spec
    assert resources is not None
    container_resources = resources.containers[0].resources
    assert container_resources is not None
    assert container_resources.limits == {
        "cpu": "1",
        "nvidia.com/gpu": "1",
        "memory": "512Mi",
    }
    assert container_resources.requests == {"cpu": "0.5"}


def _crd(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "apiVersion": "apiextensions.k8s.io/v1",
        "kind": "CustomResourceDefinition",
        "metadata": {"name": "widgets.example.io"},
        "spec": {
            "group": "example.io",
            "scope": "Namespaced",
            "names": {
                "plural": "widgets",
                "singular": "widget",
                "kind": "Widget",
                "listKind": "WidgetList",
            },
            "versions": [
                {
                    "name": "v1",
                    "served": True,
                    "storage": True,
                    "schema": {"openAPIV3Schema": schema},
                }
            ],
        },
    }


def test_crd_schema_round_trip() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "x-kubernetes-preserve-unknown-fields": True,
        "properties": {
            "spec": {
                "type": "object",
                "required": ["mode"],
                "properties": {
                    "mode": {"type": "string", "enum": ["a", "b"], "default": "a"},
                    "replicas": {"type": "integer", "default": 1, "minimum": 0},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 5},
                    },
                    "pairs": {
                        "type": "array",
                        "items": [{"type": "string"}, {"type": "integer"}],
                    },
                    "labels": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    "anything": {"type": "object", "additionalProperties": True},
                    "closed": {"type": "object", "additionalProperties": False},
                    "cfg": {"type": "object", "default": {"x": 1, "y": [None, "z"]}},
                    "strategy": {
                        "type": "string",
                        "x-kubernetes-validations": [{"rule": "self != ''"}],
                    },
                },
                "dependencies": {"replicas": ["mode"], "tags": {"required": ["mode"]}},
            }
        },
    }
    crd = CustomResourceDefinition.model_validate_json(json.dumps(_crd(schema)))
    open_api = crd.spec.versions[0].schema_
    assert open_api is not None
    root = open_api.open_apiv_3_schema
    assert root is not None and root.properties is not None
    spec = root.properties["spec"]
    assert spec.properties is not None
    tags_items = spec.properties["tags"].items
    assert isinstance(tags_items, JSONSchemaProps)
    assert tags_items.max_length == 5
    assert isinstance(spec.properties["pairs"].items, list)
    assert spec.properties["anything"].additional_properties is True
    assert spec.properties["closed"].additional_properties is False
    assert isinstance(spec.properties["labels"].additional_properties, JSONSchemaProps)
    assert spec.properties["mode"].enum == ["a", "b"]
    assert spec.properties["cfg"].default == {"x": 1, "y": [None, "z"]}
    dumped = json.loads(crd.model_dump_json(by_alias=True, exclude_none=True))
    round_tripped = dumped["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
    # `minimum` is a float64 in Go; 0 and 0.0 are the same JSON number.
    assert round_tripped == schema


def test_crd_default_with_scalar_value() -> None:
    # A K3S built-in CRD (helmcharts) carries `default: "reinstall"`.
    crd = CustomResourceDefinition.model_validate(
        _crd(
            {
                "type": "object",
                "properties": {
                    "failurePolicy": {"type": "string", "default": "reinstall"}
                },
            }
        )
    )
    open_api = crd.spec.versions[0].schema_
    assert open_api is not None and open_api.open_apiv_3_schema is not None
    props = open_api.open_apiv_3_schema.properties
    assert props is not None
    assert props["failurePolicy"].default == "reinstall"
