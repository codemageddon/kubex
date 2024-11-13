import asyncio
from typing import cast

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
    pod_name = cast(str, pod.metadata.name)
    await asyncio.sleep(5)
    try:
        logs = await api.logs(pod_name)
        print(logs)
        async for line in api.stream_logs(pod_name):
            print(line)
    finally:
        await api.delete(pod_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
