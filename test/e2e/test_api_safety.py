"""E2E checks for request-shape fixes: empty names never reach the server,
dry-run deletes are accepted, names are escaped, and server-side apply works."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.patch import ApplyPatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_condition import DeploymentCondition
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.apps.v1.deployment_status import DeploymentStatus
from kubex.k8s.v1_35.core.v1.config_map import ConfigMap
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex.k8s.v1_35.rbac.v1.cluster_role import ClusterRole
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.partial_object_meta import PartialObjectMetadata

pytestmark = pytest.mark.anyio


async def _names(api: Api[ConfigMap]) -> set[str]:
    return {cm.metadata.name for cm in (await api.list()).items if cm.metadata.name}


async def test_empty_name_never_deletes_the_collection(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    for name in ("keep-1", "keep-2"):
        await api.create(ConfigMap(metadata=ObjectMetadata(name=name)))
    unnamed = ConfigMap(metadata=ObjectMetadata(generate_name="tmp-"))
    await api.create(unnamed)  # the local object never learns its name

    empty_names: list[str | None] = [unnamed.metadata.name, ""]
    for empty in empty_names:
        with pytest.raises(ValueError, match="resource name may not be empty"):
            await api.delete(empty)  # type: ignore[arg-type]
    assert {"keep-1", "keep-2"} <= await _names(api)


async def test_dry_run_delete(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    await api.create(ConfigMap(metadata=ObjectMetadata(name="cm")))
    await api.delete("cm", dry_run=True)
    await api.delete_collection(dry_run=True)
    assert "cm" in await _names(api)


async def test_name_with_reserved_characters_is_escaped(client: BaseClient) -> None:
    # ClusterRole names are only path-segment validated, so `#`/`?` are legal.
    api: Api[ClusterRole] = Api(ClusterRole, client=client)
    suffix = uuid.uuid4().hex[:8]
    for name in (f"kubex#{suffix}", f"kubex?{suffix}"):
        await api.create(ClusterRole(metadata=ObjectMetadata(name=name)))
        try:
            assert (await api.get(name)).metadata.name == name
        finally:
            await api.delete(name)


async def test_server_side_apply(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[ConfigMap] = Api(ConfigMap, client=client, namespace=tmp_namespace_name)
    # SSA creates the object when it does not exist.
    created = await api.patch(
        "cm",
        ApplyPatch(ConfigMap(metadata=ObjectMetadata(name="cm"), data={"a": "1"})),
        field_manager="kubex-e2e",
        force=True,
    )
    assert created.data == {"a": "1"}

    # A fetched object (managedFields, creationTimestamp, ...) applies back as is.
    current = await api.get("cm")
    current.data = {"a": "2"}
    updated = await api.patch(
        "cm", ApplyPatch(current), field_manager="kubex-e2e", force=True
    )
    assert updated.data == {"a": "2"}

    meta = await api.metadata.patch(
        "cm",
        ApplyPatch(
            PartialObjectMetadata(metadata=ObjectMetadata(labels={"managed": "yes"}))
        ),
        field_manager="kubex-e2e-meta",
        force=True,
    )
    assert (meta.metadata.labels or {}).get("managed") == "yes"


async def test_server_side_apply_status_condition(
    client: BaseClient, tmp_namespace_name: str
) -> None:
    api: Api[Deployment] = Api(Deployment, client=client, namespace=tmp_namespace_name)
    labels = {"app": "ssa"}
    await api.patch(
        "ssa",
        ApplyPatch(
            Deployment(
                metadata=ObjectMetadata(name="ssa"),
                spec=DeploymentSpec(
                    replicas=0,
                    selector=LabelSelector(match_labels=labels),
                    template=PodTemplateSpec(
                        metadata=ObjectMetadata(labels=labels),
                        spec=PodSpec(containers=[Container(name="c", image="nginx")]),
                    ),
                ),
            )
        ),
        field_manager="kubex-e2e",
        force=True,
    )
    updated = await api.status.patch(
        "ssa",
        ApplyPatch(
            Deployment(
                metadata=ObjectMetadata(name="ssa"),
                status=DeploymentStatus(
                    conditions=[
                        DeploymentCondition(
                            type_="KubexReady",
                            status="True",
                            last_transition_time=datetime.now(timezone.utc),
                        )
                    ]
                ),
            )
        ),
        field_manager="kubex-e2e",
        force=True,
    )
    conditions = {
        c.type_: c for c in (updated.status and updated.status.conditions) or []
    }
    assert conditions["KubexReady"].status == "True"
    assert conditions["KubexReady"].last_transition_time is not None
