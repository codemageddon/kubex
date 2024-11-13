from kubex import Api
from kubex.models.base import ObjectMetadata
from kubex.models.pod import Pod


async def main() -> None:
    api: Api[Pod] = Api.namespaced(Pod, namespace="default")
    pod = await api.create(
        Pod(
            metadata=ObjectMetadata(generate_name="example-pod-"),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
    )
    assert pod.metadata.name is not None
    print(pod)
    await api.delete(pod.metadata.name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
