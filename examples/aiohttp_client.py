from kubex.api import Api
from kubex.client import ClientChoise, create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    client = await create_client(client_class=ClientChoise.AIOHTTP)
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)

        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-aiohttp-"),
                spec=PodSpec(
                    containers=[Container(name="nginx", image="nginx:latest")]
                ),
            ),
        )
        assert pod.metadata.name is not None
        print(f"Created pod: {pod.metadata.name}")

        try:
            fetched = await api.get(pod.metadata.name)
            print(f"Fetched pod: {fetched.metadata.name}")
        finally:
            await api.delete(pod.metadata.name)
            print(f"Deleted pod: {pod.metadata.name}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
