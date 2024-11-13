import asyncio
from contextlib import suppress
from typing import cast

from kubex import Api
from kubex.core.params import WatchOptions
from kubex.models.metadata import ObjectMetadata
from kubex.models.pod import Pod


async def watcher() -> None:
    api: Api[Pod] = Api.all(Pod)
    async for event in api.watch(WatchOptions(allow_bookmarks=True)):
        print(event)


async def main() -> None:
    _watcher = asyncio.create_task(watcher())
    api: Api[Pod] = Api.namespaced(Pod, namespace="default")
    _pod = await api.create(
        Pod(
            metadata=ObjectMetadata(generate_name="example-pod-"),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
    )
    pod_name = cast(str, _pod.metadata.name)

    print(await api.delete(pod_name))
    _watcher.cancel()
    with suppress(asyncio.CancelledError):
        await _watcher


if __name__ == "__main__":
    asyncio.run(main())
