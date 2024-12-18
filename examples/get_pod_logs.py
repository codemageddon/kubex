import asyncio
from typing import cast

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
