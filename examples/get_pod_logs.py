from kubex.api.api import Api
from kubex.models.pod import Pod


async def main() -> None:
    api: Api[Pod] = Api.namespaced(Pod, namespace="default")
    # pod = await api.create(
    #     Pod(
    #         metadata=NamespaceScopedMetadata(name="example-pod"),
    #         spec={"containers": [{"name": "example", "image": "nginx"}]},
    #     ),
    # )
    logs = await api.logs("example-pod")
    print(logs)
    async for l in api.stream_logs("example-pod"):
        print(l)
    # api.delete("example-pod")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
