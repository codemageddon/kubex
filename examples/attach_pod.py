import asyncio
from typing import cast

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"


async def _wait_for_running(api: Api[Pod], name: str, timeout: int = 120) -> None:
    pod = await api.get(name)
    if pod.status is not None and pod.status.phase == "Running":
        return
    resource_version = pod.metadata.resource_version if pod.metadata else None
    async for event in api.watch(
        field_selector=f"metadata.name={name}",
        resource_version=resource_version,
        timeout_seconds=timeout,
        request_timeout=timeout,
    ):
        obj = event.object
        if (
            isinstance(obj, Pod)
            and obj.status is not None
            and obj.status.phase == "Running"
        ):
            return
    raise TimeoutError(f"Pod {name} did not reach Running within {timeout}s")


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-attach-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="busybox:1.36",
                            command=[
                                "sh",
                                "-c",
                                'while IFS= read -r line; do printf "echo: %s\\n" "$line"; done',
                            ],
                            stdin=True,
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            await _wait_for_running(api, pod_name)

            async with api.attach.stream(
                pod_name,
                stdin=True,
                stdout=True,
            ) as session:
                await session.stdin.write(b"hello\n")

                buf = bytearray()
                with anyio.fail_after(10):
                    async for chunk in session.stdout:
                        buf.extend(chunk)
                        if b"echo: hello" in buf:
                            break
                print("attach output:", bytes(buf).decode(errors="replace"))

                await session.close_stdin()
        finally:
            await api.delete(pod_name)


if __name__ == "__main__":
    asyncio.run(main())
