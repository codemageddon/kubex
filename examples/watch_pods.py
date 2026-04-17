import asyncio
from contextlib import suppress
from typing import cast

from kubex.api import Api, create_api
from kubex.k8s.v1_32.core.v1.container import Container
from kubex.k8s.v1_32.core.v1.pod import Pod
from kubex.k8s.v1_32.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def watcher(pod_api: Api[Pod]) -> None:
    async for event in pod_api.watch(
        allow_bookmarks=True,
        namespace=None,
    ):
        print(event)


async def main() -> None:
    api: Api[Pod] = await create_api(Pod, namespace=NAMESPACE)
    _watcher = asyncio.create_task(watcher(api))
    _pod = await api.create(
        Pod(
            metadata=ObjectMetadata(generate_name="example-pod-"),
            spec=PodSpec(containers=[Container(name="example", image="nginx")]),
        ),
    )
    pod_name = cast(str, _pod.metadata.name)

    print(await api.delete(pod_name))
    _watcher.cancel()
    with suppress(asyncio.CancelledError):
        await _watcher


if __name__ == "__main__":
    asyncio.run(main())
