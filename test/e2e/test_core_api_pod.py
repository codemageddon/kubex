import pytest

from kubex.api import Api, create_api
from kubex.client import BaseClient
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata


@pytest.mark.anyio
async def test_core_api_pod(client: BaseClient, tmp_namespace_name: str) -> None:
    pod_api: Api[Pod] = await create_api(Pod, client=client)
    pod = await pod_api.create(
        Pod(
            metadata=ObjectMetadata(name="example-pod", namespace=tmp_namespace_name),
            spec=PodSpec(containers=[Container(name="example", image="nginx")]),
        ),
        namespace=tmp_namespace_name,
    )
    assert pod.metadata.name == "example-pod"
    assert pod.metadata.namespace == tmp_namespace_name
