import asyncio
from typing import cast

from kubex.api import Api, create_api
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    api: Api[Pod] = await create_api(Pod, namespace=NAMESPACE)
    pod = await api.create(
        Pod(
            metadata=ObjectMetadata(generate_name="example-pod-"),
            spec=PodSpec(containers=[Container(name="example", image="nginx")]),
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
