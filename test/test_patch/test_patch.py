from __future__ import annotations

import json

from pydantic import BaseModel

from kubex.core.patch import ApplyPatch, MergePatch, StrategicMergePatch


class _Spec(BaseModel):
    replicas: int | None = None
    name: str | None = None


class _Resource(BaseModel):
    spec: _Spec | None = None


def test_merge_patch_default_preserves_explicit_null() -> None:
    """RFC 7396: an explicit null must reach the server to delete the field."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(patch.serialize(by_alias=True, exclude_unset=True))
    assert result == {"spec": {"replicas": None}}


def test_merge_patch_no_args_default_preserves_explicit_null() -> None:
    """patch_subresource()/patch_metadata() call serialize() with no arguments."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(patch.serialize())
    assert result == {"spec": {"replicas": None}}


def test_merge_patch_omitted_field_still_excluded() -> None:
    """A field the caller never touched stays distinguishable from an explicit null."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=5)))
    result = json.loads(patch.serialize(by_alias=True, exclude_unset=True))
    assert result == {"spec": {"replicas": 5}}
    assert "name" not in result["spec"]


def test_merge_patch_explicit_exclude_none_true_still_available() -> None:
    """Callers can still opt back into the old (null-dropping) behavior explicitly."""
    patch = MergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(
        patch.serialize(by_alias=True, exclude_unset=True, exclude_none=True)
    )
    assert result == {"spec": {}}


def test_strategic_merge_patch_default_preserves_explicit_null() -> None:
    patch = StrategicMergePatch(_Resource(spec=_Spec(replicas=None)))
    result = json.loads(patch.serialize(by_alias=True, exclude_unset=True))
    assert result == {"spec": {"replicas": None}}


def test_apply_patch_default_still_drops_none() -> None:
    """ApplyPatch intentionally keeps exclude_none=True (SSA has no null-delete convention)."""
    patch = ApplyPatch(_Resource(spec=_Spec(replicas=None)))
    result = patch.serialize(by_alias=True, exclude_unset=True)
    assert "replicas" not in result


# --- ApplyPatch serialization ---------------------------------------------


def test_apply_patch_includes_defaulted_api_version_and_kind() -> None:
    """exclude_unset would drop the defaulted apiVersion/kind; the server needs them."""
    from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
    from kubex_core.models.metadata import ObjectMetadata

    body = ApplyPatch(
        ConfigMap(metadata=ObjectMetadata(name="cm"), data={"k": "v"})
    ).serialize()
    assert json.loads(body) == {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "cm"},
        "data": {"k": "v"},
    }
    # apiVersion/kind lead the document, like a hand-written manifest.
    assert body.startswith('{"apiVersion": "v1", "kind": "ConfigMap"')


def test_apply_patch_serializes_datetimes_as_rfc3339() -> None:
    from datetime import datetime, timezone

    from kubex.k8s.v1_35.apps.v1.deployment import Deployment
    from kubex.k8s.v1_35.apps.v1.deployment_condition import DeploymentCondition
    from kubex.k8s.v1_35.apps.v1.deployment_status import DeploymentStatus
    from kubex_core.models.metadata import ObjectMetadata

    ts = datetime(2026, 10, 23, 22, 18, tzinfo=timezone.utc)
    body = ApplyPatch(
        Deployment(
            metadata=ObjectMetadata(name="d"),
            status=DeploymentStatus(
                conditions=[
                    DeploymentCondition(
                        type_="Ready", status="True", last_transition_time=ts
                    )
                ]
            ),
        )
    ).serialize()
    data = json.loads(body)
    assert data["apiVersion"] == "apps/v1"
    assert data["kind"] == "Deployment"
    (condition,) = data["status"]["conditions"]
    assert condition["type"] == "Ready"
    # JSON-mode datetime, not YAML's "2026-10-23 22:18:00+00:00".
    assert condition["lastTransitionTime"].startswith("2026-10-23T22:18:00")


def test_apply_patch_explicit_type_overrides_body() -> None:
    from kubex_core.models.metadata import ObjectMetadata
    from kubex_core.models.partial_object_meta import PartialObjectMetadata

    patch = ApplyPatch(
        PartialObjectMetadata(metadata=ObjectMetadata(labels={"a": "b"}))
    )
    assert json.loads(patch.serialize()) == {
        "apiVersion": "meta.k8s.io/v1",
        "kind": "PartialObjectMetadata",
        "metadata": {"labels": {"a": "b"}},
    }
    assert json.loads(patch.serialize(api_version="apps/v1", kind="Deployment")) == {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"labels": {"a": "b"}},
    }


def test_apply_patch_drops_managed_fields() -> None:
    """A fetched object can be applied back: managedFields must be nil in SSA."""
    from kubex.k8s.v1_35.core.v1.config_map import ConfigMap

    cm = ConfigMap.model_validate(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "cm",
                "creationTimestamp": "2026-10-23T22:18:00Z",
                "managedFields": [{"manager": "kubectl", "operation": "Apply"}],
            },
            "data": {"a": "1"},
        }
    )
    data = json.loads(ApplyPatch(cm).serialize())
    assert "managedFields" not in data["metadata"]
    assert data["metadata"]["creationTimestamp"].startswith("2026-10-23T22:18:00")


def test_apply_patch_plain_model_without_resource_config() -> None:
    """No apiVersion/kind is invented for a model that has none."""
    patch = ApplyPatch(_Resource(spec=_Spec(replicas=2)))
    assert json.loads(patch.serialize()) == {"spec": {"replicas": 2}}


def test_apply_patch_keeps_non_ascii() -> None:
    from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
    from kubex_core.models.metadata import ObjectMetadata

    body = ApplyPatch(
        ConfigMap(metadata=ObjectMetadata(name="cm"), data={"k": "café"})
    ).serialize()
    assert "café" in body
    assert json.loads(body)["data"] == {"k": "café"}
