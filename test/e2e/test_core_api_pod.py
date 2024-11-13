import pytest

from kubex import Api, Client
from kubex.models.base import ObjectMetadata
from kubex.models.pod import Pod


@pytest.mark.anyio
async def test_core_api_pod(client: Client, tmp_namespace_name: str) -> None:
    pod_api: Api[Pod] = Api.namespaced(Pod, namespace=tmp_namespace_name, client=client)
    pod = await pod_api.create(
        Pod(
            metadata=ObjectMetadata(name="example-pod", namespace=tmp_namespace_name),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
    )
    assert pod.metadata.name == "example-pod"
    assert pod.metadata.namespace == tmp_namespace_name
