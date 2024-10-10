from kubex.api.api import Api
from kubex.client.client import Client
from kubex.models.base import NamespaceScopedMetadata
from kubex.models.pod import Pod


async def main() -> None:
    api: Api[Pod] = Api.namespaced(Client(), Pod, namespace="default")
    pod = await api.create(
        Pod(
            metadata=NamespaceScopedMetadata(name="example-pod"),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
    )

    print(pod)
    print(await api.delete("example-pod"))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
