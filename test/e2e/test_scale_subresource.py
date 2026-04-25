from __future__ import annotations

import pytest

from kubex.api import Api
from kubex.client import BaseClient
from kubex.core.exceptions import Conflict
from kubex.core.patch import MergePatch
from kubex.k8s.v1_35.apps.v1.deployment import Deployment
from kubex.k8s.v1_35.apps.v1.deployment_spec import DeploymentSpec
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex.k8s.v1_35.core.v1.pod_template_spec import PodTemplateSpec
from kubex.k8s.v1_35.meta.v1.label_selector import LabelSelector
from kubex_core.models.metadata import ObjectMetadata
from kubex_core.models.scale import Scale, ScaleSpec


def _deployment(name: str, namespace: str, replicas: int = 1) -> Deployment:
    return Deployment(
        metadata=ObjectMetadata(name=name, namespace=namespace, labels={"app": name}),
        spec=DeploymentSpec(
            replicas=replicas,
            selector=LabelSelector(match_labels={"app": name}),
            template=PodTemplateSpec(
                metadata=ObjectMetadata(labels={"app": name}),
                spec=PodSpec(
                    containers=[Container(name="nginx", image="nginx:latest")],
                ),
            ),
        ),
    )


@pytest.mark.anyio
async def test_scale_replace(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Deployment] = Api(Deployment, client=client, namespace=tmp_namespace_name)
    await api.create(_deployment("scale-replace", tmp_namespace_name, replicas=1))

    for _ in range(5):
        current = await api.scale.get("scale-replace")
        assert isinstance(current, Scale)
        assert current.spec.replicas in (1, 3)

        current.spec = ScaleSpec(replicas=3)
        try:
            updated = await api.scale.replace("scale-replace", current)
            break
        except Conflict:
            continue
    else:
        raise AssertionError(
            "scale.replace kept returning 409 Conflict after 5 retries"
        )
    assert isinstance(updated, Scale)
    assert updated.spec.replicas == 3

    confirmed = await api.scale.get("scale-replace")
    assert confirmed.spec.replicas == 3


@pytest.mark.anyio
async def test_scale_patch(client: BaseClient, tmp_namespace_name: str) -> None:
    api: Api[Deployment] = Api(Deployment, client=client, namespace=tmp_namespace_name)
    await api.create(_deployment("scale-patch", tmp_namespace_name, replicas=1))

    patch = MergePatch(Scale.model_validate({"metadata": {}, "spec": {"replicas": 5}}))
    result = await api.scale.patch("scale-patch", patch)
    assert isinstance(result, Scale)
    assert result.spec.replicas == 5

    confirmed = await api.scale.get("scale-patch")
    assert confirmed.spec.replicas == 5
