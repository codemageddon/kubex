from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)

        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(
                    name="example-replace-pod",
                    labels={"app": "example"},
                ),
                spec=PodSpec(
                    containers=[Container(name="nginx", image="nginx:latest")]
                ),
            ),
        )
        name = cast(str, pod.metadata.name)

        try:
            # Get → modify → replace pattern
            current = await api.get(name)
            current.metadata.labels = {
                **(current.metadata.labels or {}),
                "env": "staging",
            }
            updated = await api.replace(name, current)
            print(f"Labels after replace: {updated.metadata.labels}")
        finally:
            await api.delete(name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
