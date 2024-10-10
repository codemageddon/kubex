import asyncio
from contextlib import suppress

from kubex.api.api import Api
from kubex.api.params import WatchOptions
from kubex.models.base import NamespaceScopedMetadata
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
            metadata=NamespaceScopedMetadata(name="example-pod"),
            spec={"containers": [{"name": "example", "image": "nginx"}]},
        ),
    )

    await api.delete("example-pod")
    _watcher.cancel()
    with suppress(asyncio.CancelledError):
        await _watcher


if __name__ == "__main__":
    asyncio.run(main())
