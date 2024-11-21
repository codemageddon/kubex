import pytest

from kubex import Api, Client, create_api
from kubex.models.metadata import ObjectMetadata
from kubex.models.pod import Pod


@pytest.mark.anyio
async def test_core_api_pod(client: Client, tmp_namespace_name: str) -> None:
    pod_api: Api[Pod] = await create_api(Pod, client=client)
    pod = await pod_api.create(
        Pod(
            metadata=ObjectMetadata(name="example-pod", namespace=tmp_namespace_name),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
        namespace=tmp_namespace_name,
    )
    assert pod.metadata.name == "example-pod"
    assert pod.metadata.namespace == tmp_namespace_name
