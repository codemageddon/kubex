import asyncio
from typing import cast

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-pod-"),
                spec=PodSpec(containers=[Container(name="example", image="nginx")]),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        await asyncio.sleep(5)

        async def _consume_log_stream() -> None:
            async for line in api.logs.stream(pod_name):
                print(line)

        try:
            logs = await api.logs.get(pod_name)
            print(logs)
            # stream() uses follow=true, so the loop runs until the pod
            # terminates or the timeout fires.  We cap it here so the
            # example always reaches cleanup.
            await asyncio.wait_for(_consume_log_stream(), timeout=10)
        except asyncio.TimeoutError:
            pass
        finally:
            await api.delete(pod_name)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
