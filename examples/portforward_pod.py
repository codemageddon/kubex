import asyncio
from typing import cast

import anyio

from kubex.api import Api
from kubex.client import create_client
from kubex.k8s.v1_35.core.v1.container import Container
from kubex.k8s.v1_35.core.v1.container_port import ContainerPort
from kubex.k8s.v1_35.core.v1.pod import Pod
from kubex.k8s.v1_35.core.v1.pod_spec import PodSpec
from kubex_core.models.metadata import ObjectMetadata

NAMESPACE = "default"
LOCAL_PORT = 18080
HTTP_REQUEST = b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n"


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


async def demo_low_level(api: Api[Pod], pod_name: str) -> None:
    print("--- low-level forward() ---")
    async with api.portforward.forward(pod_name, ports=[80]) as pf:
        stream = pf.streams[80]
        with anyio.fail_after(10):
            await stream.send(HTTP_REQUEST)
            buf = bytearray()
            while True:
                try:
                    chunk = await stream.receive()
                    buf.extend(chunk)
                    if b"\r\n\r\n" in buf:
                        break
                except anyio.EndOfStream:
                    break
        print(buf.decode(errors="replace").split("\r\n")[0])


async def demo_high_level(api: Api[Pod], pod_name: str) -> None:
    print("--- high-level listen() ---")
    async with api.portforward.listen(pod_name, port_map={80: LOCAL_PORT}):
        async with await anyio.connect_tcp("127.0.0.1", LOCAL_PORT) as conn:
            with anyio.fail_after(10):
                await conn.send(HTTP_REQUEST)
                buf = bytearray()
                while True:
                    try:
                        chunk = await conn.receive()
                        buf.extend(chunk)
                        if b"\r\n\r\n" in buf:
                            break
                    except anyio.EndOfStream:
                        break
        print(buf.decode(errors="replace").split("\r\n")[0])


async def main() -> None:
    client = await create_client()
    async with client:
        api: Api[Pod] = Api(Pod, client=client, namespace=NAMESPACE)
        pod = await api.create(
            Pod(
                metadata=ObjectMetadata(generate_name="example-portforward-"),
                spec=PodSpec(
                    containers=[
                        Container(
                            name="main",
                            image="nginx:1.25",
                            ports=[ContainerPort(container_port=80)],
                        )
                    ]
                ),
            ),
        )
        pod_name = cast(str, pod.metadata.name)
        try:
            await _wait_for_running(api, pod_name)
            await demo_low_level(api, pod_name)
            await demo_high_level(api, pod_name)
        finally:
            await api.delete(pod_name)


if __name__ == "__main__":
    asyncio.run(main())
