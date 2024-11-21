from kubex import Api, create_api
from kubex.models.metadata import ObjectMetadata
from kubex.models.pod import Pod

NAMESPACE = "default"


async def main() -> None:
    api: Api[Pod] = await create_api(Pod, namespace=NAMESPACE)
    pod = await api.create(
        Pod(
            metadata=ObjectMetadata(generate_name="example-pod-"),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
    )
    assert pod.metadata.name is not None
    print(pod)
    print(await api.get_metadata(pod.metadata.name))
    print(await api.list_metadata())
    await api.delete(pod.metadata.name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
